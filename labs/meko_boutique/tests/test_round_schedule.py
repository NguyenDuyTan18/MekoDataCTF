"""Chạy pump() thật của ForcAD với đồng hồ giả; database và Redis được thay bằng bản giả."""
from contextlib import nullcontext
import importlib
import json
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
        self.row["tick"] = self.lab.get("tick_offset", 0)
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
        storage.game, storage.teams, storage.tasks, storage.caching = (
            MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
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


@pytest.mark.parametrize("lab,first,last,task_count", [
    ("full_rounds", 1, 10, 5),
    ("full_rounds_crypto", 11, 20, 3),
])
def test_full_rounds_preview_then_fifty_minutes(lab, first, last, task_count):
    sim = Sim(lab)
    sim.module.configured = lambda: True
    sim.call("pump")
    assert sim.row["phase"] == "preview" and sim.row["tick"] == first - 1
    assert sim.row["deadline"] == START + 600
    assert sim.call("accepting") is False
    sim.now = START + 599
    sim.call("pump")
    assert not sim.placed and not sim.checked_ticks
    sim.now = START + 600
    sim.run()
    assert sim.tick_starts[first] == pytest.approx(START + 600, abs=1)
    assert sim.checked_ticks == list(range(first, last + 1))
    assert len(sim.placed) == 3 * task_count * (last - first + 1)
    assert sim.finished_at == pytest.approx(START + 3600, abs=1)


def test_full_rounds_preview_can_pause_and_resume():
    sim = Sim("full_rounds")
    sim.call("pump")
    sim.now += 100
    sim.enabled = False
    sim.call("pump")
    assert sim.row["phase"] == "paused" and sim.row["remaining"] == 500
    sim.now += 30
    sim.enabled = True
    sim.call("pump")
    assert sim.row["phase"] == "preview" and sim.row["deadline"] == START + 630
    assert not sim.placed


@pytest.mark.parametrize("phase", ["running", "finished"])
def test_full_rounds_switch_only_after_web_finishes(phase):
    sim = Sim("full_rounds")
    m = sim.module
    conn, cursor = m.utils.db_cursor.return_value.__enter__.return_value
    cursor.fetchone.side_effect = [
        {"enabled": False, "resetting": False},
        {"configured": True, "lab": "full_rounds", "phase": phase, "tick": 10},
    ]
    target = m.lab_profile.get("full_rounds_crypto")
    cursor.fetchall.return_value = [{"checker": target["prefix"] + task + ".py"} for task in target["tasks"]]
    if phase == "running":
        with pytest.raises(ValueError):
            m.next_full_round("full_rounds_crypto", target)
        conn.commit.assert_not_called()
        return
    m.next_full_round("full_rounds_crypto", target)
    conn.commit.assert_called_once()
    queries = [call.args[0] for call in cursor.execute.call_args_list]
    assert any("phase='ready'" in query for query in queries)
    assert not any("DELETE" in query or "UPDATE Teams" in query for query in queries)
    sim.storage.game.update_game_state.assert_called_once_with(for_round=10)


def test_slots_can_start_in_reverse_order_and_resume_with_the_same_tick_clock():
    sim = Sim("meko_boutique")
    m = sim.module
    sim.enabled = False
    m.configured = lambda: True
    m.lifecycle_lock = lambda: nullcontext(True)
    conn, cursor = m.utils.db_cursor.return_value.__enter__.return_value
    roster = [{"ip": ip} for ip in sim.lab["teams"]]

    def execute(sql, params=()):
        if sql.startswith("SELECT enabled,resetting"):
            cursor.fetchone.return_value = {"enabled": sim.enabled, "resetting": False}
        elif sql.startswith("SELECT * FROM MekodataRound1"):
            cursor.fetchone.return_value = dict(sim.row)
        elif sql.startswith("SELECT real_round"):
            cursor.fetchone.return_value = {"real_round": sim.row["tick"]}
        elif sql.startswith("SELECT EXISTS"):
            cursor.fetchone.return_value = {"has_flags": False}
        elif sql.startswith("SELECT checker"):
            cursor.fetchall.return_value = [{"checker": path} for path in params[0]]
        elif sql.startswith("SELECT ip"):
            cursor.fetchall.return_value = roster
        elif sql.startswith("UPDATE MekodataRound1 SET configured=true"):
            slot, inactive, *values = params
            sim.row.update(zip(m.SLOT_FIELDS, values))
            sim.row.update(slot=slot, inactive_slots=json.loads(inactive))
        elif sql.startswith("UPDATE MekodataRoundControl SET enabled=true"):
            sim.enabled = True

    cursor.execute.side_effect = execute
    m._flush_score_cache = MagicMock()
    m._refresh_slot_cache = MagicMock()
    with pytest.raises(ValueError, match="hai lab khác nhau"):
        m.configure_slots({"1": "full_rounds", "2": "full_rounds"})
    with pytest.raises(ValueError, match="không được hỗ trợ"):
        m.configure_slots({"1": "full_rounds", "2": []})
    conn.commit.assert_not_called()

    # Invert the Full Rounds defaults to make sure a profile does not impose its slot.
    m.configure_slots({"1": "full_rounds_crypto", "2": "full_rounds"})
    assert m.profile()["round"] == 1
    m.start_slot(2)
    assert (sim.row["lab"], m.profile()["round"], sim.row["tick"]) == ("full_rounds", 2, 10)
    with pytest.raises(ValueError, match="Dừng vòng hiện tại"):
        m.start_slot(1)
    sim.call("pump")
    assert sim.row["phase"] == "preview" and not sim.placed
    sim.now += 600
    sim.call("pump")
    assert {tick for _, _, tick in sim.placed} == {11}
    sim.now += 100
    sim.enabled = False
    with pytest.raises(ValueError, match="chờ checker"):
        m.start_slot(1)
    sim.call("pump")
    assert sim.row["phase"] == "paused" and sim.row["remaining"] == 200
    m.start_slot(1)
    assert sim.row["tick"] == 0 and m.profile()["crypto_seed"]
    sim.call("pump")
    assert sim.row["phase"] == "preview" and not sim.call("accepting")
    sim.now += 50
    sim.enabled = False
    sim.call("pump")
    m.start_slot(2)
    assert m.slot_states(sim.row)["1"]["remaining"] == 550
    sim.call("pump")
    assert sim.row["tick"] == 11 and sim.row["deadline"] == sim.now + 200
    assert m._refresh_slot_cache.call_args_list[-1].args == (11,)


def test_slot_score_windows_use_saved_tick_and_only_combine_matching_rosters():
    sim = Sim("full_rounds")
    m = sim.module
    first = m.fresh_slot("full_rounds", 1)
    second = m.fresh_slot("full_rounds_crypto", 2)
    second.update(phase="paused", tick=16)
    sim.row.update(first, slot=1, inactive_slots={"2": second})
    _, cursor = m.utils.db_cursor.return_value.__enter__.return_value
    m.scores(sim.row)
    windows = json.loads(cursor.execute.call_args.args[1]["windows"])
    assert {(w["lo"], w["hi"], w["at_tick"], w["closed"]) for w in windows} == {
        (1, 10, 0, False), (11, 20, 16, False)
    }
    sim.row["inactive_slots"]["2"] = m.fresh_slot("round1", 2)
    assert set(m.scoring_slots(sim.row)) == {"1"}


def test_slot_between_ticks_is_paused_before_it_can_switch():
    sim = Sim("full_rounds")
    m = sim.module
    sim.row.update(slot=1, inactive_slots={"2": m.fresh_slot("full_rounds_crypto", 2)},
                   phase="ready", tick=4, deadline=START)
    sim.now = START + 5
    sim.enabled = False
    assert not m.slot_can_start(sim.row)
    sim.call("pump")
    assert sim.row["phase"] == "paused" and sim.row["remaining"] == 0
    assert m.slot_can_start(sim.row)
