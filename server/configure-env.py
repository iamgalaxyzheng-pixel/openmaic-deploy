#!/opt/finance-observatory/.venv/bin/python
"""Create OpenMAIC's private runtime configuration without printing credentials."""

from pathlib import Path
import os
import secrets
from urllib.parse import urlparse

from dotenv import dotenv_values


FINANCE_ENV = Path('/etc/finance-observatory/finance.env')
OPENMAIC_ENV = Path('/opt/openmaic/.env')


def main() -> None:
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    if OPENMAIC_ENV.exists():
        raise SystemExit('OpenMAIC configuration already exists; refusing to overwrite it')

    finance = dotenv_values(FINANCE_ENV)
    key = finance.get('LLM_API_KEY') or ''
    base_url = (finance.get('LLM_BASE_URL') or '').rstrip('/')
    model = finance.get('LLM_MODEL') or ''
    if urlparse(base_url).hostname != 'api.deepseek.com' or model != 'deepseek-chat' or not key:
        raise SystemExit('Finance model settings differ from the reviewed DeepSeek configuration')
    if any(char in key for char in '\r\n$'):
        raise SystemExit('Finance key needs manual dotenv escaping; no configuration was written')

    password = secrets.token_hex(24)
    access_code = secrets.token_urlsafe(32)
    lines = [
        'OPENMAIC_IMAGE=',
        f'POSTGRES_PASSWORD={password}',
        f'DATABASE_URL=postgres://openmaic:{password}@postgres:5432/openmaic',
        'PERSISTENCE_DEV_TOKEN=openmaic-tailnet-single-user-v1',
        'PERSISTENCE_ALLOW_INSECURE_DEV_AUTH=true',
        f'ACCESS_CODE={access_code}',
        f'DEEPSEEK_API_KEY={key}',
        f'DEEPSEEK_BASE_URL={base_url}',
        f'DEEPSEEK_MODELS={model}',
        f'DEFAULT_MODEL=deepseek:{model}',
    ]
    fd = os.open(OPENMAIC_ENV, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')
    print('OpenMAIC configuration created with root-only access; image digest remains unset.')


if __name__ == '__main__':
    main()

