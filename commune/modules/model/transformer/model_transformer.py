from pprint import pp
import asyncio
from copy import deepcopy
from typing import Union, Optional, List
import os, sys
from typing import *
from loguru import logger
import torch
from torch import nn
import commune as c

# we are inheriting from the base model class which is a c.Module and a torch.nn.Module
Model = c.module('model')

class ModelTransformer(Model):
    default_config = c.config('model.transformer')
    shortcuts = default_config.shortcuts
    def __init__(self,
                 config = None,
                 **kwargs
                ):
        config = self.set_config(config=config, kwargs=kwargs)
        Model.init_model(self)
        self.set_model(config)
    
    
    def forward(self,  
                input_ids: Union[str, torch.Tensor], 
                attention_mask: torch.Tensor = None,
                return_keys:List[str] = ['topk', 'hidden_states'],
                topk:int=32,
                hidden_layer: int = -1, # -1 is the last hidden layer
                max_sequence_length : int = 256,                        
                **kwargs):


        if isinstance(input_ids, str) or isinstance(input_ids, list):
            input_ids = self.tokenize(input_ids)['input_ids']
        elif isinstance(input_ids, torch.Tensor):
            input_ids = input_ids

        # resolve the max sequence length (sometimes we want to clip the input to make it faster)
        attention_mask = attention_mask if isinstance(attention_mask, torch.Tensor) else torch.ones_like(input_ids)

        if max_sequence_length > self.config.max_sequence_length:
            max_sequence_length = self.config.max_sequence_length
            logger.warning(f"max_sequence_length is larger than the model's max_sequence_length. Clipping to {max_sequence_length}")
        
        sample = {
        'input_ids': input_ids[:, -max_sequence_length:],
        'attention_mask': attention_mask[:, -max_sequence_length:] if attention_mask is not None else None
        }

        # move to device for all tensors
        for k,v in sample.items():
            if isinstance(v, torch.Tensor):
                sample[k] = sample[k].to(self.device)
        
        
        # clip the input ids to the vocab size to avoid index errors
        sample['input_ids'] = torch.clip(sample['input_ids'], 0, self.tokenizer.vocab_size-1)
        
        output_hidden_states = 'hidden_states' in return_keys
        output_topk = 'topk' in return_keys

        # forward pass
        output = self.model(input_ids=sample['input_ids'].to(self.device),
                            output_hidden_states=output_hidden_states, **kwargs)
        

        if output_hidden_states:
            output['hidden_states'] = output.hidden_states[hidden_layer].detach()

        if output_topk:
            output['topk']=self.encode_topk(output['logits'].detach(), topk=topk)
        return {key:output[key] for key in return_keys}
        
    
    def encode(self, text:str, token_idx:int = None, **kwargs) -> torch.Tensor:
        kwargs['return_keys'] = ['hidden_states']
        sample  = self.tokenize(text)
        kwargs.update(sample)
        hidden_states = self.forward(**kwargs)['hidden_states']
        if isinstance(token_idx, int):
            return hidden_states[:,token_idx, :]
        else:
            return hidden_states
    
    embed = encode

    def set_model(self, config) -> None: 
        config.model = config.shortcuts.get(config.model, config.model)
        c.print('SETTING Tokenizer -> ', config.model)
        self.set_tokenizer(config.model)
        c.print('Tokenizer SET -> ', config.model)
        from transformers import  AutoModelForCausalLM, AutoModel
        from accelerate import init_empty_weights
        c.print('LOADING MODEL -> ', config.model)
        t = c.time()
        self.model = AutoModelForCausalLM.from_pretrained(config.model,
                                                            device_map= config.device_map,
                                                            max_memory=config.max_memory,
                                                            trust_remote_code=config.trust_remote_code,
                                                             offload_folder="offload", torch_dtype=torch.float16) 

        time_taken = c.time() - t       
        self.devices = config.devices = list(set(list(self.model.hf_device_map.values())))          
        c.print(f'MODEL LOADED ({time_taken}s) on {self.devices}', config.model)         
        self.set_optimizer(config.optimizer)
        self.set_finetune(config.finetune) 
        c.print('FINETUNE SET -> ', config.finetune)
        if config.load:
            self.load(keys=['model', 'optimizer'])     

        

    def set_tokenizer(self, tokenizer:str):
        from transformers import AutoTokenizer
        try:
            tokenizer = AutoTokenizer.from_pretrained(tokenizer, use_fast=True)
        except ValueError:
            
            print('resorting ot use_fast = False')
            tokenizer = AutoTokenizer.from_pretrained(tokenizer, use_fast=False)


        if not hasattr(tokenizer, 'pad_token') or tokenizer.pad_token is None:
            assert hasattr(tokenizer, 'eos_token') and tokenizer.eos_token is not None
            tokenizer.add_special_tokens({'pad_token': tokenizer.eos_token})
            
        self.tokenizer = tokenizer
                
        return self.tokenizer

    
    
    @staticmethod
    def encode_topk( forward_response_tensor: torch.Tensor , topk:int=4096) -> torch.Tensor:
        """ Returns topk tokens/probabilities given unnormalized logits as input. """

        #import ipdb; ipdb.set_trace()

        logits = forward_response_tensor  # unnormalized logit scores: [batch_size, sequence_len, vocab_size]
        probs = torch.softmax(logits, dim=-1).to(torch.float32)  # normalized probabilities: [batch_size, sequence_len, vocab_size]

        topk_indices = torch.argsort(probs, dim=-1, descending=True)[...,:topk]
        # topk_values, topk_indices = torch.topk(probs, topk) # topk probs and indices: [batch_size, sequence_len, topk]

        topk_values = probs.gather( index=topk_indices, dim=-1)
        encoded_probs = torch.cat([topk_values, topk_indices], dim=-1)  # [batch_size, sequence_len, topk + topk]
        return encoded_probs  # [batch_size, sequence_len, topk + topk]


    @staticmethod
    def decode_topk(  forward_response_tensor: torch.Tensor, topk=4096, vocab_size:int=50257) -> torch.Tensor:
        """ Returns full logits by decoding topk-encoding input. """
        batch_size, sequence_len, _ = forward_response_tensor.shape
        
        encoded_probs = forward_response_tensor  # encoded probabilities: [batch_size, sequence_len, topk + topk]
        topk_values = encoded_probs[..., :topk]  # topk probs: [batch_size, sequence_len, topk]
        topk_indices = encoded_probs[..., topk:].long()  # topk probs indices: [batch_size, sequence_len, topk]

        topk_pmass = topk_values.sum(dim=-1)  # topk probability mass: [batch_size, sequence_len]
        remainder_pmass = torch.clamp(1 - topk_pmass, 1e-40, 1)  # remainder probability mass: [batch_size, sequence_len]
        remainder_floor = remainder_pmass / (vocab_size - topk)  # divide remainder: [batch_size, sequence_len]

        logits = torch.ones((batch_size, sequence_len, vocab_size), dtype=topk_values.dtype).to(topk_values.device)
        logits *= torch.log(remainder_floor)[:, :, None]  # set probability floor: [batch_size, sequence_len, vocab_size]

        logits.scatter_(-1, topk_indices, torch.log(topk_values + 1e-40))  # insert topk probs: [batch_size, sequence_len, vocab_size]

        return logits  # [batch_size, sequence_len, vocab_size]


    def tokenizer_name(self):
        return self.config['tokenizer']

    def tokenize(self, 
                text: str = 'Whadup',
                padding=True, 
                truncation=True, 
                max_length=64,
                return_tensors='pt',
                add_special_tokens=False,
                device:str = None, 
                **kwargs) -> torch.Tensor:
        """ Returns tokenized text as torch tensor. """
        
        sample = self.tokenizer(text, padding=padding, 
                                    truncation=truncation, 
                                    max_length=max_length, 
                                    return_tensors=return_tensors,
                                    add_special_tokens=add_special_tokens, 
                                    **kwargs)  # assume tokenizer.padding_side = 'left'

        device = device if device != None else self.device
        
        sample = dict(
            input_ids= sample['input_ids'].to(device),
            attention_mask= sample['attention_mask'].to(device)
        )
        
        return sample



    def detokenize(self, input_ids: torch.Tensor, **kwargs) -> torch.Tensor:
        """ Returns tokenized text as torch tensor. """
        
        text = self.tokenizer.batch_decode(input_ids,**kwargs)  # assume tokenizer.padding_side = 'left'

        return text
    
    
    @classmethod
    def sample_check(cls, sample):
        return bool(isinstance(sample, dict) and 'input_ids' in sample)
    
    @classmethod
    async def async_get_sample(cls, dataset, max_trials=10, batch_size=1, sequence_length=64, num_batches=10):
        sample = None
        if not hasattr(cls, 'dataset_pool'):
            cls.dataset_pool = c.connect_pool(dataset)

        fail_count = 0
    
        while not cls.sample_check(sample) and fail_count < max_trials:
            if len(cls.dataset_pool) == 0:
                cls.dataset_pool = c.connect_pool(dataset)
            try:
                data_idx =cls.choice(list(range(len(cls.dataset_pool))))
                sample = cls.dataset_pool[data_idx].sample(batch_size=batch_size,
                                        sequence_length=sequence_length)
                
                if not cls.sample_check(sample):
                    raise Exception('Sample check failed')
                sample['input_ids'] = sample['input_ids'][:batch_size, -sequence_length:]
                
                
            except Exception as e:
                fail_count += 1
                del cls.dataset_pool[data_idx]
                cls.print(f'ERROR {e} failed to sample, removing dataset {data_idx}, {len(cls.dataset_pool)} remaining', color='red')
        assert cls.sample_check(sample), f'Failed to sample from {dataset} after {max_trials} trials.'
        return sample
    
    @classmethod
    def get_sample(cls, timeout=2, retries = 3, *args, **kwargs):
        try:
            if timeout:
                # Add timeout to the async_get_sample call
                coro = asyncio.wait_for(cls.async_get_sample(*args, **kwargs), timeout=timeout)
            else:
                coro = cls.async_get_sample(*args, **kwargs)
            
            return asyncio.run(coro)
        except asyncio.TimeoutError:
            # Handle the timeout error here
            print("Async function call timed out.")
            if retries > 0:
                return cls.get_sample(timeout=timeout, retries=retries-1, *args, **kwargs)
    
    
    
    @classmethod
    def resolve_model(cls, model, **kwargs):      
        if isinstance(model, str):
            if cls.exists(model):
                model  = cls.connect(model) 
            else:
                model = cls(model=model, **kwargs)
        elif isinstance(model, nn.Module):
            model = model
        elif isinstance(model, dict):
            model = cls(**model)
        elif model == None:
            model = cls()
        else:
            raise ValueError(f"Model type {type(model)} not supported.")
        
        
        return model
                

    @property
    def tag(self):
        if self.config.get('tag', None) == None:
            self.config['tag'] = 'base'
            
        return  self.config['tag']
    
    @tag.setter
    def tag(self, tag):
        self.config['tag'] = tag
        

    @classmethod
    def test_encode(cls, text=['encode, hey whadup fam how is it going']*4, num_samples:int=10):
        self = cls()
        t = cls.timer()
        for i in range(num_samples):
            cls.print(self.encode(text).shape)
            cls.print(num_samples/t.seconds, 'samples per second')

    
    

    @classmethod
    def serve(cls,
            model: str,
            tag = None,
            refresh = True,    
            **kwargs
            ):
        
        config = cls.get_config(kwargs=kwargs)
        config.tag = tag
        config.model = model
        config.pop('shortcuts', None)
        kwargs.update(
            {
                'tag': tag,
                'config': config,
                'refresh': refresh,
                'verbose': True,
                'module': cls.module_path(),
                'server_name': f'model.{model}'
            }
        )

        return c.serve(**kwargs)
        
    @classmethod
    def calculate_loss( cls, logits: torch.Tensor,
                    input_ids:torch.Tensor,
                    return_value = False,
                    **kwargs) -> torch.Tensor:
        '''
        Calculate the loss for the model.
        '''
        gt = input_ids[:, -(logits.shape[1]-1):].flatten()
        pred = logits[:, :-1]
            
        if len(pred.shape) == 3:
            pred = pred.reshape(-1, pred.shape[-1])
        
        assert gt.shape[0] == pred.shape[0], f'gt.shape: {gt.shape} pred.shape: {pred.shape}'

        loss_fn = torch.nn.CrossEntropyLoss()
        loss =  loss_fn(pred, gt.to(pred.device))
        
        # check if loss is nan
        if torch.isnan(loss):
            c.print('Loss is nan, skipping backward pass')
            train = False
            loss = torch.tensor(10)
            raise Exception('Loss is nan, skipping backward pass')
        
        if return_value:
            loss = loss.item()
        
        return loss


    def generate_stream(self, text: str, 
                max_length: int = 20, 
                max_new_tokens: int = None,
                min_length: int = 0, 
                min_new_tokens: int = None,
                early_stopping: bool = True,
                max_time: float = None,
                chunk_size: int = 10,
                **kwargs) -> List[str]:
        if isinstance(text, str):
            text = [text]

         
        input_ids = self.tokenize(text)['input_ids']
        for i in range(max_new_tokens):
            output_ids = self.model.generate(input_ids, 
                                            max_length=max_length, 
                                            max_new_tokens=chunk_size,
                                            min_length=min_length, 
                                            min_new_tokens=min_new_tokens,
                                            early_stopping=early_stopping,
                                            max_time=max_time, **kwargs)
            output_text = self.decode(output_ids)
            yield output_text
            text = output_text

    hf = c.module('huggingface')()
    def generate(self, text: str, 
                max_length: int = 20, 
                max_new_tokens: int = None,
                min_length: int = 0, 
                min_new_tokens: int = None,
                early_stopping: bool = True,
                max_time: float = None,
                stream:bool = False,
                **kwargs) -> List[str]:
        if stream:
            return self.generate_stream(text, 
                                        max_length=max_length, 
                                        max_new_tokens=max_new_tokens,
                                        min_length=min_length, 
                                        min_new_tokens=min_new_tokens,
                                        early_stopping=early_stopping,
                                        max_time=max_time, **kwargs)

        if isinstance(text, str):
            text = [text]

        input_ids = self.tokenize(text)['input_ids']
        output_ids = self.model.generate(input_ids.to(self.device), 
                                        max_length=max_length, 
                                        max_new_tokens=max_new_tokens,
                                        min_length=min_length, 
                                        min_new_tokens=min_new_tokens,
                                        early_stopping=early_stopping,
                                        max_time=max_time, **kwargs)
        output_text = self.detokenize(output_ids, skip_special_tokens=True)

        for t, ot in zip(text, output_text):
            output_text = ot.replace(t, '')


        return output_text
    

    
    @classmethod
    def test_generate(cls, *args, **kwargs):
        model = cls( *args, **kwargs)
        output_text = model.generate(text='Hello world',)

        return output_text