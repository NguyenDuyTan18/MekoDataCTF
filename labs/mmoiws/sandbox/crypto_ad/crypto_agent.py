"""ForcAD collector agent for Crypto AD on the existing checker VM."""
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aes import AES6, crypt
from crypto_keys import derive_key, flag_nonce, placement_signature


def verdict(status, public, private=''):
    return {'status': status, 'public': public, 'private': private}


def call(team, path, payload=None, method=None, signature=None):
    headers = {'Content-Type': 'application/json'}
    if signature is not None:
        headers['X-Crypto-Signature'] = signature
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(team['url'] + path, data=data, headers=headers, method=method)
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read(8192))


def execute(config, request):
    action = request.get('action')
    if request.get('task') != 'crypto' or action not in ('check', 'put', 'get'):
        return verdict(110, 'Invalid checker request')
    team = config['teams'][request['ip']]
    key = derive_key(team['token'])
    try:
        if action == 'check':
            health = call(team, '/health')
            actual = call(team, '/encrypt', {'pt': '00' * 16})
            if health.get('service') != 'crypto_ad' or actual.get('ct') != AES6(key).encrypt_block(bytes(16)).hex():
                return verdict(103, 'Crypto service check failed')
            return verdict(101, 'OK')

        locator = request['locator']
        if not re.fullmatch(r'[0-9a-f]{40}', locator):
            return verdict(110, 'Invalid flag locator')
        path = '/public/' + locator
        if action == 'put':
            ciphertext = crypt(request['flag'].encode(), key, flag_nonce(key, locator)).hex()
            signature = placement_signature(team['token'], locator, ciphertext)
            call(team, '/internal/flags/' + locator, {'ciphertext': ciphertext}, 'PUT', signature)
        public = call(team, path)
        flag = crypt(bytes.fromhex(public['flag_ct']), key, bytes.fromhex(public['nonce']))
        if flag != request['flag'].encode():
            return verdict(102, 'Crypto flag missing')
        if action == 'put':
            return verdict(101, json.dumps({'path': path}), locator)
        return verdict(101, 'OK')
    except HTTPError as exc:
        code = exc.code
        exc.close()
        if code in (502, 503, 504):
            return verdict(104, 'Crypto service unavailable')
        return verdict(102 if action == 'get' and code == 404 else 103, 'Crypto request failed')
    except (URLError, TimeoutError):
        return verdict(104, 'Crypto service unavailable')
    except (KeyError, TypeError, ValueError):
        return verdict(103, 'Crypto response invalid')


if __name__ == '__main__':
    try:
        config = json.loads(Path('/etc/crypto-ad-checker/config.json').read_text(encoding='utf-8'))
        result = execute(config, json.loads(sys.stdin.read(16384)))
    except (OSError, KeyError, TypeError, ValueError):
        result = verdict(110, 'Crypto checker failed')
    print(json.dumps(result))
