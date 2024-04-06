from pathlib import Path
import pytest

from mattock.account import Account
from mattock.files import DynamicHashedFile, StaticHashedFile, open_uv_file, key_to_type1_path, type1_path_to_key
from mattock.tests.test_data import BtreeFileSpec, DynFileSpec, HashFileSpec, NonHashFileSpec, test_files, test_files_keys
    
ap_invocations:int = 0

@pytest.fixture(params=test_files, ids=test_files_keys, scope="module")
def file(request):
    return request.param

def test_all_records_appear_enum(file:NonHashFileSpec|BtreeFileSpec|HashFileSpec|DynFileSpec):
    account_path = Path(__file__).parent.joinpath("uvdb")
    account = Account(account_path)

    file_path = account.get_filepath(str(file))

    assert file_path != None

    with open_uv_file(file_path) as uv_file:

        test_data = file.generate_data()
        processed = {}

        for r in uv_file.records():
            # for r in g.records():
            if r.key in processed:
                pytest.fail(f"{r.key} was found twice")
            try:
                value = test_data.pop(r.key)
                processed[r.key] = True
                if (value != r.raw):
                    pytest.fail(f"{r.key} in file is not the same as the test_data")    
            except KeyError:
                pytest.fail(f"{r.key} was in file but not in test_data")
        
        items_remaining = len(test_data.items())
        if items_remaining > 0:
            pytest.fail(f"{items_remaining} records of test_data were not in the file")

        print(file)




def test_all_records_accessible_random(file:NonHashFileSpec|BtreeFileSpec|HashFileSpec|DynFileSpec):
    account_path = Path(__file__).parent.joinpath("uvdb")
    account = Account(account_path)
    file_path = account.get_filepath(str(file))

    assert file_path != None

    test_data = file.generate_data()

    with open_uv_file(file_path) as uv_file:
        if isinstance(uv_file,StaticHashedFile):
            pytest.skip('Random access for StaticHashedFile is not supported')

        if isinstance(uv_file,DynamicHashedFile):
            pytest.skip('Random access for DynamicHashedFile is not supported')

        for [key,value] in test_data.items():
            uv_value = uv_file.get_record(key)
            assert uv_value == value

        

@pytest.mark.parametrize(
    "key,path",
    [
        pytest.param(
            b"",Path("?"), id="empty_key"
        ),
        pytest.param(
            b".",Path("?."), id="leading_dot"
        ),
        pytest.param(
            b"?",Path("??"), id="qmark"
        ),
        pytest.param(
            b"/",Path("?\\"), id="forward_slash"
        ),
        pytest.param(
            b"ABC023642/98734256",Path("ABC023642?\\987","34256"), id="escaped_must_not_exceed_14"
        ),
        pytest.param(
            b"K?3",Path("K??3"), id="contains_q_mark"
        ),
        pytest.param(
            b"K?3",Path("K??3"), id="contains_q_mark"
        ),
    ],
)
def test_file1_path_mapping(key,path):
    assert key_to_type1_path(key) == path
    assert type1_path_to_key(path) == key

