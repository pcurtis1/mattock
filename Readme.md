# Mattock

Mattock is a reference implementation of the various file formats of Rocket Universe based mostly on [this documentation](https://www.slideshare.net/rocketsoftware/universe-files)

Project goals:
- Zero dependencies (except for pytest in dev)
- All files supported including, Type 1 and Type 19 file support, static hashed files, dynamically hashed files and Btree files

Non-goals:
- Random record access for hashed files
- Online access

# Getting started

Print a summary of the files in an account

```
python -m mattock <path>
```

Open a file and iterate through the records

```python
from mattock.account import Account

with account.open_file(file_name) as f:
  for r in f.records():
    pass # do whatever you want here
```

[`__main__.py`](mattock/__main__.py) gives further details

# Development

## Testing

### Setup tests

```bash
bash mattock/tests/setup.sh
```

### Run tests

```bash
py.test
```

# Known issues

Not very efficient with memory. A `memoryview` implementation with lazier evaluation may be considerably faster.

