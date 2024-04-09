
import numpy as np
import commune as c

class TorchSerializer(c.Module):

    def bytes2str(self, x, **kwargs):
        return x.hex()    
    def str2bytes(self, x, **kwargs):
        return bytes.fromhex(x)

    def deserialize(self, data: dict) -> 'torch.Tensor':
        from safetensors.torch import load
        if isinstance(data, str):
            data = self.str2bytes(data)
        data = load(data)
        return data['data']

    def serialize(self, data: 'torch.Tensor') -> 'DataBlock':     
        from safetensors.torch import save
        output = save({'data':data})  
        return self.bytes2str(output)

    def bytes2torch(self, data:bytes, ) -> 'torch.Tensor':
        import torch
        numpy_object = self.serializer['numpy'].bytes2numpy(data)
        int64_workaround = bool(numpy_object.dtype == np.int64)
        if int64_workaround:
            numpy_object = numpy_object.astype(np.float64)
        torch_object = torch.tensor(numpy_object)
        if int64_workaround:
            dtype = torch.int64
        return torch_object
