#!/usr/bin/python3
"""Inspect a VNC listener; report verified systemd owners without stopping them."""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import sys

PROTECTED = {'ssh.service', 'sshd.service', 'apache2.service', 'fashion-shop.service',
             'NetworkManager.service', 'systemd-networkd.service'}


def protected(unit):
    return unit.rsplit('.', 1)[0].split('@', 1)[0] in {name.rsplit('.', 1)[0] for name in PROTECTED}


def read_socket_units():
    """Use show properties; list-sockets' address columns are not machine-stable."""
    result = subprocess.run(['/usr/bin/systemctl', 'list-units', '--type=socket',
                             '--state=active', '--no-legend', '--plain', '--no-pager'],
                            text=True, capture_output=True, check=True)
    units = []
    for row in result.stdout.splitlines():
        name = row.split()[0] if row.split() else ''
        if not re.fullmatch(r'[A-Za-z0-9_.@:-]+\.socket', name):
            continue
        details = subprocess.run(['/usr/bin/systemctl', 'show', name,
                                  '--property=Id,ActiveState,Listen,Triggers', '--no-pager'],
                                 text=True, capture_output=True, check=True)
        units.append(dict(line.split('=', 1) for line in details.stdout.splitlines() if '=' in line))
    return units


def listens_on_port(value, port):
    for endpoint in re.findall(r'(\S+)\s+\(Stream\)', value):
        if endpoint == str(port):
            return True
        host, separator, number = endpoint.rpartition(':')
        if not separator or number != str(port):
            continue
        if host == '*':
            return True
        try:
            ipaddress.ip_address(host.strip('[]'))
            return True
        except ValueError:
            pass
    return False


def listener_plan(output, proc_root, allowed_units, socket_units=(), port=5900):
    stop, unknown, own = set(), [], False
    socket_stops, triggered = set(), set()
    socket_errors = []
    for unit in socket_units:
        if unit.get('ActiveState') != 'active' or not listens_on_port(unit.get('Listen', ''), port):
            continue
        name = unit.get('Id', '')
        services = unit.get('Triggers', '').split()
        if protected(name) or name not in allowed_units:
            socket_errors.append('Unapproved or protected socket ' + name)
            continue
        if any(protected(service) for service in services):
            socket_errors.append('Protected service activated by socket ' + name)
            continue
        if any(not re.fullmatch(r'[A-Za-z0-9_.@:-]+\.service', service) for service in services):
            socket_errors.append('Unrecognized activation target for socket ' + name)
            continue
        socket_stops.add(name)
        triggered.update(service for service in services if '@.service' not in service)
    for row in output.splitlines():
        if not row.strip():
            continue
        pids = set(re.findall(r'pid=(\d+)', row))
        if not pids:
            unknown.append('Listener has no visible PID: ' + row)
        for pid in sorted(pids):
            if pid == '1':
                if socket_errors:
                    unknown.extend(socket_errors)
                elif socket_stops:
                    stop.update(socket_stops)
                    stop.update(triggered)
                else:
                    unknown.append('PID 1 owns the listener but no approved active TCP socket matches port ' + str(port))
                continue
            try:
                content = (proc_root / pid / 'cgroup').read_text()
            except OSError:
                unknown.append('Cannot identify listener PID ' + pid)
                continue
            units = {part for line in content.splitlines() for part in line.split('/')
                     if re.fullmatch(r'[A-Za-z0-9_.@:-]+\.service', part)}
            if 'fashion-desktop.service' in units:
                own = True
            elif any(protected(unit) for unit in units):
                unknown.append('Protected service owns listener PID ' + pid + ': ' + ','.join(sorted(units)))
            elif len(units & (set(allowed_units) | triggered)) == 1:
                stop.update(units & (set(allowed_units) | triggered))
            else:
                unknown.append('Unapproved listener PID ' + pid + ': ' + ','.join(sorted(units)))
    # Unknown ownership prevents the caller from performing any partial migration.
    ordered = sorted(stop, key=lambda unit: (not unit.endswith('.socket'), unit)) if not unknown else []
    return {'stop_units': ordered, 'unknown': unknown, 'own_listener': own}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', required=True, type=int)
    args = parser.parse_args()
    if not 5900 <= args.port <= 5999:
        parser.error('VNC port must be between 5900 and 5999')
    allowed = json.loads(sys.stdin.read())
    if not isinstance(allowed, list) or not all(isinstance(s, str) for s in allowed):
        parser.error('Expected a JSON list of approved GUI systemd services')
    result = subprocess.run(['/usr/bin/ss', '-H', '-ltnp', 'sport = :' + str(args.port)],
                            text=True, capture_output=True, check=True)
    sockets = read_socket_units() if '1' in re.findall(r'pid=(\d+)', result.stdout) else []
    print(json.dumps(listener_plan(result.stdout, Path('/proc'), allowed, sockets, args.port)))


if __name__ == '__main__':
    main()
