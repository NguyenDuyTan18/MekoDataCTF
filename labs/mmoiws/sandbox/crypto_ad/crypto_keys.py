import hmac


def derive_key(token):
    return hmac.digest(token.encode(), b'crypto-ad challenge key', 'sha256')[:16]


def nonce_prefix(key):
    return b'\x80' + hmac.digest(key, b'nonce prefix', 'sha256')[:1]


def flag_nonce(key, locator):
    return nonce_prefix(key) + hmac.digest(key, locator.encode(), 'sha256')[:6]


def placement_signature(token, locator, ciphertext):
    return hmac.digest(token.encode(), f'flag:{locator}:{ciphertext}'.encode(), 'sha256').hex()
