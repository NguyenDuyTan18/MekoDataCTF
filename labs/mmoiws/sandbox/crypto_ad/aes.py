SBOX = bytes.fromhex('''

63 7c 77 7b f2 6b 6f c5 30 01 67 2b fe d7 ab 76
ca 82 c9 7d fa 59 47 f0 ad d4 a2 af 9c a4 72 c0
b7 fd 93 26 36 3f f7 cc 34 a5 e5 f1 71 d8 31 15
04 c7 23 c3 18 96 05 9a 07 12 80 e2 eb 27 b2 75
09 83 2c 1a 1b 6e 5a a0 52 3b d6 b3 29 e3 2f 84
53 d1 00 ed 20 fc b1 5b 6a cb be 39 4a 4c 58 cf
d0 ef aa fb 43 4d 33 85 45 f9 02 7f 50 3c 9f a8
51 a3 40 8f 92 9d 38 f5 bc b6 da 21 10 ff f3 d2
cd 0c 13 ec 5f 97 44 17 c4 a7 7e 3d 64 5d 19 73
60 81 4f dc 22 2a 90 88 46 ee b8 14 de 5e 0b db
e0 32 3a 0a 49 06 24 5c c2 d3 ac 62 91 95 e4 79
e7 c8 37 6d 8d d5 4e a9 6c 56 f4 ea 65 7a ae 08
ba 78 25 2e 1c a6 b4 c6 e8 dd 74 1f 4b bd 8b 8a
70 3e b5 66 48 03 f6 0e 61 35 57 b9 86 c1 1d 9e
e1 f8 98 11 69 d9 8e 94 9b 1e 87 e9 ce 55 28 df
8c a1 89 0d bf e6 42 68 41 99 2d 0f b0 54 bb 16
''')
RCON = (0, 1, 2, 4, 8, 16, 32, 64, 128, 27, 54)

def xtime(value):
    return ((value << 1) ^ (27 if value & 128 else 0)) & 255

def mix_column(a):
    t = a[0] ^ a[1] ^ a[2] ^ a[3]
    u = a[0]
    a[0] ^= t ^ xtime(a[0] ^ a[1])
    a[1] ^= t ^ xtime(a[1] ^ a[2])
    a[2] ^= t ^ xtime(a[2] ^ a[3])
    a[3] ^= t ^ xtime(a[3] ^ u)

class AES6:
    def __init__(self, key, rounds=6):
        if len(key) != 16 or not 1 <= rounds <= 10:
            raise ValueError('Invalid AES key or rounds')
        self.rounds = rounds
        words = [list(key[i:i+4]) for i in range(0, 16, 4)]
        for i in range(4, 4 * (rounds + 1)):
            w = words[-1][:]
            if i % 4 == 0:
                w = [SBOX[x] for x in w[1:] + w[:1]]
                w[0] ^= RCON[i // 4]
            words.append([x ^ y for x, y in zip(w, words[-4])])
        self.keys = [words[i:i+4] for i in range(0, len(words), 4)]

    def encrypt_block(self, block):
        if len(block) != 16:
            raise ValueError('Expected 16 bytes')
        state = [list(block[i:i+4]) for i in range(0, 16, 4)]
        for c in range(4):
            for r in range(4):
                state[c][r] ^= self.keys[0][c][r]
        for n in range(1, self.rounds + 1):
            for c in range(4):
                for r in range(4):
                    state[c][r] = SBOX[state[c][r]]
            for r in range(1, 4):
                row = [state[c][r] for c in range(4)]
                for c in range(4):
                    state[c][r] = row[(c+r) % 4]
            if n != self.rounds:
                for column in state:
                    mix_column(column)
            for c in range(4):
                for r in range(4):
                    state[c][r] ^= self.keys[n][c][r]
        return bytes(x for col in state for x in col)

def encrypt(block, key):
    return AES6(key).encrypt_block(block)

def crypt(data, key, nonce):
    if len(nonce) != 8:
        raise ValueError('Expected 8-byte nonce')
    aes = AES6(key)
    stream = b''.join(aes.encrypt_block(nonce + i.to_bytes(8, 'little')) for i in range((len(data) + 15) // 16))
    return bytes(x ^ y for x, y in zip(data, stream))
