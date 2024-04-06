
import codecs
from pathlib import Path

from mattock.files import open_uv_file


class Account:
    path: Path

    def __init__(self,path:Path):
        self.path = path
        pass

    def get_filepath(self,filename:str) -> Path | None:
        with self.open_voc() as f:
            for r in f.records():
                if r.key == codecs.encode(filename):
                    fields = r.raw.split(b"\xfe")
                    if not fields[0].decode("utf8").strip().startswith("F"):
                        print(r)
                        raise Exception("Tried to get file location of a non-FILE")
                    filepath = fields[1]
                    return self.path.joinpath(codecs.decode(filepath,"utf8"))
        return None

    def open_voc(self):
        return open_uv_file(self.path.joinpath("VOC"))

    def open_file(self,filename:str):
        path = self.get_filepath(filename)
        if path == None:
            raise Exception("File does not exist")
        return open_uv_file(path)
    
    def files(self):
        with self.open_voc() as voc:
            for record in voc.records():
                f0 = record.get(0,0,0)
                if f0 and f0.startswith(b"F"):
                    yield codecs.decode(record.key)
