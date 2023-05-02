

from concurrent.futures import ThreadPoolExecutor
import grpc
import json
import traceback
import threading
import uuid
import sys
import grpc
from types import SimpleNamespace
from typing import Tuple, List, Union
from grpc import _common
import sys
import os
import random
import asyncio
from copy import deepcopy
import commune
from .serializer import Serializer


class VirtualModule:
    def __init__(self, module: str ='ReactAgentModule', include_hiddden: bool = False):

        self.synced_attributes = []
        '''
        VirtualModule is a wrapper around a Commune module.
        
        Args:
            module (str): Name of the module.
            include_hiddden (bool): If True, include hidden attributes.
        '''
        if isinstance(module, str):
            import commune
            self.module_client = commune.connect(module)
            self.success = self.module_client.success
        else:
            self.module_client = module
        self.sync_module_attributes(include_hiddden=include_hiddden)
      
    def remote_call(self, remote_fn: str, *args, return_future= False, timeout=None, **kwargs):
        
    
        if return_future:
            return self.module_client.async_forward(fn=remote_fn, args=args, kwargs=kwargs, timeout=timeout)
        else:
            return self.module_client(fn=remote_fn, args=args, kwargs=kwargs, timeout=timeout)
            
    def sync_module_attributes(self, include_hiddden: bool = False):
        '''
        Syncs attributes of the module with the VirtualModule instance.
        
        Args:
            include_hiddden (bool): If True, include hidden attributes.
        '''
        from functools import partial
                
        for attr in self.module_client.server_functions:
            # continue if attribute is private and we don't want to include hidden attributes
            if attr.startswith('_') and (not include_hiddden):
                continue
            
            
            # set attribute as the remote_call
            setattr(self, attr,  partial(self.remote_call, attr))
            self.synced_attributes.append(attr)
            
            

    def __getattr__(self, key):

        if key in ['synced_attributes', 'module_client', 'remote_call', 'sync_module_attributes'] :
            return getattr(self, key)
        elif key in self.synced_attributes:
            return getattr(self, key)
        else:
            return  self.module_client(fn='getattr', args=[key])



class Client( Serializer, commune.Module):
    """ Create and init the receptor object, which encapsulates a grpc connection to an axon endpoint
    """
    default_ip = '0.0.0.0'
    
    def __init__( 
            self,
            ip: str ='0.0.0.0',
            port: int = 80 ,
            address: str = None,
            max_processes: int = 1,
            timeout:int = 4,
            loop: 'Loop' = None,
            key: 'Key' = None,
            network : 'Network' = None,
        ):
        self.set_network(network)     
        self.set_client(ip =ip,
                        port = port ,
                        max_processes = max_processes,
                        timeout = timeout,
                        loop = loop)
        
    
    def set_event_loop(self, loop: 'asyncio.EventLoop') -> None:
        try:
            loop = loop if loop else asyncio.get_event_loop()
        except RuntimeError as e:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        self.loop = loop
                
        
        
    def resolve_ip_and_port(self, ip, port) -> Tuple[str, int]:
        ip =ip if ip else self.default_ip
        
        
        if len(ip.split(":")) == 2:
            ip = ip.split(":")[0]
            port = int(ip.split(":")[1])

        assert isinstance(ip, str), f"ip must be a str, not {type(ip)}"
        assert isinstance(port, int), f"port must be an int, not {type(port)}"
            
        return ip, port
    def set_client(self,
            ip: str ='0.0.0.0',
            port: int = 80 ,
            max_processes: int = 1,
            timeout:int = 20,
            loop: 'asycnio.EventLoop' = None
            ):
        # if ip == commune.external_ip():
        #     ip = '0.0.0.0'
        from commune.server.proto  import ServerStub
        # hopeful the only tuple i output, tehe
        if len(ip.split(":")) ==2:
            ip, port = ip.split(":")
            port = int(port)
        self.ip, self.port = self.resolve_ip_and_port(ip=ip, port=port)
        self.set_event_loop(loop)
        channel = grpc.aio.insecure_channel(
            self.endpoint,
            options=[('grpc.max_send_message_length', -1),
                     ('grpc.max_receive_message_length', -1),
                     ('grpc.keepalive_time_ms', 100000)])

        
        stub = ServerStub( channel )
        self.channel = channel
        self.stub = stub
        self.client_uid = str(uuid.uuid1())
        self.semaphore = threading.Semaphore(max_processes)
        self.state_dict = _common.CYGRPC_CONNECTIVITY_STATE_TO_CHANNEL_CONNECTIVITY
        self.timeout = timeout
        

        self.sync_the_async(loop=self.loop)
        self.success = False
        self.set_server_functions()
        # self.print(f"Connected to {self.endpoint} with {max_processes} processes")


    def set_server_functions(self):
        self.server_functions = self.forward(fn='functions', args=[True])
        
        if isinstance(self.server_functions, list):  
            self.success = True
            self.server_functions += ['root_address', 'namespace']
        else:
            self.success = False
        
    
    @property
    def endpoint(self):
        return f"{self.ip}:{self.port}"


    def __call__(self, *args, **kwargs):
        try:
            return self.loop.run_until_complete(self.async_forward(*args, **kwargs))
        except TypeError:
            return self.loop.run_until_complete(self.async_forward(*args, **kwargs))
    def __str__ ( self ):
        return "Client({})".format(self.endpoint) 
    def __repr__ ( self ):
        return self.__str__()
    def __del__ ( self ):
        try:
            result = self.channel._channel.check_connectivity_state(True)
            if self.state_dict[result] != self.state_dict[result].SHUTDOWN: 
                loop = asyncio.get_event_loop()
                loop.run_until_complete ( self.channel.close() )
        except:
            pass    
    def __exit__ ( self ):
        self.__del__()

    def nonce ( self ):
        import time as clock
        r"""creates a string representation of the time
        """
        return clock.monotonic_ns()
        
    def state ( self ):
        try: 
            return self.state_dict[self.channel._channel.check_connectivity_state(True)]
        except ValueError:
            return "Channel closed"

    def close ( self ):
        self.__exit__()

    def sign(self):
        return 'signature'

    async def async_forward(
        self, 
        data: object = None, 
        metadata: dict = None,
        timeout: int = None,
        results_only = True,
        verbose=False,
        **kwargs
    ) :
        if timeout == None:
            timeout = self.timeout
            
        data = data if data else {}
        metadata = metadata if metadata else {}
        
        # the deepcopy is a hack to get around the fact that the data is being modified in place LOL
        kwargs, data, metadata = deepcopy(kwargs), deepcopy(data), deepcopy(metadata)
        
        data.update(kwargs)

        fn = data.get('fn', None)
        random_color = random.choice(['red','green','yellow','blue','magenta','cyan','white'])
        if verbose:
            self.print(f"SENDING --> {self.endpoint}::fn::({fn}), timeout: {timeout}",color=random_color)
        stats = {
            'time': {}
        }
        try:
            # Serialize the request
            t = commune.timer()
            grpc_request = self.serialize(data=data, metadata=metadata)
            stats['time']['serial'] = t.seconds
            
            # Send the request
            t = commune.timer()
            asyncio_future = self.stub.Forward(request = grpc_request, timeout = timeout)
            response = await asyncio_future
            stats['time']['fn'] = t.seconds
            
            
            # Deserialize the response
            t = commune.timer()
            response = self.deserialize(response)
            stats['time']['deserial'] = t.seconds
   
            if results_only:
                response = response['data']['result']
                    
        except grpc.RpcError as rpc_error_call:
            response = {'error': str(rpc_error_call)}
            # commune.print(f"Timeout Error: {response}", verbose=verbose,color='red')

        # =======================
        # ==== Timeout Error ====
        # =======================
        except asyncio.TimeoutError:
            response = {'error': str(rpc_error_call)}
            # commune.print(f"Timeout Error: {response}", verbose=verbose,color='red')
    
        # ====================================
        # ==== Handle GRPC Unknown Errors ====
        # ====================================
        except Exception as e:
            response = {'error': str(e)}
            
            # commune.print(f"GRPC Unknown Error: {response}", color='red')
        if verbose:
            # if isinstance(response, str):
            # if 'error' in response:
            #     self.print(f"ERROR {self.endpoint}::fn::({fn}), error: {response['error'][:100]}",color='red')
            self.print(f"SUCCESS <-- {self.endpoint}::fn::({fn}), time: {stats['time']} ",color=random_color)
                     
        
        return  response
    
    async_call = async_forward
    
    

    def sync_the_async(self, loop = None):
        for f in dir(self):
            if 'async_' in f:
                setattr(self, f.replace('async_',  ''), self.sync_wrapper(getattr(self, f), loop=loop))

    def sync_wrapper(self,fn:'asyncio.callable', loop = None) -> 'callable':
        '''
        Convert Async funciton to Sync.

        Args:
            fn (callable): 
                An asyncio function.

        Returns: 
            wrapper_fn (callable):
                Synchronous version of asyncio function.
        '''
        loop = loop if loop else self.loop
        def wrapper_fn(*args, **kwargs):
            return self.loop.run_until_complete(fn(*args, **kwargs))
        return  wrapper_fn

    def test_module(self):
        module = Client(ip='0.0.0.0', port=8091)
        import torch
        data = {
            'bro': torch.ones(10,10),
            'fam': torch.zeros(10,10)
        }

        st.write(module.forward(data=data))


    def virtual(self):
        module = VirtualModule(module = self)    
        # module.key = self.key
        # module.subspce = self.subspace   
        return module


if __name__ == "__main__":
    Client.test_module()

    # st.write(module)
