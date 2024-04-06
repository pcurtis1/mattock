import os
from pathlib import Path
from stat import S_ISDIR

if __name__ == "__main__":

    test_path = Path(__file__).parent.joinpath("uvdb")

    if (test_path.exists() and S_ISDIR(test_path.lstat().st_mode)):
        print(f"Will delete files under path {test_path}")
        import shutil
        shutil.rmtree(test_path)
    os.mkdir(test_path)

    exit(0)