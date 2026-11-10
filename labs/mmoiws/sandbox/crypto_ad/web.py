"""HTTP entry point for Sevenfold on the shared team address."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import ctypes
import hmac
import os
from pathlib import Path
import re
import sqlite3
from threading import Lock

from flask import Flask, abort, jsonify, request, send_file

from aes import AES6
from crypto_keys import derive_key, flag_nonce, nonce_prefix, placement_signature


def make_bitmap(cipher, base, group, target):
    lib = ctypes.CDLL(str(Path(__file__).with_name('core.so')))
    lib.make_bitmap.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64,
                                ctypes.c_uint32, ctypes.c_char_p]
    round_keys = ctypes.create_string_buffer(bytes(x for key in cipher.keys for column in key for x in column))
    base = ctypes.create_string_buffer(base)
    temp = target.with_suffix('.tmp')
    try:
        if lib.make_bitmap(round_keys, base, 1 << 32, group, os.fsencode(temp)):
            raise RuntimeError('Bitmap generation failed')
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)


def create_app(data_dir, token):
    if not token:
        raise ValueError('Missing Crypto AD checker token')
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 2048
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    database = data_dir / 'flags.sqlite3'
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute('CREATE TABLE IF NOT EXISTS flags (locator TEXT PRIMARY KEY, ciphertext TEXT NOT NULL)')
    key = derive_key(token)
    cipher = AES6(key)
    prefix = nonce_prefix(key)
    bases = [bytearray(hmac.digest(key, bytes([n]), 'sha256')[:16]) for n in range(6)]
    for base in bases:
        base[1] = prefix[1] ^ 255
    sample = cipher.encrypt_block(bytes(16)).hex()
    bitmap_worker = ThreadPoolExecutor(max_workers=1)
    bitmap_lock = Lock()
    bitmap_job = None

    def public_data(locator, ciphertext):
        return {'rounds': 6, 'locator': locator, 'nonce': flag_nonce(key, locator).hex(), 'flag_ct': ciphertext,
                'bases': [base.hex() for base in bases], 'pt': '00' * 16, 'ct': sample}

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'crypto_ad', 'ct': sample}

    @app.get('/')
    def index():
        with closing(sqlite3.connect(database)) as conn:
            row = conn.execute('SELECT locator, ciphertext FROM flags ORDER BY rowid DESC LIMIT 1').fetchone()
        return {'service': 'crypto_ad', 'title': 'Sevenfold / Integral Six',
                'public': public_data(*row) if row else None,
                'encrypt': 'POST /encrypt with JSON {"pt": "<32 hex characters>"}',
                'bitmap': 'GET /bitmap/<group>/<structure>'}

    @app.get('/public/<locator>')
    def public(locator):
        with closing(sqlite3.connect(database)) as conn:
            row = conn.execute('SELECT ciphertext FROM flags WHERE locator=?', (locator,)).fetchone()
        if row is None:
            abort(404)
        return public_data(locator, row[0])

    @app.put('/internal/flags/<locator>')
    def place_flag(locator):
        body = request.get_json(silent=True)
        ciphertext = body.get('ciphertext') if isinstance(body, dict) else None
        if (not re.fullmatch(r'[0-9a-f]{40}', locator) or not isinstance(ciphertext, str)
                or not re.fullmatch(r'(?:[0-9a-f]{2}){1,64}', ciphertext)):
            abort(400)
        signature = placement_signature(token, locator, ciphertext)
        if not hmac.compare_digest(request.headers.get('X-Crypto-Signature', '').encode(), signature.encode()):
            abort(403)
        with closing(sqlite3.connect(database)) as conn, conn:
            conn.execute('INSERT OR IGNORE INTO flags VALUES (?, ?)', (locator, ciphertext))
            stored, = conn.execute('SELECT ciphertext FROM flags WHERE locator=?', (locator,)).fetchone()
        if stored != ciphertext:
            abort(409)
        return {'locator': locator}

    @app.post('/encrypt')
    def encrypt():
        body = request.get_json(silent=True)
        value = body.get('pt') if isinstance(body, dict) else None
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F]{32}', value):
            abort(400)
        block = bytes.fromhex(value)
        # All flag nonces share this prefix. Reserve their CTR blocks for the flags.
        if block.startswith(prefix) and int.from_bytes(block[8:], 'little') < 4:
            abort(400)
        return {'ct': cipher.encrypt_block(block).hex()}

    @app.get('/bitmap/<int:group>/<int:structure>')
    def bitmap(group, structure):
        nonlocal bitmap_job
        if group >= 4 or structure >= len(bases):
            abort(404)
        target = data_dir / f'integral_g{group}_s{structure}.bt'
        if target.is_file():
            return send_file(target, mimetype='application/octet-stream')
        with bitmap_lock:
            if bitmap_job is not None and bitmap_job.done() and bitmap_job.exception():
                app.logger.error('Crypto AD bitmap generation failed: %s', bitmap_job.exception())
                bitmap_job = None
                abort(503)
            if bitmap_job is None or bitmap_job.done():
                if not target.is_file():
                    bitmap_job = bitmap_worker.submit(make_bitmap, cipher, bytes(bases[structure]), group, target)
        return jsonify(status='generating'), 202, {'Retry-After': '5'}

    return app


if __name__ == '__main__':
    from waitress import serve

    token = Path('/etc/crypto-ad/token').read_text(encoding='utf-8').strip()
    serve(create_app('/var/lib/crypto-ad', token), host='127.0.0.1', port=8080)
