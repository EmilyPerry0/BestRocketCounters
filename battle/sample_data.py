"""Sample fixture data for the battle simulator tests.

Every number here (base stats, move power/duration/energy, the type chart,
and the CPM-per-level table) is copied from a specific snapshot of
data/latest.json (the PokeMiners Game Master dump) rather than read from
that file at test time, so the test suite stays deterministic even as the
daily sync workflow (.github/workflows/update-game-master.yaml) updates it.
See /Users/emily/.claude/plans/dynamic-painting-widget.md for exactly which
fields each value came from.

Perfect IVs (15/15/15) are assumed for every sample Pokemon.
"""

from battle.models import Move, Pokemon

# --- combatSettings constants (data/latest.json) ---------------------------
SAME_TYPE_ATTACK_BONUS_MULTIPLIER = 1.2  # STAB
SHADOW_ATTACK_BONUS_MULTIPLIER = 1.2
SHADOW_DEFENSE_BONUS_MULTIPLIER = 0.8333

# --- playerLevel.cpMultiplier (data/latest.json) ----------------------------
# Indexed by WHOLE Pokemon level: CPM_TABLE[0] is level 1, CPM_TABLE[n] is
# level n + 1. Confirmed correct because CPM_TABLE[39] (level 40) is
# 0.7903, the well-known real level-40 CP multiplier. Sliced here to just
# the levels the sample Pokemon below use, plus a couple of neighbors.
CPM_TABLE = {
    15: 0.51739395,
    20: 0.5974,
    25: 0.667934,
    40: 0.7903,
}

# --- typeEffective.attackScalar (data/latest.json) --------------------------
# Defending-type order confirmed against POKEMON_TYPE_FIRE's known real
# matchups (1.6x vs Bug/Steel/Grass/Ice, 0.625x vs Rock/Fire/Water/Dragon).
# fmt: off
TYPE_ORDER = [
    "NORMAL", "FIGHTING", "FLYING", "POISON", "GROUND", "ROCK", "BUG",
    "GHOST", "STEEL", "FIRE", "WATER", "GRASS", "ELECTRIC", "PSYCHIC",
    "ICE", "DRAGON", "DARK", "FAIRY",
]
# fmt: on

# fmt: off
TYPE_CHART = {
    "NORMAL":   [1.0, 1.0, 1.0, 1.0, 1.0, 0.625, 1.0, 0.390625, 0.625, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    "FIGHTING": [1.6, 1.0, 0.625, 0.625, 1.0, 1.6, 0.625, 0.390625, 1.6, 1.0, 1.0, 1.0, 1.0, 0.625, 1.6, 1.0, 1.6, 0.625],
    "GROUND":   [1.0, 1.0, 0.390625, 1.6, 1.0, 1.6, 0.625, 1.0, 1.6, 1.6, 1.0, 0.625, 1.6, 1.0, 1.0, 1.0, 1.0, 1.0],
    "DARK":     [1.0, 0.625, 1.0, 1.0, 1.0, 1.0, 1.0, 1.6, 1.0, 1.0, 1.0, 1.0, 1.0, 1.6, 1.0, 1.0, 0.625, 0.625],
    "STEEL":    [1.0, 1.0, 1.0, 1.0, 1.0, 1.6, 1.0, 1.0, 0.625, 0.625, 0.625, 1.0, 0.625, 1.0, 1.6, 1.0, 1.0, 1.6],
    "FIRE":     [1.0, 1.0, 1.0, 1.0, 1.0, 0.625, 1.6, 1.0, 1.6, 0.625, 0.625, 1.6, 1.0, 1.0, 1.6, 0.625, 1.0, 1.0],
}
# fmt: on
# NOTE: only the attacking types used by the sample data / tests below are
# filled in above. Add rows here (straight from typeEffective.attackScalar)
# as more attacking types are needed -- do not guess values for a type
# that isn't listed.
#
# Looking up a value is battle.engine.type_effectiveness()'s job (not
# implemented yet) -- this module only holds the raw chart data.


# --- Moves (moveSettings in data/latest.json) -------------------------------
SCRATCH_FAST = Move(
    "SCRATCH_FAST", "NORMAL", power=6.0, duration_turns=1, energy_delta=4
)
FOUL_PLAY = Move("FOUL_PLAY", "DARK", power=70.0, duration_turns=4, energy_delta=-50)

LOW_KICK_FAST = Move(
    "LOW_KICK_FAST", "FIGHTING", power=5.0, duration_turns=1, energy_delta=5
)
EARTHQUAKE = Move(
    "EARTHQUAKE", "GROUND", power=140.0, duration_turns=7, energy_delta=-100
)

COUNTER_FAST = Move(
    "COUNTER_FAST", "FIGHTING", power=13.0, duration_turns=2, energy_delta=9
)
AURA_SPHERE = Move(
    "AURA_SPHERE", "FIGHTING", power=100.0, duration_turns=4, energy_delta=-50
)

MUD_SHOT_FAST = Move(
    "MUD_SHOT_FAST", "GROUND", power=4.0, duration_turns=1, energy_delta=6
)

BULLET_PUNCH_FAST = Move(
    "BULLET_PUNCH_FAST", "STEEL", power=10.0, duration_turns=2, energy_delta=11
)
CLOSE_COMBAT = Move(
    "CLOSE_COMBAT", "FIGHTING", power=105.0, duration_turns=5, energy_delta=-100
)

# A cheap, fast-casting fast/charge pair used only to exercise the
# charge-move-fires-cleanly mechanic (see tests 8/9) -- real move data, just
# not the moveset either sample species actually carries in the app.
LOCK_ON_FAST = Move(
    "LOCK_ON_FAST", "NORMAL", power=2.0, duration_turns=1, energy_delta=10
)
RETURN = Move("RETURN", "NORMAL", power=25.0, duration_turns=1, energy_delta=-33)


# --- Opponents: always Shadow (pokemonSettings in data/latest.json) --------
def shadow_persian(
    fast_move: Move = SCRATCH_FAST, charge_move: Move = FOUL_PLAY
) -> Pokemon:
    return Pokemon(
        species="PERSIAN",
        level=20,
        types=["NORMAL"],
        base_attack=150,
        base_defense=136,
        base_stamina=163,
        fast_move=fast_move,
        charge_move=charge_move,
        is_shadow=True,
    )


def shadow_kangaskhan() -> Pokemon:
    return Pokemon(
        species="KANGASKHAN",
        level=20,
        types=["NORMAL"],
        base_attack=181,
        base_defense=165,
        base_stamina=233,
        fast_move=LOW_KICK_FAST,
        charge_move=EARTHQUAKE,
        is_shadow=True,
    )


OPPONENTS = [shadow_persian(), shadow_kangaskhan()]


# --- Players: never Shadow (pokemonSettings in data/latest.json) ----------
def non_shadow_persian(
    fast_move: Move = LOCK_ON_FAST, charge_move: Move = RETURN
) -> Pokemon:
    """Used only for the charge-move mechanic tests (8/9), not as a Rocket opponent."""
    return Pokemon(
        species="PERSIAN",
        level=20,
        types=["NORMAL"],
        base_attack=150,
        base_defense=136,
        base_stamina=163,
        fast_move=fast_move,
        charge_move=charge_move,
        is_shadow=False,
    )


def player_lucario() -> Pokemon:
    return Pokemon(
        species="LUCARIO",
        level=40,
        types=["FIGHTING", "STEEL"],
        base_attack=236,
        base_defense=144,
        base_stamina=172,
        fast_move=COUNTER_FAST,
        charge_move=AURA_SPHERE,
        is_shadow=False,
    )


def player_excadrill() -> Pokemon:
    return Pokemon(
        species="EXCADRILL",
        level=25,
        types=["GROUND", "STEEL"],
        base_attack=255,
        base_defense=129,
        base_stamina=242,
        fast_move=MUD_SHOT_FAST,
        charge_move=EARTHQUAKE,
        is_shadow=False,
    )


def player_machamp() -> Pokemon:
    return Pokemon(
        species="MACHAMP",
        level=15,
        types=["FIGHTING"],
        base_attack=234,
        base_defense=159,
        base_stamina=207,
        fast_move=BULLET_PUNCH_FAST,
        charge_move=CLOSE_COMBAT,
        is_shadow=False,
    )


PLAYERS = [player_lucario(), player_excadrill(), player_machamp()]
