import ctypes
import json
import os
import fcntl
import secrets
import sys
import subprocess
from pathlib import Path
from aes import AES6, crypt

STATE = Path(__file__).with_name('.demo_state.json')
CACHE = STATE.parent


def load():
    with STATE.with_suffix('.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not STATE.exists():
            key = secrets.token_bytes(16)
            nonce = b'\x80' + secrets.token_bytes(7)
            bases = [bytearray(secrets.token_bytes(16)) for _ in range(6)]
            for b in bases:
                b[1] = nonce[1] ^ 255
            state = {'key': key.hex(), 'nonce': nonce.hex(), 'bases': [bytes(b).hex() for b in bases]}
            STATE.write_text(json.dumps(state))
        state = json.loads(STATE.read_text())
    return bytes.fromhex(state['key']), bytes.fromhex(state['nonce']), [bytes.fromhex(x) for x in state['bases']]


def main():
    key, nonce, bases = load()
    flag = b'flag{local_demo_only}'
    cipher = AES6(key)
    public = {'rounds': 6, 'nonce': nonce.hex(), 'flag_ct': crypt(flag, key, nonce).hex(), 'bases': [x.hex() for x in bases], 'pt': '00'*16, 'ct': cipher.encrypt_block(bytes(16)).hex()}
    print('SEVENFOLD / INTEGRAL SIX', flush=True)
    print('PUBLIC=' + json.dumps(public), flush=True)
    while True:
        print('1. Encrypt\n2. Get structure bitmap\n3. Exit', flush=True)
        try:
            choice = input('> ').strip()
            if choice == '1':
                value = input('pt> ').strip()
                p = bytes.fromhex(value)
                if len(p) != 16 or p[:8] == nonce and int.from_bytes(p[8:], 'little') < (len(flag)+15)//16:
                    print('Rejected', flush=True)
                else:
                    print('CT=' + cipher.encrypt_block(p).hex(), flush=True)
            elif choice == '2':
                group_value = input('group (0-3)> ').strip()
                if group_value not in ('0', '1', '2', '3'):
                    print('Rejected', flush=True)
                    continue
                group = int(group_value)
                value = input('structure (0-5)> ').strip()
                if value not in tuple(str(i) for i in range(6)):
                    print('Rejected', flush=True)
                    continue
                num = int(value)
                dst = CACHE / (('integral_%d.bt' % num) if group == 0 else ('integral_g%d_s%d.bt' % (group, num)))
                with (CACHE / 'generation.lock').open('a+b') as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    if not dst.is_file():
                        libpath = Path(__file__).with_name('core.so')
                        if not libpath.is_file():
                            subprocess.run(['gcc', '-O3', '-maes', '-msse2', '-fopenmp', '-fPIC', '-shared', str(Path(__file__).with_name('core.c')), '-o', str(libpath)], check=True)
                        lib = ctypes.CDLL(str(libpath))
                        a = ctypes.create_string_buffer(b''.join(bytes(x for col in k for x in col) for k in cipher.keys))
                        b = ctypes.create_string_buffer(bases[num])
                        lib.make_bitmap.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint32, ctypes.c_char_p]
                        temp = dst.with_suffix('.tmp.'+str(os.getpid()))
                        r = lib.make_bitmap(a, b, 1 << 32, group, os.fsencode(temp))
                        if r:
                            temp.unlink(missing_ok=True)
                            print('Generation failed', flush=True)
                            continue
                        temp.replace(dst)
                print('BYTES=' + str(dst.stat().st_size), flush=True)
                with dst.open('rb') as f:
                    while block := f.read(1<<20):
                        sys.stdout.buffer.write(block)
                sys.stdout.buffer.flush()
                return
            elif choice == '3':
                return
        except (EOFError, ValueError, BrokenPipeError):
            return


if __name__ == '__main__':
    main()
