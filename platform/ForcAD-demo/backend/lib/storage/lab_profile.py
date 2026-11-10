"""Fixed facts of each lab the round lifecycle can run. Defaults stay on round1.

To add a lab, add an entry here; timing fields are explained in round_schedule.py.
"""
DEFAULT = 'round1'
DEFAULT_SLOTS = {'1': 'full_rounds', '2': 'full_rounds_crypto'}
SLOT_TICKS = 10
PROFILES = {
    'round1': {
        'title': 'Round1',
        'prefix': '/checkers/round1/',
        'tasks': ('idor', 'sqli', 'upload'),
        'teams': {'10.80.0.11': 'team01', '10.80.0.12': 'team02',
                  '10.80.0.13': 'team03', '10.80.0.14': 'team04'},
        'hosts': ['attacker1', 'attacker2', 'attacker3', 'attacker4'],
        'create_teams': False,
        # The round1 web service only accepts flags of exactly 32 characters.
        'flag_template': '{letter}{body}=',
        'round_time': 300,
        'ticks_per_round': 10,
        'check_seconds': 0,
        'drain_ticks': 2,
        # Sub-check health mỗi ~30s trong tick; 1 lần DOWN => mất toàn bộ SLA tick đó.
        'probe_seconds': 30,
    },
    'meko_boutique': {
        'title': 'Meko',
        'prefix': '/checkers/meko_boutique/',
        'tasks': ('idor', 'sqli', 'upload', 'jwt', 'backup'),
        'teams': {'10.90.0.11': 'team1', '10.90.0.12': 'team2', '10.90.0.13': 'team3'},
        'hosts': ['team1', 'team2', 'team3'],
        'create_teams': True,
        'flag_template': 'MekoDataCTF{{{body}}}',
        'round_time': 300,
        'ticks_per_round': 10,
        'check_seconds': 60,
        'drain_ticks': 0,
        # Sub-check health mỗi ~30s trong tick; 1 lần DOWN => mất toàn bộ SLA tick đó.
        'probe_seconds': 30,
    },
}

PROFILES['mmoiws'] = {
    **PROFILES['meko_boutique'],
    'title': 'Crypto AD',
    'prefix': '/checkers/mmoiws/',
    'tasks': ('crypto',),
    'round': 2,
    'previous_lab': 'meko_boutique',
    'intermission_seconds': 600,
}

PROFILES['full_rounds'] = {
    **PROFILES['meko_boutique'],
    'title': 'Full Rounds Web',
    'prefix': '/checkers/full_rounds/',
    'preview_seconds': 600,
    'next_lab': 'full_rounds_crypto',
}

PROFILES['full_rounds_crypto'] = {
    **PROFILES['meko_boutique'],
    'title': 'Full Rounds Crypto',
    'prefix': '/checkers/full_rounds_crypto/',
    'tasks': ('curveball', 'padding_oracle', 'ecdsa_nonce'),
    'flag_template': 'MekoDataCTF{{{hexbody}}}',
    'preview_seconds': 600,
    'probe_seconds': 0,
    'crypto_seed': True,
    'round': 2,
    'tick_offset': PROFILES['full_rounds']['ticks_per_round'],
    'first_lab': 'full_rounds',
}


def transition_delay(lab, state, now):
    """Seconds left before the next lab may use the shared sandbox."""
    if state.get('lab') != lab['previous_lab'] or state.get('finished_at') is None:
        raise ValueError('Meko Boutique phải kết thúc trước khi chuyển sang Crypto AD.')
    return max(0, state['finished_at'] + lab['intermission_seconds'] - now)


def get(name):
    if not isinstance(name, str) or name not in PROFILES:
        raise ValueError('Lab không được hỗ trợ: ' + str(name))
    return PROFILES[name]


def for_slot(name, slot):
    return {**get(name), 'round': slot, 'tick_offset': (slot - 1) * SLOT_TICKS,
            'ticks_per_round': SLOT_TICKS, 'round_time': 300, 'preview_seconds': 600,
            'check_seconds': 60, 'drain_ticks': 0}
