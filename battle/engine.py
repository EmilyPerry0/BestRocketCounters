"""Battle simulation engine for Team GO Rocket encounters.

Stat/damage math (effective_attack/defense/hp, type_effectiveness,
calculate_damage) is kept separate from the turn-casting policy
(_select_move, _simulate_side) so a longer or multi-Pokemon simulation can
reuse either half independently -- e.g. calculate_damage works standalone
for a single hit, and _simulate_side is the one piece that would need to
change to support a different AI strategy or a longer battle window.
"""

import math
from dataclasses import dataclass

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
