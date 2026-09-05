"""TDD 'red' phase for the 5-turn Rocket battle simulator.

battle/engine.py does not exist yet -- every test below is expected to fail
(on collection, via this import) until it's implemented. See
/Users/emily/.claude/plans/dynamic-painting-widget.md for the full design
and where each expected number came from.
"""

import pytest
from battle.engine import (
    calculate_damage,
    effective_attack,
    effective_defense,
    simulate_turns,
    type_effectiveness,
)

from battle.sample_data import (
    LOCK_ON_FAST,
    OPPONENTS,
    RETURN,
    non_shadow_persian,
    player_excadrill,
    player_lucario,
    player_machamp,
    shadow_kangaskhan,
    shadow_persian,
)

# --- 1. Shadow stat multipliers ---------------------------------------------


def test_shadow_multipliers_apply_to_attack_and_defense():
    shadow = shadow_persian()
    non_shadow = shadow_persian()
    non_shadow.is_shadow = False

    assert effective_attack(shadow) == pytest.approx(effective_attack(non_shadow) * 1.2)
    assert effective_defense(shadow) == pytest.approx(
        effective_defense(non_shadow) * 0.8333
    )


# --- 2. Type effectiveness lookup -------------------------------------------


@pytest.mark.parametrize(
    "move_type, defender_types, expected",
    [
        ("FIGHTING", ["NORMAL"], 1.6),
        ("GROUND", ["NORMAL"], 1.0),
        ("FIRE", ["WATER"], 0.625),
    ],
)
def test_type_effectiveness_lookup(move_type, defender_types, expected):
    assert type_effectiveness(move_type, defender_types) == pytest.approx(expected)


# --- 3. STAB applies only when the move's type matches the attacker's ------


def test_stab_applies_when_move_type_matches_attacker_type():
    persian = shadow_persian()  # NORMAL type, Scratch is NORMAL -> STAB applies
    defender = shadow_kangaskhan()
    damage_with_stab = calculate_damage(persian, defender, persian.fast_move)

    # Same attacker/move, but no longer NORMAL-typed -> STAB should not apply.
    persian_no_stab = shadow_persian()
    persian_no_stab.types = ["WATER"]
    damage_without_stab = calculate_damage(
        persian_no_stab, defender, persian_no_stab.fast_move
    )

    assert damage_with_stab > damage_without_stab


def test_stab_does_not_apply_to_a_move_of_a_different_type():
    machamp = player_machamp()  # FIGHTING only; Bullet Punch is STEEL -> no STAB
    persian = shadow_persian()
    damage = calculate_damage(machamp, persian, machamp.fast_move)
    assert damage == 8


# --- 4. Single-hit damage matches hand calculation --------------------------


def test_single_hit_damage_values():
    lucario, persian = player_lucario(), shadow_persian()
    kangaskhan, excadrill = shadow_kangaskhan(), player_excadrill()
    machamp = player_machamp()

    assert calculate_damage(lucario, persian, lucario.fast_move) == 20
    assert calculate_damage(persian, lucario, persian.fast_move) == 4
    assert calculate_damage(excadrill, kangaskhan, excadrill.fast_move) == 5
    assert calculate_damage(kangaskhan, excadrill, kangaskhan.fast_move) == 7
    assert calculate_damage(machamp, persian, machamp.fast_move) == 8
    assert calculate_damage(persian, machamp, persian.fast_move) == 6


# --- 5/6/7. Full 5-turn sample battles ---------------------------------------


def test_lucario_vs_shadow_persian_slot_1():
    result = simulate_turns(player_lucario(), shadow_persian(), opponent_slot=1)

    assert [m.move_id for m in result.player.completed_moves] == [
        "COUNTER_FAST",
        "COUNTER_FAST",
    ]
    assert result.player.total_damage_dealt == 40
    assert result.player.final_energy == 18
    assert result.player.turns_used == 4

    assert [m.move_id for m in result.opponent.completed_moves] == ["SCRATCH_FAST"] * 5
    assert result.opponent.total_damage_dealt == 20
    assert result.opponent.final_energy == 20
    assert result.opponent.turns_used == 5


def test_excadrill_vs_shadow_kangaskhan_slot_2_never_fits_earthquake():
    result = simulate_turns(player_excadrill(), shadow_kangaskhan(), opponent_slot=2)

    assert [m.move_id for m in result.player.completed_moves] == ["MUD_SHOT_FAST"] * 5
    assert result.player.total_damage_dealt == 25
    assert result.player.final_energy == 30

    assert [m.move_id for m in result.opponent.completed_moves] == ["LOW_KICK_FAST"] * 5
    assert result.opponent.total_damage_dealt == 35
    assert result.opponent.final_energy == 25

    # A 7-turn charge move can never complete in a 5-turn window, regardless of energy.
    assert "EARTHQUAKE" not in [m.move_id for m in result.player.completed_moves]
    assert "EARTHQUAKE" not in [m.move_id for m in result.opponent.completed_moves]


def test_machamp_vs_shadow_persian_slot_1():
    result = simulate_turns(player_machamp(), shadow_persian(), opponent_slot=1)

    assert [m.move_id for m in result.player.completed_moves] == [
        "BULLET_PUNCH_FAST"
    ] * 2
    assert result.player.total_damage_dealt == 16
    assert result.player.final_energy == 22
    assert (
        result.player.turns_used == 4
    )  # 1 turn wasted -- a 3rd Bullet Punch doesn't fit

    assert [m.move_id for m in result.opponent.completed_moves] == ["SCRATCH_FAST"] * 5
    assert result.opponent.total_damage_dealt == 30
    assert result.opponent.final_energy == 20


# --- 8. The slot rule -- player may only charge-move against slot 3 --------


def test_player_withholds_charge_move_against_slot_1_despite_having_energy():
    player = non_shadow_persian(fast_move=LOCK_ON_FAST, charge_move=RETURN)
    opponent = shadow_persian()

    result = simulate_turns(player, opponent, opponent_slot=1)

    assert [m.move_id for m in result.player.completed_moves] == ["LOCK_ON_FAST"] * 5
    assert "RETURN" not in [m.move_id for m in result.player.completed_moves]
    assert [m.damage for m in result.player.completed_moves] == [2, 2, 2, 2, 2]
    assert result.player.total_damage_dealt == 10
    assert result.player.final_energy == 50
    assert result.player.turns_used == 5


def test_player_uses_charge_move_against_slot_3():
    player = non_shadow_persian(fast_move=LOCK_ON_FAST, charge_move=RETURN)
    opponent = shadow_persian()

    result = simulate_turns(player, opponent, opponent_slot=3)

    assert [m.move_id for m in result.player.completed_moves] == [
        "LOCK_ON_FAST"
    ] * 4 + ["RETURN"]
    assert [m.damage for m in result.player.completed_moves] == [2, 2, 2, 2, 20]
    assert result.player.total_damage_dealt == 28
    assert result.player.final_energy == 7
    assert result.player.turns_used == 5


# --- 9. The slot rule does not apply to the opponent ------------------------


def test_opponent_uses_charge_move_regardless_of_slot():
    player = (
        shadow_persian()
    )  # stand-in "attacker" role; is_shadow irrelevant to this check
    opponent = non_shadow_persian(fast_move=LOCK_ON_FAST, charge_move=RETURN)
    opponent.is_shadow = True

    result = simulate_turns(player, opponent, opponent_slot=1)

    assert [m.move_id for m in result.opponent.completed_moves] == [
        "LOCK_ON_FAST"
    ] * 4 + ["RETURN"]
    assert [m.damage for m in result.opponent.completed_moves] == [2, 2, 2, 2, 20]
    assert result.opponent.total_damage_dealt == 28
    assert result.opponent.final_energy == 7


# --- 10. Every opponent fixture is Shadow -----------------------------------


@pytest.mark.parametrize("opponent", OPPONENTS, ids=lambda p: p.species)
def test_opponents_are_always_shadow(opponent):
    assert opponent.is_shadow is True
