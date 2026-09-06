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

# Used only for the Rocket CP-formula verification (test 12) -- the moveset
# doesn't matter there, just real legal ones for the species.
MUD_SLAP_FAST = Move(
    "MUD_SLAP_FAST", "GROUND", power=19.0, duration_turns=3, energy_delta=13
)
STONE_EDGE = Move(
    "STONE_EDGE", "ROCK", power=105.0, duration_turns=5, energy_delta=-100
)
EARTH_POWER = Move(
    "EARTH_POWER", "GROUND", power=100.0, duration_turns=7, energy_delta=-50
)

ASTONISH_FAST = Move(
    "ASTONISH_FAST", "GHOST", power=7.0, duration_turns=2, energy_delta=13
)
SHADOW_CLAW_FAST = Move(
    "SHADOW_CLAW_FAST", "GHOST", power=6.0, duration_turns=1, energy_delta=4
)
SHADOW_BALL = Move(
    "SHADOW_BALL", "GHOST", power=100.0, duration_turns=6, energy_delta=-50
)

# Magikarp's real moveset -- Splash deals no damage, and Struggle (its only
# legal charge move) doesn't actually use energy in the real game, unlike
# every other charge move here. energy_delta=0 is the closest fit within
# our model (a move that's always "affordable").
SPLASH_FAST = Move("SPLASH_FAST", "WATER", power=0.0, duration_turns=3, energy_delta=17)
STRUGGLE = Move("STRUGGLE", "NORMAL", power=35.0, duration_turns=4, energy_delta=0)

WATERFALL_FAST = Move(
    "WATERFALL_FAST", "WATER", power=13.0, duration_turns=2, energy_delta=7
)
HYDRO_PUMP = Move(
    "HYDRO_PUMP", "WATER", power=135.0, duration_turns=7, energy_delta=-100
)

SAND_TOMB = Move("SAND_TOMB", "GROUND", power=60.0, duration_turns=8, energy_delta=-33)

BULLDOZE = Move("BULLDOZE", "GROUND", power=80.0, duration_turns=7, energy_delta=-50)


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


def shadow_rhyperior() -> Pokemon:
    return Pokemon(
        species="RHYPERIOR",
        level=20,
        types=["GROUND", "ROCK"],
        base_attack=241,
        base_defense=190,
        base_stamina=251,
        fast_move=MUD_SLAP_FAST,
        charge_move=STONE_EDGE,
        is_shadow=True,
    )


def shadow_landorus() -> Pokemon:
    return Pokemon(
        species="LANDORUS",
        level=20,
        types=["GROUND", "FLYING"],
        base_attack=261,
        base_defense=182,
        base_stamina=205,
        fast_move=MUD_SLAP_FAST,
        charge_move=EARTH_POWER,
        is_shadow=True,
    )


def shadow_magikarp() -> Pokemon:
    return Pokemon(
        species="MAGIKARP",
        level=20,
        types=["WATER"],
        base_attack=29,
        base_defense=85,
        base_stamina=85,
        fast_move=SPLASH_FAST,
        charge_move=STRUGGLE,
        is_shadow=True,
    )


def shadow_gyarados() -> Pokemon:
    return Pokemon(
        species="GYARADOS",
        level=20,
        types=["WATER", "FLYING"],
        base_attack=237,
        base_defense=186,
        base_stamina=216,
        fast_move=WATERFALL_FAST,
        charge_move=HYDRO_PUMP,
        is_shadow=True,
    )


def shadow_gastly() -> Pokemon:
    return Pokemon(
        species="GASTLY",
        level=20,
        types=["GHOST", "POISON"],
        base_attack=186,
        base_defense=67,
        base_stamina=102,
        fast_move=ASTONISH_FAST,
        charge_move=SHADOW_BALL,
        is_shadow=True,
    )


def shadow_gengar() -> Pokemon:
    return Pokemon(
        species="GENGAR",
        level=20,
        types=["GHOST", "POISON"],
        base_attack=261,
        base_defense=149,
        base_stamina=155,
        fast_move=SHADOW_CLAW_FAST,
        charge_move=SHADOW_BALL,
        is_shadow=True,
    )


def shadow_cofagrigus() -> Pokemon:
    return Pokemon(
        species="COFAGRIGUS",
        level=20,
        types=["GHOST"],
        base_attack=163,
        base_defense=237,
        base_stamina=151,
        fast_move=ASTONISH_FAST,
        charge_move=SHADOW_BALL,
        is_shadow=True,
    )


def shadow_rhyhorn() -> Pokemon:
    return Pokemon(
        species="RHYHORN",
        level=20,
        types=["GROUND", "ROCK"],
        base_attack=140,
        base_defense=127,
        base_stamina=190,
        fast_move=MUD_SLAP_FAST,
        charge_move=BULLDOZE,
        is_shadow=True,
    )


def shadow_golurk() -> Pokemon:
    return Pokemon(
        species="GOLURK",
        level=20,
        types=["GROUND", "GHOST"],
        base_attack=222,
        base_defense=154,
        base_stamina=205,
        fast_move=ASTONISH_FAST,
        charge_move=EARTH_POWER,
        is_shadow=True,
    )


def shadow_vibrava() -> Pokemon:
    return Pokemon(
        species="VIBRAVA",
        level=20,
        types=["GROUND", "DRAGON"],
        base_attack=134,
        base_defense=99,
        base_stamina=137,
        fast_move=MUD_SHOT_FAST,
        charge_move=SAND_TOMB,
        is_shadow=True,
    )


OPPONENTS = [
    shadow_persian(),
    shadow_kangaskhan(),
    shadow_rhyperior(),
    shadow_landorus(),
    shadow_magikarp(),
    shadow_gyarados(),
    shadow_gastly(),
    shadow_gengar(),
    shadow_cofagrigus(),
    shadow_rhyhorn(),
    shadow_golurk(),
    shadow_vibrava(),
]


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
