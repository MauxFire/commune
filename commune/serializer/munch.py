
import commune as c
from munch import Munch
class MunchSerializer(c.Module):

    
    def dict2str(self, data:dict) -> bytes:
        try:
            data_json_str = json.dumps(data)
        except Exception as e:
            c.print(data)
            raise e
        return data_json_str

    def serialize(self, data: dict) -> str:
        data=self.munch2dict(data)
        data = self.dict2str(data=data)
        return  data

    def deserialize(self, data: bytes) -> 'Munch':
        return self.dict2munch(self.str2dict(data))


    def munch2dict(self, x:Munch, recursive:bool=True)-> dict:
        '''
        Turn munch object  into dictionary
        '''
        if isinstance(x, Munch):
            x = dict(x)
            for k,v in x.items():
                if isinstance(v, Munch) and recursive:
                    x[k] = munch2dict(v)

        return x 



    def bytes2dict(self, data:bytes) -> dict:
        import msgpack
        json_object_bytes = msgpack.unpackb(data)
        return json.loads(json_object_bytes)