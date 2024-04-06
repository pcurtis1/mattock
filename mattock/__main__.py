from pathlib import Path
from mattock.account import Account
import sys

from mattock.files import File1, File19, U2ReadError, U2ReadException

help_text = """
Mattock reads Universe and Unidata databases

Usage:

python -m mattock [--keys|--values] <path>

    path:
        The path of a U2 database containing a VOC file
    --keys:
        Print record keys
    --values:
        Print record keys and values

"""

if len(sys.argv) == 2:
    path = Path(sys.argv[1])
    print_summary = True
    print_keys = False
    print_values = False
elif len(sys.argv) == 3:
    path = Path(sys.argv[2])
    opt = sys.argv[1]
    if opt == "--keys":
        print_summary = False
        print_keys = True
        print_values = False
    elif opt == "--values":
        print_summary = False
        print_keys = True
        print_values = False
    else:
        print(help_text)
        exit(1)

else:
    print(help_text)
    exit(1)
if not path.is_dir():
    raise Exception(f"Not a directory: {path}")
else:
    account = Account(path)
    for file_name in account.files():
        
        rec_count = 0
        byte_count = 0
        try:
            with account.open_file(file_name) as f:
                for r in f.records():
                    rec_count = rec_count + 1
                    byte_count = byte_count + len(r.key) + len(r.raw)
                    if print_keys:
                        if print_values:
                            print(f"{file_name} has record {r.key} with value {r.raw}")
                        else:
                            print(f"{file_name} has record {r.key}")

            if print_summary:
                if isinstance(f,File1):
                    print(f"{file_name} (1) has {rec_count} records and {byte_count} bytes")
                elif isinstance(f,File19):
                    print(f"{file_name} (19) has {rec_count} records and {byte_count} bytes")
                else:
                    print(f"{file_name} ({f.info.file_type}) has {rec_count} records and {byte_count} bytes")

        except U2ReadException as e:
            if e.error_code != U2ReadError.FILE_NOT_FOUND:
                raise e
