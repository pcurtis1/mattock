class Value:
    subvalues: list[bytes]

    def get(self, s_idx:int):
        return self.subvalues[s_idx] if s_idx < len(self.subvalues) else None

    def to_list(self):
        return self.subvalues
    
    def __init__(self, bytes:bytes):
        self.subvalues = [b for b in bytes.split(b"\xfc")]

class Field:
    values: list[Value]

    def get(self, v_idx:int, s_idx:int):
        return self.values[v_idx].get(s_idx) if v_idx < len(self.values) else None

    def to_list(self):
        return [v.to_list() for v in self.values]

    def __init__(self, bytes:bytes):
        self.values = [Value(b) for b in bytes.split(b"\xfd")]

class Record:
    key: bytes
    fields: list[Field]
    raw:bytes

    def get(self, f_idx: int, v_idx:int, s_idx:int):
        return self.fields[f_idx].get(v_idx, s_idx) if f_idx < len(self.fields) else None

    def to_list(self):
        return [f.to_list() for f in self.fields]

    def __init__(self, key:bytes, raw:bytes):
        self.raw = raw
        self.key = key
        self.fields = [Field(b) for b in raw.split(b"\xfe")]