#!/usr/bin/env python3
"""CLI wrapper for ctx-packer-init script."""

import subprocess
import sys
import os


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    init_script = os.path.join(script_dir, "scripts", "init.sh")

    result = subprocess.run(
        ["bash", init_script] + sys.argv[1:],
        cwd=os.getcwd()
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
