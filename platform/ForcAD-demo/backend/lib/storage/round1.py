"""Round-one lifecycle; reuse ForcAD Flag, CheckerRunner, storage and judge."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import secrets
import time

from lib import models, storage
from lib.helpers.checkers import CheckerRunner
from lib.models import Action, TaskStatus
from . import lab_profile, round_schedule, utils
import logging

logger = logging.getLogger(__name__)
PUT_RETRY_SECONDS = 10
_put_pool = ThreadPoolExecutor(max_workers=12)
_put_jobs = {}
_put_retry = {}
SLOT_FIELDS = ('lab', 'phase', 'tick', 'deadline', 'remaining', 'prior_phase',
               'started_at', 'finished_at', 'last_probe', 'error')
SWITCHABLE_PHASES = ('ready', 'paused', 'finished')
LIFECYCLE_LOCK = 713109


def collect_puts(wait=False):
    for key, job in list(_put_jobs.items()):
        if not wait and not job.done():
            continue
        try:
            job.result()
        except Exception:
            logger.exception('PUT worker failed team/task/tick=%s', key)
        del _put_jobs[key]
        _put_retry[key] = time.time() + PUT_RETRY_SECONDS


def schedule_puts(teams, tasks, tick):
    collect_puts()
    with utils.db_cursor() as (_, c):
        c.execute('SELECT team_id,task_id FROM MekodataPlacements WHERE tick=%s AND flag_id IS NOT NULL', (tick,))
        placed = set(c.fetchall())
    now = time.time()
    for team in teams:
        for task in tasks:
            key = (team.id, task.id, tick)
            if (team.id, task.id) not in placed and key not in _put_jobs and now >= _put_retry.get(key, 0):
                _put_jobs[key] = _put_pool.submit(put_flag, (team, task, tick))



def ensure_schema():
    with utils.db_cursor() as (conn, c):
        c.execute('''CREATE TABLE IF NOT EXISTS MekodataRound1 (
            id INTEGER PRIMARY KEY CHECK(id=1), configured BOOLEAN NOT NULL DEFAULT FALSE,
            phase TEXT NOT NULL DEFAULT 'ready', tick INTEGER NOT NULL DEFAULT 0,
            deadline DOUBLE PRECISION, remaining DOUBLE PRECISION,
            prior_phase TEXT, error TEXT NOT NULL DEFAULT '', archive_id TEXT)''')
        c.execute('ALTER TABLE MekodataRound1 ADD COLUMN IF NOT EXISTS archive_id TEXT')
        c.execute("ALTER TABLE MekodataRound1 ADD COLUMN IF NOT EXISTS lab TEXT NOT NULL DEFAULT 'round1'")
        c.execute('ALTER TABLE MekodataRound1 ADD COLUMN IF NOT EXISTS started_at DOUBLE PRECISION')
        c.execute('ALTER TABLE MekodataRound1 ADD COLUMN IF NOT EXISTS finished_at DOUBLE PRECISION')
        c.execute("UPDATE MekodataRound1 SET finished_at=deadline WHERE phase='finished' AND finished_at IS NULL AND deadline IS NOT NULL")
        c.execute('ALTER TABLE MekodataRound1 ADD COLUMN IF NOT EXISTS last_probe DOUBLE PRECISION')
        c.execute('ALTER TABLE MekodataRound1 ADD COLUMN IF NOT EXISTS slot INTEGER')
        c.execute("ALTER TABLE MekodataRound1 ADD COLUMN IF NOT EXISTS inactive_slots JSONB NOT NULL DEFAULT '{}'::jsonb")
        # Flag formats differ per lab; the native column only fits 32 characters.
        c.execute('ALTER TABLE Flags ALTER COLUMN flag TYPE VARCHAR(64)')
        c.execute('''CREATE TABLE IF NOT EXISTS MekodataArchives (
            id TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            snapshot JSONB NOT NULL)''')
        c.execute('''UPDATE MekodataRound1 r
                     SET finished_at=(a.snapshot #>> '{tables,MekodataRound1,0,deadline}')::double precision
                     FROM MekodataArchives a WHERE r.id=1 AND r.archive_id=a.id AND r.phase='archived'
                     AND r.finished_at IS NULL
                     AND a.snapshot #>> '{tables,MekodataRound1,0,phase}' = 'finished'
                     AND a.snapshot #>> '{tables,MekodataRound1,0,deadline}' IS NOT NULL''')
        c.execute('INSERT INTO MekodataRound1(id) VALUES(1) ON CONFLICT DO NOTHING')
        c.execute('''CREATE TABLE IF NOT EXISTS MekodataPlacements (
            team_id INTEGER REFERENCES Teams(id), task_id INTEGER REFERENCES Tasks(id),
            tick INTEGER NOT NULL, seed TEXT NOT NULL, flag_id INTEGER REFERENCES Flags(id),
            PRIMARY KEY(team_id,task_id,tick))''')
        c.execute('''CREATE TABLE IF NOT EXISTS MekodataSLA (
            team_id INTEGER REFERENCES Teams(id), tick INTEGER NOT NULL,
            status INTEGER NOT NULL, points INTEGER NOT NULL CHECK(points IN(0,1)),
            PRIMARY KEY(team_id,tick))''')
        # Theo dõi health liên tục trong tick (mô hình CyberRangeCZ): mỗi probe ~25-30s;
        # downs>0 trong tick => MẤT TOÀN BỘ SLA của tick đó.
        c.execute('''CREATE TABLE IF NOT EXISTS MekodataTickHealth (
            team_id INTEGER REFERENCES Teams(id), tick INTEGER NOT NULL,
            probes INTEGER NOT NULL DEFAULT 0, downs INTEGER NOT NULL DEFAULT 0,
            last_status INTEGER, PRIMARY KEY(team_id,tick))''')
        conn.commit()


def state():
    with utils.db_cursor(dict_cursor=True) as (_, c):
        c.execute('SELECT * FROM MekodataRound1 WHERE id=1')
        return dict(c.fetchone())


def profile(lifecycle=None):
    """Lab of the prepared competition; a database from before this column means round1."""
    lifecycle = state() if lifecycle is None else lifecycle
    name = lifecycle.get('lab') or lab_profile.DEFAULT
    if lifecycle.get('slot'):
        return lab_profile.for_slot(name, lifecycle['slot'])
    return lab_profile.get(name)


def fresh_slot(lab, slot):
    return dict.fromkeys(SLOT_FIELDS) | {
        'lab': lab, 'phase': 'ready', 'tick': lab_profile.for_slot(lab, slot)['tick_offset'], 'error': '',
    }


def slot_states(lifecycle):
    if not lifecycle.get('slot'):
        return {}
    return {**lifecycle['inactive_slots'],
            str(lifecycle['slot']): {key: lifecycle[key] for key in SLOT_FIELDS}}


def scoring_slots(lifecycle):
    """Combine results only for slots whose teams have the same identity in ForcAD."""
    roster = profile(lifecycle)['teams']
    return {slot: row for slot, row in slot_states(lifecycle).items()
            if lab_profile.get(row['lab'])['teams'].keys() == roster.keys()}


def slot_can_configure(lifecycle):
    if lifecycle['phase'] == 'archived' and lifecycle.get('archive_id'):
        return True
    if lifecycle['phase'] != 'ready':
        return False
    saved = slot_states(lifecycle)
    if not saved:
        return lifecycle['tick'] == 0 and lifecycle['deadline'] is None
    return all(row['phase'] == 'ready' and row['deadline'] is None
               and row['tick'] == lab_profile.for_slot(row['lab'], int(slot))['tick_offset']
               for slot, row in saved.items())


def slot_can_start(lifecycle):
    return lifecycle['phase'] in SWITCHABLE_PHASES and not (
        lifecycle['phase'] == 'ready' and lifecycle['deadline'] is not None)


@contextmanager
def lifecycle_lock(required=True):
    # Stop can still close the gate while the ticker waits for checker results.
    with utils.db_cursor() as (conn, c):
        c.execute('SELECT pg_try_advisory_xact_lock(%s)', (LIFECYCLE_LOCK,))
        try:
            locked = c.fetchone()[0]
            if required and not locked:
                raise ValueError('Checker đang hoàn tất lượt chạy. Hãy thử lại.')
            yield locked
        finally:
            conn.rollback()


def _checker_paths(settings):
    return [settings['prefix'] + task + '.py' for task in settings['tasks']]


def _write_slot(c, saved, slot):
    current = saved[str(slot)]
    c.execute('UPDATE MekodataRound1 SET configured=true,archive_id=NULL,slot=%s,inactive_slots=%s::jsonb,'
              + ','.join(key + '=%s' for key in SLOT_FIELDS) + ' WHERE id=1',
              (slot, json.dumps({key: row for key, row in saved.items() if key != str(slot)}),
               *(current[key] for key in SLOT_FIELDS)))
    settings = lab_profile.for_slot(current['lab'], slot)
    paths = _checker_paths(settings)
    c.execute('SELECT checker FROM Tasks WHERE checker=ANY(%s)', (paths,))
    if sorted(row['checker'] for row in c.fetchall()) != sorted(paths):
        raise ValueError('Thiếu hoặc trùng checker cho lab ' + settings['title'] + '.')
    ips = list(settings['teams'])
    c.execute('SELECT ip FROM Teams WHERE ip=ANY(%s)', (ips,))
    if sorted(row['ip'] for row in c.fetchall()) != sorted(ips):
        raise ValueError('Thiếu hoặc trùng IP đội cho lab ' + settings['title'] + '.')
    c.execute('UPDATE Tasks SET active=COALESCE(checker=ANY(%s),false)', (paths,))
    c.execute('UPDATE Teams SET active=(ip=ANY(%s))', (ips,))
    c.execute('UPDATE GameConfig SET real_round=%s,round_time=%s,flag_lifetime=2,game_running=true WHERE id=1',
              (current['tick'], settings['round_time']))
    return current['tick']


def _register_slot(c, settings):
    """Register missing teams and tasks, using the same models as legacy preparation."""
    c.execute('SELECT ip FROM Teams WHERE ip=ANY(%s)', (list(settings['teams']),))
    rows = c.fetchall()
    known = {row['ip'] for row in rows}
    if len(rows) != len(known):
        raise ValueError('Trùng IP đội cho lab ' + settings['title'] + '.')
    for ip, name in settings['teams'].items():
        if ip in known:
            continue
        if not settings['create_teams']:
            raise ValueError('Cần đăng ký đội IP ' + ip + ' cho lab ' + settings['title'] + '.')
        team = models.Team(name=name, ip=ip, token=models.Team.generate_token(), active=False)
        c.execute(team.get_insert_query(), team.to_dict())
        team_id = c.fetchone()['id']
        c.execute('INSERT INTO TeamTasks(task_id,team_id,score,status) SELECT id,%s,default_score,-1 FROM Tasks',
                  (team_id,))
    paths = _checker_paths(settings)
    c.execute('SELECT checker FROM Tasks WHERE checker=ANY(%s)', (paths,))
    existing = [row['checker'] for row in c.fetchall()]
    if len(existing) != len(set(existing)):
        raise ValueError('Trùng checker cho lab ' + settings['title'] + '.')
    for kind, path in zip(settings['tasks'], paths):
        if path in existing:
            continue
        task = models.Task(name=settings['title'] + '/' + kind.upper(), checker=path, gets=1, puts=1,
                           places=1, checker_timeout=45, checker_type='hackerdom_pfr',
                           env_path='', default_score=0, get_period=0, active=False)
        c.execute(task.get_insert_query(), task.to_dict())
        task_id = c.fetchone()['id']
        c.execute('INSERT INTO TeamTasks(task_id,team_id,score,status) SELECT %s,id,0,-1 FROM Teams', (task_id,))


def configure_slots(labs):
    if not isinstance(labs, dict) or set(labs) != {'1', '2'}:
        raise ValueError('Cần chọn lab cho cả hai vòng.')
    profiles = [lab_profile.get(name) for name in labs.values()]
    if profiles[0]['prefix'] == profiles[1]['prefix']:
        raise ValueError('Chọn hai lab khác nhau để mỗi vòng có checker và điểm riêng.')
    with lifecycle_lock():
        with utils.db_cursor(dict_cursor=True) as (conn, c):
            c.execute('SELECT enabled,resetting FROM MekodataRoundControl WHERE id=1 FOR UPDATE')
            gate = c.fetchone()
            c.execute('SELECT * FROM MekodataRound1 WHERE id=1 FOR UPDATE')
            current = c.fetchone()
            if gate['enabled'] or gate['resetting'] or not slot_can_configure(current):
                raise ValueError('Dừng và lưu hồ sơ cuộc thi đang có trước khi đổi cấu hình hai vòng.')
            if current['phase'] == 'archived':
                _clear_scores(c)
            else:
                c.execute('SELECT real_round FROM GameConfig WHERE id=1')
                if c.fetchone()['real_round'] != current['tick']:
                    raise ValueError('Hãy reset bản health về tick 0 trước khi cấu hình hai vòng.')
                c.execute('SELECT EXISTS(SELECT 1 FROM Flags) AS has_flags')
                if c.fetchone()['has_flags']:
                    raise ValueError('Hãy lưu hồ sơ cuộc thi đang có trước khi đổi cấu hình hai vòng.')
            for settings in profiles:
                _register_slot(c, settings)
            saved = {slot: fresh_slot(name, int(slot)) for slot, name in labs.items()}
            _write_slot(c, saved, 1)
            conn.commit()
        _flush_score_cache(drop_tokens=False)


def start_slot(slot):
    if type(slot) is not int or slot not in (1, 2):
        raise ValueError('Chỉ có Round 1 và Round 2.')
    with lifecycle_lock():
        with utils.db_cursor(dict_cursor=True) as (conn, c):
            c.execute('SELECT enabled,resetting FROM MekodataRoundControl WHERE id=1 FOR UPDATE')
            gate = c.fetchone()
            c.execute('SELECT * FROM MekodataRound1 WHERE id=1 FOR UPDATE')
            current = c.fetchone()
            saved = slot_states(current)
            if not saved:
                raise ValueError('Hãy lưu cấu hình hai vòng trước.')
            if gate['enabled'] or gate['resetting'] or not slot_can_start(current):
                raise ValueError('Dừng vòng hiện tại và chờ checker hoàn tất trước khi chọn vòng.')
            if saved[str(slot)]['phase'] == 'finished':
                raise ValueError('Vòng này đã kết thúc. Dùng Bắt đầu lại để mở lượt thi mới.')
            tick = _write_slot(c, saved, slot)
            c.execute('UPDATE MekodataRoundControl SET enabled=true,updated_at=now() WHERE id=1')
            conn.commit()
        try:
            _refresh_slot_cache(tick)
        except Exception:
            from . import round_control
            round_control.set_enabled(False)
            raise


def _refresh_slot_cache(tick):
    storage.caching.flush_tasks_cache()
    storage.caching.flush_teams_cache()
    redis = utils.RedisStorage.get()
    redis.delete(storage.keys.CacheKeys.game_config(), storage.keys.CacheKeys.attack_data())
    redis.set(storage.keys.CacheKeys.current_round(), tick)
    refresh_flag_cache()
    storage.game.update_attack_data(tick)
    storage.game.update_game_state(for_round=tick)


def configured():
    # This table is created before the ticker or receiver starts using it.
    with utils.db_cursor() as (_, c):
        c.execute("SELECT to_regclass('mekodataround1')")
        if c.fetchone()[0] is None:
            return False
        c.execute('SELECT configured FROM MekodataRound1 WHERE id=1')
        row = c.fetchone()
        return bool(row and row[0])


def update(**values):
    allowed = {'phase', 'tick', 'deadline', 'remaining', 'prior_phase', 'error', 'configured', 'archive_id', 'lab', 'started_at', 'finished_at', 'last_probe'}
    if not values or not set(values) <= allowed:
        raise ValueError('Invalid state update')
    with utils.db_cursor() as (conn, c):
        c.execute('UPDATE MekodataRound1 SET ' + ','.join(k + '=%s' for k in values) + ' WHERE id=1', tuple(values.values()))
        conn.commit()


def accepting():
    if not configured():
        return True
    from . import round_control
    s = state()
    return (round_control.get_enabled() and s['phase'] in ('running', 'checking', 'ready', 'draining')
            and bool(s['deadline']) and time.time() < s['deadline'])


def refresh_flag_cache():
    """Reload live flags on the next lookup.

    Each flag key expires, but the "cached" marker does not: after a long pause or slow
    ticks a live flag would otherwise be reported invalid.
    """
    utils.RedisStorage.get().delete(storage.keys.CacheKeys.flags_cached())


def leave_archived_lab(lab):
    """Clear an archived competition of another lab; its snapshot stays in MekodataArchives."""
    with utils.db_cursor() as (conn, c):
        try:
            c.execute('SELECT phase,archive_id,lab FROM MekodataRound1 WHERE id=1 FOR UPDATE')
            phase, archive_id, current = c.fetchone()
            if phase != 'archived' or not archive_id or current == lab:
                conn.rollback()
                return
            c.execute('SELECT enabled FROM MekodataRoundControl WHERE id=1 FOR UPDATE')
            if c.fetchone()[0]:
                raise ValueError('Dừng cuộc thi trước khi đổi lab.')
            _clear_scores(c)
            c.execute('UPDATE GameConfig SET real_round=0 WHERE id=1')
            c.execute("UPDATE MekodataRound1 SET configured=false,phase='ready',tick=0,started_at=NULL,deadline=NULL,remaining=NULL,prior_phase=NULL,error='',archive_id=NULL WHERE id=1")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    _flush_score_cache(drop_tokens=False)


def prepare(lab=lab_profile.DEFAULT):
    """Explicit admin preparation, only on an empty, stopped competition."""
    from . import round_control
    chosen = lab_profile.get(lab)
    ips = list(chosen['teams'])
    ensure_schema()
    if state().get('slot'):
        raise ValueError('Cuộc thi đang dùng hai vòng cấu hình. Hãy chọn Round 1 hoặc Round 2.')
    if 'first_lab' in chosen:
        next_full_round(lab, chosen)
        return
    if 'previous_lab' in chosen:
        previous = state()
        retrying = not previous['configured'] and previous['phase'] == 'ready'
        if previous['phase'] != 'archived' and not retrying:
            raise ValueError('Lưu hồ sơ vòng 1 trước khi chuẩn bị Crypto AD.')
        if lab_profile.transition_delay(chosen, previous, time.time()):
            raise ValueError('Crypto AD chỉ có thể bắt đầu sau khi vòng 1 kết thúc đủ 10 phút.')
    leave_archived_lab(lab)
    if round_control.get_enabled() or storage.game.get_real_round_from_db() != 0:
        raise ValueError('Dừng và reset bản health về tick 0 trước khi chuẩn bị Round 1.')
    with utils.db_cursor() as (_, c):
        c.execute('SELECT phase FROM MekodataRound1 WHERE id=1')
        if c.fetchone()[0] in ('archived', 'recreating'):
            raise ValueError('Cuộc thi cũ đang đóng hoặc tái tạo; hãy hoàn tất quy trình từ hồ sơ lưu trước.')
    with utils.db_cursor() as (_, c):
        c.execute('SELECT COUNT(*) FROM Flags')
        if c.fetchone()[0]:
            raise ValueError('Đã có flag. Không tự xóa dữ liệu thi; cần lưu trữ cuộc thi cũ trước.')
        c.execute('SELECT ip FROM Teams WHERE ip = ANY(%s)', (ips,))
        known = {row[0] for row in c.fetchall()}
        c.execute('SELECT COUNT(*) FROM Teams WHERE active AND ip = ANY(%s)', (ips,))
        active = c.fetchone()[0]
    if chosen['create_teams']:
        for ip in ips:
            if ip not in known:
                storage.teams.create_team(models.Team(id=None, name=chosen['teams'][ip], ip=ip,
                                                      token=models.Team.generate_token(),
                                                      highlighted=False, active=True))
    elif active != len(ips):
        raise ValueError(f'Cần đủ {len(ips)} đội có IP {ips[0]}–{ips[-1].rsplit(".", 1)[-1]}.')
    # Reuse the native task registration so TeamTasks/cache are initialized correctly.
    tasks = storage.tasks.get_all_tasks()
    profiles = [chosen]
    if 'next_lab' in chosen:
        profiles.append(lab_profile.get(chosen['next_lab']))
    for index, settings in enumerate(profiles):
        for kind in settings['tasks']:
            path = settings['prefix'] + kind + '.py'
            if not any(t.checker == path for t in tasks):
                storage.tasks.create_task(models.Task(id=None, name=settings['title'] + '/' + kind.upper(), checker=path,
                    gets=1, puts=1, places=1, checker_timeout=45, checker_type='hackerdom_pfr',
                    env_path='', default_score=0, get_period=0, active=index == 0))
    with utils.db_cursor() as (conn, c):
        c.execute('UPDATE Tasks SET active=(checker LIKE %s)', (chosen['prefix'] + '%',))
        c.execute('UPDATE Teams SET active=(ip = ANY(%s))', (ips,))
        c.execute('UPDATE GameConfig SET round_time=%s, flag_lifetime=2, game_running=true WHERE id=1', (chosen['round_time'],))
        # Fixed attack/defense scoring may produce a negative total.
        c.execute('ALTER TABLE TeamTasks DROP CONSTRAINT IF EXISTS teamtasks_score_check')
        conn.commit()
    storage.caching.flush_tasks_cache()
    storage.caching.flush_teams_cache()
    utils.RedisStorage.get().delete(storage.keys.CacheKeys.game_config())
    update(configured=True, phase='ready', tick=0, started_at=None, finished_at=None,
           deadline=None, remaining=None, error='', lab=lab)
    storage.game.update_game_state(for_round=0)


def next_full_round(lab, chosen):
    """Switch the finished Web round to Crypto while keeping match data and team tokens."""
    offset = chosen['tick_offset']
    with utils.db_cursor(dict_cursor=True) as (conn, c):
        c.execute('SELECT enabled,resetting FROM MekodataRoundControl WHERE id=1 FOR UPDATE')
        gate = c.fetchone()
        c.execute('SELECT configured,lab,phase,tick FROM MekodataRound1 WHERE id=1 FOR UPDATE')
        current = c.fetchone()
        if (gate['enabled'] or gate['resetting'] or not current['configured']
                or current['lab'] != chosen['first_lab'] or current['phase'] != 'finished'
                or current['tick'] != offset):
            raise ValueError('Chỉ chuyển sang Crypto sau khi vòng Web Full Rounds kết thúc.')
        c.execute('SELECT checker FROM Tasks WHERE checker LIKE %s', (chosen['prefix'] + '%',))
        if {row['checker'] for row in c.fetchall()} != {chosen['prefix'] + task + '.py' for task in chosen['tasks']}:
            raise ValueError('Thiếu cấu hình checker Crypto của Full Rounds.')
        c.execute('UPDATE Tasks SET active=(checker LIKE %s)', (chosen['prefix'] + '%',))
        c.execute('UPDATE GameConfig SET real_round=%s,round_time=%s WHERE id=1', (offset, chosen['round_time']))
        c.execute("""UPDATE MekodataRound1 SET lab=%s,phase='ready',started_at=NULL,finished_at=NULL,
                     deadline=NULL,remaining=NULL,prior_phase=NULL,last_probe=NULL,error='' WHERE id=1""", (lab,))
        conn.commit()
    storage.caching.flush_tasks_cache()
    redis = utils.RedisStorage.get()
    redis.delete(storage.keys.CacheKeys.game_config(), storage.keys.CacheKeys.attack_data())
    redis.set(storage.keys.CacheKeys.current_round(), offset)
    refresh_flag_cache()
    storage.game.update_game_state(for_round=offset)


def put_flag(args):
    team, task, tick = args
    from . import round_control
    if not round_control.get_enabled():
        return False
    with utils.db_cursor() as (conn, c):
        chosen = profile()
        flag = models.Flag.generate(task.name[0], team.id, task.id, tick, template=chosen['flag_template'])
        seed = secrets.token_hex(20)
        flag.private_flag_data = json.dumps({'seed': seed, 'tick': tick}) if chosen.get('crypto_seed') else seed
        flag.vuln_number = 1
        c.execute('''INSERT INTO MekodataPlacements(team_id,task_id,tick,seed)
                     VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING''', (team.id, task.id, tick, flag.to_json()))
        c.execute('SELECT seed,flag_id FROM MekodataPlacements WHERE team_id=%s AND task_id=%s AND tick=%s', (team.id, task.id, tick))
        seed, existing = c.fetchone()
        conn.commit()
    if existing:
        return True
    flag = models.Flag.from_json(seed)
    verdict = CheckerRunner(team, task, logger, flag=flag).put()
    if verdict.status != TaskStatus.UP:
        logger.warning('PUT failed team=%s task=%s tick=%s status=%s', team.id, task.id, tick, verdict.status)
        return False
    current = state()
    if (not round_control.get_enabled() or current['phase'] != 'running'
            or current['tick'] != tick or time.time() >= current['deadline']):
        logger.info('Ignoring late/stopped PUT team=%s task=%s tick=%s', team.id, task.id, tick)
        return False
    flag = task.set_flag_data(flag, verdict)
    with utils.db_cursor() as (_, c):
        c.execute('SELECT id FROM Flags WHERE flag=%s', (flag.flag,))
        old = c.fetchone()
    if old:
        flag.id = old[0]
        # Recover a crash after SQL commit but before the native Redis cache write.
        cfg = storage.game.get_current_game_config()
        expires = cfg.flag_lifetime * cfg.round_time * 2
        redis = utils.RedisStorage.get()
        redis.set(storage.keys.CacheKeys.flag_by_id(flag.id), flag.to_json(), ex=expires)
        redis.set(storage.keys.CacheKeys.flag_by_str(flag.flag), flag.to_json(), ex=expires)
    else:
        flag = storage.flags.add_flag(flag)
    with utils.db_cursor() as (conn, c):
        c.execute('UPDATE MekodataPlacements SET flag_id=%s WHERE team_id=%s AND task_id=%s AND tick=%s', (flag.id, team.id, task.id, tick))
        conn.commit()
    return True


def verify(args):
    team, task, tick = args
    runner = CheckerRunner(team, task, logger)
    verdict = runner.check()
    if verdict.status == TaskStatus.UP:
        with utils.db_cursor(dict_cursor=True) as (_, c):
            c.execute('SELECT * FROM Flags WHERE team_id=%s AND task_id=%s AND round BETWEEN %s AND %s ORDER BY round', (team.id, task.id, max(1, tick-2), tick))
            flags = [models.Flag.from_dict(dict(row)) for row in c.fetchall()]
        if not any(f.round == tick for f in flags):
            verdict.status = TaskStatus(110)
            verdict.public_message = 'Current tick flag was not placed'
            flags = []
        for flag in flags:
            verdict = CheckerRunner(team, task, logger, flag=flag).get()
            if verdict.status != TaskStatus.UP:
                break
    with utils.db_cursor() as (conn, c):
        c.execute('UPDATE TeamTasks SET status=%s,checks=checks+1,checks_passed=checks_passed+%s,public_message=%s WHERE team_id=%s AND task_id=%s',
                  (verdict.status.value, int(verdict.status == TaskStatus.UP), verdict.public_message, team.id, task.id))
        conn.commit()
    return team.id, task.id, verdict.status.value


def health_probe(args):
    """Một sub-check health trong tick (mô hình CyberRangeCZ): chỉ chạy check() chức năng,
    KHÔNG GET flag (đầu tick flag chưa chắc đã đặt). Trả (team_id, task_id, status)."""
    team, task, tick = args
    verdict = CheckerRunner(team, task, logger).check()
    return team.id, task.id, verdict.status.value


def run_health_probes(teams, tasks, tick):
    """Một lượt probe mọi đội; đội nào có task không UP => cộng 1 'down' cho (đội, tick).
    downs>0 ở cuối tick sẽ làm mất toàn bộ SLA của tick đó."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(health_probe, [(t, k, tick) for t in teams for k in tasks]))
    with utils.db_cursor() as (conn, c):
        for team in teams:
            statuses = [v for tid, _, v in results if tid == team.id]
            up = len(statuses) == len(tasks) and all(v == 101 for v in statuses)
            status = 101 if up else (110 if 110 in statuses else 104)
            c.execute('''INSERT INTO MekodataTickHealth(team_id,tick,probes,downs,last_status)
                         VALUES(%s,%s,1,%s,%s)
                         ON CONFLICT(team_id,tick) DO UPDATE
                         SET probes=MekodataTickHealth.probes+1,
                             downs=MekodataTickHealth.downs+EXCLUDED.downs,
                             last_status=EXCLUDED.last_status''',
                      (team.id, tick, int(not up), status))
        conn.commit()
    return results


def pump():
    """Called only by the ticker process. Never generate flags at container startup."""
    from . import round_control
    s = state()
    enabled = round_control.get_enabled()
    now = time.time()
    tick_seconds = storage.game.get_current_game_config().round_time
    timing = {**profile(s), 'round_time': tick_seconds}
    if not enabled:
        # Drain remote operations before marking paused (archive/reset may follow).
        collect_puts(wait=True)
        waiting = s['phase'] == 'ready' and s['deadline'] is not None and (s.get('slot') or now < s['deadline'])
        if s['phase'] in ('preview', 'running', 'preparing', 'checking', 'draining') or waiting:
            update(prior_phase=s['phase'], phase='paused', remaining=max(0, (s['deadline'] or now) - now))
        return
    if s['phase'] == 'paused':
        resumed = now + (s['remaining'] or 0)
        # A pause moves the whole plan, so the round keeps its full length.
        shift = resumed - (s['deadline'] or resumed)
        update(phase=s['prior_phase'], deadline=resumed,
               started_at=s['started_at'] + shift if s.get('started_at') else None)
        refresh_flag_cache()
        s = state()
    offset = timing.get('tick_offset', 0)
    preview = timing.get('preview_seconds', 0)
    if s['phase'] == 'ready' and preview and s['tick'] == offset and s['started_at'] is None:
        update(phase='preview', deadline=now + preview)
        return
    if s['phase'] == 'preview':
        if now < s['deadline']:
            return
        update(phase='preparing', tick=offset + 1, started_at=s['deadline'], deadline=None)
        s = state()
    teams, tasks = storage.teams.get_teams(), storage.tasks.get_tasks()
    if s['phase'] == 'ready':
        if s['deadline'] and now < s['deadline']:
            return
        update(phase='preparing', tick=s['tick'] + 1, deadline=None)
        s = state()
    if s['phase'] == 'preparing':
        tick = s['tick']
        storage.game.update_real_round_in_db(tick)
        storage.game.set_round_start(tick)
        utils.RedisStorage.get().set(storage.keys.CacheKeys.current_round(), tick)
        refresh_flag_cache()
        storage.game.update_attack_data(tick)
        started = s.get('started_at') or time.time()
        update(phase='running', started_at=started, error='',
               deadline=round_schedule.tick_deadline(timing, started, tick - offset, time.time()))
        storage.game.update_game_state(for_round=tick)
        schedule_puts(teams, tasks, tick)
        return
    if s['phase'] == 'running' and now < round_schedule.check_at(timing, s['deadline']):
        schedule_puts(teams, tasks, s['tick'])
        storage.game.update_attack_data(s['tick'])
        # Sub-check health liên tục (~probe_seconds). Đặt mốc TRƯỚC khi probe (probe chặn lâu),
        # tránh dồn probe. 1 lần DOWN trong tick sẽ làm mất toàn bộ SLA tick đó (xử ở phase checking).
        probe_every = timing.get('probe_seconds') or 0
        if probe_every and now - (s.get('last_probe') or 0) >= probe_every:
            update(last_probe=now)
            run_health_probes(teams, tasks, s['tick'])
        return
    if s['phase'] == 'running':
        update(phase='checking')
        s = state()
    if s['phase'] == 'checking':
        # No next tick or final GET until all old PUT processes have returned.
        collect_puts(wait=True)
        _put_retry.clear()
        tick = s['tick']
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(verify, [(t, k, tick) for t in teams for k in tasks]))
        with utils.db_cursor() as (conn, c):
            for team in teams:
                statuses = [v for tid, _, v in results if tid == team.id]
                status = 101 if len(statuses) == len(tasks) and all(v == 101 for v in statuses) else (110 if 110 in statuses else 104)
                # Mô hình CyberRangeCZ: chỉ cần 1 sub-probe DOWN trong tick là mất toàn bộ SLA tick đó.
                c.execute('SELECT downs FROM MekodataTickHealth WHERE team_id=%s AND tick=%s', (team.id, tick))
                hrow = c.fetchone()
                had_down = bool(hrow and hrow[0] > 0)
                points = int(status == 101 and not had_down)
                c.execute('INSERT INTO MekodataSLA VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING tick', (team.id, tick, status, points))
                if c.fetchone():
                    c.execute('UPDATE TeamTasks SET score=score+%s WHERE team_id=%s AND task_id=%s', (points, team.id, min(t.id for t in tasks)))
            conn.commit()
        if tick < offset + timing['ticks_per_round']:
            update(phase='ready', deadline=s['deadline'] if round_schedule.is_fixed(timing) else None)
        else:
            update(phase='draining', deadline=round_schedule.after_last_tick(timing, s['deadline'], time.time()))
        storage.game.update_game_state(for_round=tick)
        return
    if s['phase'] == 'draining':
        virtual_tick = offset + round_schedule.virtual_tick(timing, s['deadline'], now)
        if storage.game.get_real_round() != virtual_tick:
            utils.RedisStorage.get().set(storage.keys.CacheKeys.current_round(), virtual_tick)
            storage.game.update_attack_data(virtual_tick)
        if now >= s['deadline']:
            update(phase='finished', finished_at=now)
            round_control.set_enabled(False)


def scores(lifecycle=None):
    """Rank active teams by their combined attack and defense points."""
    lifecycle = state() if lifecycle is None else lifecycle
    chosen = profile(lifecycle)
    pattern = chosen['prefix'] + '%'
    windows = []
    included_slots = scoring_slots(lifecycle)
    for slot, row in included_slots.items():
        settings = lab_profile.for_slot(row['lab'], int(slot))
        start = settings['tick_offset']
        windows.append({'paths': _checker_paths(settings), 'lo': start + 1,
                        'hi': start + settings['ticks_per_round'], 'at_tick': row['tick'],
                        'closed': row['phase'] == 'finished' or lifecycle['phase'] == 'archived'})
    patterns = [lab_profile.get(row['lab'])['prefix'] + '%' for row in included_slots.values()] or [pattern]
    if not windows and 'first_lab' in chosen:
        patterns.append(lab_profile.get(chosen['first_lab'])['prefix'] + '%')
    current_round = storage.game.get_real_round()
    with utils.db_cursor(dict_cursor=True) as (_, c):
        c.execute('''
            WITH slots AS (
                SELECT * FROM jsonb_to_recordset(%(windows)s::jsonb)
                    AS w(paths text[],lo integer,hi integer,at_tick integer,closed boolean)
            ),
            lab_flags AS (
                SELECT f.id AS flag_id
                FROM Flags f JOIN Tasks k ON k.id = f.task_id
                WHERE k.checker LIKE ANY(%(patterns)s)
                  AND (NOT %(slot_mode)s OR EXISTS (
                       SELECT 1 FROM slots w WHERE k.checker=ANY(w.paths) AND f.round BETWEEN w.lo AND w.hi))
            ),
            first_blood AS (
                SELECT DISTINCT ON (sf.flag_id) sf.flag_id, sf.attacker_id
                FROM StolenFlags sf JOIN lab_flags lf ON lf.flag_id = sf.flag_id
                ORDER BY sf.flag_id, sf.submit_time, sf.attacker_id
            ),
            steals AS (
                SELECT sf.attacker_id AS team_id, COUNT(*) AS n
                FROM StolenFlags sf JOIN lab_flags lf ON lf.flag_id = sf.flag_id
                GROUP BY sf.attacker_id
            ),
            bloods AS (
                SELECT attacker_id AS team_id, COUNT(*) AS n
                FROM first_blood GROUP BY attacker_id
            ),
            protected AS (
                SELECT p.team_id, COUNT(*) AS n
                FROM MekodataPlacements p JOIN Tasks k ON k.id = p.task_id
                JOIN MekodataRound1 r ON r.id = 1
                JOIN GameConfig cfg ON cfg.id = 1
                WHERE k.checker LIKE ANY(%(patterns)s) AND p.flag_id IS NOT NULL
                  AND ((%(slot_mode)s AND EXISTS (
                         SELECT 1 FROM slots w WHERE k.checker=ANY(w.paths) AND p.tick BETWEEN w.lo AND w.hi
                           AND (w.closed OR p.tick + cfg.flag_lifetime < w.at_tick)))
                       OR (NOT %(slot_mode)s AND (k.checker NOT LIKE %(pattern)s OR r.phase IN ('finished', 'archived') OR p.tick + cfg.flag_lifetime <
                       CASE WHEN r.phase = 'draining' OR (r.phase = 'paused' AND r.prior_phase = 'draining')
                            THEN GREATEST(cfg.real_round, %(current_round)s) ELSE cfg.real_round END)))
                  AND NOT EXISTS (SELECT 1 FROM StolenFlags sf WHERE sf.flag_id = p.flag_id)
                GROUP BY p.team_id
            ),
            sla AS (
                SELECT team_id, SUM(points) AS n FROM MekodataSLA l
                WHERE NOT %(slot_mode)s OR EXISTS (SELECT 1 FROM slots w WHERE l.tick BETWEEN w.lo AND w.hi)
                GROUP BY team_id
            )
            SELECT t.id AS team_id, t.name,
                   COALESCE(st.n,0) + COALESCE(b.n,0) AS attack_raw,
                   COALESCE(pr.n,0) + COALESCE(sl.n,0) AS defense_raw,
                   COALESCE(sl.n,0) AS sla
            FROM Teams t
            LEFT JOIN steals st ON st.team_id = t.id
            LEFT JOIN bloods b ON b.team_id = t.id
            LEFT JOIN protected pr ON pr.team_id = t.id
            LEFT JOIN sla sl ON sl.team_id = t.id
            WHERE t.active
        ''', {'patterns': patterns, 'pattern': pattern, 'current_round': current_round,
              'windows': json.dumps(windows), 'slot_mode': bool(windows)})
        rows = [dict(r) for r in c.fetchall()]

    out = []
    for r in rows:
        attack = r['attack_raw']
        defense = r['defense_raw']
        out.append({'team_id': r['team_id'], 'name': r['name'],
                    'attack': attack, 'defense': defense,
                    'sla': r['sla'], 'total': attack + defense})
    out.sort(key=lambda x: (-x['total'], x['name']))
    return out


def record_attack(result, flag):
    """Record a valid capture and award the first submission its bonus."""
    from lib.helpers.exceptions import FlagExceptionEnum
    with utils.db_cursor() as (conn, c):
        try:
            # Lock the gate so a stop cannot race acceptance of this flag.
            c.execute('SELECT enabled AND NOT resetting FROM MekodataRoundControl WHERE id=1 FOR SHARE')
            if not c.fetchone()[0] or not accepting():
                raise FlagExceptionEnum.GAME_NOT_AVAILABLE
            current = state()
            chosen = profile(current)
            if current.get('slot'):
                if not chosen['tick_offset'] < flag.round <= current['tick']:
                    raise FlagExceptionEnum.FLAG_INVALID
                if current['tick'] - flag.round > 2:
                    raise FlagExceptionEnum.FLAG_TOO_OLD
            c.execute('SELECT 1 FROM Teams WHERE id=%s AND active', (result.attacker_id,))
            if not c.fetchone():
                raise FlagExceptionEnum.GAME_NOT_AVAILABLE
            c.execute('SELECT 1 FROM Tasks WHERE id=%s AND active AND checker LIKE %s',
                      (flag.task_id, chosen['prefix'] + '%'))
            if not c.fetchone():
                raise FlagExceptionEnum.FLAG_INVALID
            # Stable lock order avoids two teams attacking each other deadlocking.
            c.execute('SELECT team_id FROM TeamTasks WHERE task_id=%s AND team_id IN (%s,%s) ORDER BY team_id FOR UPDATE', (flag.task_id, result.attacker_id, flag.team_id))
            c.fetchall()
            # Keep the same per-flag order for scoring even if transactions acquired
            # the victim's lock in a different order from their start times.
            c.execute('''INSERT INTO StolenFlags(attacker_id,flag_id,submit_time)
                         SELECT %s, %s, GREATEST(clock_timestamp(), MAX(submit_time) + interval '1 microsecond')
                         FROM StolenFlags WHERE flag_id=%s
                         ON CONFLICT DO NOTHING RETURNING flag_id''', (result.attacker_id, flag.id, flag.id))
            if c.fetchone() is None:
                raise FlagExceptionEnum.FLAG_ALREADY_STOLEN
            # RuCTFE: đội nộp flag đầu tiên +2, mọi đội nộp cùng flag sau đó +1.
            # Hàng TeamTasks của nạn nhân đã bị khóa FOR UPDATE ở trên nên mọi đội tấn công
            # cùng một flag bị tuần tự hóa; đếm số dòng của flag ngay sau INSERT là an toàn.
            c.execute('SELECT COUNT(*) FROM StolenFlags WHERE flag_id=%s', (flag.id,))
            delta = 2.0 if c.fetchone()[0] == 1 else 1.0
            c.execute('UPDATE TeamTasks SET stolen=stolen+1,score=score+%s WHERE team_id=%s AND task_id=%s', (delta, result.attacker_id, flag.task_id))
            # RuCTFE: mất flag KHÔNG bị trừ điểm phòng thủ; chỉ giữ số đếm để thống kê.
            c.execute('UPDATE TeamTasks SET lost=lost+1 WHERE team_id=%s AND task_id=%s', (flag.team_id, flag.task_id))
            result.attacker_delta = delta
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    result.submit_ok = True
    result.victim_id = flag.team_id
    result.task_id = flag.task_id
    result.victim_delta = 0.0
    result.message = ('Flag accepted! Attack +2 (first blood!)' if result.attacker_delta >= 2
                      else 'Flag accepted! Attack +1.')
    storage.game.update_game_state(for_round=state()['tick'])
    return result


def archive_competition():
    """Persist a private, immutable snapshot before any competition data is removed."""
    import uuid
    ensure_schema()
    archive_id = str(uuid.uuid4())
    tables = ('Teams', 'Tasks', 'GameConfig', 'TeamTasks', 'TeamTasksLog',
              'Flags', 'StolenFlags', 'MekodataPlacements', 'MekodataSLA',
              'MekodataTickHealth', 'MekodataTickResults', 'MekodataRoundControl', 'MekodataRound1')
    with utils.db_cursor(dict_cursor=True) as (conn, c):
        try:
            c.execute('SELECT enabled FROM MekodataRoundControl WHERE id=1 FOR UPDATE')
            if c.fetchone()['enabled']:
                raise ValueError('Dừng cuộc thi trước khi đóng và lưu hồ sơ.')
            c.execute('SELECT * FROM MekodataRound1 WHERE id=1 FOR UPDATE')
            lifecycle = dict(c.fetchone())
            if not lifecycle['configured']:
                raise ValueError('Chưa có cuộc thi Round 1 được chuẩn bị để đóng.')
            if (lifecycle['phase'] not in SWITCHABLE_PHASES
                    or (lifecycle.get('slot') and not slot_can_start(lifecycle))):
                raise ValueError('Đợi checker hoàn tất chu kỳ hiện tại rồi mới đóng cuộc thi.')
            if lifecycle.get('archive_id'):
                raise ValueError('Cuộc thi này đã có hồ sơ lưu: ' + lifecycle['archive_id'])
            snapshot = {'schema_version': 1, 'archive_id': archive_id, 'tables': {}}
            for table in tables:
                c.execute('SELECT * FROM ' + table + ' ORDER BY 1')
                snapshot['tables'][table] = [dict(row) for row in c.fetchall()]
            c.execute('INSERT INTO MekodataArchives(id,snapshot) VALUES(%s,%s::jsonb)',
                      (archive_id, json.dumps(snapshot, default=str)))
            c.execute("UPDATE MekodataRound1 SET phase='archived',archive_id=%s,deadline=NULL,remaining=NULL WHERE id=1", (archive_id,))
            c.execute('UPDATE MekodataRoundControl SET enabled=false,updated_at=now() WHERE id=1')
            c.execute('UPDATE GameConfig SET game_running=false WHERE id=1')
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    utils.RedisStorage.get().delete(storage.keys.CacheKeys.game_config())
    storage.game.update_game_state(for_round=lifecycle['tick'])
    return archive_id


def get_archive(archive_id):
    ensure_schema()
    with utils.db_cursor(dict_cursor=True) as (_, c):
        c.execute('SELECT id,created_at,snapshot FROM MekodataArchives WHERE id=%s', (archive_id,))
        row = c.fetchone()
        return dict(row) if row else None


def recreate_from_archive(archive_id, verified_hosts):
    """Clear this competition's state only after the operator verified the lab VMs."""
    ensure_schema()
    with utils.db_cursor(dict_cursor=True) as (conn, c):
        try:
            c.execute('SELECT enabled FROM MekodataRoundControl WHERE id=1 FOR UPDATE')
            if c.fetchone()['enabled']:
                raise ValueError('Round đang bật; không thể tái tạo.')
            c.execute('SELECT * FROM MekodataRound1 WHERE id=1 FOR UPDATE')
            lifecycle = c.fetchone()
            if not lifecycle or lifecycle['phase'] not in ('archived', 'recreating') or lifecycle['archive_id'] != archive_id:
                raise ValueError('Mã hồ sơ không khớp cuộc thi đang đóng.')
            current_lab = lifecycle['lab']
            saved = slot_states(lifecycle)
            labs = [row['lab'] for row in saved.values()] or [current_lab]
            hosts = {host for lab in labs for host in lab_profile.get(lab)['hosts']}
            if (not isinstance(verified_hosts, list) or any(not isinstance(host, str) for host in verified_hosts)
                    or sorted(verified_hosts) != sorted(hosts)):
                raise ValueError('Cần xác nhận đã tái tạo đủ các máy đội: ' + ', '.join(sorted(hosts)) + '.')
            c.execute('SELECT 1 FROM MekodataArchives WHERE id=%s', (archive_id,))
            if not c.fetchone():
                raise ValueError('Không tìm thấy hồ sơ lưu trong PostgreSQL.')
            if lifecycle['phase'] == 'archived':
                _clear_scores(c)
                if saved:
                    _reset_slots(c, saved)
                    first_lab = saved['1']['lab']
                else:
                    first_lab = reset_round_profile(c, current_lab)
                    c.execute('UPDATE Tasks SET active=(checker LIKE %s)', (lab_profile.get(first_lab)['prefix'] + '%',))
                c.execute('SELECT id FROM Teams ORDER BY id')
                for row in c.fetchall():
                    c.execute('UPDATE Teams SET token=%s WHERE id=%s', (secrets.token_hex(8), row['id']))
                c.execute('UPDATE GameConfig SET real_round=0,game_running=true WHERE id=1')
                c.execute('UPDATE MekodataRoundControl SET enabled=false,resetting=false,updated_at=now() WHERE id=1')
                c.execute("UPDATE MekodataRound1 SET configured=%s,phase='recreating',archive_id=%s,lab=%s,tick=0,started_at=NULL,finished_at=NULL,deadline=NULL,remaining=NULL,prior_phase=NULL,last_probe=NULL,error='' WHERE id=1", (bool(saved), archive_id, first_lab))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    _flush_score_cache(drop_tokens=True)
    update(phase='ready', archive_id=None, error='')


# >= checker_timeout (45 giây): PUT của lượt cũ đã xong, không thể ghi đè placement tick 1 của lượt mới.
RESTART_QUIET_SECONDS = 45


def restart_competition():
    """Archive the stopped competition, then replay it from tick 0 with the same teams, tokens and VMs.

    Also accepts a competition already closed with "Đóng và lưu hồ sơ" (phase archived): its archive is reused.
    """
    ensure_schema()
    with utils.db_cursor() as (_, c):
        c.execute('SELECT enabled, EXTRACT(EPOCH FROM (now() - updated_at)) FROM MekodataRoundControl WHERE id=1')
        enabled, stopped_for = c.fetchone()
        c.execute('SELECT phase,archive_id,configured FROM MekodataRound1 WHERE id=1')
        phase, saved_archive, was_configured = c.fetchone()
    if enabled:
        raise ValueError('Dừng cuộc thi trước khi bắt đầu lại.')
    if stopped_for < RESTART_QUIET_SECONDS:
        raise ValueError(f'Mới dừng {int(stopped_for)} giây; chờ đủ {RESTART_QUIET_SECONDS} giây để checker hoàn tất rồi bắt đầu lại.')
    if phase == 'archived' and saved_archive and was_configured:
        archive_id = saved_archive
    else:
        archive_id = archive_competition()
    with utils.db_cursor(dict_cursor=True) as (conn, c):
        try:
            c.execute('SELECT enabled FROM MekodataRoundControl WHERE id=1 FOR UPDATE')
            if c.fetchone()['enabled']:
                raise ValueError('Round đang bật; không thể bắt đầu lại.')
            c.execute('SELECT * FROM MekodataRound1 WHERE id=1 FOR UPDATE')
            current = c.fetchone()
            if (current['phase'], current['archive_id']) != ('archived', archive_id):
                raise ValueError('Trạng thái cuộc thi đã đổi trong lúc lưu hồ sơ ' + archive_id + '; kiểm tra lại trước khi bắt đầu.')
            _clear_scores(c)
            saved = slot_states(current)
            if saved:
                _reset_slots(c, saved)
            else:
                current_lab = current['lab']
                first_lab = reset_round_profile(c, current_lab)
                if first_lab != current_lab:
                    c.execute('UPDATE Tasks SET active=(checker LIKE %s)', (lab_profile.get(first_lab)['prefix'] + '%',))
                c.execute("UPDATE MekodataRound1 SET phase='ready',lab=%s,tick=0,started_at=NULL,finished_at=NULL,deadline=NULL,remaining=NULL,prior_phase=NULL,last_probe=NULL,error='',archive_id=NULL WHERE id=1", (first_lab,))
            c.execute('UPDATE GameConfig SET real_round=0,game_running=true WHERE id=1')
            c.execute('UPDATE MekodataRoundControl SET enabled=false,resetting=false,updated_at=now() WHERE id=1')
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    _flush_score_cache(drop_tokens=False)
    return archive_id


def _reset_slots(c, saved):
    _write_slot(c, {slot: fresh_slot(row['lab'], int(slot)) for slot, row in saved.items()}, 1)


def reset_round_profile(c, current_lab):
    """A replay of Full Rounds starts with Web, even if the archived round was Crypto."""
    first_lab = lab_profile.get(current_lab).get('first_lab', current_lab)
    if first_lab != current_lab:
        c.execute('UPDATE GameConfig SET round_time=%s WHERE id=1', (lab_profile.get(first_lab)['round_time'],))
    return first_lab


def _clear_scores(c):
    """Delete flags, captures, SLA and tick history and zero TeamTasks inside the caller's transaction."""
    c.execute('DELETE FROM MekodataPlacements')
    c.execute('DELETE FROM MekodataSLA')
    c.execute('DELETE FROM MekodataTickHealth')
    c.execute('DELETE FROM StolenFlags')
    c.execute('DELETE FROM Flags')
    c.execute('DELETE FROM MekodataTickResults')
    c.execute('DELETE FROM TeamTasksLog')
    c.execute('''UPDATE TeamTasks SET status=-1,stolen=0,lost=0,score=0,checks=0,checks_passed=0,
        public_message='',private_message='',command='' ''')


def _flush_score_cache(drop_tokens):
    redis = utils.RedisStorage.get()
    patterns = ['teamtasks:*', 'flag:*', 'team:*:stolen_flags'] + (['team:token:*'] if drop_tokens else [])
    for pattern in patterns:
        keys = list(redis.scan_iter(match=pattern))
        if keys:
            redis.delete(*keys)
    redis.delete(storage.keys.CacheKeys.flags_cached(), storage.keys.CacheKeys.attack_data())
    redis.set(storage.keys.CacheKeys.current_round(), 0)
    storage.caching.flush_tasks_cache()
    storage.caching.flush_teams_cache()
    redis.delete(storage.keys.CacheKeys.game_config())
    storage.game.set_round_start(0)
    storage.game.update_game_state(for_round=0)
