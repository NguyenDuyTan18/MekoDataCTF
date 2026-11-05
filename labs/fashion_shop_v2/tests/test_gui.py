"""Regressions for CyberRange Open GUI, independent of the shop's health."""
from pathlib import Path
import yaml
from jinja2 import Environment, StrictUndefined

SANDBOX = Path(__file__).resolve().parents[1] / 'sandbox'


def test_desktop_is_enabled_and_bootstrapped_before_web_tasks():
    defaults = yaml.safe_load((SANDBOX / 'provisioning/group_vars/all.yml').read_text())
    play = yaml.safe_load((SANDBOX / 'provisioning/playbook.yml').read_text())[0]
    assert defaults['meko_desktop_enabled'] is True
    assert any(task.get('ansible.builtin.include_tasks') == 'desktop.yml' for task in play.get('pre_tasks', []))


def test_gui_has_an_independent_repair_entrypoint():
    path = SANDBOX / 'provisioning/gui-repair.yml'
    assert path.is_file(), 'GUI repair must be runnable when website provisioning fails'
    play = yaml.safe_load(path.read_text())[0]
    includes = [task.get('ansible.builtin.include_tasks') for task in play['tasks']]
    assert includes == ['trainee-access.yml', 'desktop.yml']


def test_desktop_authenticates_from_gateway_and_has_no_http_dependency():
    path = SANDBOX / 'provisioning/desktop.yml'
    assert path.is_file(), 'A Kali user account alone does not start a VNC server'
    tasks = yaml.safe_load(path.read_text())
    blocks = [nested for task in tasks for nested in task.get('block', [])]
    network_probe = next(task for task in blocks if task.get('name') == 'Authenticate VNC from gateway and receive a desktop frame')
    assert network_probe['delegate_to'] == 'gateway'
    assert network_probe['no_log'] is True
    assert not any('ansible.builtin.uri' in task for task in tasks)


def test_vnc_network_map_exists_for_each_entrypoint():
    for name in ('playbook.yml', 'gui-repair.yml'):
        play = yaml.safe_load((SANDBOX / 'provisioning' / name).read_text())[0]
        assert 'meko_team_addresses' in play['vars'], name


def test_network_failure_does_not_stop_a_verified_local_desktop():
    tasks = yaml.safe_load((SANDBOX / 'provisioning/desktop.yml').read_text())
    network = next((task for task in tasks if task.get('name') == 'Verify the external VNC path without rolling back a healthy desktop'), None)
    assert network is not None
    assert all('ansible.builtin.systemd' not in task for task in network['rescue'])


def test_service_template_matches_each_team_account_and_guest_vnc_endpoint():
    settings = yaml.safe_load((SANDBOX / 'provisioning/group_vars/all.yml').read_text())
    source = (SANDBOX / 'provisioning/files/meko-desktop.service').read_text()
    for host in ('team1', 'team2', 'team3', 'team4'):
        unit = Environment(undefined=StrictUndefined).from_string(source).render(inventory_hostname=host, **settings)
        assert 'User=' + host in unit
        assert '-rfbport 5900 -localhost no -SecurityTypes VncAuth' in unit
        assert '/home/' + host + '/.vnc/passwd' in unit

