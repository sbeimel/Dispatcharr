#!/usr/bin/env python
"""
Bumps the version number according to semantic versioning.
Usage: python bump_version.py [major|minor|patch]
"""
import re
import sys
from pathlib import Path

def bump_version(version_type='patch'):
    version_file = Path(__file__).parent.parent / "version.py"
    content = version_file.read_text()

    # Extract version
    version_match = re.search(r"__version__ = '(\d+)\.(\d+)\.(\d+)'", content)
    if not version_match:
        print("Could not find version number in version.py")
        return

    major, minor, patch = map(int, version_match.groups())

    # Update version based on type
    if version_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif version_type == 'minor':
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    new_version = f"{major}.{minor}.{patch}"

    # Update version in file
    new_content = re.sub(
        r"__version__ = '\d+\.\d+\.\d+'",
        f"__version__ = '{new_version}'",
        content
    )

    # Reset build number
    new_content = re.sub(
        r"__build__ = '\d+'",
        "__build__ = '0'",
        new_content
    )

    version_file.write_text(new_content)
    print(f"Version bumped to {new_version}")
    return new_version

if __name__ == "__main__":
    version_type = 'patch'
    if len(sys.argv) > 1:
        version_type = sys.argv[1].lower()

    if version_type not in ('major', 'minor', 'patch'):
        print("Invalid version type. Use major, minor, or patch.")
        sys.exit(1)

    bump_version(version_type)
