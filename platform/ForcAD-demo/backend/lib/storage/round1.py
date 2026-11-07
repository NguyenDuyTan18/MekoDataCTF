"""Round-one lifecycle; reuse ForcAD Flag, CheckerRunner, storage and judge."""
from concurrent.futures import ThreadPoolExecutor
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
        # Flag formats differ per lab; the native column only fits 32 characters.
        c.execute('ALTER TABLE Flags ALTER COLUMN flag TYPE VARCHAR(64)')
        c.execute('''CREATE TABLE IF NOT EXISTS MekodataArchives (
            id TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            snapshot JSONB NOT NULL)''')
        c.execute('INSERT INTO MekodataRound1(id) VALUES(1) ON CONFLICT DO NOTHING')
        c.execute('''CREATE TABLE IF NOT EXISTS MekodataPlacements (
            team_id INTEGER REFERENCES Teams(id), task_id INTEGER REFERENCES Tasks(id),
            tick INTEGER NOT NULL, seed TEXT NOT NULL, flag_id INTEGER REFERENCES Flags(id),
            PRIMARY KEY(team_id,task_id,tick))''')
        c.execute('''CREATE TABLE IF NOT EXISTS MekodataSLA (
            team_id INTEGER REFERENCES Teams(id), tick INTEGER NOT NULL,
            status INTEGER NOT NULL, points INTEGER NOT NULL CHECK(points IN(0,1)),
            PRIMARY KEY(team_id,tick))''')
        conn.commit()


def state():
    with utils.db_cursor(dict_cursor=True) as (_, c):
        c.execute('SELECT * FROM MekodataRound1 WHERE id=1')
        return dict(c.fetchone())


def profile():
    """Lab of the prepared competition; a database from before this column means round1."""
    return lab_profile.get(state().get('lab') or lab_profile.DEFAULT)


def checker_pattern():
    return profile()['prefix'] + '%'


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
    allowed = {'phase', 'tick', 'deadline', 'remaining', 'prior_phase', 'error', 'configured', 'archive_id', 'lab', 'started_at'}
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
    for kind in chosen['tasks']:
        path = chosen['prefix'] + kind + '.py'
        found = next((t for t in tasks if t.checker == path), None)
        if not found:
            storage.tasks.create_task(models.Task(id=None, name=chosen['title'] + '/' + kind.upper(), checker=path,
                gets=1, puts=1, places=1, checker_timeout=45, checker_type='hackerdom_pfr',
                env_path='', default_score=0, get_period=0, active=True))
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
    update(configured=True, phase='ready', tick=0, started_at=None, deadline=None, remaining=None, error='', lab=lab)
    storage.game.update_game_state(for_round=0)


def put_flag(args):
    team, task, tick = args
    from . import round_control
    if not round_control.get_enabled():
        return False
    with utils.db_cursor() as (conn, c):
        flag = models.Flag.generate(task.name[0], team.id, task.id, tick, template=profile()['flag_template'])
        flag.private_flag_data = secrets.token_hex(20)
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


def pump():
    """Called only by the ticker process. Never generate flags at container startup."""
    from . import round_control
    s = state()
    enabled = round_control.get_enabled()
    now = time.time()
    tick_seconds = storage.game.get_current_game_config().round_time
    timing = {**profile(), 'round_time': tick_seconds}
    if not enabled:
        # Drain remote operations before marking paused (archive/reset may follow).
        collect_puts(wait=True)
        waiting = s['phase'] == 'ready' and s['deadline'] and now < s['deadline']
        if s['phase'] in ('running', 'preparing', 'checking', 'draining') or waiting:
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
               deadline=round_schedule.tick_deadline(timing, started, tick, time.time()))
        storage.game.update_game_state(for_round=tick)
        schedule_puts(teams, tasks, tick)
        return
    if s['phase'] == 'running' and now < round_schedule.check_at(timing, s['deadline']):
        schedule_puts(teams, tasks, s['tick'])
        storage.game.update_attack_data(s['tick'])
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
                points = int(status == 101)
                c.execute('INSERT INTO MekodataSLA VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING tick', (team.id, tick, status, points))
                if c.fetchone():
                    c.execute('UPDATE TeamTasks SET score=score+%s WHERE team_id=%s AND task_id=%s', (points, team.id, min(t.id for t in tasks)))
            conn.commit()
        if tick < timing['ticks_per_round']:
            update(phase='ready', deadline=s['deadline'] if round_schedule.is_fixed(timing) else None)
        else:
            update(phase='draining', deadline=round_schedule.after_last_tick(timing, s['deadline'], time.time()))
        storage.game.update_game_state(for_round=tick)
        return
    if s['phase'] == 'draining':
        virtual_tick = round_schedule.virtual_tick(timing, s['deadline'], now)
        if storage.game.get_real_round() != virtual_tick:
            utils.RedisStorage.get().set(storage.keys.CacheKeys.current_round(), virtual_tick)
            storage.game.update_attack_data(virtual_tick)
        if now >= s['deadline']:
            update(phase='finished')
            round_control.set_enabled(False)


def scores():
    """Bảng điểm theo RuCTFE 2012.

    - Attack thô = số flag cướp được + số lần first-blood (đội đầu +2 = +1 cơ bản thêm +1).
    - Defense thô = số flag bảo vệ được (đã đặt nhưng không bị cướp) + điểm SLA (service UP).
    - Chuẩn hóa về 100 CHỈ ở bước hiển thị: attack_i/attack_max*100, defense_i/defense_max*100.
      DB vẫn giữ nguyên số đếm thô (StolenFlags, MekodataPlacements, MekodataSLA).
    """
    pattern = checker_pattern()
    with utils.db_cursor(dict_cursor=True) as (_, c):
        c.execute('''
            WITH lab_flags AS (
                SELECT f.id AS flag_id
                FROM Flags f JOIN Tasks k ON k.id = f.task_id
                WHERE k.checker LIKE %(pattern)s
            ),
            first_blood AS (
                SELECT DISTINCT ON (sf.flag_id) sf.flag_id, sf.attacker_id
                FROM StolenFlags sf JOIN lab_flags lf ON lf.flag_id = sf.flag_id
                ORDER BY sf.flag_id, sf.submit_time
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
                WHERE k.checker LIKE %(pattern)s AND p.flag_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM StolenFlags sf WHERE sf.flag_id = p.flag_id)
                GROUP BY p.team_id
            ),
            sla AS (
                SELECT team_id, SUM(points) AS n FROM MekodataSLA GROUP BY team_id
            )
            SELECT t.id AS team_id, t.name,
                   COALESCE(st.n,0) + COALESCE(b.n,0) AS attack_raw,
                   COALESCE(pr.n,0) AS defense_flags,
                   COALESCE(sl.n,0) AS sla
            FROM Teams t
            LEFT JOIN steals st ON st.team_id = t.id
            LEFT JOIN bloods b ON b.team_id = t.id
            LEFT JOIN protected pr ON pr.team_id = t.id
            LEFT JOIN sla sl ON sl.team_id = t.id
            WHERE t.active
        ''', {'pattern': pattern})
        rows = [dict(r) for r in c.fetchall()]

    for r in rows:
        r['defense_raw'] = r['defense_flags'] + r['sla']
    attack_max = max((r['attack_raw'] for r in rows), default=0)
    defense_max = max((r['defense_raw'] for r in rows), default=0)
    out = []
    for r in rows:
        attack = round(r['attack_raw'] / attack_max * 100, 2) if attack_max else 0.0
        defense = round(r['defense_raw'] / defense_max * 100, 2) if defense_max else 0.0
        out.append({'team_id': r['team_id'], 'name': r['name'],
                    'attack': attack, 'defense': defense,
                    'sla': r['sla'], 'total': round(attack + defense, 2)})
    out.sort(key=lambda x: (-x['total'], x['name']))
    return out


def record_attack(result, flag):
    """Keep native flag validation; atomically apply fixed +1/-1 on native tables."""
    from lib.helpers.exceptions import FlagExceptionEnum
    pattern = checker_pattern()
    with utils.db_cursor() as (conn, c):
        try:
            # Lock the gate so a stop cannot race acceptance of this flag.
            c.execute('SELECT enabled AND NOT resetting FROM MekodataRoundControl WHERE id=1 FOR SHARE')
            if not c.fetchone()[0] or not accepting():
                raise FlagExceptionEnum.GAME_NOT_AVAILABLE
            c.execute('SELECT 1 FROM Teams WHERE id=%s AND active', (result.attacker_id,))
            if not c.fetchone():
                raise FlagExceptionEnum.GAME_NOT_AVAILABLE
            c.execute('SELECT 1 FROM Tasks WHERE id=%s AND active AND checker LIKE %s', (flag.task_id, pattern))
            if not c.fetchone():
                raise FlagExceptionEnum.FLAG_INVALID
            # Stable lock order avoids two teams attacking each other deadlocking.
            c.execute('SELECT team_id FROM TeamTasks WHERE task_id=%s AND team_id IN (%s,%s) ORDER BY team_id FOR UPDATE', (flag.task_id, result.attacker_id, flag.team_id))
            c.fetchall()
            c.execute('INSERT INTO StolenFlags(attacker_id,flag_id) VALUES(%s,%s) ON CONFLICT DO NOTHING RETURNING flag_id', (result.attacker_id, flag.id))
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
              'MekodataTickResults', 'MekodataRoundControl', 'MekodataRound1')
    with utils.db_cursor(dict_cursor=True) as (conn, c):
        try:
            c.execute('SELECT enabled FROM MekodataRoundControl WHERE id=1 FOR UPDATE')
            if c.fetchone()['enabled']:
                raise ValueError('Dừng cuộc thi trước khi đóng và lưu hồ sơ.')
            c.execute('SELECT * FROM MekodataRound1 WHERE id=1 FOR UPDATE')
            lifecycle = dict(c.fetchone())
            if not lifecycle['configured']:
                raise ValueError('Chưa có cuộc thi Round 1 được chuẩn bị để đóng.')
            if lifecycle['phase'] not in ('ready', 'paused', 'finished'):
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
    from . import round_control
    ensure_schema()
    pattern = checker_pattern()
    if verified_hosts != profile()['hosts']:
        raise ValueError('Chỉ reset dữ liệu thi sau khi xác nhận đã tái tạo đủ các máy đội.')
    with utils.db_cursor() as (conn, c):
        try:
            c.execute('SELECT phase,archive_id FROM MekodataRound1 WHERE id=1 FOR UPDATE')
            lifecycle = c.fetchone()
            if not lifecycle or lifecycle[0] not in ('archived', 'recreating') or lifecycle[1] != archive_id:
                raise ValueError('Mã hồ sơ không khớp cuộc thi đang đóng.')
            c.execute('SELECT 1 FROM MekodataArchives WHERE id=%s', (archive_id,))
            if not c.fetchone():
                raise ValueError('Không tìm thấy hồ sơ lưu trong PostgreSQL.')
            c.execute('SELECT enabled FROM MekodataRoundControl WHERE id=1 FOR UPDATE')
            if c.fetchone()[0]:
                raise ValueError('Round đang bật; không thể tái tạo.')
            if lifecycle[0] == 'archived':
                _clear_scores(c)
                c.execute('UPDATE Tasks SET active=(checker LIKE %s)', (pattern,))
                c.execute('SELECT id FROM Teams ORDER BY id')
                for (team_id,) in c.fetchall():
                    c.execute('UPDATE Teams SET token=%s WHERE id=%s', (secrets.token_hex(8), team_id))
                c.execute('UPDATE GameConfig SET real_round=0,game_running=true WHERE id=1')
                c.execute('UPDATE MekodataRoundControl SET enabled=false,resetting=false,updated_at=now() WHERE id=1')
                c.execute("UPDATE MekodataRound1 SET configured=false,phase='recreating',tick=0,started_at=NULL,deadline=NULL,remaining=NULL,prior_phase=NULL,error='' WHERE id=1")
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
    with utils.db_cursor() as (conn, c):
        try:
            c.execute('SELECT phase,archive_id FROM MekodataRound1 WHERE id=1 FOR UPDATE')
            if tuple(c.fetchone()) != ('archived', archive_id):
                raise ValueError('Trạng thái cuộc thi đã đổi trong lúc lưu hồ sơ ' + archive_id + '; kiểm tra lại trước khi bắt đầu.')
            c.execute('SELECT enabled FROM MekodataRoundControl WHERE id=1 FOR UPDATE')
            if c.fetchone()[0]:
                raise ValueError('Round đang bật; không thể bắt đầu lại.')
            _clear_scores(c)
            c.execute('UPDATE GameConfig SET real_round=0,game_running=true WHERE id=1')
            c.execute('UPDATE MekodataRoundControl SET enabled=false,resetting=false,updated_at=now() WHERE id=1')
            c.execute("UPDATE MekodataRound1 SET phase='ready',tick=0,started_at=NULL,deadline=NULL,remaining=NULL,prior_phase=NULL,error='',archive_id=NULL WHERE id=1")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    _flush_score_cache(drop_tokens=False)
    return archive_id


def _clear_scores(c):
    """Delete flags, captures, SLA and tick history and zero TeamTasks inside the caller's transaction."""
    c.execute('DELETE FROM MekodataPlacements')
    c.execute('DELETE FROM MekodataSLA')
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
