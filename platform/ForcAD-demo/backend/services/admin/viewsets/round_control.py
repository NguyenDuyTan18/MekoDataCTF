from flask import jsonify, request

from lib.storage import round_control
from .authentication import check_session
from .utils import abort_with_error


def round_control_status():
    check_session()
    round_control.ensure_table()
    from lib.storage import competition
    state = competition.state()
    profile = competition.profile(state)
    running = round_control.get_enabled()
    slots = {slot: {'lab': row['lab'], 'phase': row['phase']}
             for slot, row in competition.slot_states(state).items()}
    return jsonify({'running': running, 'round1': state, 'slots': slots,
                    'can_configure_slots': not running and competition.slot_can_configure(state),
                    'can_start_slot': bool(slots) and not running and competition.slot_can_start(state),
                    'default_slots': competition.lab_profile.DEFAULT_SLOTS,
                    'labs': {lab: settings['title'] for lab, settings in competition.lab_profile.PROFILES.items()},
                    # Bài chuẩn bị trực tiếp được (không phải bài nối sau first_lab/previous_lab) — nút "Chuẩn bị" tự sinh từ đây.
                    'prepare_labs': {lab: {'title': settings['title'], 'tasks': list(settings['tasks'])}
                                     for lab, settings in competition.lab_profile.PROFILES.items()
                                     if 'first_lab' not in settings and 'previous_lab' not in settings},
                    'next_lab_title': (competition.lab_profile.PROFILES[profile['next_lab']]['title']
                                       if not slots and profile.get('next_lab') in competition.lab_profile.PROFILES else None),
                    'ticks_per_round': profile['ticks_per_round'],
                    'display_tick': state['tick'] - profile.get('tick_offset', 0),
                    'preview_seconds': profile.get('preview_seconds', 0),
                    'next_lab': None if slots else profile.get('next_lab')})


def round_slots_update():
    check_session()
    if request.headers.get('Origin') != request.host_url.rstrip('/'):
        abort_with_error('Invalid origin', 403)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) not in ({'labs'}, {'slot'}):
        abort_with_error('Expected labs or slot', 400)
    from lib.storage import competition
    round_control.ensure_table()
    try:
        if 'labs' in data:
            competition.configure_slots(data['labs'])
        else:
            competition.start_slot(data['slot'])
    except ValueError as exc:
        abort_with_error(str(exc), 409)
    return jsonify({'running': round_control.get_enabled()})


def round1_prepare():
    check_session()
    if request.headers.get('Origin') != request.host_url.rstrip('/'):
        abort_with_error('Invalid origin', 403)
    data = request.get_json(silent=True) or {}
    if data.get('confirm') != 'PREPARE ROUND1':
        abort_with_error('Preparation confirmation required', 400)
    from lib.storage import competition
    try:
        with competition.lifecycle_lock():
            competition.prepare(data.get('lab', 'round1'))
    except ValueError as exc:
        abort_with_error(str(exc), 409)
    return jsonify({'status': 'prepared', 'running': False})


def round1_archive():
    check_session()
    if request.headers.get('Origin') != request.host_url.rstrip('/'):
        abort_with_error('Invalid origin', 403)
    if (request.get_json(silent=True) or {}).get('confirm') != 'ARCHIVE ROUND1':
        abort_with_error('Archive confirmation required', 400)
    from lib.storage import competition
    try:
        with competition.lifecycle_lock():
            archive_id = competition.archive_competition()
    except ValueError as exc:
        abort_with_error(str(exc), 409)
    return jsonify({'status': 'archived', 'archive_id': archive_id})


def round1_restart():
    check_session()
    if request.headers.get('Origin') != request.host_url.rstrip('/'):
        abort_with_error('Invalid origin', 403)
    if (request.get_json(silent=True) or {}).get('confirm') != 'RESTART ROUND1':
        abort_with_error('Restart confirmation required', 400)
    from lib.storage import competition
    try:
        with competition.lifecycle_lock():
            archive_id = competition.restart_competition()
    except ValueError as exc:
        abort_with_error(str(exc), 409)
    return jsonify({'status': 'ready', 'archive_id': archive_id, 'round': 0, 'running': False})


def round1_archive_download(archive_id):
    check_session()
    from flask import make_response
    from lib.storage import competition
    archive = competition.get_archive(archive_id)
    if not archive:
        abort_with_error('Archive not found', 404)
    response = make_response(jsonify(archive))
    response.headers['Content-Disposition'] = 'attachment; filename="round1-archive-' + archive_id + '.json"'
    response.headers['Cache-Control'] = 'no-store'
    return response


def round1_recreate():
    check_session()
    if request.headers.get('Origin') != request.host_url.rstrip('/'):
        abort_with_error('Invalid origin', 403)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get('confirm') != 'RECREATE ROUND1':
        abort_with_error('Recreate confirmation required', 400)
    from lib.storage import competition
    try:
        with competition.lifecycle_lock():
            competition.recreate_from_archive(data.get('archive_id'), data.get('verified_hosts'))
    except ValueError as exc:
        abort_with_error(str(exc), 409)
    return jsonify({'status': 'ready', 'round': 0, 'running': False})


def round_control_update():
    check_session()
    if request.headers.get('Origin') != request.host_url.rstrip('/'):
        abort_with_error('Invalid origin', 403)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or type(data.get('running')) is not bool:
        abort_with_error('Expected boolean running', 400)
    round_control.ensure_table()
    try:
        round_control.set_enabled(data['running'])
    except round_control.ResetUnavailable as exc:
        abort_with_error(str(exc), 409)
    return jsonify({'running': round_control.get_enabled()})


def round_control_reset():
    check_session()
    if request.headers.get('Origin') != request.host_url.rstrip('/'):
        abort_with_error('Invalid origin', 403)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get('confirm') != 'RESET':
        abort_with_error('Reset confirmation required', 400)
    try:
        round_control.reset_health_demo()
    except round_control.ResetUnavailable as exc:
        abort_with_error(str(exc), 409)
    return jsonify({'round': 0, 'running': False})


def arena_data():
    check_session()
    from lib.storage import utils
    with utils.db_cursor(dict_cursor=True) as (_, c):
        c.execute("SELECT tt.team_id,t.name AS team,k.name AS service,tt.status,tt.checks,tt.checks_passed FROM TeamTasks tt JOIN Teams t ON t.id=tt.team_id JOIN Tasks k ON k.id=tt.task_id WHERE t.active AND k.active ORDER BY t.name,k.name")
        services=[dict(r) for r in c.fetchall()]
        c.execute("SELECT f.id AS capture_flag_id,s.attacker_id,f.team_id AS victim_id,a.name AS attacker,v.name AS victim,k.name AS service,f.round AS tick,s.submit_time FROM StolenFlags s JOIN Flags f ON f.id=s.flag_id JOIN Teams a ON a.id=s.attacker_id JOIN Teams v ON v.id=f.team_id JOIN Tasks k ON k.id=f.task_id ORDER BY s.submit_time DESC,f.id DESC,s.attacker_id LIMIT 50")
        captures=[dict(r) for r in c.fetchall()]
        c.execute("SELECT l.team_id,t.name AS team,l.tick,l.status,l.points FROM MekodataSLA l JOIN Teams t ON t.id=l.team_id ORDER BY l.tick DESC,t.name LIMIT 120")
        checks=[dict(r) for r in c.fetchall()]
    response=jsonify({'services':services,'captures':captures,'checks':checks})
    response.headers['Cache-Control']='no-store'
    return response
