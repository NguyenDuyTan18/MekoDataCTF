"""Chạy checker thật qua HTTP với app local và kiểm tra trạng thái ForcAD."""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "sandbox" / "app"), str(ROOT / "sandbox" / "checker")]
import app as shop  # noqa: E402
import meko_checker as checker  # noqa: E402

STAFF_PASSWORD = "staff-secret-pw"
TASKS = ("idor", "sqli", "upload", "jwt", "backup")
FLAG = "MekoDataCTF{ABCDEFGHIJKLMNOPQRSTUVWXYZ0123}"


class Shop:
    def __init__(self, tmp_path, patches=None):
        self.data = tmp_path / "data"
        self.data.mkdir(parents=True, exist_ok=True)
        if patches:
            (self.data / "patches.json").write_text(json.dumps(patches), encoding="utf-8")
        self.app = shop.create_app({"DATA_DIR": self.data, "TEAM_ID": "team1",
                                    "STAFF_PASSWORD": STAFF_PASSWORD})
        self.server = make_server("127.0.0.1", 0, self.app, threaded=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def run(self, task, action, **kwargs):
        return checker.run(task, action, self.base, team="team1",
                           staff_password=STAFF_PASSWORD, **kwargs)

    def put(self, task, flag=FLAG):
        result = self.run(task, "put", flag=flag)
        assert result["status"] == checker.UP, result
        return result


@pytest.fixture
def lab(tmp_path):
    instance = Shop(tmp_path)
    yield instance
    instance.close()


@pytest.mark.parametrize("task", TASKS)
def test_check_put_get_are_up(lab, task):
    assert lab.run(task, "check")["status"] == checker.UP
    stored = lab.put(task)
    assert json.loads(stored["public"])
    assert lab.run(task, "get", flag=FLAG, private=stored["private"])["status"] == checker.UP


@pytest.mark.parametrize("task", TASKS)
def test_all_patches_keep_service_up(tmp_path, task):
    lab = Shop(tmp_path, {name: True for name in TASKS})
    try:
        assert lab.run(task, "check")["status"] == checker.UP
        stored = lab.put(task)
        assert lab.run(task, "get", flag=FLAG, private=stored["private"])["status"] == checker.UP
    finally:
        lab.close()


@pytest.mark.parametrize("task", TASKS)
def test_older_flags_stay_readable(lab, task):
    flags = [f"MekoDataCTF{{{number:030d}}}" for number in range(3)]
    stored = [lab.put(task, flag) for flag in flags]
    for flag, result in zip(flags, stored):
        assert lab.run(task, "get", flag=flag, private=result["private"])["status"] == checker.UP


@pytest.mark.parametrize("task", ("idor", "sqli", "upload", "jwt"))
def test_public_data_has_no_credentials(lab, task):
    stored = lab.put(task)
    private = json.loads(stored["private"])
    assert private["p"] not in stored["public"] and private["u"] not in stored["public"]


@pytest.mark.parametrize("task", TASKS)
def test_wrong_flag_is_corrupt(lab, task):
    stored = lab.put(task)
    result = lab.run(task, "get", flag="MekoDataCTF{OTHER}", private=stored["private"])
    assert result["status"] == checker.CORRUPT


def wipe(lab, task):
    if task == "upload":
        shutil.rmtree(lab.data / "simulation" / "private")
        (lab.data / "simulation" / "private").mkdir()
        return
    path, statement = {
        "idor": ("shop.sqlite3", "UPDATE orders SET memo=''"),
        "sqli": ("catalog.sqlite3", "DELETE FROM collection_notes"),
        "jwt": ("shop.sqlite3", "DELETE FROM vip_offers"),
        "backup": ("shop.sqlite3", "DELETE FROM reconciliation_notes"),
    }[task]
    with sqlite3.connect(lab.data / path) as db:
        db.execute(statement)


@pytest.mark.parametrize("task", TASKS)
def test_lost_data_is_corrupt(lab, task):
    stored = lab.put(task)
    wipe(lab, task)
    assert lab.run(task, "get", flag=FLAG, private=stored["private"])["status"] == checker.CORRUPT


def test_lost_account_is_corrupt(lab):
    stored = lab.put("idor")
    with sqlite3.connect(lab.data / "shop.sqlite3") as db:
        db.execute("DELETE FROM customers WHERE id<>900")
    assert lab.run("idor", "get", flag=FLAG, private=stored["private"])["status"] == checker.CORRUPT


@pytest.mark.parametrize("task,endpoint", [
    ("idor", "checkout"), ("sqli", "collection_search"), ("upload", "outfit_new"),
    ("jwt", "benefits"), ("backup", "operations_export"),
])
def test_disabled_feature_is_mumble(lab, task, endpoint):
    lab.app.view_functions[endpoint] = lambda **kwargs: ("disabled", 404)
    assert lab.run(task, "check")["status"] == checker.MUMBLE


def test_wrong_team_is_mumble(lab):
    result = checker.run("idor", "check", lab.base, team="team2", staff_password=STAFF_PASSWORD)
    assert result["status"] == checker.MUMBLE


@pytest.mark.parametrize("task", TASKS)
def test_stopped_service_is_down(tmp_path, task):
    lab = Shop(tmp_path)
    base = lab.base
    lab.close()
    result = checker.run(task, "check", base, team="team1", staff_password=STAFF_PASSWORD, timeout=1)
    assert result["status"] == checker.DOWN


def test_gateway_error_is_down(lab):
    lab.app.view_functions["health"] = lambda: ("bad gateway", 502)
    assert lab.run("idor", "check")["status"] == checker.DOWN


def test_bad_private_data_is_check_failed(lab):
    result = lab.run("idor", "get", flag=FLAG, private="not-json")
    assert result["status"] == checker.CHECK_FAILED


def test_missing_staff_password_is_check_failed(lab):
    result = checker.run("backup", "check", lab.base, team="team1")
    assert result["status"] == checker.CHECK_FAILED


def write_config(lab, tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"timeout": 5, "teams": {"10.90.0.11": {
        "team": "team1", "url": lab.base, "staff_password": STAFF_PASSWORD}}}), encoding="utf-8")
    return path


@pytest.mark.parametrize("task", TASKS)
def test_forcad_command_line(lab, tmp_path, task):
    env = {**os.environ, "MEKO_CHECKER_CONFIG": str(write_config(lab, tmp_path))}
    script = str(ROOT / "sandbox" / "checker" / (task + ".py"))

    def call(*args):
        return subprocess.run([sys.executable, script, *args], capture_output=True, text=True,
                              env=env, timeout=30)

    assert call("check", "10.90.0.11").returncode == checker.UP
    stored = call("put", "10.90.0.11", "seed", FLAG, "1")
    assert stored.returncode == checker.UP, stored.stdout + stored.stderr
    assert json.loads(stored.stdout) and json.loads(stored.stderr)
    fetched = call("get", "10.90.0.11", stored.stderr.strip(), FLAG, "1")
    assert fetched.returncode == checker.UP
    assert call("get", "10.90.0.11", "not-json", FLAG, "1").returncode == checker.CHECK_FAILED
    assert call("check").returncode == checker.CHECK_FAILED


def test_agent_answers_collector_request(lab, tmp_path):
    config = write_config(lab, tmp_path)
    request = {"task": "idor", "action": "put", "ip": "10.90.0.11", "key": "seed",
               "locator": "seed", "flag": FLAG}
    proc = subprocess.run([sys.executable, str(ROOT / "sandbox" / "checker" / "agent.py"),
                           "--config", str(config)], input=json.dumps(request), text=True,
                          capture_output=True, timeout=30)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["status"] == checker.UP
