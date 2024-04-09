import commue as c

class BytesSerializer(c.Module):
    def serialize(self, data: dict) -> bytes:
        return c.bytes2str(data)
        
    def deserialize(self, data: bytes) -> 'DataBlock':
        if isinstance(data, str):
            data = c.str2bytes(data)
        return data