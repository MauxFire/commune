# import nest_asyncio
# nest_asyncio.apply()
import commune as c
c.new_event_loop()
import bittensor
import streamlit as st
import torch
from typing import Dict, List, Union, Any
import random
from copy import deepcopy
import pandas as pd
import asyncio
from munch import Munch
from bittensor.utils.tokenizer_utils import prep_tokenizer, get_translation_map, translate_logits_to_probs_std, \
    translate_special_token_text, pad_offsets, topk_token_phrases, compact_topk_token_phrases

from torch import nn


class Validator(c.Module):

    def __init__(self, 
                 config = None,
                 subspace = None,
                 **kwargs
                 ):
        config = self.set_config(config=config,kwargs=kwargs)
        self.set_models(config)
        self.set_dataset(config.dataset)
        self.set_tokenizer(config.tokenizer)
        self.subspace = c.module('subspace')()
        self.weights = nn.Parameter(torch.ones(5))



if __name__ == '__main__':
    Validator.run()

        
