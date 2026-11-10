import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
CRYPTO = ROOT / 'round2' / 'crypto_ad'


class SandboxTests(unittest.TestCase):
    def test_uses_boutique_topology_and_both_checker_agents(self):
        topology = yaml.safe_load((ROOT / 'topology.yml').read_text(encoding='utf-8'))
        self.assertEqual({node['host']: node['ip'] for node in topology['net_mappings']},
                         {'team1': '10.90.0.11', 'team2': '10.90.0.12',
                          'team3': '10.90.0.13', 'checker': '10.90.0.30'})
        provisioning = ROOT / 'provisioning'
        variables = yaml.safe_load((provisioning / 'group_vars/all.yml').read_text(encoding='utf-8'))
        self.assertEqual(variables['meko_addresses'], {
            node['host']: node['ip'] for node in topology['net_mappings'] if node['host'] != 'checker'
        })
        web_playbook = (provisioning / 'playbook.yml').read_text(encoding='utf-8')
        plays = yaml.safe_load(web_playbook)
        crypto_path = provisioning / plays[-1]['ansible.builtin.import_playbook']
        crypto_playbook = crypto_path.read_text(encoding='utf-8')
        crypto_plays = yaml.safe_load(crypto_playbook)
        for play in crypto_plays:
            self.assertEqual(play['vars']['crypto_ad_services'], {
                'curveball': 9011, 'padding_oracle': 9012, 'ecdsa_nonce': 9013,
            })
        self.assertIn('/opt/meko-checker/agent.py', web_playbook)
        self.assertIn('/opt/crypto-checker/agent.py', crypto_playbook)
        self.assertTrue((ROOT / 'checker/agent.py').is_file())
        self.assertTrue((CRYPTO / 'agent.py').is_file())
        self.assertEqual([p['hosts'] for p in crypto_plays],
                         ['team1:team2:team3', 'checker'])

    def test_checkout_contains_boutique_login_defaults(self):
        variables = yaml.safe_load((ROOT / 'provisioning/group_vars/all.yml').read_text(encoding='utf-8'))
        self.assertEqual(set(variables), {'meko_team_passwords', 'meko_staff_secret', 'meko_addresses'})
        passwords = variables['meko_team_passwords']
        self.assertEqual(set(passwords), {'team1', 'team2', 'team3'})
        self.assertTrue(all(len(password) >= 8 and '{{' not in password
                            for password in passwords.values()))
        self.assertTrue(len(variables['meko_staff_secret']) >= 16 and
                        '{{' not in variables['meko_staff_secret'])

    def test_training_definition_describes_both_rounds(self):
        training = json.loads((ROOT / 'training-definition.json').read_text(encoding='utf-8'))
        access, web, crypto = training['levels']
        self.assertEqual([level['order'] for level in training['levels']], [0, 1, 2])
        self.assertEqual(access['level_type'], 'ACCESS_LEVEL')
        self.assertIn(access['passkey'], access['cloud_content'])
        self.assertIn('Meko Boutique', web['title'])
        for item in ('SQLi', 'IDOR', 'Upload', 'JWT', 'Backup'):
            self.assertIn(item, web['content'])
        for port in ('9011', '9012', '9013'):
            self.assertIn(port, crypto['content'])

    def test_open_gui_uses_each_team_account_and_fixed_vnc_password(self):
        provisioning = ROOT / 'provisioning'
        plays = yaml.safe_load((provisioning / 'playbook.yml').read_text(encoding='utf-8'))
        desktop, = [task for task in plays[0]['tasks']
                    if task.get('ansible.builtin.include_tasks') == 'desktop.yml']
        self.assertEqual(desktop.get('when'), 'meko_desktop_enabled | bool')
        access_check, gui_check = plays[0]['pre_tasks'][:2]
        self.assertFalse(any('meko_team_vnc_passwords' in rule for rule in
                             access_check['ansible.builtin.assert']['that']))
        self.assertEqual(gui_check.get('when'), 'meko_desktop_enabled | bool')
        for team in ('team1', 'team2', 'team3'):
            self.assertIn(f'{team.upper()}_VNC_PASSWORD', plays[0]['vars']['meko_team_vnc_passwords'][team])
        unit = (provisioning / 'templates/meko-team-desktop.service.j2').read_text(encoding='utf-8')
        self.assertIn('User={{ inventory_hostname }}', unit)
        self.assertIn('-rfbport 5900 -localhost no -SecurityTypes VncAuth', unit)
        self.assertIn('/home/{{ inventory_hostname }}/.vnc/passwd', unit)

    def test_all_web_checker_actions(self):
        exercise = """
import os
from pathlib import Path
import sys
from threading import Thread
from werkzeug.serving import make_server

sys.path[:0] = [str(Path('app').resolve()), str(Path('checker').resolve())]
from app import create_app
from forcad import execute
from meko_checker import SERVICES

with make_server('127.0.0.1', 0, create_app()) as server:
    ip = '10.90.0.13'
    url = f'http://127.0.0.1:{server.server_port}'
    config = {'teams': {ip: {'team': 'team3', 'url': url,
                             'staff_password': os.environ['MEKO_STAFF_PASSWORD']}}}
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        for task in SERVICES:
            request = {'task': task, 'ip': ip, 'flag': 'MekoDataCTF{' + 'A' * 30 + '}'}
            check = execute(config, dict(request, action='check'))
            assert check['status'] == 101, (task, check)
            put = execute(config, dict(request, action='put'))
            assert put['status'] == 101, (task, put)
            get = execute(config, dict(request, action='get', locator=put['private']))
            assert get['status'] == 101, (task, get)
    finally:
        server.shutdown()
        worker.join()
"""
        with tempfile.TemporaryDirectory() as data:
            run = subprocess.run([sys.executable, '-c', exercise], cwd=ROOT,
                                 env={**os.environ, 'MEKO_DATA': data, 'TEAM_ID': 'team3',
                                      'MEKO_STAFF_PASSWORD': 'fixture-only'},
                                 capture_output=True, text=True, timeout=40)
            self.assertEqual(run.returncode, 0, run.stderr)

    def test_all_crypto_checker_actions(self):
        # Use the same request/response contract without binding the lab's ports.
        exercise = """
import sys
from unittest.mock import patch
from agent import run
from protocol import SERVICES
from service import Service

ip = '10.90.0.13'
flag = 'MekoDataCTF{' + 'a' * 32 + '}'
for task in SERVICES:
    service = Service(task, {'data_dir': sys.argv[1], 'admin_token': 'fixture'})
    assert service.handle({'op': 'targets'})['targets'] == []
    client = type('Client', (), {
        'call': lambda self, **req: service.handle(req),
        '__enter__': lambda self: self,
        '__exit__': lambda self, *exc: None,
    })()
    config = {'teams': {ip: {'token': 'fixture'}}}
    request = {'task': task, 'ip': ip, 'flag': flag, 'key': '{"tick":11}'}
    with patch('agent.Client', return_value=client):
        assert run(dict(request, action='check'), config)['status'] == 101
        put = run(dict(request, action='put'), config)
        assert put['status'] == 101
        assert run(dict(request, action='put'), config) == put
        assert run(dict(request, action='get', locator=put['private']), config)['status'] == 101
        assert service.handle({'op': 'targets'})['targets'][0]['tick'] == 11
"""
        with tempfile.TemporaryDirectory() as data:
            run = subprocess.run([sys.executable, '-c', exercise, data], cwd=CRYPTO,
                                 capture_output=True, text=True, timeout=20)
            self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == '__main__':
    unittest.main()
