#!/usr/bin/env python
"""
Increments the build number in version.py
"""
import re
import os
from pathlib import Path

def increment_build():
    version_file = Path(__file__).parent.parent / "version.py"
    content = version_file.read_text()

    # Extract build number
    build_match = re.search(r"__build__ = '(\d+)'", content)
    if not build_match:
        print("Could not find build number in version.py")
        return

    build = int(build_match.group(1))
    new_build = str(build + 1)

    # Update build number
    new_content = re.sub(
        r"__build__ = '\d+'",
        f"__build__ = '{new_build}'",
        content
    )

    version_file.write_text(new_content)
    print(f"Build number incremented to {new_build}")

if __name__ == "__main__":
    increment_build()
