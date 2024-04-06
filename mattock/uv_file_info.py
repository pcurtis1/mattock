from dataclasses import dataclass
from typing import Literal


@dataclass()
class UvFileInfo:
    byteorder: Literal["little"]|Literal["big"]
    arch: Literal["32", "64"]
    file_type: int
    modulus: int
    separation: int
    group_length: int
    header_length: int
    dyn_hash_alg: int | None
