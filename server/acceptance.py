#!/usr/bin/env python3
"""Exercise private OpenMAIC login, persistence, and a small classroom job."""

import argparse
from http.cookies import SimpleCookie
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


BASE = 'http://127.0.0.1:3001'
ENV = Path('/opt/openmaic/.env')
STATE = Path('/opt/openmaic/acceptance-state.json')


def access_code():
    for line in ENV.read_text(encoding='utf-8').splitlines():
        if line.startswith('ACCESS_CODE='):
            return line.split('=', 1)[1]
    raise RuntimeError('ACCESS_CODE is missing')


def request(method, path, body=None, cookies=None):
    headers = {}
    payload = None
    if body is not None:
        payload = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    if cookies:
        headers['Cookie'] = '; '.join(f'{key}={value}' for key, value in cookies.items())
    req = Request(BASE + path, data=payload, headers=headers, method=method)
    try:
        response = urlopen(req, timeout=30)
    except HTTPError as error:
        response = error
    with response:
        raw = response.read()
        data = json.loads(raw) if raw else None
        set_cookies = SimpleCookie()
        for item in response.headers.get_all('Set-Cookie', []):
            set_cookies.load(item)
        return response.status, data, {key: morsel.value for key, morsel in set_cookies.items()}


def expect(status, actual, payload):
    if actual != status:
        raise RuntimeError(f'HTTP {actual}, expected {status}: {str(payload)[:350]}')


def authenticated(owner_id):
    status, data, minted = request('POST', '/api/access-code/verify', {'code': access_code()})
    expect(200, status, data)
    token = minted.get('openmaic_access')
    if not token:
        raise RuntimeError('Access-code login did not issue a cookie')
    return {'openmaic_access': token, 'anonymous_id': owner_id}


def verify_saved(state, cookies):
    status, data, _ = request('GET', f"/api/persistence/documents/{state['document_id']}", cookies=cookies)
    expect(200, status, data)
    if data['stage']['name'] != 'Deployment acceptance course':
        raise RuntimeError('Saved course content changed')
    if 'classroom_id' in state:
        status, data, _ = request('GET', f"/api/classroom?id={state['classroom_id']}", cookies=cookies)
        expect(200, status, data)
        if not data['classroom']['scenes']:
            raise RuntimeError('Saved classroom has no scenes')
    print('Saved course and classroom can be read.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('run', 'verify'))
    args = parser.parse_args()

    if args.mode == 'verify':
        state = json.loads(STATE.read_text(encoding='utf-8'))
        verify_saved(state, authenticated(state['owner_id']))
        return

    status, data, _ = request('GET', '/api/persistence/documents')
    expect(401, status, data)
    owner_id = str(uuid4())
    cookies = authenticated(owner_id)
    status, data, _ = request('GET', '/api/stages', cookies=cookies)
    expect(200, status, data)
    if not isinstance(data.get('stages'), list):
        raise RuntimeError('Owner stage list is invalid')
    status, data, _ = request('POST', '/api/stages', {'name': 'Deployment acceptance course'}, cookies)
    expect(201, status, data)
    document_id = data['stage']['id']
    status, document, _ = request('GET', f'/api/persistence/documents/{document_id}', cookies=cookies)
    expect(200, status, document)
    document['scenes'] = [{
            'id': 'acceptance-slide', 'stageId': document_id, 'title': 'Introduction',
            'order': 0, 'type': 'slide',
            'content': {'type': 'slide', 'canvas': {'id': 'acceptance-canvas', 'elements': []}},
        }]
    status, data, _ = request('PUT', f'/api/persistence/documents/{document_id}', document, cookies)
    expect(204, status, data)
    state = {'owner_id': owner_id, 'document_id': document_id}
    STATE.write_text(json.dumps(state), encoding='utf-8')
    STATE.chmod(0o600)
    verify_saved(state, cookies)
    print('Starting a small classroom generation job.')

    body = {
        'requirement': '制作一节给初学者的简短中文课：什么是圆周率。只讲一个核心概念，尽量使用少量幻灯片，不需要图片、语音或视频。',
        'enableWebSearch': False, 'enableImageGeneration': False,
        'enableVideoGeneration': False, 'enableTTS': False,
    }
    status, data, _ = request('POST', '/api/generate-classroom', body, cookies)
    expect(202, status, data)
    job_id = data['jobId']
    deadline = time.monotonic() + 900
    last = None
    while time.monotonic() < deadline:
        time.sleep(10)
        status, data, _ = request('GET', f'/api/generate-classroom/{job_id}', cookies=cookies)
        expect(200, status, data)
        job = data
        progress = (job['status'], job['step'], job.get('progress'))
        if progress != last:
            print(f"Generation: {progress[0]} / {progress[1]} / {progress[2]}", flush=True)
            last = progress
        if job['status'] == 'failed':
            raise RuntimeError(f"Classroom generation failed: {job.get('error')}")
        if job['status'] == 'succeeded':
            state['classroom_id'] = job['result']['classroomId']
            STATE.write_text(json.dumps(state), encoding='utf-8')
            STATE.chmod(0o600)
            verify_saved(state, cookies)
            print(f"Generation succeeded with {job['result']['scenesCount']} scenes.")
            return
    raise TimeoutError('Classroom generation did not finish within 15 minutes')


if __name__ == '__main__':
    main()
