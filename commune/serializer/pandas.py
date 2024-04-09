
import commune as c
import json

class PandasSerializer(c.Module):

    def serialize(self, data: 'pd.DataFrame') -> 'DataBlock':
        data = data.to_json()
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        return data
    
    def deserialize(self, data: bytes) -> 'pd.DataFrame':
        import pandas as pd
        data = pd.DataFrame.from_dict(json.loads(data))
        return data

    def test(self):
        import pandas as pd
        data = pd.DataFrame([{'a': [1,2,3], 'b': [4,5,6]}])
        serialized = self.serialize(data)
        c.print(serialized)
        deserialized = self.deserialize(serialized)
        c.print(deserialized)
        assert data.to_json()==deserialized.to_json()
        return {'success': True, 'data': data, 'deserialized': deserialized}
        
