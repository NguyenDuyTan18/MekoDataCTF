"""Only verified GUI listeners may be replaced; management SSH is protected."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
from unittest.mock import patch
import pytest

FILE = Path(__file__).resolve().parents[1] / 'sandbox/provisioning/files/vnc-listener.py'


def helper():
    spec = importlib.util.spec_from_file_location('vnc_listener', FILE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_free_port_and_verified_lightdm(tmp_path):
    m = helper()
    assert m.listener_plan('', tmp_path, ['lightdm.service']) == {'stop_units': [], 'unknown': [], 'own_listener': False}
    p = tmp_path / '123'
    p.mkdir()
    (p / 'cgroup').write_text('0::/system.slice/lightdm.service\n')
    row = 'LISTEN 0 5 0.0.0.0:5900 0.0.0.0:* users:(("Xvnc",pid=123,fd=8))'
    plan = m.listener_plan(row, tmp_path, ['lightdm.service'])
    assert plan == {'stop_units': ['lightdm.service'], 'unknown': [], 'own_listener': False}


@pytest.mark.parametrize('unit', ['ssh.service', 'apache2.service', 'other.service'])
def test_unknown_or_management_listener_is_never_stopped(tmp_path, unit):
    m = helper()
    p = tmp_path / '321'
    p.mkdir()
    (p / 'cgroup').write_text('0::/system.slice/' + unit + '\n')
    plan = m.listener_plan('LISTEN users:(("process",pid=321,fd=8))', tmp_path,
                           ['lightdm.service', 'ssh.service', 'apache2.service'])
    assert plan['stop_units'] == []
    assert plan['unknown']


def test_own_listener_is_not_stopped_and_missing_pid_is_not_guessed(tmp_path):
    m = helper()
    p = tmp_path / '100'
    p.mkdir()
    (p / 'cgroup').write_text('0::/system.slice/meko-desktop.service\n')
    assert m.listener_plan('LISTEN users:(("Xtigervnc",pid=100,fd=8))', tmp_path, [])['own_listener']
    assert m.listener_plan('LISTEN 0 5 *:5900 *:*', tmp_path, [])['unknown']
    assert m.listener_plan('LISTEN users:(("gone",pid=999,fd=8))', tmp_path, [])['unknown']


def test_cli_is_inspection_only(capsys):
    m = helper()
    with patch.object(m.sys, 'argv', ['vnc-listener', '--port', '5900']), \
         patch.object(m.sys, 'stdin', io.StringIO('["lightdm.service"]')), \
         patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '')) as run:
        m.main()
    assert json.loads(capsys.readouterr().out)['stop_units'] == []
    assert run.call_args.args[0] == ['/usr/bin/ss', '-H', '-ltnp', 'sport = :5900']
    assert run.call_count == 1


@pytest.mark.parametrize('port,allowed', [('22', '[]'), ('5900', '{}')])
def test_cli_rejects_invalid_inputs_before_running_commands(port, allowed):
    m = helper()
    with patch.object(m.sys, 'argv', ['vnc-listener', '--port', port]), \
         patch.object(m.sys, 'stdin', io.StringIO(allowed)), patch.object(m.subprocess, 'run') as run:
        with pytest.raises(SystemExit) as exc:
            m.main()
        assert exc.value.code == 2
        run.assert_not_called()


def socket_unit(name='xvnc.socket', listen='[::]:5900 (Stream)', triggers='xvnc@.service'):
    return {'Id': name, 'ActiveState': 'active', 'Listen': listen, 'Triggers': triggers}


def test_systemd_pid_one_maps_to_verified_vnc_socket(tmp_path):
    m = helper()
    row = 'LISTEN 0 4096 [::]:5900 [::]:* users:(("systemd",pid=1,fd=40))'
    plan = m.listener_plan(row, tmp_path, ['xvnc.socket'], [socket_unit()], port=5900)
    assert plan == {'stop_units': ['xvnc.socket'], 'unknown': [], 'own_listener': False}


@pytest.mark.parametrize('unit', [socket_unit(listen='[::]:22 (Stream)'),
    socket_unit(listen='/run/vnc:5900 (Stream)'),
    socket_unit(name='ssh.socket'), socket_unit(triggers='ssh.service'),
    socket_unit(triggers='ssh@.service'),
    socket_unit(name='unapproved.socket')])
def test_pid_one_requires_correct_endpoint_and_unprotected_approved_socket(tmp_path, unit):
    m = helper()
    plan = m.listener_plan('LISTEN users:(("systemd",pid=1,fd=40))', tmp_path,
                           ['xvnc.socket', 'ssh.socket'], [unit], port=5900)
    assert plan['unknown'] and not plan['stop_units']


def test_socket_is_stopped_before_its_activated_service(tmp_path):
    m = helper()
    p = tmp_path / '222'
    p.mkdir()
    (p / 'cgroup').write_text('0::/system.slice/xvnc.service\n')
    row = 'LISTEN users:(("systemd",pid=1,fd=40),("Xvnc",pid=222,fd=40))'
    plan = m.listener_plan(row, tmp_path, ['xvnc.socket'],
                           [socket_unit(triggers='xvnc.service')], port=5900)
    assert plan['stop_units'] == ['xvnc.socket', 'xvnc.service']
    assert plan['unknown'] == []


def test_socket_metadata_uses_machine_readable_show_properties():
    m = helper()
    with patch.object(m.subprocess, 'run', side_effect=[
        subprocess.CompletedProcess([], 0, 'xvnc.socket loaded active listening VNC\n'),
        subprocess.CompletedProcess([], 0, 'Id=xvnc.socket\nActiveState=active\nListen=[::]:5900 (Stream)\nTriggers=xvnc@.service\n')
    ]) as run:
        assert m.read_socket_units() == [socket_unit()]
    assert 'list-units' in run.call_args_list[0].args[0]
    assert 'show' in run.call_args_list[1].args[0]
    assert not any('list-sockets' in c.args[0] for c in run.call_args_list)
