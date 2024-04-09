
import commune as c
import numpy as np

class NumpySerializer(c.Module):

    
    def bytes2numpy(self, data:bytes) -> np.ndarray:
        import msgpack_numpy
        import msgpack
        output = msgpack.unpackb(data, object_hook=msgpack_numpy.decode)
        return output

    def numpy2bytes(self, data:np.ndarray)-> bytes:
        import msgpack_numpy
        import msgpack
        output = msgpack.packb(data, default=msgpack_numpy.encode)
        return output
    

    def bytes2str(self, data: bytes, mode: str = 'utf-8') -> str:
        if hasattr(data, 'hex'):
            return data.hex()
        else:
            return bytes.decode(data, mode)
    

    def serialize(self, data: 'np.ndarray') -> 'np.ndarray':     
        data =  self.numpy2bytes(data)
        return self.bytes2str(data)

    def deserialize(self, data: bytes) -> 'np.ndarray':     
        if isinstance(data, str):
            data = self.str2bytes(data)
        return self.bytes2numpy(data)

