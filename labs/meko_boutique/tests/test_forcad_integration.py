"""Chạy đường ForcAD thật: script → rpc → collector → agent → app. Chỉ thay SSH bằng lệnh local."""
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from test_checker import FLAG, ROOT, STAFF_PASSWORD, TASKS, Shop, checker

WORKSPACE = ROOT.parents[1]
FORCAD = WORKSPACE / "platform" / "ForcAD-demo"
SCRIPTS = FORCAD / "checkers" / "meko_boutique"
TEAM_IP = "10.90.0.11"

os.environ["MEKO_LAB"] = "meko_boutique"
sys.path.insert(0, str(FORCAD))
import collect_checker as collector  # noqa: E402


def load_profiles():
    spec = importlib.util.spec_from_file_location(
        "lab_profile", FORCAD / "backend" / "lib" / "storage" / "lab_profile.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lab_json_matches_backend_profile_and_topology():
    lab = collector.LAB
    profile = load_profiles().get("meko_boutique")
    assert lab["name"] == "meko_boutique" and collector.AGENT_TIMEOUT == 35
    assert tuple(lab["tasks"]) == profile["tasks"]
    assert {team["ip"]: team["name"] for team in lab["teams"]} == profile["teams"]
    topology = (ROOT / "sandbox" / "topology.yml").read_text(encoding="utf-8")
    assert "- name: checker" in topology
    assert all(ip in topology for ip in profile["teams"])
    assert all((SCRIPTS / (task + ".py")).is_file() for task in lab["tasks"])
    assert "/opt/meko-checker/agent.py" in collector.AGENT_COMMAND


def test_round1_stays_the_default_profile():
    profiles = load_profiles()
    assert profiles.DEFAULT == "round1"
    round1 = profiles.get("round1")
    assert round1["tasks"] == ("idor", "sqli", "upload") and len(round1["teams"]) == 4
    assert round1["round_time"] == 300
    assert profiles.get("meko_boutique")["round_time"] == 300
    for name in profiles.PROFILES:  # Một round 50 phút.
        assert profiles.get(name)["round_time"] * profiles.get(name)["ticks_per_round"] == 3000
    with pytest.raises(ValueError):
        profiles.get("unknown")
    body = "A" * 30
    assert len(round1["flag_template"].format(letter="I", body=body)) == 32  # Giới hạn của webservice round1.
    assert profiles.get("meko_boutique")["flag_template"].format(letter="I", body=body) == "MekoDataCTF{" + body + "}"


def test_flag_column_fits_every_lab_format():
    schema = (FORCAD / "backend" / "scripts" / "create_tables.sql").read_text(encoding="utf-8")
    limit = int(re.search(r"flag\s+VARCHAR\((\d+)\)", schema).group(1))
    lifecycle = (FORCAD / "backend" / "lib" / "storage" / "round1.py").read_text(encoding="utf-8")
    assert f"ALTER COLUMN flag TYPE VARCHAR({limit})" in lifecycle
    profiles = load_profiles()
    for name in profiles.PROFILES:
        flag = profiles.get(name)["flag_template"].format(letter="M", body="A" * 30, hexbody="a" * 32)
        assert len(flag) <= limit


@pytest.mark.parametrize("name,path", [("full_rounds", "full_rounds"), ("full_rounds_crypto", "full_rounds/round2")])
def test_full_rounds_routes_to_the_expected_agent(name, path, tmp_path, monkeypatch):
    profile = load_profiles().get(name)
    lab = collector.labconfig.load(path)
    assert lab["name"] == name
    assert tuple(lab["tasks"]) == profile["tasks"]
    assert {t["ip"]: t["name"] for t in lab["teams"]} == profile["teams"]
    assert all((FORCAD / profile["prefix"].lstrip("/") / (task + ".py")).is_file() for task in lab["tasks"])
    assert lab["checker_host"] == "checker"
    expected = "/opt/crypto-checker/agent.py" if name.endswith("_crypto") else "/opt/meko-checker/agent.py"
    assert expected in lab["agent_command"]

    def fake_ssh(argv, **options):
        assert argv[-2:] == ["checker", lab["agent_command"]]
        assert json.loads(options["input"]) == payload
        return subprocess.CompletedProcess(argv, 0, stdout='{"status":101,"public":"UP","private":""}')

    monkeypatch.setattr(collector.subprocess, "run", fake_ssh)
    identity = "a" * 32
    payload = {"task": lab["tasks"][0], "ip": TEAM_IP, "action": "check"}
    request = tmp_path / (identity + ".request.json")
    request.write_text(json.dumps({"id": identity, "expires": time.time() + 40, "payload": payload}))
    collector.process_rpc(request, lab)
    reply = tmp_path / (identity + ".response.json")
    assert json.loads(reply.read_text())["status"] == 101


@pytest.fixture
def route(tmp_path, monkeypatch):
    """App local, cấu hình agent, và một vòng collector thật xử lý thư mục rpc."""
    lab = Shop(tmp_path)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"timeout": 5, "teams": {TEAM_IP: {
        "team": "team1", "url": lab.base, "staff_password": STAFF_PASSWORD}}}), encoding="utf-8")
    agent = [sys.executable, str(ROOT / "sandbox" / "checker" / "agent.py"), "--config", str(config)]
    monkeypatch.setattr(collector.labconfig, "ssh", lambda *args: agent)
    collector.RPC_ROOT.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()

    def pump():
        while not stop.is_set():
            for path in collector.RPC_ROOT.glob("*.request.json"):
                collector.process_rpc(path)
            time.sleep(0.05)

    thread = threading.Thread(target=pump, daemon=True)
    thread.start()
    yield lab
    stop.set()
    thread.join(timeout=5)
    lab.close()


def forcad_call(task, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / (task + ".py")), *args],
                          capture_output=True, text=True, timeout=45)


@pytest.mark.parametrize("task", TASKS)
def test_forcad_script_reaches_app_through_collector(route, task):
    assert forcad_call(task, "check", TEAM_IP).returncode == checker.UP
    stored = forcad_call(task, "put", TEAM_IP, "a1b2c3", FLAG, "1")
    assert stored.returncode == checker.UP, stored.stdout + stored.stderr
    assert json.loads(stored.stdout) and json.loads(stored.stderr)
    fetched = forcad_call(task, "get", TEAM_IP, stored.stderr.strip(), FLAG, "1")
    assert fetched.returncode == checker.UP
    wrong = forcad_call(task, "get", TEAM_IP, stored.stderr.strip(), "MekoDataCTF{OTHER}", "1")
    assert wrong.returncode == checker.CORRUPT


def test_unknown_team_is_rejected_by_collector(route):
    assert forcad_call("idor", "check", "10.90.0.99").returncode == checker.CHECK_FAILED


def test_stopped_collector_is_not_blamed_on_team(monkeypatch, tmp_path):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("meko_common", SCRIPTS / "common.py")
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    monkeypatch.setattr(common, "ROOT", tmp_path)
    assert common.rpc({"task": "idor"}, timeout=0.2)["status"] == checker.CHECK_FAILED
