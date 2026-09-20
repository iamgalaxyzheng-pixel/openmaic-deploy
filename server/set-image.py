#!/usr/bin/env python3
"""Pin the deployed image to a GHCR SHA-256 digest without showing secrets."""

from pathlib import Path
import os
import re
import sys


CONFIG = Path('/opt/openmaic/.env')
IMAGE = re.compile(r'^ghcr\.io/iamgalaxyzheng-pixel/openmaic@sha256:[0-9a-f]{64}$')


def main() -> None:
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    if len(sys.argv) != 2 or not IMAGE.fullmatch(sys.argv[1]):
        raise SystemExit('Pass the verified ghcr.io/iamgalaxyzheng-pixel/openmaic@sha256:<digest>')
    text = CONFIG.read_text(encoding='utf-8')
    if text.count('OPENMAIC_IMAGE=') != 1:
        raise SystemExit('Expected exactly one OPENMAIC_IMAGE setting')
    lines = [f'OPENMAIC_IMAGE={sys.argv[1]}' if line.startswith('OPENMAIC_IMAGE=') else line
             for line in text.splitlines()]
    temp = CONFIG.with_name('.env.next')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')
    os.replace(temp, CONFIG)
    print('OpenMAIC image digest pinned.')


if __name__ == '__main__':
    main()

