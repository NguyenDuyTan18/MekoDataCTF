"""Mô phỏng nhiều tick với app thật: flag đổi theo tick, code và bản vá không đổi."""
import hashlib
import json

import pytest

from test_checker import ROOT, TASKS, Shop, checker


def tick_flag(tick):
    return f"MekoDataCTF{{{tick:030d}}}"


def source_digest():
    return hashlib.sha256((ROOT / "sandbox" / "app" / "app.py").read_bytes()).hexdigest()


@pytest.fixture
def lab(tmp_path):
    instance = Shop(tmp_path)
    yield instance
    instance.close()


@pytest.mark.parametrize("task", TASKS)
def test_each_tick_adds_a_flag_and_live_flags_stay_readable(lab, task):
    source = source_digest()
    placed = []
    for tick in range(1, 6):
        placed.append((tick_flag(tick), lab.put(task, tick_flag(tick))))
        assert lab.run(task, "check")["status"] == checker.UP
        for flag, stored in placed[-3:]:  # Tick này và 2 tick trước còn hiệu lực.
            result = lab.run(task, "get", flag=flag, private=stored["private"])
            assert result["status"] == checker.UP
    assert source_digest() == source
    assert len({stored["public"] for _, stored in placed}) == 5


@pytest.mark.parametrize("task", TASKS)
def test_flags_survive_service_restart_between_ticks(tmp_path, task):
    first = Shop(tmp_path)
    stored = first.put(task, tick_flag(1))
    first.close()
    second = Shop(tmp_path)
    try:
        result = second.run(task, "get", flag=tick_flag(1), private=stored["private"])
        assert result["status"] == checker.UP
        second.put(task, tick_flag(2))
    finally:
        second.close()


@pytest.mark.parametrize("flag", ["MekoDataCTF{ABCDEFGHIJKLMNOPQRSTUVWXYZ0123}",
                                  "MABCDEFGHIJKLMNOPQRSTUVWXYZ0123="])
@pytest.mark.parametrize("task", TASKS)
def test_both_forcad_flag_formats_are_stored(lab, task, flag):
    stored = lab.put(task, flag)
    assert lab.run(task, "get", flag=flag, private=stored["private"])["status"] == checker.UP


def test_patches_stay_in_place_across_ticks(tmp_path):
    patches = {name: True for name in TASKS}
    lab = Shop(tmp_path, patches)
    path = lab.data / "patches.json"
    before = path.read_bytes()
    try:
        for tick in range(1, 4):
            for task in TASKS:
                lab.put(task, tick_flag(tick))
    finally:
        lab.close()
    assert path.read_bytes() == before
    assert json.loads(before) == patches
