"""Battle simulation engine for Team GO Rocket encounters.

Stat/damage math (effective_attack/defense/hp, type_effectiveness,
calculate_damage) is kept separate from the turn-casting policy
(_select_move, _simulate_side) so a longer or multi-Pokemon simulation can
reuse either half independently -- e.g. calculate_damage works standalone
for a single hit, and _simulate_side is the one piece that would need to
change to support a different AI strategy or a longer battle window.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from battle.sample_data import (
    CPM_TABLE,
    SAME_TYPE_ATTACK_BONUS_MULTIPLIER,
    SHADOW_ATTACK_BONUS_MULTIPLIER,
    SHADOW_DEFENSE_BONUS_MULTIPLIER,
    TYPE_CHART,
    TYPE_ORDER,
)

PERFECT_IV = 15  # every sample Pokemon is assumed to have 15/15/15 IVs
MAX_ENERGY = 100  # combatSettings.maxEnergy


def _cpm(level: int) -> float:
    return CPM_TABLE[level]


def effective_attack(pokemon) -> float:
    attack = (pokemon.base_attack + PERFECT_IV) * _cpm(pokemon.level)
    if pokemon.is_shadow:
        attack *= SHADOW_ATTACK_BONUS_MULTIPLIER
    return attack


def effective_defense(pokemon) -> float:
    defense = (pokemon.base_defense + PERFECT_IV) * _cpm(pokemon.level)
    if pokemon.is_shadow:
        defense *= SHADOW_DEFENSE_BONUS_MULTIPLIER
    return defense


def effective_hp(pokemon) -> int:
    """Not exercised by a 5-turn slice (no one faints that fast), but part
    of the engine's public surface for whenever a full battle needs to know
    when a side is knocked out. Shadow has no stamina/HP bonus."""
    return math.floor((pokemon.base_stamina + PERFECT_IV) * _cpm(pokemon.level))


# Team GO Rocket's Shadow Pokemon do NOT use the standard player CP formula
# above (base + 15 IV, run through the player's per-level CPM curve) --
# they're NPC-controlled and Niantic assigns their stats directly via a
# separate formula, keyed by the Rocket member's rank and a difficulty
# multiplier (rCPM) tied to the *trainer's* level rather than a Pokemon
# level. Confirmed against Pokebattler's reverse-engineered formula
# (https://articles.pokebattler.com/2021/06/21/cracking-the-rocket-cp-formula-2021-edition/),
# not derived from data/latest.json -- the Game Master doesn't publish this.
ROCKET_RANK_GRUNT = 1.0
ROCKET_RANK_LEADER = 1.05
ROCKET_RANK_GIOVANNI = 1.15

# defaulting to level 80 (full strength, as if uncapped by trainer level).
DEFAULT_TRAINER_LEVEL = 80


ROCKET_CPM_RAW_BY_TRAINER_LEVEL = {
    8: 0.29899919,
    9: 0.352000237,
    10: 0.399999797,
    11: 0.443999946,
    12: 0.487000316,
    13: 0.529002368,
    14: 0.569000363,
    15: 0.60800004,
    16: 0.645999432,
    17: 0.683000147,
    18: 0.719999731,
    19: 0.755000234,
    20: 0.795999765,
    21: 0.808000207,
    22: 0.820000947,
    23: 0.831999838,
    24: 0.843999565,
    25: 0.855000198,
    26: 0.866999269,
    27: 0.877999663,
    28: 0.88999939,
    29: 0.901000082,
    30: 0.911996603,
    31: 0.92299962,
    32: 0.934000373,
    33: 0.944997787,
    34: 0.954999924,
    35: 0.965000153,
    36: 0.976000071,
    37: 0.985995412,
    38: 0.997000039,
    39: 1.0069952,
    40: 1.01599848,
    41: 1.02600098,
    42: 1.03600228,
    43: 1.04599953,
    44: 1.05600107,
    45: 1.06500006,
    46: 1.07499981,
    47: 1.08400011,
    48: 1.09299958,
    49: 1.10200143,
    50: 1.11099982,
    51: 1.12,
    52: 1.12799954,
    53: 1.13699937,
    54: 1.14499974,
    55: 1.15299988,
    56: 1.16100001,
    57: 1.16799998,
    58: 1.17600024,
    59: 1.18400049,
    60: 1.19099939,
    61: 1.19899976,
    62: 1.20600212,
    63: 1.21400058,
    64: 1.22099972,
    65: 1.22899985,
    66: 1.23599958,
    67: 1.24299955,
    68: 1.25099993,
    69: 1.2579999,
    70: 1.2650001,
    71: 1.26999998,
    72: 1.27499998,
    73: 1.28000009,
    74: 1.28499985,
    75: 1.28999996,
    76: 1.29500079,
    77: 1.29999983,
    78: 1.30500031,
    79: 1.30999994,
    80: 1.31500006,
}


def rocket_cpm_for_trainer_level(trainer_level: int) -> float:
    """Look up the raw (pre-multiplier) rCPM for a given trainer level
    (8-90, the range the source data covers)."""
    try:
        return ROCKET_CPM_RAW_BY_TRAINER_LEVEL[trainer_level]
    except KeyError:
        raise ValueError(
            f"no known rCPM for trainer level {trainer_level!r} -- only "
            f"{min(ROCKET_CPM_RAW_BY_TRAINER_LEVEL)}-"
            f"{max(ROCKET_CPM_RAW_BY_TRAINER_LEVEL)} are confirmed"
        ) from None


def rocket_attack_iv(base_attack: int) -> int:
    """Shadow Pokemon get a fixed, species-dependent 'attack IV' instead of
    the usual 0-15 -- much larger, and it scales with the species' own base
    attack so CP stays roughly comparable across different Pokemon."""
    return math.floor(2 / 3 * base_attack + 25)


def rocket_effective_attack(pokemon, rank: float, rCPM: float) -> float:
    return (pokemon.base_attack + rocket_attack_iv(pokemon.base_attack)) * rCPM * rank


def rocket_effective_defense(pokemon, rank: float, rCPM: float) -> float:
    return (pokemon.base_defense + 15) * rCPM * rank  # fixed defense IV of 15


def rocket_effective_hp(pokemon, rank: float, rCPM: float) -> int:
    """Floored, for battle use. rocket_cp() below uses the unfloored value,
    per Niantic's own CP calculation."""
    return math.floor(0.6 * (pokemon.base_stamina + 15)) * rCPM * rank


def rocket_cp(pokemon, rank: float, trainer_level: int = DEFAULT_TRAINER_LEVEL) -> int:
    rCPM = rocket_cpm_for_trainer_level(trainer_level)
    attack = rocket_effective_attack(pokemon, rank, rCPM)
    defense = rocket_effective_defense(pokemon, rank, rCPM)
    stamina = rocket_effective_hp(pokemon, rank, rCPM)
    return math.floor(0.1 * attack * math.sqrt(defense) * math.sqrt(stamina))


def type_effectiveness(move_type: str, defender_types: list[str]) -> float:
    scalar = TYPE_CHART[move_type]
    effectiveness = 1.0
    for defender_type in defender_types:
        effectiveness *= scalar[TYPE_ORDER.index(defender_type)]
    return effectiveness


def calculate_damage(attacker, defender, move) -> int:
    stab = SAME_TYPE_ATTACK_BONUS_MULTIPLIER if move.type in attacker.types else 1.0
    effectiveness = type_effectiveness(move.type, defender.types)
    raw = (
        0.5
        * move.power
        * (effective_attack(attacker) / effective_defense(defender))
        * stab
        * effectiveness
    )
    return math.floor(raw) + 1


@dataclass
class CompletedMove:
    move_id: str
    damage: int
    turn_completed_at: float
    energy_after: int


@dataclass
class SideResult:
    completed_moves: list[CompletedMove]
    total_damage_dealt: int
    final_energy: int
    turns_used: float


@dataclass
class BattleResult:
    player: SideResult
    opponent: SideResult


def _select_move(pokemon, energy: int, may_use_charge_move: bool):
    """Which move `pokemon` throws next, given its currently banked energy.

    Greedy: fire the charge move the instant it's affordable, unless this
    side isn't allowed to use one at all right now (the player, outside of
    opponent_slot 3).
    """
    charge_cost = -pokemon.charge_move.energy_delta
    if may_use_charge_move and energy >= charge_cost:
        return pokemon.charge_move
    return pokemon.fast_move


def _simulate_side(
    attacker, defender, num_turns: int, may_use_charge_move: bool
) -> SideResult:
    """Run one side's independent move-casting loop against a static,
    undamaged defender for num_turns. A move that would extend past
    num_turns is cut off entirely -- no damage, no energy, and the leftover
    turns just go unused.
    """
    turn = 0.0
    energy = 0
    completed_moves = []

    while True:
        move = _select_move(attacker, energy, may_use_charge_move)
        if turn + move.duration_turns > num_turns:
            break

        damage = calculate_damage(attacker, defender, move)
        turn += move.duration_turns
        energy = max(0, min(MAX_ENERGY, energy + move.energy_delta))
        completed_moves.append(CompletedMove(move.move_id, damage, turn, energy))

    return SideResult(
        completed_moves=completed_moves,
        total_damage_dealt=sum(m.damage for m in completed_moves),
        final_energy=energy,
        turns_used=turn,
    )


def simulate_turns(
    player, opponent, opponent_slot: int, num_turns: int = 5
) -> BattleResult:
    """Simulate a fixed window of a Team GO Rocket encounter.

    The opponent (always Shadow) uses its charge move as soon as it can,
    regardless of slot. The player may only do the same when opponent_slot
    is 3 (the Rocket's final Pokemon) -- otherwise it sticks to its fast
    move, saving its charge move for that final fight.
    """
    if opponent_slot not in (1, 2, 3):
        raise ValueError(f"opponent_slot must be 1, 2, or 3, got {opponent_slot!r}")

    player_result = _simulate_side(
        player, opponent, num_turns, may_use_charge_move=(opponent_slot == 3)
    )
    opponent_result = _simulate_side(
        opponent, player, num_turns, may_use_charge_move=True
    )
    return BattleResult(player=player_result, opponent=opponent_result)


# --- Full battle simulation (fight to a faint, not a fixed window) --------


class BattleOutcome(Enum):
    PLAYER_WIN = "PLAYER_WIN"
    ROCKET_WIN = "ROCKET_WIN"


PLAYER_WIN = BattleOutcome.PLAYER_WIN
ROCKET_WIN = BattleOutcome.ROCKET_WIN

MAX_BATTLE_TURNS = 600  # ~5 simulated minutes at 500ms/turn


@dataclass
class MatchupResult:
    outcome: BattleOutcome
    turns_taken: int
    player_hp_remaining: int
    opponent_hp_remaining: int
    player_shields_used: int = 0
    opponent_shields_used: int = 0


def _resolve_stats(pokemon, rank: float, rCPM: float) -> tuple[float, float, int]:
    """A Pokemon's (attack, defense, hp) via whichever formula actually
    applies to it: the Rocket formula (rank/rCPM aware) for a Shadow
    Pokemon, the standard player formula otherwise. This is what lets
    simulate_battle generalize to any player-vs-Rocket matchup."""
    if pokemon.is_shadow:
        return (
            rocket_effective_attack(pokemon, rank, rCPM),
            rocket_effective_defense(pokemon, rank, rCPM),
            rocket_effective_hp(pokemon, rank, rCPM),
        )
    return effective_attack(pokemon), effective_defense(pokemon), effective_hp(pokemon)


def _damage_from_stats(
    power: float,
    move_type: str,
    attacker_types: list[str],
    atk: float,
    defense: float,
    defender_types: list[str],
) -> int:
    """The same formula calculate_damage() uses, but taking already-resolved
    atk/def instead of deriving them from a Pokemon -- needed because the
    two sides of a Rocket battle use different stat formulas (see
    _resolve_stats)."""
    stab = SAME_TYPE_ATTACK_BONUS_MULTIPLIER if move_type in attacker_types else 1.0
    effectiveness = type_effectiveness(move_type, defender_types)
    return math.floor(0.5 * power * (atk / defense) * stab * effectiveness) + 1


@dataclass
class _CombatantState:
    pokemon: object
    attack: float
    defense: float
    hp: float
    energy: int = 0
    move: object = None
    turns_into_move: int = 0
    shields_remaining: int = 0
    shields_used: int = 0


def _compute_damage(attacker: _CombatantState, defender: _CombatantState) -> int:
    """Pure -- what attacker's current move would deal to defender, without
    applying it. Needed to decide same-tick priority (e.g. "would this be
    fatal?") before committing to an order."""
    move = attacker.move
    return _damage_from_stats(
        move.power,
        move.type,
        attacker.pokemon.types,
        attacker.attack,
        defender.defense,
        defender.pokemon.types,
    )


def _apply_attack(attacker: _CombatantState, defender: _CombatantState) -> None:
    """Applies attacker's current move to defender, including the Protect
    Shield mechanic: a Charged Attack against a defender with a shield
    left is blocked down to a flat 1 damage (the same guaranteed-minimum
    every hit already has) instead of its real computed damage. Fast
    Attacks are never shielded -- only a side's own charge_move counts."""
    is_charge_attack = attacker.move is attacker.pokemon.charge_move
    if is_charge_attack and defender.shields_remaining > 0:
        damage = 1
        defender.shields_remaining -= 1
        defender.shields_used += 1
    else:
        damage = _compute_damage(attacker, defender)
    defender.hp -= damage
    attacker.energy = max(
        0, min(MAX_ENERGY, attacker.energy + attacker.move.energy_delta)
    )


def _resolve_phase_a_conflict(a: _CombatantState, b: _CombatantState) -> bool:
    """Both a and b trigger a multi-turn move on the same tick. Applies
    damage per the same-turn priority spec; returns True if this is a
    freeze (an NPC-battle softlock -- the battle should stop progressing).

    - Exactly one side casts a Charged Attack: the NPC rule -- the Charged
      Attack resolves, the Fast Attack is cancelled outright, unless that
      cancelled Fast Attack would have been fatal to the Charged Attack's
      caster, in which case the whole battle freezes instead.
    - Both cast Charged Attacks: higher Attack stat goes first; the other
      still resolves right after, unless the first knocked it out. (A tied
      Attack stat -- not exercised by any test -- deterministically favors
      `a`, our stand-in for the spec's "randomly assigned.")
    - Both cast Fast Attacks: whichever would be fatal to its target goes
      first, if only one of the two would be; the other still resolves
      right after, unless the first knocked it out. If both or neither
      would be fatal, apply both simultaneously, same as always.
    """
    a_is_charge = a.move is a.pokemon.charge_move
    b_is_charge = b.move is b.pokemon.charge_move

    if a_is_charge != b_is_charge:
        charger, faster = (a, b) if a_is_charge else (b, a)
        if _compute_damage(faster, charger) >= charger.hp:
            return True  # freeze: the cancelled Fast Attack would be fatal
        _apply_attack(charger, faster)  # the Fast Attack is simply cancelled
        return False

    if a_is_charge:  # both charge
        first, second = (a, b) if a.attack >= b.attack else (b, a)
    else:  # both fast
        a_fatal = _compute_damage(a, b) >= b.hp
        b_fatal = _compute_damage(b, a) >= a.hp
        if a_fatal == b_fatal:
            _apply_attack(a, b)
            _apply_attack(b, a)
            return False
        first, second = (a, b) if a_fatal else (b, a)

    _apply_attack(first, second)
    if second.hp > 0:
        _apply_attack(second, first)
    return False


def _resolve_outcome(player_hp: float, opponent_hp: float) -> BattleOutcome | None:
    player_down = player_hp <= 0
    opponent_down = opponent_hp <= 0
    if not player_down and not opponent_down:
        return None
    if player_down and opponent_down:
        return PLAYER_WIN  # simultaneous KO: the player acted first
    return PLAYER_WIN if opponent_down else ROCKET_WIN


def simulate_battle(
    player,
    opponent,
    rank: float = ROCKET_RANK_GRUNT,
    trainer_level: int = DEFAULT_TRAINER_LEVEL,
    max_turns: int = MAX_BATTLE_TURNS,
    player_shields: int = 0,
    opponent_shields: int = 0,
) -> MatchupResult:
    """Simulate a full battle, turn by turn (500ms each), until one side
    faints. Both sides freely use their fast or charge move (greedy: charge
    the instant it's affordable) -- there's no opponent-slot gating here,
    that's specific to simulate_turns' Rocket-lineup context.

    `player` is never Shadow; `opponent` is always Shadow, and its stats
    come from the Rocket formula, keyed by `rank` and `trainer_level`
    (defaulting to a Grunt at max trainer level).

    `player_shields`/`opponent_shields` are each side's Protect Shield
    count (0 by default, matching every caller that doesn't care about
    the mechanic). A shield blocks a Charged Attack down to 1 damage --
    see _apply_attack. Grunts never use their shields in the real game
    even though the player always brings 2, so `opponent_shields` is only
    honored when `rank` isn't ROCKET_RANK_GRUNT; a Grunt opponent's
    effective shield count is always 0 regardless of what's passed in.

    Damage timing has two ordered phases each tick, so a multi-turn move
    finishing this tick can knock out a Pokemon before a 1-turn move
    landing on that same tick gets to resolve:
      - Phase A: a move with duration > 1 that reaches its final tick deals
        damage *before* that tick's progress is counted -- "the gap after
        the second-to-last turn, before the last turn." If *both* sides
        trigger a multi-turn move the same tick, see
        _resolve_phase_a_conflict for the same-turn priority rules (fatal-
        attack priority, Charged-vs-Charged priority by Attack stat, and
        the NPC rule that a Charged Attack cancels an opposing Fast Attack
        outright -- occasionally softlocking the battle, mapped here to
        never resolving within max_turns).
      - Phase B (after incrementing and checking for a faint): a 1-turn
        move, whose only tick is simultaneously its last, deals damage.
        Unconditional, even if both sides trigger one -- deliberately not
        given the same priority treatment as Phase A (see the plan doc).
    """
    rCPM = rocket_cpm_for_trainer_level(trainer_level)
    player_atk, player_def, player_hp = _resolve_stats(player, rank, rCPM)
    opponent_atk, opponent_def, opponent_hp = _resolve_stats(opponent, rank, rCPM)

    # Grunts never shield, regardless of how many they're "given" here.
    effective_opponent_shields = 0 if rank == ROCKET_RANK_GRUNT else opponent_shields

    player_state = _CombatantState(
        player, player_atk, player_def, player_hp, shields_remaining=player_shields
    )
    opponent_state = _CombatantState(
        opponent,
        opponent_atk,
        opponent_def,
        opponent_hp,
        shields_remaining=effective_opponent_shields,
    )
    sides = (player_state, opponent_state)
    frozen = False

    for turn in range(1, max_turns + 1):
        if frozen:
            continue  # softlocked: nothing progresses until max_turns raises

        for side in sides:
            if side.move is None:
                side.move = _select_move(
                    side.pokemon, side.energy, may_use_charge_move=True
                )
                side.turns_into_move = 0

        # Phase A: multi-turn moves finishing this tick, before it's counted.
        player_triggers_a = (
            player_state.move.duration_turns > 1
            and player_state.turns_into_move == player_state.move.duration_turns - 1
        )
        opponent_triggers_a = (
            opponent_state.move.duration_turns > 1
            and opponent_state.turns_into_move == opponent_state.move.duration_turns - 1
        )
        if player_triggers_a and opponent_triggers_a:
            frozen = _resolve_phase_a_conflict(player_state, opponent_state)
            if frozen:
                continue
        elif player_triggers_a:
            _apply_attack(player_state, opponent_state)
        elif opponent_triggers_a:
            _apply_attack(opponent_state, player_state)

        for side in sides:
            side.turns_into_move += 1

        outcome = _resolve_outcome(player_state.hp, opponent_state.hp)
        if outcome is not None:
            return MatchupResult(
                outcome,
                turn,
                max(player_state.hp, 0),
                max(opponent_state.hp, 0),
                player_state.shields_used,
                opponent_state.shields_used,
            )

        # Phase B: 1-turn moves, whose only tick just completed.
        for side, other in (
            (player_state, opponent_state),
            (opponent_state, player_state),
        ):
            if (
                side.move.duration_turns == 1
                and side.turns_into_move == side.move.duration_turns
            ):
                _apply_attack(side, other)

        outcome = _resolve_outcome(player_state.hp, opponent_state.hp)
        if outcome is not None:
            return MatchupResult(
                outcome,
                turn,
                max(player_state.hp, 0),
                max(opponent_state.hp, 0),
                player_state.shields_used,
                opponent_state.shields_used,
            )

        for side in sides:
            if side.turns_into_move >= side.move.duration_turns:
                side.move = None

    raise RuntimeError(f"battle did not resolve within {max_turns} turns")
