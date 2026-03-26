#!/bin/env python3

#
# This is a migration script to update from legacy version of MTC
#
import os
import sys
import subprocess
from myionctrl.myionctrl import run_migrations

requirements_path = "/usr/src/myionctrl/requirements.txt"
if os.path.isfile(requirements_path):
    args = ["pip3", "install", "-r", requirements_path]
    subprocess.run(args)
#end if

sys.path.insert(0, '/usr/bin/myionctrl')  # Add path to myionctrl module
sys.path.insert(0, '/usr/src/myionctrl')


if __name__ == '__main__':
    print('Found new version of myionctrl! Migrating!')
    run_migrations()
