#!/usr/bin/env python3
"""CLI wrapper for wsctx-init script."""

import subprocess
import sys
import os
import stat


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    init_script = os.path.join(script_dir, "scripts", "init.sh")

    # Ensure executable bit (lost during pip install)
    st = os.stat(init_script)
    os.chmod(init_script, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    result = subprocess.run(
        ["bash", init_script] + sys.argv[1:],
        cwd=os.getcwd()
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
