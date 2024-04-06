#!/bin/bash
sudo /usr/uv/bin/uv -admin -stop
python3 -m mattock.tests.clean
sudo /usr/uv/bin/uv -admin -start
python3 -m mattock.tests.setup
sudo /usr/uv/bin/uv -admin -stop