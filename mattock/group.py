from io import BufferedReader
from mattock.record import Record
from mattock.uv_file_info import UvFileInfo


class ReadItemResult:
    next_item_offset: int | None
    next_item_in_over30: bool
    record_buffer: bytes | None

    def __init__(self, next_item_offset: int | None, next_item_in_over30:bool, record_buffer: bytes | None) -> None:
        self.next_item_offset = next_item_offset
        self.next_item_in_over30 = next_item_in_over30
        self.record_buffer = record_buffer
        pass

class Group:
    groupIndex: int

    def __init__(self, groupIndex: int, info:UvFileInfo, fd: BufferedReader, over_30_fd: BufferedReader | None):
        self.groupIndex = groupIndex
        self.info = info
        self.fd = fd
        self.over_30_fd = over_30_fd
        
    def read_item_header(self, offset: int, in_over_30: bool = False):
        fd = self.fd

        if self.over_30_fd and in_over_30:
            fd = self.over_30_fd

        fd.seek(offset)
        if self.info.arch == '32':
            itemHeaderSize = 4*3
            itemHeader = fd.read(itemHeaderSize)
            forwardPointer = int.from_bytes(itemHeader[0:4],self.info.byteorder)
            blink = int.from_bytes(itemHeader[4:8],self.info.byteorder)
            flags = int.from_bytes(itemHeader[10:12],self.info.byteorder)
        else:
            itemHeaderSize = 8*3
            itemHeader = fd.read(itemHeaderSize)
            forwardPointer = int.from_bytes(itemHeader[0:8],self.info.byteorder)
            blink = int.from_bytes(itemHeader[8:16],self.info.byteorder)
            flags = int.from_bytes(itemHeader[18:20],self.info.byteorder)

        if (self.info.byteorder == 'little'):
            free_item = bool(flags & (1 << 1))
            record_padded = bool(flags & (1 << 5))
            new_style_padding = bool(flags & (1 << 4))
            forward_to_over30 = bool(flags & (1 << 13))
            oversized_item = bool(flags & (1 << 7))
            oversized_item_buffer = bool(flags & (1 << 6))
        else:
            free_item = bool(flags & (1 << 14))
            record_padded = bool(flags & (1 << 10))
            new_style_padding = bool(flags & (1 << 11))
            forward_to_over30 = bool(flags & (1 << 2))
            oversized_item = bool(flags & (1 << 8))
            oversized_item_buffer = bool(flags & (1 << 9))

        flags = (free_item, record_padded, new_style_padding, forward_to_over30, oversized_item, oversized_item_buffer)
            
        return (itemHeader, forwardPointer, blink, flags, itemHeaderSize)

    def read_item(self, offset:int, in_over_30:bool):

        (
            itemHeader,
            forwardPointer,
            blink,
            (
                free_item,
                record_padded,
                new_style_padding,
                forward_to_over30,
                oversized_item,
                oversized_item_buffer
            ),
            itemHeaderSize
        ) = self.read_item_header(offset, in_over_30=in_over_30)

        if (itemHeader == b""):
            return None
        
        is_last = not forwardPointer
        next_item_offset = forwardPointer or None
        next_item_in_over30 = forward_to_over30 or in_over_30

        if (free_item):
            if is_last:
                return None
            return ReadItemResult(
                next_item_offset,
                next_item_in_over30,
                record_buffer=None
            )

        current_buffer_index = (offset - self.info.header_length) // self.info.group_length
        current_buffer_offset = self.info.header_length + current_buffer_index * self.info.group_length
        next_buffer_offset = current_buffer_offset + self.info.group_length

        if forwardPointer:
            itemLength = forwardPointer - offset - itemHeaderSize

            if (forwardPointer <= current_buffer_offset) or (forwardPointer >= next_buffer_offset):
                itemLength = next_buffer_offset - offset - itemHeaderSize

        else:
            itemLength = next_buffer_offset - offset - itemHeaderSize

        # read record content
        fd = self.fd
        if self.over_30_fd and in_over_30:
            fd = self.over_30_fd

        record_buffer = b""
        if itemLength > 0:                
            record_buffer = fd.read(itemLength)
        

        # concat oversized data
        if oversized_item:

            if (self.info.arch == '32'):
                os_offset = int.from_bytes(record_buffer[0:4],self.info.byteorder)
                os_count = int.from_bytes(record_buffer[4:8],self.info.byteorder)
                record_buffer = record_buffer[8:]
            else:
                os_offset = int.from_bytes(record_buffer[0:8],self.info.byteorder)
                os_count = int.from_bytes(record_buffer[8:12],self.info.byteorder)
                record_buffer = record_buffer[12:]

            for i in range(os_count):
                os_item:ReadItemResult|None = self.read_item(os_offset,True)
                if (os_item):
                    if (os_item.record_buffer):
                        record_buffer = record_buffer + os_item.record_buffer
                    else:
                        pass
                    if not os_item.next_item_offset:
                        break
                    os_offset = os_item.next_item_offset
                else:
                    raise Exception("Expected os_item for oversized item")

            pass

        if (record_padded):
            padding_digits = record_buffer[-1]
            if padding_digits == 0:
                padding_digits = int.from_bytes(record_buffer[-8:],self.info.byteorder)
            record_buffer = record_buffer[:len(record_buffer) - padding_digits]

        return ReadItemResult(
            next_item_offset = next_item_offset,
            next_item_in_over30 = next_item_in_over30,
            record_buffer = record_buffer
        )


    def records(self):
        # yield next non-free item
        groupFileOffset = self.info.header_length + self.info.group_length * self.groupIndex
        
        state = ReadItemResult(
            next_item_offset = groupFileOffset,
            next_item_in_over30=False,
            record_buffer=None
        )

        while True:
            if state.next_item_offset == None:
                break

            state = self.read_item(state.next_item_offset,state.next_item_in_over30)
            
            if state == None:
                break

            if state.record_buffer:
                try:
                    keyMarkIndex = state.record_buffer.index(b"\xff")
                except ValueError as v:
                    raise v

                key = state.record_buffer[0:keyMarkIndex]
                content = state.record_buffer[keyMarkIndex + 1:]

                yield Record(key,content)
