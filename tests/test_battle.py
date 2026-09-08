"""Tests for the 5-turn Rocket battle simulator.

See /Users/emily/.claude/plans/dynamic-painting-widget.md for the full
design and where each expected number came from.
"""

import pytest

from battle.engine import (
    PLAYER_WIN,
    ROCKET_RANK_GIOVANNI,
    ROCKET_RANK_GRUNT,
    ROCKET_WIN,
    calculate_damage,
    effective_attack,
    effective_defense,
    rocket_attack_iv,
    rocket_cp,
    rocket_cpm_for_trainer_level,
    simulate_battle,
    simulate_turns,
    type_effectiveness,
)
from battle.models import Move, Pokemon
from battle.sample_data import (
    LOCK_ON_FAST,
    OPPONENTS,
    RETURN,
    non_shadow_persian,
    player_excadrill,
    player_lucario,
    player_machamp,
    player_mega_mewtwo_y,
    player_weedle_level_1,
    shadow_cofagrigus,
    shadow_gastly,
    shadow_gengar,
    shadow_golurk,
    shadow_gyarados,
    shadow_kangaskhan,
    shadow_landorus,
    shadow_magikarp,
    shadow_mewtwo,
    shadow_persian,
    shadow_rhyhorn,
    shadow_rhyperior,
    shadow_vibrava,
    shadow_weedle,
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
    assert damage == 9


# --- 4. Single-hit damage matches hand calculation --------------------------


def test_single_hit_damage_values():
    lucario, persian = player_lucario(), shadow_persian()
    kangaskhan, excadrill = shadow_kangaskhan(), player_excadrill()
    machamp = player_machamp()

    assert calculate_damage(lucario, persian, lucario.fast_move) == 33
    assert calculate_damage(persian, lucario, persian.fast_move) == 3
    assert calculate_damage(excadrill, kangaskhan, excadrill.fast_move) == 5
    assert calculate_damage(kangaskhan, excadrill, kangaskhan.fast_move) == 6
    assert calculate_damage(machamp, persian, machamp.fast_move) == 9
    assert calculate_damage(persian, machamp, persian.fast_move) == 5


# --- 5/6/7. Full 5-turn sample battles ---------------------------------------


def test_lucario_vs_shadow_persian_slot_1():
    result = simulate_turns(player_lucario(), shadow_persian(), opponent_slot=1)

    assert [m.move_id for m in result.player.completed_moves] == [
        "COUNTER_FAST",
        "COUNTER_FAST",
    ]
    assert result.player.total_damage_dealt == 66
    assert result.player.final_energy == 18
    assert result.player.turns_used == 4

    assert [m.move_id for m in result.opponent.completed_moves] == ["SCRATCH_FAST"] * 5
    assert result.opponent.total_damage_dealt == 15
    assert result.opponent.final_energy == 20
    assert result.opponent.turns_used == 5


def test_excadrill_vs_shadow_kangaskhan_slot_2_never_fits_earthquake():
    result = simulate_turns(player_excadrill(), shadow_kangaskhan(), opponent_slot=2)

    assert [m.move_id for m in result.player.completed_moves] == ["MUD_SHOT_FAST"] * 5
    assert result.player.total_damage_dealt == 25
    assert result.player.final_energy == 30

    assert [m.move_id for m in result.opponent.completed_moves] == ["LOW_KICK_FAST"] * 5
    assert result.opponent.total_damage_dealt == 30
    assert result.opponent.final_energy == 25

    # A 7-turn charge move can never complete in a 5-turn window, regardless of energy.
    assert "EARTHQUAKE" not in [m.move_id for m in result.player.completed_moves]
    assert "EARTHQUAKE" not in [m.move_id for m in result.opponent.completed_moves]


def test_machamp_vs_shadow_persian_slot_1():
    result = simulate_turns(player_machamp(), shadow_persian(), opponent_slot=1)

    assert [m.move_id for m in result.player.completed_moves] == [
        "BULLET_PUNCH_FAST"
    ] * 2
    assert result.player.total_damage_dealt == 18
    assert result.player.final_energy == 22
    assert (
        result.player.turns_used == 4
    )  # 1 turn wasted -- a 3rd Bullet Punch doesn't fit

    assert [m.move_id for m in result.opponent.completed_moves] == ["SCRATCH_FAST"] * 5
    assert result.opponent.total_damage_dealt == 25
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
    # Reuses the exact non-shadow Persian L20 fixture from test 8 as the
    # "opponent" here -- is_shadow only affects effective_attack/defense
    # (see test 1), not move selection, so it's irrelevant to what this
    # test checks and left alone to keep the numbers directly comparable
    # to test_player_uses_charge_move_against_slot_3 above.
    player = shadow_persian()  # stand-in defender; a real opponent is always Shadow
    opponent = non_shadow_persian(fast_move=LOCK_ON_FAST, charge_move=RETURN)

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


# --- 11. Team GO Rocket's real (non-standard) stat formula ------------------
#
# Rocket's Shadow Pokemon aren't leveled up like a player's -- Niantic
# assigns their stats directly via a formula keyed by the Rocket member's
# rank and a trainer-level-driven difficulty multiplier (rCPM), not the
# usual base+IV/CPM(level) curve. See the comment above these functions in
# battle/engine.py for the source. These are standalone right now -- not
# yet wired into calculate_damage/simulate_turns, which still use the
# generic effective_attack/effective_defense for every existing test above.


def test_rocket_attack_iv_scales_with_base_attack():
    persian, kangaskhan = shadow_persian(), shadow_kangaskhan()
    assert rocket_attack_iv(persian.base_attack) == 125
    assert rocket_attack_iv(kangaskhan.base_attack) == 145


def test_rocket_cp_matches_formula_giovanni():
    persian = shadow_persian()
    rhyperior = shadow_rhyperior()
    landorus = shadow_landorus()

    assert rocket_cp(persian, ROCKET_RANK_GIOVANNI) == 7956
    assert rocket_cp(rhyperior, ROCKET_RANK_GIOVANNI) == 17588
    assert rocket_cp(landorus, ROCKET_RANK_GIOVANNI) == 16963


# def test_rocket_cp_matches_formula_leader():


def test_rocket_cp_matches_formula_grunt():
    magikarp = shadow_magikarp()
    gyrados = shadow_gyarados()
    gastly = shadow_gastly()
    gengar = shadow_gengar()
    cofagrigus = shadow_cofagrigus()
    rhyhorn = shadow_rhyhorn()
    golurk = shadow_golurk()
    vibrava = shadow_vibrava()

    assert rocket_cp(magikarp, ROCKET_RANK_GRUNT, 78) == 962
    assert rocket_cp(gyrados, ROCKET_RANK_GRUNT, 78) == 11912
    assert rocket_cp(gastly, ROCKET_RANK_GRUNT, 58) == 3510
    assert rocket_cp(gengar, ROCKET_RANK_GRUNT, 58) == 8228
    assert rocket_cp(cofagrigus, ROCKET_RANK_GRUNT, 58) == 6465
    assert rocket_cp(rhyhorn, ROCKET_RANK_GRUNT, 58) == 4715
    assert rocket_cp(vibrava, ROCKET_RANK_GRUNT, 58) == 3493
    assert rocket_cp(golurk, ROCKET_RANK_GRUNT, 58) == 8159


def test_attack_IV_rocket_matches():
    landorus = shadow_landorus()
    persian = shadow_persian()
    rhyperior = shadow_rhyperior()
    assert rocket_attack_iv(landorus.base_attack) == 199
    assert rocket_attack_iv(persian.base_attack) == 125
    assert rocket_attack_iv(rhyperior.base_attack) == 185


# --- 12. Rocket CP formula vs. real observed values -------------------------
#
# General-purpose check: given a Pokemon, a trainer level (or rCPM directly,
# when the trainer level isn't known), and a rank, does rocket_cp() match a
# real observed CP? trainer_level=None means "not given, use the default
# rCPM (1.0)" rather than guessing one.


def assert_rocket_cp_matches(pokemon, rank, trainer_level, expected_cp):
    rcpm = (
        rocket_cpm_for_trainer_level(trainer_level)
        if trainer_level is not None
        else None
    )
    kwargs = {"rCPM": rcpm} if rcpm is not None else {}
    assert rocket_cp(pokemon, rank, **kwargs) == expected_cp


@pytest.mark.parametrize(
    "pokemon_factory, rank, trainer_level, expected_cp",
    [
        # A Giovanni fight: Giovanni rank, rCPM=1.0 (trainer_level=None).
        (shadow_persian, ROCKET_RANK_GIOVANNI, None, 7956),
        (shadow_rhyperior, ROCKET_RANK_GIOVANNI, None, 17588),
        (shadow_landorus, ROCKET_RANK_GIOVANNI, None, 16963),
    ],
)
def test_rocket_cp_against_real_observed_values(
    pokemon_factory, rank, trainer_level, expected_cp
):
    assert_rocket_cp_matches(pokemon_factory(), rank, trainer_level, expected_cp)


# --- 13. A wildly lopsided fight: does the player actually win? -------------


def test_mega_mewtwo_level_51_beats_grunt_shadow_weedle_at_trainer_level_70():
    mewtwo = player_mega_mewtwo_y()
    weedle = shadow_weedle()

    result = simulate_battle(mewtwo, weedle)
    assert result.outcome == PLAYER_WIN
    result = simulate_battle(mewtwo, weedle, ROCKET_RANK_GRUNT)
    assert result.outcome == PLAYER_WIN
    result = simulate_battle(mewtwo, weedle, ROCKET_RANK_GRUNT, 80)
    assert result.outcome == PLAYER_WIN
    result = simulate_battle(mewtwo, weedle, trainer_level=80)
    assert result.outcome == PLAYER_WIN


def test_level_1_weedle_loses_to_shadow_mewtwo_at_max_difficulty():
    weedle = player_weedle_level_1()
    mewtwo = shadow_mewtwo()

    result = simulate_battle(weedle, mewtwo)
    assert result.outcome == ROCKET_WIN
    result = simulate_battle(weedle, mewtwo, ROCKET_RANK_GRUNT)
    assert result.outcome == ROCKET_WIN
    result = simulate_battle(weedle, mewtwo, ROCKET_RANK_GRUNT, 80)
    assert result.outcome == ROCKET_WIN
    result = simulate_battle(weedle, mewtwo, trainer_level=80)
    assert result.outcome == ROCKET_WIN


# --- 14. Same-turn move-priority spec -----------------------------------
#
# These probe a detailed real-game spec for what happens when both sides'
# moves resolve on the same turn (fatal-attack priority, Charged-vs-Charged
# priority by Attack stat, and the NPC-battle-specific rule that a Charged
# Attack cancels an opposing Fast Attack outright -- relevant here since
# every Team GO Rocket battle is an NPC battle). Several of these are
# expected to fail: simulate_battle doesn't implement Attack-stat Charged
# priority, NPC-specific Fast-cancelling, or the "battle freezes" quirk at
# all today -- only the fatal-priority-within-a-phase and multi-turn/1-turn
# phase split from before exist. See the plan doc for the full reasoning.
#
# All use a synthetic, contrived 100/100 base-stat block (not real species
# -- these are built purely to probe timing, so they're constructed here
# rather than added to sample_data.py, whose stated purpose is real numbers
# from data/latest.json) at ROCKET_RANK_GRUNT / trainer level 8, chosen
# because with base_attack=base_defense=100 for both sides, each hit's
# damage number works out numerically equal to the move's power -- makes
# the fixtures easy to reason about by hand.

_PRIORITY_RANK = ROCKET_RANK_GRUNT
_PRIORITY_LEVEL = 8

# A charge move so expensive it's never affordable -- a safe "do nothing
# else" filler for the required charge_move field in tests that don't care
# about charge moves at all.
_NEVER_AFFORDABLE = Move(
    "FILLER_CHARGE", "NORMAL", power=1.0, duration_turns=1, energy_delta=-999999
)


def _priority_mon(
    base_stamina,
    fast_move,
    charge_move=_NEVER_AFFORDABLE,
    base_attack=100,
    base_defense=100,
):
    return Pokemon(
        "TEST",
        20,
        ["NORMAL"],
        base_attack,
        base_defense,
        base_stamina,
        fast_move,
        charge_move,
        is_shadow=True,
    )


def _run(player, opponent):
    return simulate_battle(
        player, opponent, rank=_PRIORITY_RANK, trainer_level=_PRIORITY_LEVEL
    )


def test_fatal_fast_attack_takes_priority_same_turn():
    # Rule: "damage will first be applied to the Pokemon that will faint."
    # Both fast attacks finish tick 3; the player's is fatal to the
    # opponent, the opponent's is not fatal to the player. The opponent
    # should faint before its own same-tick attack can register.
    player = _priority_mon(1000, Move("P_FAST", "NORMAL", 100.0, 3, 0))
    opponent = _priority_mon(1, Move("O_FAST", "NORMAL", 10.0, 3, 0))

    result = _run(player, opponent)

    assert result.outcome == PLAYER_WIN
    assert result.player_hp_remaining == pytest.approx(
        182.09050671
    )  # full HP, untouched


def test_fatal_fast_attack_takes_priority_same_turn_mirrored():
    player = _priority_mon(1, Move("P_FAST", "NORMAL", 10.0, 3, 0))
    opponent = _priority_mon(1000, Move("O_FAST", "NORMAL", 100.0, 3, 0))

    result = _run(player, opponent)

    assert result.outcome == ROCKET_WIN
    assert result.opponent_hp_remaining == pytest.approx(
        182.09050671
    )  # full HP, untouched


def test_neither_fast_attack_fatal_both_land():
    # Rule's other two clauses ("1-turn attack first, else simultaneous")
    # aren't independently observable via MatchupResult (no move log), so
    # this only checks the part that *is* observable: neither side's hit
    # gets skipped just because the other also landed this turn.
    player = _priority_mon(1000, Move("P_FAST", "NORMAL", 10.0, 3, 0))
    opponent = _priority_mon(1000, Move("O_FAST", "NORMAL", 10.0, 3, 0))

    result = _run(player, opponent)

    assert result.player_hp_remaining < 182.09050671
    assert result.opponent_hp_remaining < 182.09050671


def test_both_fatal_one_turn_attacks_is_engines_documented_tiebreak():
    # Rule: "if both would be knocked out by a one-turn Fast Attack... this
    # can result in a double-knockout or a tie" -- the real game is
    # latency-/randomness-dependent here, which isn't something we can
    # assert deterministically. This checks our engine's own documented
    # simplification instead (simultaneous double-KO favors the player).
    player = _priority_mon(1, Move("P_FAST", "NORMAL", 100.0, 1, 0))
    opponent = _priority_mon(1, Move("O_FAST", "NORMAL", 100.0, 1, 0))

    result = _run(player, opponent)

    assert result.outcome == PLAYER_WIN


def test_both_fatal_one_turn_beats_multi_turn():
    # Not a direct quote -- a reasoned extrapolation combining the rule's
    # two clauses: among two simultaneously-fatal attacks, the one-turn
    # attack should take priority (as it would over a non-fatal multi-turn
    # attack), so the one-turn attacker should win outright, not trade a
    # double-KO.
    #
    # NOTE: this directly contradicts the multi-turn/1-turn phase ordering
    # built (and confirmed) in the previous session, where a multi-turn
    # move finishing this tick resolves *before* a 1-turn move can, on the
    # theory that its damage lands "in the gap before the last turn." That
    # was itself an extrapolation from a different framing of the same
    # kind of scenario -- this spec suggests it may have been backwards.
    # opponent's base_stamina=1600 -> hp ~=289.73: survives 2 of the
    # player's 100-power hits (200 dmg) but not a 3rd (300), so it's alive
    # right up to the tick where both attacks coincide, not KO'd earlier.
    player = _priority_mon(1, Move("P_FAST", "NORMAL", 100.0, 1, 0))
    opponent = _priority_mon(1600, Move("O_FAST", "NORMAL", 100.0, 3, 0))

    result = _run(player, opponent)

    assert result.outcome == PLAYER_WIN


def test_charged_vs_charged_priority_by_attack_stat():
    # Rule: "the one with a higher Attack stat will go first ... the other
    # Pokemon will move immediately after, unless it was knocked out."
    # Both sides ramp up on the same fast/charge shape, so their charge
    # moves complete on the same tick (4); only base_attack differs.
    #
    # low_attack's base_stamina=50 (not 1) is deliberate: HIGH's own Attack
    # stat is so large that even its 1-power Fast Attack would one-shot a
    # 1-HP target during the ramp-up tick, never reaching the charge-move
    # showdown this test is meant to probe.
    fast = Move("FAST", "NORMAL", 1.0, 1, 50)
    charge = Move("CHARGE", "NORMAL", 100.0, 3, -50)
    high_attack = _priority_mon(1000, fast, charge, base_attack=300)
    low_attack = _priority_mon(50, fast, charge, base_attack=50)

    result = _run(high_attack, low_attack)

    assert result.outcome == PLAYER_WIN
    # Untouched by the charge move specifically -- the -1 is the one
    # incidental point of chip damage from the mutual ramp-up Fast Attack
    # exchange on turn 1, unrelated to the priority mechanic under test.
    assert result.player_hp_remaining == pytest.approx(182.09050671 - 1)


def test_charged_vs_charged_priority_by_attack_stat_mirrored():
    fast = Move("FAST", "NORMAL", 1.0, 1, 50)
    charge = Move("CHARGE", "NORMAL", 100.0, 3, -50)
    low_attack = _priority_mon(50, fast, charge, base_attack=50)
    high_attack = _priority_mon(1000, fast, charge, base_attack=300)

    result = _run(low_attack, high_attack)

    assert result.outcome == ROCKET_WIN
    assert result.opponent_hp_remaining == pytest.approx(182.09050671 - 1)


def test_charged_attack_cancels_fast_attack_in_npc_battle():
    # Rule (NPC-battle footnote, which is what every Rocket battle is): "a
    # Charged Attack will instead cancel the Fast Attack." Player's 3-turn
    # Fast Attack registers the same tick (3) that the opponent's Charged
    # Attack completes -- per the NPC rule, the Fast Attack should never
    # land at all, not just be delayed.
    player = _priority_mon(1000, Move("P_FAST", "NORMAL", 100.0, 3, 10))
    opponent = _priority_mon(
        1600,
        Move("O_FAST", "NORMAL", 1.0, 1, 50),
        Move("O_CHARGE", "NORMAL", 30.0, 2, -50),
    )

    result = _run(player, opponent)

    assert result.opponent_hp_remaining == pytest.approx(
        289.73021511
    )  # full HP, untouched


def test_cancelled_fatal_fast_attack_freezes_the_battle():
    # Same shape as above, but the cancelled Fast Attack would have been
    # fatal to the Charged Attack's caster. Per the NPC-battle footnote,
    # "the battle would freeze and no longer progress" -- mapped to our
    # engine's closest concept, a battle that never resolves within
    # max_turns and raises RuntimeError.
    player = _priority_mon(1000, Move("P_FAST", "NORMAL", 300.0, 3, 10))
    opponent = _priority_mon(
        1600,
        Move("O_FAST", "NORMAL", 1.0, 1, 50),
        Move("O_CHARGE", "NORMAL", 30.0, 2, -50),
    )

    with pytest.raises(RuntimeError):
        _run(player, opponent)
