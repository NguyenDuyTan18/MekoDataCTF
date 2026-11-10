from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import Mock, patch

LAB = Path(__file__).resolve().parent
FORCAD = LAB.parents[1] / 'platform' / 'ForcAD-demo'
sys.path.insert(0, str(LAB / 'sandbox' / 'crypto_ad'))


def load_script(path):
    spec = spec_from_file_location(path.stem, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CryptoADTest(unittest.TestCase):
    def test_flag_round_trip_and_private_placement(self):
        from web import create_app
        from crypto_keys import derive_key, flag_nonce, placement_signature
        from aes import crypt

        with TemporaryDirectory() as directory:
            token = 'test-operator-key'
            key = derive_key(token)
            client = create_app(Path(directory), token).test_client()
            self.assertEqual(client.get('/health').json['service'], 'crypto_ad')
            locator = 'a' * 40
            flag = 'MekoDataCTF{test_round_two}'
            url = f'/internal/flags/{locator}'
            ciphertext = crypt(flag.encode(), key, flag_nonce(key, locator)).hex()
            self.assertEqual(client.put(url, json={'ciphertext': ciphertext}).status_code, 403)
            headers = {'X-Crypto-Signature': placement_signature(token, locator, ciphertext)}
            placed = client.put(url, headers=headers, json={'ciphertext': ciphertext})
            self.assertEqual(placed.status_code, 200)
            self.assertEqual(client.put(url, headers=headers, json={'ciphertext': ciphertext}).json, placed.json)
            changed = ciphertext + 'aa'
            headers = {'X-Crypto-Signature': placement_signature(token, locator, changed)}
            self.assertEqual(client.put(url, headers=headers, json={'ciphertext': changed}).status_code, 409)
            public = client.get(f'/public/{locator}').json
            self.assertEqual(crypt(bytes.fromhex(public['flag_ct']), key,
                                   bytes.fromhex(public['nonce'])).decode(), flag)
            self.assertNotIn(flag, client.get('/').get_data(as_text=True))
            blocked = public['nonce'] + '00' * 8
            self.assertEqual(client.post('/encrypt', json={'pt': blocked}).status_code, 400)
            self.assertEqual(client.post('/encrypt', json={'pt': '00' * 16}).json['ct'], public['ct'])

    def test_agent_checks_and_recovers_flag_from_public_ciphertext(self):
        from werkzeug.serving import make_server
        from crypto_agent import execute
        from web import create_app

        with TemporaryDirectory() as directory:
            token = 'checker-token-for-test'
            server = make_server('127.0.0.1', 0, create_app(directory, token))
            worker = Thread(target=server.serve_forever)
            worker.start()
            try:
                team = {'url': f'http://127.0.0.1:{server.server_port}', 'token': token}
                config = {'teams': {'127.0.0.1': team}}
                payload = {'task': 'crypto', 'ip': '127.0.0.1', 'locator': 'b' * 40,
                           'flag': 'MekoDataCTF{test_round_two}'}
                self.assertEqual(execute(config, dict(payload, action='check'))['status'], 101)
                self.assertEqual(execute(config, dict(payload, action='get'))['status'], 102)
                placed = execute(config, dict(payload, action='put'))
                self.assertEqual((placed['status'], placed['private']), (101, payload['locator']))
                self.assertEqual(execute(config, dict(payload, action='get'))['status'], 101)
                self.assertEqual(execute(config, dict(payload, action='get', flag='different'))['status'], 102)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()

    def test_round_two_waits_ten_minutes_after_round_one_finishes(self):
        profile = load_script(FORCAD / 'backend' / 'lib' / 'storage' / 'lab_profile.py')
        crypto = profile.get('mmoiws')
        self.assertEqual(crypto['teams'], profile.get('meko_boutique')['teams'])
        state = {'lab': 'meko_boutique', 'finished_at': 1000, 'phase': 'finished'}
        self.assertEqual(profile.transition_delay(crypto, state, 1599), 1)
        self.assertEqual(profile.transition_delay(crypto, state, 1600), 0)
        with self.assertRaises(ValueError):
            profile.transition_delay(crypto, dict(state, finished_at=None), 1600)

        switch = load_script(FORCAD / 'switch_round.py')
        status = {'running': False, 'round1': state}
        api = Mock()
        api.status.return_value = status
        with patch.object(switch.time, 'time', side_effect=[1599, 1600]), patch.object(switch.time, 'sleep') as wait:
            self.assertIs(switch.wait_for_crypto(api, status), status)
        wait.assert_called_once_with(1)


if __name__ == '__main__':
    unittest.main()
