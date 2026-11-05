"""Chạy pump() thật của ForcAD với đồng hồ giả; database và Redis được thay bằng bản giả."""
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

STORAGE = Path(__file__).resolve().parents[3] / "platform" / "ForcAD-demo" / "backend" / "lib" / "storage"
START = 1000.0


class Status:
    UP = 101

    def __init__(self, value):
        self.value = value


class Sim:
    """Một cuộc thi giả: giữ trạng thái, đồng hồ, và ghi lại flag được nạp."""

    def __init__(self, lab, check_cost=20.0):
        self.now = START
        self.check_cost = check_cost
        self.enabled = True
        self.row = {"phase": "ready", "tick": 0, "deadline": None, "remaining": None, "prior_phase": None,
                    "error": "", "lab": lab, "started_at": None, "configured": True, "archive_id": None}
        self.placed = set()
        self.tick_starts = {}
        self.finished_at = None
        self.checked_ticks = []
        self.module = self.load()
        self.lab = self.module.lab_profile.get(lab)
        self.teams = [types.SimpleNamespace(id=i) for i in (1, 2, 3)]
        self.tasks = [types.SimpleNamespace(id=10 + i) for i in range(len(self.lab["tasks"]))]
        self.wire()

    def load(self):
        lib = types.ModuleType("lib")
        storage = types.ModuleType("lib.storage")
        storage.__path__ = [str(STORAGE)]
        utils = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        utils.db_cursor.return_value.__enter__.return_value = (MagicMock(), cursor)
        control = types.ModuleType("lib.storage.round_control")
        control.get_enabled = lambda: self.enabled
        control.set_enabled = lambda value: setattr(self, "enabled", value)
        storage.game, storage.teams, storage.tasks = MagicMock(), MagicMock(), MagicMock()
        storage.keys, storage.utils, storage.round_control = MagicMock(), utils, control
        lib.storage, lib.models = storage, MagicMock()
        models = types.ModuleType("lib.models")
        models.Action, models.TaskStatus = MagicMock(), Status
        checkers = types.ModuleType("lib.helpers.checkers")
        checkers.CheckerRunner = MagicMock()
        fakes = {"lib": lib, "lib.storage": storage, "lib.storage.utils": utils, "lib.models": models,
                 "lib.storage.round_control": control, "lib.helpers": types.ModuleType("lib.helpers"),
                 "lib.helpers.checkers": checkers}
        self.fakes = fakes
        with patch.dict(sys.modules, fakes):
            sys.modules.pop("lib.storage.round1", None)
            module = importlib.import_module("lib.storage.round1")
        self.storage = storage
        return module

    def call(self, name):
        """pump() và accepting() import round_control lúc chạy, nên cần module giả."""
        with patch.dict(sys.modules, self.fakes):
            return getattr(self.module, name)()

    def wire(self):
        m = self.module
        m.state = lambda: dict(self.row)
        m.update = self.update
        m.collect_puts = lambda wait=False: None
        m.schedule_puts = self.schedule_puts
        m.verify = self.verify
        m.refresh_flag_cache = lambda: None
        m.time = types.SimpleNamespace(time=lambda: self.now)
        self.storage.game.get_current_game_config.return_value.round_time = self.lab["round_time"]
        self.storage.teams.get_teams.return_value = self.teams
        self.storage.tasks.get_tasks.return_value = self.tasks

    def update(self, **values):
        self.row.update(values)
        if values.get("phase") == "running":
            self.tick_starts[self.row["tick"]] = self.now
        if values.get("phase") == "finished":
            self.finished_at = self.now

    def schedule_puts(self, teams, tasks, tick):
        self.placed.update((team.id, task.id, tick) for team in teams for task in tasks)

    def verify(self, args):
        team, task, tick = args
        if tick not in self.checked_ticks:
            self.checked_ticks.append(tick)
            self.now += self.check_cost
        return team.id, task.id, 101

    def run(self, stop_at=None):
        with patch.dict(sys.modules, self.fakes):
            for _ in range(100000):
                self.module.pump()
                if self.finished_at is not None or (stop_at and self.now >= stop_at):
                    return
                self.now += 0.5
        raise AssertionError("round did not finish")


def test_meko_round_lasts_exactly_fifty_minutes():
    sim = Sim("meko_boutique")
    sim.run()
    assert sim.finished_at - START == pytest.approx(3000, abs=1)
    assert sim.row["tick"] == 10
    for tick in range(1, 11):
        assert sim.tick_starts[tick] - START == pytest.approx((tick - 1) * 300, abs=1)


def test_meko_gives_each_team_five_flags_every_tick():
    sim = Sim("meko_boutique")
    sim.run()
    assert sim.checked_ticks == list(range(1, 11))
    for team in sim.teams:
        for tick in range(1, 11):
            assert sum(1 for t, _, k in sim.placed if t == team.id and k == tick) == 5
    assert len(sim.placed) == 150


def test_slow_checks_do_not_add_up():
    sim = Sim("meko_boutique", check_cost=110)
    sim.run()
    assert sim.finished_at - START <= 3000 + 60
    assert sim.row["tick"] == 10


def test_pause_moves_the_plan_and_keeps_full_length():
    sim = Sim("meko_boutique")
    sim.run(stop_at=START + 700)
    sim.enabled = False
    sim.call("pump")
    assert sim.row["phase"] == "paused"
    sim.now += 100
    sim.enabled = True
    sim.run()
    assert sim.finished_at - START == pytest.approx(3100, abs=2)


def test_flags_are_accepted_until_the_tick_ends():
    sim = Sim("meko_boutique")
    sim.run(stop_at=START + 270)
    assert sim.row["phase"] in ("checking", "ready")
    assert sim.call("accepting") is True
    sim.run(stop_at=START + 3000)
    assert sim.call("accepting") is False


def test_round1_keeps_checks_after_the_tick_and_final_window():
    sim = Sim("round1", check_cost=0)
    sim.run()
    assert sim.finished_at - START == pytest.approx(3600, abs=12)
    assert sim.row["tick"] == 10


def test_schedule_rules_are_lab_independent():
    sim = Sim("meko_boutique")
    rules = sim.module.round_schedule
    lab = {"tasks": ("a", "b"), "round_time": 60, "ticks_per_round": 4, "check_seconds": 0, "drain_ticks": 1}
    assert rules.round_seconds(lab) == 300 and rules.flags_per_tick(lab) == 2
    assert rules.round_seconds(sim.lab) == 3000 and rules.flags_per_tick(sim.lab) == 5
    assert rules.check_at(sim.lab, 300) == 240
