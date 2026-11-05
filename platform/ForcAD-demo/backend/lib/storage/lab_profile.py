"""Fixed facts of each lab the round lifecycle can run. Defaults stay on round1.

To add a lab, add an entry here; timing fields are explained in round_schedule.py.
"""
DEFAULT = 'round1'
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
    },
}


def get(name):
    if name not in PROFILES:
        raise ValueError('Lab không được hỗ trợ: ' + str(name))
    return PROFILES[name]
