"""Battle simulation logic.

Only stubbed out so far -- just enough for tests/test_battle.py to import
successfully and get test 10 (the sample opponents are always Shadow) to
pass. Every other test still fails, now at call time (NotImplementedError)
rather than at collection time (ImportError), which is expected until the
rest of this module is implemented.
"""


def effective_attack(pokemon):
    raise NotImplementedError


def effective_defense(pokemon):
    raise NotImplementedError


def type_effectiveness(move_type, defender_types):
    raise NotImplementedError


def calculate_damage(attacker, defender, move):
    raise NotImplementedError


def simulate_turns(player, opponent, opponent_slot, num_turns=5):
    raise NotImplementedError
