
from typing import Dict, List, Optional, Union
import commune as c
import torch 
import traceback
import json




class ServerHTTP(c.Module):
    def __init__(
        self,
        module: Union[c.Module, object],
        name: str = None,
        network:str = 'local',
        port: Optional[int] = None,
        sse: bool = False,
        chunk_size: int = 42_000,
        max_request_staleness: int = 60, 
        max_workers: int = None,
        mode:str = 'thread',
        verbose: bool = False,
        timeout: int = 256,
        access_module: str = 'server.access',
        public: bool = False,
        serializer: str = 'serializer',
        new_event_loop:bool = True,
        save_history:bool= True,
        history_path:str = None 
        ) -> 'Server':

        self.serializer = c.module(serializer)()
        self.ip = c.default_ip # default to '0.0.0.0'
        self.port = int(port) if port != None else c.free_port()
        self.address = f"{self.ip}:{self.port}"
        self.max_request_staleness = max_request_staleness
        self.network = network
        self.verbose = verbose
        self.sse = sse
        self.save_history = save_history

        if self.sse == False:
            if max_workers != None:
                self.max_workers = max_workers
                self.mode = mode
                self.executor = c.executor(max_workers=max_workers, mode=mode)
                
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.public = public
        self.module = module 
        if new_event_loop:
            c.new_event_loop()

        # name 
        if name == None:
            if hasattr(self.module, 'server_name'):
                name = self.module.server_name
            else:
                name = self.module.__class__.__name__
        self.name = name


        self.key = module.key      
        # register the server
        module.ip = self.ip
        module.port = self.port
        module.address  = self.address
        self.access_module = c.module(access_module)(module=self.module)  
        self.history_path = history_path or f'history/{self.name}'

        self.set_api(ip=self.ip, port=self.port)


    def set_api(self, ip:str = '0.0.0.0', port:int = 8888):
        ip = self.ip if ip == None else ip
        port = self.port if port == None else port
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware

        self.app = FastAPI()
        self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        

        @self.app.post("/{fn}")
        def forward_api(fn:str, input:dict):
            """
            fn (str): the function to call
            input (dict): the input to the function
                data: the data to pass to the function
                    kwargs: the keyword arguments to pass to the function
                    args: the positional arguments to pass to the function
                    timestamp: the timestamp of the request
                    address: the address of the caller

                signature: the signature of the request

            """
            input['fn'] = fn
            # you can verify the input with the server key class
            if not self.public:
                assert self.key.verify(input), f"Data not signed with correct key"
            
            
            input['data'] = self.serializer.deserialize(input['data'])
            # here we want to verify the data is signed with the correct key
            request_staleness = c.timestamp() - input['data'].get('timestamp', 0)
            # verifty the request is not too old
            assert request_staleness < self.max_request_staleness, f"Request is too old, {request_staleness} > MAX_STALENESS ({self.max_request_staleness})  seconds old"
            
            self.access_module.verify(input)

            data = input['data']
            args = data.get('args',[])
            kwargs = data.get('kwargs', {})
            
            input_kwargs = dict(fn=fn, 
                                args=args, 
                                kwargs=kwargs)
            fn_name = f"{self.name}::{fn}"
            c.print(f'🚀 Forwarding {input["address"]} --> {fn_name} 🚀\033', color='yellow')


            try:
                result = self.forward(**input_kwargs)
                # if the result is a future, we need to wait for it to finish
            except Exception as e:
                result = c.detailed_error(e)
                
            if isinstance(result, dict) and 'error' in result:
                success = False 
            success = True


            if success:
                c.print(f'✅ Success: {self.name}::{fn} --> {input["address"]}... ✅\033 ', color='green')
            else:
                c.print(f'🚨 Error: {self.name}::{fn} --> {input["address"]}... 🚨\033', color='red')
            result = self.process_result(result)

            
            if self.save_history:
                path = self.history_path+'/' + str(input['data']['timestamp']) + '_' +input['address'] 
                input['result'] = result
                self.put(path, input)
            
            
            return result
        
        self.serve()

    @classmethod
    def history(cls, server='module', history_path='history'):
        dirpath  = f'{history_path}/{server}'
        return cls.ls(dirpath)
    
    @classmethod
    def all_history(cls,history_path='history'):
        dirpath  = f'{history_path}'
        return cls.glob(dirpath)
    
    @classmethod
    def rm_history(cls, server='module', history_path='history'):
        dirpath  = f'{history_path}/{server}'
        return cls.rm(dirpath)

    def state_dict(self) -> Dict:
        return {
            'ip': self.ip,
            'port': self.port,
            'address': self.address,
        }


    


    def process_result(self,  result):
        if self.sse:
            from sse_starlette.sse import EventSourceResponse

            # for sse we want to wrap the generator in an eventsource response
            result = self.generator_wrapper(result)
            return EventSourceResponse(result)
        else:
            # if we are not using sse, then we can do this with json
            if c.is_generator(result):
                result = list(result)
            result = self.serializer.serialize({'data': result})
            result = self.key.sign(result, return_json=True)
            return result
        
    
    def generator_wrapper(self, generator):
        if not c.is_generator(generator):   
            generator = [generator]
            
        for item in generator:
            # we wrap the item in a json object, just like the serializer does
            item = self.serializer.serialize({'data': item})
            item = self.key.sign(item, return_json=True)
            item = json.dumps(item)
            item_size = c.sizeof(item)
            if item_size > self.chunk_size:
                # if the item is too big, we need to chunk it
                item_hash = c.hash(item)
                chunks =[f'CHUNKSTART:{item_hash}'] + [item[i:i+self.chunk_size] for i in range(0, item_size, self.chunk_size)] + [f'CHUNKEND:{item_hash}']
                # we need to yield the chunks in a format that the eventsource response can understand
                for chunk in chunks:
                    yield chunk

            yield item


    def serve(self, **kwargs):
        import uvicorn

        try:
            c.print(f'\033🚀 Serving {self.name} on {self.address} 🚀\033')
            c.register_server(name=self.name, address = self.address, network=self.network)
            c.print(f'\033🚀 Registered {self.name} --> {self.ip}:{self.port} 🚀\033')
            uvicorn.run(self.app, host=c.default_ip, port=self.port)
        except Exception as e:
            c.print(e, color='red')
            c.deregister_server(self.name, network=self.network)
        finally:
            c.deregister_server(self.name, network=self.network)
        

    def forward(self, fn: str, args: List = None, kwargs: Dict = None, **extra_kwargs):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        obj = getattr(self.module, fn)
        if callable(obj):
            response = obj(*args, **kwargs)
        else:
            response = obj

        return response


    def __del__(self):
        c.deregister_server(self.name)



    def test(self):
        module_name = 'storage::test'
        module = c.serve(module_name, wait_for_server=True)
        module = c.connect(module_name)
        module.put("hey",1)
        c.kill(module_name)


