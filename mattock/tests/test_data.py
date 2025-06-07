import functools
from typing import Any, Literal, Union
import codecs

class NonHashFileSpec:
    def __init__(self,type:Literal[1]|Literal[19],dataset_name:str) -> None:
        self.type = type
        self.dataset_name = dataset_name
        pass

    def generate_data(self):
        return dataset_getters[self.dataset_name]()

    def __str__(self) -> str:
        return f"NONHASH_{self.type}_{self.dataset_name}"

    def create_file_command(self) -> str:
        return f"CREATE.FILE {self} {self.type}"

class BtreeFileSpec:
    def __init__(
            self,
            dataset_name:str,
            arch:Literal["64BIT"]|Literal["32BIT"],
            machine_class:Literal["little"]|Literal["big"],
    ) -> None:
        self.dataset_name = dataset_name
        self.arch = arch
        self.machine_class = machine_class
        pass

    def generate_data(self):
        return dataset_getters[self.dataset_name]()

    def __str__(self) -> str:
        return f"BT_{self.arch}_{self.machine_class[0].upper()}E_{self.dataset_name}"

    def create_file_command(self) -> str:
        return f"CREATE.FILE {self} 25 {self.arch}"

    
class HashFileSpec:
    """
    type is a value between 2 and 18
    """
    machine_class: Literal["little"]|Literal["big"]

    def __init__(
            self,
            type:int,
            modulus:int,
            separation:int,
            arch:Literal["64BIT"]|Literal["32BIT"],
            machine_class:Literal["little"]|Literal["big"],
            dataset_name:str,
    ) -> None:
        self.dataset_name = dataset_name
        self.type = type
        self.modulus = modulus
        self.separation = separation
        self.arch = arch
        self.machine_class = machine_class
        pass

    def generate_data(self):
        return dataset_getters[self.dataset_name]()

    def __str__(self) -> str:
        return f"STATHASH_{self.type}_{self.modulus}_{self.separation}_{self.arch}_{self.machine_class[0].upper()}E_{self.dataset_name}"
    
    def create_file_command(self) -> str:
        return f"CREATE.FILE {self} {self.type} {self.modulus} {self.separation} {self.arch}"

class DynFileSpec:
    """
    type is a value between 2 and 18
    """
    machine_class: Literal["little"]|Literal["big"]

    def __init__(
            self,
            modulus:int,
            group_size:int,
            arch:Literal["64BIT"]|Literal["32BIT"],
            alg:Literal["GENERAL"]|Literal["SEQ.NUM"],
            machine_class:Literal["little"]|Literal["big"],
            dataset_name:str,
    ) -> None:
        self.modulus = modulus
        self.group_size = group_size
        self.arch = arch
        self.alg = alg
        self.machine_class = machine_class
        self.dataset_name = dataset_name
        pass

    def generate_data(self):
        return dataset_getters[self.dataset_name]()

    def __str__(self) -> str:
        return f"DYNHASH_{self.alg[0]}_{self.modulus}_{self.group_size}_{self.arch}_{self.machine_class[0].upper()}E_{self.dataset_name}"

    def create_file_command(self) -> str:
        return f"CREATE.FILE {self} 30 MINIMUM.MODULUS {self.modulus} GROUP.SIZE {self.group_size} {self.alg} {self.arch}"

def combinations(l:list[Any]):
    c = []
    if (len(l) == 1):
        return [[l[0]]]
    for i in range(len(l)):
        choice = [l[i]]
        remaining = l[:i] + l[i+1:]
        comb_of_remaining = combinations(remaining)
        for r in comb_of_remaining:
            c.append(choice + r)
    return c

# key_combinations = ["".join(c) for c in combinations(list("LECT"))]
# hashes = [hash17(codecs.encode(c)) for c in key_combinations]

# print(hashes)

combos = combinations(["ABCD","EFGH","IJKL","MNOP","QRST"])
key_combinations = [functools.reduce(lambda a, b: a + b,c) for c in combos]

def get_test_data_empty():
    return {}

def get_test_data():
    test_data = {
        b"KEY1": b"Key1_value",
        b"KEY2": b"Key2_value",
        b"K?3": b"Key3_value",
        b"": b"Emptykey",
        b".": b"DotKey",
        b"?": b"QKey",
        b"/": b"Slashkey",

        b"Key_of_8": b"Key_of_8",
        b"Key_of__9": b"Key_of__9",
        b"Key_of__10": b"Key_of__10",
        b"Key_of___11": b"Key_of___11",
        b"Key_of____12": b"Key_of____12",

        b"This is a long key with more than 14": b"Long key",

        b"Large record": b"_".join([codecs.encode(str(i))+b": "+(b"U" * 100) for i in range(0,400)]),
        b"Large record": b"_".join([codecs.encode(str(i))+b": "+(b"U" * 100) for i in range(0,400)]) + b"1", # test padding

        b"Field marks converted": b"Field1\xfeField2",

        b"AAAAAAAA":b"AAAAAAAA",
        b"BBBBBBBB":b"BBBBBBBB",
        b"CCCCCCCC":b"CCCCCCCC",
        b"DDDDDDDD":b"DDDDDDDD",

        b"ABC02364298734256":b"ABC02364298734256",
        b"ABC023642/98734256":b"ABC0236429/8734256",

        b"H":b"H",
        b"H1":b"H1",
        b"H12":b"H12",
        b"H123":b"H123",
        b"H1234":b"H1234",
        b"H12345":b"H12345",
        b"H123456":b"H123456",
        b"H1234567":b"H1234567",
        b"H12345678":b"H12345678",
        b"H123456789":b"H123456789",

        (b"L" * 41):b"L"*(150-40),
    }

    # test for over.30
    for i in range(100):
        test_data[codecs.encode(f"many_{i}")] = b"UUUUUUUUUUUUUUUUUUUUUU"

    for i in range(41): # 41 is maximum key length of a Type 1 file on UNIX and Windows
        test_data[(i+1)*b"0"] = (b"X" * i) + b"O"*(150-2*i)

    for c in key_combinations:
        test_data[codecs.encode(c)] = b"UUUUUUUUUUUUUUUUUUUUUU"


    return test_data

def alpha_from_num(to_convert:int, base = 26):
    stack = []
    while to_convert > 0:
        l,r = (to_convert // base), to_convert % base
        to_convert = l
        stack.append(r)
    return b"".join([(i+1+64+32).to_bytes(1,'little') for i in reversed(stack)])

# btree_data = dict([(x.upper(),x) for x in [alpha_from_num(i, 13) for i in range(1)]])

dataset_getters = {
    "EMPTY": get_test_data_empty,
    "FULL": get_test_data,
    "SOME": lambda: {
        b"KEY1": b"KEY1_DATA"
    },
    "BTR1": lambda: dict([(x.upper(),x) for x in [alpha_from_num(i, 13) for i in range(1)]]),
    "BTR2": lambda: dict([(x.upper(),x) for x in [alpha_from_num(i, 13) for i in range(2)]]),
    "BTR10": lambda: dict([(x.upper(),x) for x in [alpha_from_num(i, 13) for i in range(10)]]),
    "BTR20": lambda: dict([(x.upper(),x) for x in [alpha_from_num(i, 13) for i in range(20)]]),
    "BTR100": lambda: dict([(x.upper(),x) for x in [alpha_from_num(i, 13) for i in range(100)]]),
    "BTR200": lambda: dict([(x.upper(),x) for x in [alpha_from_num(i, 13) for i in range(200)]]),
    "BTR1000": lambda: dict([(x.upper(),x) for x in [alpha_from_num(i, 13) for i in range(1000)]]),
    "BTR2000": lambda: dict([(x.upper(),x) for x in [alpha_from_num(i, 13) for i in range(2000)]]),
    
}

test_files:list[Union[NonHashFileSpec,HashFileSpec,DynFileSpec,BtreeFileSpec]] = [
    NonHashFileSpec(1,dataset_name="FULL"),
    NonHashFileSpec(19,dataset_name="FULL"),
    HashFileSpec(2,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(2,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="EMPTY"),
    HashFileSpec(3,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(4,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(5,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(6,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(7,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(8,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(9,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(10,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(11,modulus=97,separation=1,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(12,modulus=97,separation=1,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(13,modulus=97,separation=1,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(14,modulus=97,separation=1,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(15,modulus=97,separation=1,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(16,modulus=97,separation=1,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(17,modulus=97,separation=1,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(17,modulus=1,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(17,modulus=97,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(17,modulus=97,separation=2,arch="32BIT",machine_class='big',dataset_name="FULL"),
    HashFileSpec(17,modulus=1089733,separation=2,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(17,modulus=97,separation=4,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(17,modulus=97,separation=15,arch="32BIT",machine_class='little',dataset_name="FULL"),
    HashFileSpec(18,modulus=97,separation=1,arch="32BIT",machine_class='little',dataset_name="FULL"),
    #important edge case is dynamic file with modulus 1
    DynFileSpec(modulus=1,group_size=2,arch="32BIT",alg="GENERAL",machine_class='little',dataset_name="EMPTY"),
    DynFileSpec(modulus=1,group_size=2,arch="32BIT",alg="GENERAL",machine_class='little',dataset_name="FULL"),
    DynFileSpec(modulus=1,group_size=2,arch="32BIT",alg="SEQ.NUM",machine_class='little',dataset_name="FULL"),
    DynFileSpec(modulus=2,group_size=2,arch="32BIT",alg="GENERAL",machine_class='little',dataset_name="FULL"),
    DynFileSpec(modulus=2,group_size=2,arch="32BIT",alg="SEQ.NUM",machine_class='little',dataset_name="FULL"),
    DynFileSpec(modulus=97,group_size=2,arch="32BIT",alg="GENERAL",machine_class='little',dataset_name="FULL"),
    DynFileSpec(modulus=97,group_size=2,arch="32BIT",alg="SEQ.NUM",machine_class='little',dataset_name="FULL"),
    
    # BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="EMPTY"),
    # BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="SOME"),
    BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="BTR1"),
    BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="BTR2"),
    BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="BTR10"),
    BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="BTR20"),
    BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="BTR100"),
    BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="BTR200"),
    BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="BTR1000"),
    BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="BTR2000"),
    
    BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="EMPTY"),
    BtreeFileSpec(arch="32BIT",machine_class='little',dataset_name="FULL"),

    BtreeFileSpec(arch="32BIT",machine_class='big',dataset_name="EMPTY"),
    BtreeFileSpec(arch="32BIT",machine_class='big',dataset_name="FULL"),

]

test_files_map = dict([(str(f),f) for f in test_files])
test_files_keys = [k for k in test_files_map]

if __name__ == "__main__":
    
    d = dict([
            (dataset_name, dict([
                (codecs.decode(k), codecs.encode(v,'base64').decode().replace('\n',''))
                for (k, v) in generate_data().items()
            ]))
            for (dataset_name, generate_data) in dataset_getters.items()
        ])

    import json
    
    # print(d)
    
    print(json.dumps(d,indent=2))

    exit(0)