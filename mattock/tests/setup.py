import os
from datetime import datetime
from pathlib import Path
import subprocess

from mattock.account import Account
from mattock.files import key_to_type19_path
from mattock.tests.test_data import BtreeFileSpec, DynFileSpec, HashFileSpec, NonHashFileSpec, test_files, dataset_getters

def which(s):
    res = subprocess.run(f"which {s}", shell=True, capture_output=True)
    if not res.returncode == 0:
        raise Exception(f"Non-zero return code {res.returncode} for which {s}")
    return res.stdout.strip()

mkdir = which("mkdir")
# uvsh = which("uvsh")
# execuv = which("execuv")
# uv = which("uv")

uvsh = "/usr/uv/bin/uvsh"
execuv = "/usr/uv/bin/execuv"
uv = "/usr/uv/bin/uv"
fnuxi = "/usr/uv/bin/fnuxi"

def writeFile(path:Path,contents):
    posix_path = path.as_posix()
    path.parent.mkdir(parents=True,exist_ok=True)
    fd = os.open(posix_path, os.O_CREAT ^ os.O_APPEND ^ os.O_WRONLY)
    os.write(fd,contents)
    os.close(fd)

def create_uv_account(test_path:Path):

    id = datetime.now().isoformat().replace(':','-')

    print(uvsh)

    print(f"Create test database in {test_path}")
    with subprocess.Popen([uvsh], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=test_path) as proc:

        if not proc.stdin or not proc.stdout:
            raise Exception("not proc.stdin or not proc.stdout")

        content = b""
        while True:
            content = content + proc.stdout.read(1)
            # print(content)

            if content == b'This directory is not set up for uniVerse.\nWould you like to set it up (Y/N)?':
                proc.stdin.write(b"Y\n")
                proc.stdin.flush()
                break

        content = b""
        while True:
            content = content + proc.stdout.read(1)
            # print(content)

            if content.endswith(b'Which way do you wish to configure your VOC ? '):
                proc.stdin.write(b"0\n")
                proc.stdin.flush()
                break            

        content = b""
        while True:
            content = content + proc.stdout.read(1)
            # print(content)

            if content.endswith(b'\n\n>'):
                proc.stdin.write(b"Q\n")
                proc.stdin.flush()
                break

    for (dataset_name, generate_data) in dataset_getters.items():

        print(f"Create type 19 file DS_{dataset_name}")

        create_result = subprocess.run([execuv,f"CREATE.FILE DS_{dataset_name} 19"], cwd=test_path, capture_output=True)
        print(f"create_result: ${create_result}")


        test_data = generate_data()
        for k in test_data:
            value = test_data[k]
            value = value.replace(b"\xfe",b"\r\n")
            # type1_path
            # record_path = key_to_type1_path(k)
            record_path = key_to_type19_path(k)
            path = Path(test_path).joinpath(f"DS_{dataset_name}",record_path)
            writeFile(path,value)

def create_file(test_path:Path, file_spec: NonHashFileSpec|HashFileSpec|DynFileSpec|BtreeFileSpec):

    file_name = str(file_spec)
    create_file_command = file_spec.create_file_command()
    machine_class = None
    if not isinstance(file_spec,NonHashFileSpec):
        machine_class = file_spec.machine_class

    print(f"Create file {file_name}")
    create_result = subprocess.run([execuv,create_file_command], cwd=test_path, capture_output=True)
    print(create_result)
    path = Account(test_path).get_filepath(file_name)
    if (path == None):
        raise Exception(f"{file_name} was not created successfully")
    print(f"Created file {file_name} with path {path}")

    populate_result = subprocess.run([execuv,f"ICOPY FROM DS_{file_spec.dataset_name} TO {file_name} ALL"], cwd=test_path, capture_output=True)
    print(populate_result)

    machine_class_option = None
    if machine_class == "big":
        machine_class_option = '-u'
    elif machine_class == "little":
        machine_class_option = '-x'
    if machine_class_option != None:
        convert_result = subprocess.run([fnuxi,machine_class_option,str(path)], cwd=test_path, capture_output=True)
        print(convert_result)


if __name__ == "__main__":

    test_path = Path(__file__).parent.joinpath("uvdb")

    create_uv_account(test_path)

    for file_spec in test_files:       
        create_file(test_path,file_spec)

    exit(0)