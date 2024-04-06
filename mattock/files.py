import codecs
from dataclasses import dataclass
from enum import Enum
from io import BufferedReader
from pathlib import Path
from stat import S_ISREG
from typing import Any, Generator

from mattock.group import Group
from mattock.record import Record
from mattock.uv_file_info import UvFileInfo

def type1_escape_unix(s:bytes):
    if len(s) == 0:
        return b"?"
    s = s.replace(b"?",b"??")
    s = s.replace(b"/",b"?\\")

    if s[0:1] == b".":
        s = b"?" + s

    return s

def type1_unescape_unix(s:str):
    if len(s) == 0:
        raise Exception("This should never happen because an empty key will be encoded to ?")
    if s == "?":
        return ""
    if s == "?0":
        return ""
    if (len(s) > 1):
        if s[:2] == "?.":
            s = s[1:]

    s = s.replace("?\\","/")
    s = s.replace("??","?")

    return s

def key_to_type1_path(key:bytes):
    parts = [key]
    last = parts[-1]
    while True:
        escaped_left: bytes | None = None
        right: bytes | None = None
        for len0 in reversed(range(14)):
            len_ = len0 + 1
            left = last[:len_]
            right = last[len_:]

            escaped_left = type1_escape_unix(left)
            if len(escaped_left) > 14:
                continue
            else:
                break

        if escaped_left == None or right == None:
            raise Exception("escaped_left == None or right == None") # this should never happen, just here for type safety

        if len(right) > 0:
            parts[-1] = escaped_left
            parts.append(right)
            last = parts[-1]
        else:
            parts[-1] = escaped_left
            if len(escaped_left) == 14:
                parts.append(type1_escape_unix(b""))
            break
  
    return Path(*[codecs.decode(p) for p in parts])

def key_to_type19_path(key:bytes):  
    return Path(codecs.decode(type1_escape_unix(key)))


def type1_path_to_key(path:Path)->bytes:
    return b"".join([codecs.encode(type1_unescape_unix(p)) for p in path.parts])

class File1:

    def __init__(self,path:Path) -> None:
        self.path = path
        self.is_valid = S_ISREG(self.path.joinpath(".Type1").lstat().st_mode)
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def get_record(self,key:bytes) -> bytes:
        path = self.path.joinpath(key_to_type1_path(key))
        return path.read_bytes().replace(b"\r\n",b"\xfe")   
    
    def records(self):
        for file in self.path.rglob("*"):
            if (file.is_dir()):
                continue

            if file.name == ".Type1":
                continue

            if (file.is_file()):
                relative_path = file.relative_to(self.path)
                key = type1_path_to_key(relative_path)
                yield Record(key,file.read_bytes().replace(b"\r\n",b"\xfe"))

class File19:

    def __init__(self,path:Path) -> None:
        self.path = path
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def get_record(self,key:bytes) -> bytes:
        path = self.path.joinpath(key_to_type19_path(key))
        return path.read_bytes().replace(b"\r\n",b"\xfe")   
    
    def records(self):
        for file in self.path.iterdir():
            if (file.is_dir()):
                continue

            if file.name == ".Type1":
                continue

            if (file.is_file()):
                relative_path = file.relative_to(self.path)
                key = type1_path_to_key(relative_path)
                yield Record(key,file.read_bytes().replace(b"\r\n",b"\xfe"))


def read_file_header(fd:BufferedReader):
    headerBuf = fd.read(1024)

    is_machine_class_le = headerBuf[2:4] == b'\xef\xac'
    if not is_machine_class_le:
        byteorder = 'big'
        arch_byte = headerBuf[2]
        revision = headerBuf[3]
    else:
        byteorder = 'little'
        arch_byte = headerBuf[1]
        revision = headerBuf[0]

    if (arch_byte == 1):
        arch = '32'
        file_type = int.from_bytes(headerBuf[4:8],byteorder)
        modulus = int.from_bytes(headerBuf[12:16],byteorder)
        if (file_type == 30):
            modulus = int.from_bytes(headerBuf[0x24:0x28],byteorder)
        separation = int.from_bytes(headerBuf[16:20],byteorder)

    else:
        arch = '64'
        file_type = int.from_bytes(headerBuf[4:8],byteorder)
        modulus = int.from_bytes(headerBuf[8:16],byteorder)
        if (file_type == 30):
            modulus= int.from_bytes(headerBuf[0x20:0x28],byteorder)
        separation = int.from_bytes(headerBuf[16:20],byteorder)

    dyn_hash_alg = int.from_bytes(headerBuf[0x48:0x4c],byteorder)

    if not revision == 0x0c:
        raise U2ReadException(U2ReadError.UNSUPPORTED_REVISION)

    group_length = separation * 512
    even_separation = (separation % 2) == 0
    header_length = separation * 512 if even_separation else 1024

    return UvFileInfo(
        byteorder,
        arch,
        file_type,
        modulus,
        separation,
        group_length,
        header_length,
        dyn_hash_alg,
    )

class StaticHashedFile:
    fd: BufferedReader
    info: UvFileInfo

    def __init__(self,fd:BufferedReader,info:UvFileInfo):
        self.fd = fd
        self.info = info

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.fd.close()

    def groups(self):
        for group_index in range(self.info.modulus):
            group = Group(group_index, self.info, self.fd, None)
            yield group

    def records(self):
        for group in self.groups():
            for record in group.records():
                yield record


class DynamicHashedFile:
    fd: BufferedReader
    info: UvFileInfo
    dyn_hash_alg: int

    def __init__(self,fd:BufferedReader,over_30_fd:BufferedReader,info:UvFileInfo):
        self.fd = fd
        self.over_30_fd = over_30_fd
        self.info = info
        if info.dyn_hash_alg == None:
            raise Exception("info.dyn_hash_alg == None")
        self.dyn_hash_alg = info.dyn_hash_alg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.fd.close()
        self.over_30_fd.close()

    def groups(self):
        for group_index in range(self.info.modulus + 1):
            group = Group(group_index, self.info, self.fd, self.over_30_fd)
            yield group

    def records(self):
        for group in self.groups():
            for record in group.records():
                yield record

class BTreeLeaf:
    def __init__(self,buf:bytes, info: UvFileInfo, fd: BufferedReader):
        self.buf = buf
        self.info = info
        self.fd = fd

    def read_oversize(self,offset:int):
        self.fd.seek(offset)
        page = self.fd.read(self.info.group_length)
        page_type = int.from_bytes(page[0:2],self.info.byteorder)
        if page_type != 8:
            raise Exception("Expected oversize page_type to be 8 but was ${page_type}")
        
        if self.info.arch == "32":
            next_offset = int.from_bytes(page[4:8],self.info.byteorder)
            length = int.from_bytes(page[8:12],self.info.byteorder)
            buf = page[12:12+length]
        else:
            length = int.from_bytes(page[4:8],self.info.byteorder)
            next_offset = int.from_bytes(page[8:16],self.info.byteorder)
            buf = page[16:16+length]

        return (next_offset,buf)
    
    def get_record(self,key:bytes) -> bytes | None:
        for r in self.records():
            if r.key == key:
                return r.raw
        return None

    def records(self) -> Generator[Record, Any, None]:
        page = self.buf

        if self.info.arch == "32":
            data_list_offset = 0x0e
            lengths_offset = 0x0e + 0x100
            data_offset = 0x0e + 0x200
            data_size = int.from_bytes(page[2:4],self.info.byteorder)
            data_items = int.from_bytes(page[0x0c:0x0e],self.info.byteorder)
        else:
            data_list_offset = 0x1a
            lengths_offset = 0x11a
            data_offset = 0x21a
            data_size = int.from_bytes(page[2:4],self.info.byteorder)
            data_items = int.from_bytes(page[0x18:0x1a],self.info.byteorder)

        item_order = 0

        for i in range(data_items):
            item_offset = int.from_bytes(page[data_list_offset + i  * 2:data_list_offset + (i + 1) * 2],self.info.byteorder)
            item_length = int.from_bytes(page[lengths_offset + i  * 2:lengths_offset + (i + 1) * 2],self.info.byteorder)
            item_bytes = page[data_offset + item_offset:data_offset + item_offset + item_length]
            padding = item_bytes[-1]

            if self.info.byteorder == 'little':
                if item_bytes[0] < item_order:
                    raise Exception("Btree leaf records are out of order")
                item_order = item_bytes[0]
                item_flags = item_bytes[1]

            else:
                if item_bytes[1] < item_order:
                    raise Exception("Btree leaf records are out of order")
                item_order = item_bytes[1]
                item_flags = item_bytes[0]

            if not(item_flags & (1 << 5)):
                padding = 0
            oversize = item_flags & (1 << 6)


            item_bytes = item_bytes[2:len(item_bytes)-padding]

            oversize_buf = b""

            if oversize:
                if self.info.arch == "32":
                    next_offset = int.from_bytes(item_bytes[:4],self.info.byteorder)
                    item_bytes = item_bytes[4:]
                else:
                    next_offset = int.from_bytes(item_bytes[:8],self.info.byteorder)
                    item_bytes = item_bytes[8:]
                while next_offset > 0:
                    (next_offset,buf) = self.read_oversize(next_offset)
                    oversize_buf = oversize_buf + buf

            keylen = item_bytes.find(b'\xff')
            (key, value) = (item_bytes[:keylen],item_bytes[keylen+1:])
            value = value + oversize_buf
            yield Record(key,value)

class BTreeParent:
    def __init__(self,buf:bytes,info: UvFileInfo, fd: BufferedReader):
        self.buf = buf
        self.info = info
        self.fd = fd

    def child_group_indices(self):
        page = self.buf 
        
        if self.info.arch == "32":

            key_offset_list_offset = 0x6 + 0x600
            key_length_list_offset = 0x6 + 0x600 + 0x300
            key_data_offset = 0x6 + 0x600 + 0x300 + 0x300
            key_offset_list_length = int.from_bytes(page[2:4],self.info.byteorder)
            key_offset_list_count = int.from_bytes(page[key_offset_list_offset-2:key_offset_list_offset],self.info.byteorder)

            item_order = 0

            for i in range(key_offset_list_count + 1):
                child_offset = int.from_bytes(page[4 + i*4:4 + (i+1)*4],self.info.byteorder)
                group_index = (child_offset - self.info.header_length) // self.info.group_length

                key_offset = int.from_bytes(page[key_offset_list_offset + 2*i:key_offset_list_offset+2*(i+1)],self.info.byteorder)
                key_length = int.from_bytes(page[key_length_list_offset + i*2:key_length_list_offset + (i + 1)*2],self.info.byteorder)
                key_data = page[key_data_offset + key_offset:key_data_offset + key_offset + key_length]
                
                if not len(key_data):
                    yield (group_index,None)
                else:
                    if key_data[0] < item_order:
                        raise Exception("Btree index entries are out of order")
                    item_order = key_data[0]
                    key_data = key_data[2:]

                    yield (group_index,key_data)

        else:

            key_offset_list_offset = 0xa + 0xc00
            key_length_list_offset = 0xa + 0xc00 + 0x300
            key_data_offset = 0xa + 0xc00 + 0x300 + 0x300
            key_offset_list_length = int.from_bytes(page[2:4],self.info.byteorder)
            key_offset_list_count = int.from_bytes(page[key_offset_list_offset-2:key_offset_list_offset],self.info.byteorder)

            item_order = 0

            for i in range(key_offset_list_count + 1):
                child_offset = int.from_bytes(page[8 + i*8:8 + (i+1)*8],self.info.byteorder)
                group_index = (child_offset - self.info.header_length) // self.info.group_length

                key_offset = int.from_bytes(page[key_offset_list_offset + 2*i:key_offset_list_offset+2*(i+1)],self.info.byteorder)
                key_length = int.from_bytes(page[key_length_list_offset + i*2:key_length_list_offset + (i + 1)*2],self.info.byteorder)
                key_data = page[key_data_offset + key_offset:key_data_offset + key_offset + key_length]

                if not len(key_data):
                    yield (group_index,None)
                else:
                    if key_data[0] < item_order:
                        raise Exception("Btree index entries are out of order")
                    item_order = key_data[0]
                    key_data = key_data[2:]

                    yield (group_index,key_data)


    def get_record(self,key:bytes) -> bytes | None:
        for (i,i_key) in self.child_group_indices():
            if i_key == None or key <= i_key:
                buffer = BtreeBuffer(i, self.info, self.fd)
                child = buffer.read_buffer()
                return child.get_record(key)
        return None

    def records(self)-> Generator[Record, Any, None]:
        for (i,_) in self.child_group_indices():
            buffer = BtreeBuffer(i, self.info, self.fd)
            child = buffer.read_buffer()
            for record in child.records():
                yield record

class BtreeBuffer:
    group_index: int
    info: UvFileInfo
    fd: BufferedReader

    def __init__(self, group_index:int, info: UvFileInfo, fd: BufferedReader):
        self.group_index = group_index
        self.info = info
        self.fd = fd
  
    def read_buffer(self):
        group_offset = self.info.header_length + self.info.group_length * self.group_index
        self.fd.seek(group_offset)
        page = self.fd.read(self.info.group_length)
        page_type = int.from_bytes(page[0:2],self.info.byteorder)
        if page_type == 2:
            return BTreeLeaf(page, self.info, self.fd)
        elif page_type == 1:
            return BTreeParent(page, self.info, self.fd)
        else:
            raise Exception(f"Not implemented page type {page[0]}")


    def records(self):
        buffer = self.read_buffer()
        if not (isinstance(buffer, BTreeLeaf) or isinstance(buffer, BTreeParent)):
            raise Exception("Btree root should be either a leaf or a tree")
        for record in buffer.records():
            yield record

class BtreeFile:
    fd: BufferedReader
    info: UvFileInfo

    def __init__(self,fd:BufferedReader, info:UvFileInfo):
        self.fd = fd
        self.info = info

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.fd.close()

    def records(self):
        root = BtreeBuffer(0, self.info, self.fd)
        for record in root.records():
            yield record

    def get_record(self,key:bytes) -> bytes | None:
        root = BtreeBuffer(0, self.info, self.fd)
        return root.read_buffer().get_record(key)
    
def open_uv_file(path:Path):
    if not path.exists():
        raise U2ReadException(U2ReadError.FILE_NOT_FOUND)

    if path.is_file():
        # if the path is a file then it's probably a static hashed file. Try to read it.

        fd = path.open("rb")
        info = read_file_header(fd)
        if isinstance(info,UvFileInfo):
            if info.file_type != 25:
                return StaticHashedFile(fd,info)
            else:
                return BtreeFile(fd,info)
        else:
            fd.close()
        
        # could also be a B-Tree

    if path.is_dir():
        if path.joinpath(".Type1").is_file():
            return File1(path)

        if path.joinpath(".Type30").is_file():
            fd = path.joinpath("DATA.30").open("rb")
            info = read_file_header(fd)
            if isinstance(info,UvFileInfo):
                return DynamicHashedFile(
                    fd,
                    path.joinpath("OVER.30").open("rb"),
                    info
                )
            else:
                fd.close()

        # if neither of the above then treat it as a type 19
        return File19(path)

    raise Exception("I don't know what to do")

class U2ReadError(Enum):
    MACHINE_CLASS_BE_UNSUPPORTED = 1
    UNSUPPORTED_REVISION = 2
    UNSUPPORTED_ARCH = 3
    FILE_NOT_FOUND = 3

@dataclass
class U2ReadException(Exception):
    error_code:U2ReadError