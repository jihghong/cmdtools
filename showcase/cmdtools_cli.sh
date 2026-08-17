#!/usr/bin/env bash
set +e

echo "## Help"
python showcase/cmdtools_cli.py -h
python showcase/cmdtools_cli.py -h add
python showcase/cmdtools_cli.py -h greet
python showcase/cmdtools_cli.py add -h
python showcase/cmdtools_cli.py --help echo

echo "## Success"
python showcase/cmdtools_cli.py greet Alice
python showcase/cmdtools_cli.py add 2 3
python showcase/cmdtools_cli.py echo text=hello
python showcase/cmdtools_cli.py overview
python showcase/cmdtools_cli.py shift for robot1.[0]
python showcase/cmdtools_cli.py reboot robot1

echo "## Dry-run"
python showcase/cmdtools_cli.py dry_check greet,Bob
python showcase/cmdtools_cli.py dry_check add
python showcase/cmdtools_cli.py dry_check shift,for,robot1.[9]
python showcase/cmdtools_cli.py dry_check unknown

echo "## User Errors"
python showcase/cmdtools_cli.py nope
python showcase/cmdtools_cli.py add
python showcase/cmdtools_cli.py add =1
python showcase/cmdtools_cli.py add c=1
python showcase/cmdtools_cli.py add a=1 a=2
python showcase/cmdtools_cli.py add a=1 2
python showcase/cmdtools_cli.py add 1 2 3
python showcase/cmdtools_cli.py add x
python showcase/cmdtools_cli.py version 1 for all
python showcase/cmdtools_cli.py overview for
python showcase/cmdtools_cli.py greet for robot1
python showcase/cmdtools_cli.py reboot robot1 robot2
python showcase/cmdtools_cli.py overview for robot1.[0]
python showcase/cmdtools_cli.py shift for robot1.[x]
python showcase/cmdtools_cli.py overview for robot9
python showcase/cmdtools_cli.py shift for ghost
python showcase/cmdtools_cli.py shift for dup
python showcase/cmdtools_cli.py shift for robot1.[9]
python showcase/cmdtools_cli.py shift for self
python showcase/cmdtools_cli.py shift for self.[0]
python showcase/cmdtools_cli.py simulate empty_command
python showcase/cmdtools_cli.py simulate missing_target
python showcase/cmdtools_cli.py simulate all_requires_all
python showcase/cmdtools_cli.py simulate self_not_main
python showcase/cmdtools_cli.py simulate self_not_sub
python showcase/cmdtools_cli.py simulate sub_targets_not_supported
