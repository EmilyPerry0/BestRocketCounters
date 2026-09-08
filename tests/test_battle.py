"""Tests for the 5-turn Rocket battle simulator.

See /Users/emily/.claude/plans/dynamic-painting-widget.md for the full
design and where each expected number came from.
"""

import pytest

from battle.engine import (
    PLAYER_WIN,
    ROCKET_RANK_GIOVANNI,
    ROCKET_RANK_GRUNT,
    ROCKET_RANK_LEADER,
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


# Lucario (FIGHTING/STEEL) against all 18 attacking types -- a dual-type
# defender's effectiveness is the product of each of its own types'
# effectiveness against the move, so Lucario's Steel typing turns what
# would otherwise be several neutral matchups (vs. NORMAL alone, say)
# into resisted ones, and stacks with Fighting's own resistances/
# weaknesses for the doubly-resisted (BUG/POISON/ROCK) and neutral
# (FLYING/PSYCHIC/FAIRY, where a Fighting weakness and a Steel resistance
# exactly cancel out) cases. Every value here is hand-verified against
# TYPE_CHART/TYPE_ORDER in battle/sample_data.py.
LUCARIO_TYPES = player_lucario().types  # ["FIGHTING", "STEEL"]


@pytest.mark.parametrize(
    "move_type, expected_multiplier",
    [
        # Super effective (160%)
        ("FIGHTING", 1.6),
        ("FIRE", 1.6),
        ("GROUND", 1.6),
        # Resisted (62.5%)
        ("STEEL", 0.625),
        ("NORMAL", 0.625),
        ("ICE", 0.625),
        ("GRASS", 0.625),
        ("DRAGON", 0.625),
        ("DARK", 0.625),
        # Doubly resisted (39.1%)
        ("BUG", 0.390625),
        ("POISON", 0.390625),
        ("ROCK", 0.390625),
        # Regular/neutral (100%) -- every other attacking type
        ("FLYING", 1.0),
        ("WATER", 1.0),
        ("ELECTRIC", 1.0),
        ("PSYCHIC", 1.0),
        ("GHOST", 1.0),
        ("FAIRY", 1.0),
    ],
)
def test_type_effectiveness_against_dual_type_lucario(move_type, expected_multiplier):
    assert type_effectiveness(move_type, LUCARIO_TYPES) == pytest.approx(
        expected_multiplier
    )


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


# --- 15. Protect Shields ------------------------------------------------
#
# The Protect Shield mechanic does not exist anywhere in battle/engine.py
# today -- these tests are written against an *assumed* extension:
# simulate_battle(..., player_shields=0, opponent_shields=0) and two new
# MatchupResult fields, player_shields_used/opponent_shields_used, where
# a shielded Charged Attack deals a fixed 1 damage instead of its real
# computed damage. All 6 are expected to fail today (most likely a
# TypeError for the unrecognized keyword arguments) -- per the standing
# "write a unit test" rule, that's expected, not a bug to fix here.
#
# Real-game rules, verified via web search (not in data/latest.json --
# this is battle-UI behavior, not Game Master data):
#   - The player has exactly 2 Protect Shields per Rocket encounter.
#   - Grunts never use their Protect Shields. Leaders and Giovanni do:
#     they always block the Trainer's first two Charged Attacks.
#   - A shielded Charged Attack deals exactly 1 damage, regardless of the
#     move's real power.
# Sources: https://bulbapedia.bulbagarden.net/wiki/Team_GO_Rocket_Grunt_%28Trainer_class%29 ,
# https://pokemongohub.net/post/tips-and-tricks/go-hub-guide-to-team-go-rocket-battles/ ,
# https://www.pokemon.com/us/strategy/master-charged-attacks-and-fast-attacks-in-the-go-battle-league
#
# All fixtures here reuse base_attack=base_defense=100 (the _priority_mon
# default) on both sides, type NORMAL throughout (STAB always applies,
# effectiveness always neutral) -- but note _priority_mon sets
# is_shadow=True on *both* sides, so damage actually goes through the
# Rocket attack/defense formula, not a flat 100/100 shortcut. Verified
# directly by calling the real engine functions: the attack/defense
# *ratio* (and so unshielded damage) is identical at every rank (rank
# and rCPM cancel out of it) -- only HP scales with rank. A power-1 Fast
# Attack deals 1 damage, a power-100 Charged Attack deals 100 unshielded,
# and a power-1000 one deals 997 unshielded, at every rank.
#
# A side alternating this fast/charge pair fires a Charged Attack every
# 3rd turn (turns 3, 6, 9, ...), with exactly 2 Fast Attacks landing in
# between each.
_SHIELD_FAST = Move("FAST", "NORMAL", 1.0, 1, 50)  # 2 hits = 100 energy
_SHIELD_CHARGE = Move("CHARGE", "NORMAL", 100.0, 1, -100)  # needs exactly 100


def test_player_shields_first_two_opponent_charge_attacks_not_a_third():
    # GRUNT rank. Opponent alternates fast/charge (base_stamina=1000,
    # irrelevant HP -- just needs to survive); player is a pure tank
    # (base_stamina=400, HP 74.45079831) with a never-affordable charge
    # move, isolating the test to just the opponent's charge stream.
    # Cumulative damage to the player: turns 1-2 chip (2), turn 3
    # shielded charge (+1=3), turns 4-5 chip (+2=5), turn 6 shielded
    # charge (+1=6), turns 7-8 chip (+2=8), turn 9's 3rd charge -- shields
    # exhausted -- lands unshielded (+100=108), fatal (> 74.45).
    player = _priority_mon(400, _SHIELD_FAST, _NEVER_AFFORDABLE)
    opponent = _priority_mon(1000, _SHIELD_FAST, _SHIELD_CHARGE)

    result = simulate_battle(
        player,
        opponent,
        rank=_PRIORITY_RANK,
        trainer_level=_PRIORITY_LEVEL,
        player_shields=2,
    )

    assert result.outcome == ROCKET_WIN
    assert result.turns_taken == 9
    assert result.player_shields_used == 2
    assert result.player_hp_remaining == 0


def test_first_opponent_charge_attack_is_shielded():
    # GRUNT rank. Player is the tank (base_stamina=1000, HP 182.09050671)
    # with a never-affordable charge move; opponent alternates fast/charge
    # but with base_stamina=5 (HP 3.58799028), so it's the one who faints
    # -- purely from the player's own ongoing Fast Attack chip damage
    # (1/turn), independent of shields -- right after landing its *one*
    # Charged Attack (turn 3) and taking one more chip hit (turn 4):
    # cumulative damage to the opponent is 4 by turn 4 (> 3.588), fatal.
    # It faints before its energy ever reaches 100 again (next charge
    # would be turn 6), so exactly one Charged Attack ever occurs --
    # letting the player's resulting HP unambiguously prove whether that
    # one attack was shielded.
    player = _priority_mon(1000, _SHIELD_FAST, _NEVER_AFFORDABLE)
    opponent = _priority_mon(5, _SHIELD_FAST, _SHIELD_CHARGE)

    result = simulate_battle(
        player,
        opponent,
        rank=_PRIORITY_RANK,
        trainer_level=_PRIORITY_LEVEL,
        player_shields=2,
    )

    assert result.outcome == PLAYER_WIN
    assert result.turns_taken == 4
    assert result.player_shields_used == 1
    # 2 chip + 1 shielded charge + 1 more chip = 4 -- would be 103 if
    # that first attack had landed unshielded instead.
    assert result.player_hp_remaining == pytest.approx(182.09050671 - 4)


def test_grunt_opponent_never_shields_even_after_three_player_charge_attacks():
    # Mirror of the first test with roles swapped: the *player* alternates
    # fast/charge (base_stamina=1000); the *opponent* is the tank,
    # base_stamina=1350 (GRUNT HP 244.88033661), never-affordable charge
    # move. opponent_shields=2 is deliberately passed (not 0) so this
    # proves the real rule -- Grunts *choose* never to shield -- rather
    # than trivially passing because none were available.
    # Cumulative damage to the opponent (all 3 unshielded, since Grunts
    # never shield): turns 1-2 chip (2), turn 3 charge (+100=102), turns
    # 4-5 chip (+2=104), turn 6 charge (+100=204), turns 7-8 chip
    # (+2=206), turn 9's 3rd charge (+100=306) -- fatal (> 244.88).
    player = _priority_mon(1000, _SHIELD_FAST, _SHIELD_CHARGE)
    opponent = _priority_mon(1350, _SHIELD_FAST, _NEVER_AFFORDABLE)

    result = simulate_battle(
        player,
        opponent,
        rank=ROCKET_RANK_GRUNT,
        trainer_level=_PRIORITY_LEVEL,
        opponent_shields=2,
    )

    assert result.outcome == PLAYER_WIN
    assert result.turns_taken == 9
    assert result.opponent_shields_used == 0
    assert result.opponent_hp_remaining == 0


def test_shielded_charge_attack_deals_exactly_one_damage():
    # Same shape/timing as test_first_opponent_charge_attack_is_shielded,
    # but the opponent's charge move here is deliberately huge (997
    # damage unshielded) to make the point unmistakable: no matter how
    # strong the move, a shielded hit is still capped at exactly 1, not
    # some fraction of it.
    big_charge = Move("BIG_CHARGE", "NORMAL", 1000.0, 1, -100)
    player = _priority_mon(1000, _SHIELD_FAST, _NEVER_AFFORDABLE)
    opponent = _priority_mon(5, _SHIELD_FAST, big_charge)

    result = simulate_battle(
        player,
        opponent,
        rank=_PRIORITY_RANK,
        trainer_level=_PRIORITY_LEVEL,
        player_shields=2,
    )

    assert result.outcome == PLAYER_WIN
    assert result.turns_taken == 4
    assert result.player_shields_used == 1
    # Would be ~1000 total damage taken, not 4, at the move's real power.
    assert result.player_hp_remaining == pytest.approx(182.09050671 - 4)


def test_leader_opponent_shields_first_two_player_charge_attacks_not_a_third():
    # Mirror of the first shield test's exact shape/numbers, but roles
    # swapped (player attacks, opponent/Leader tanks and shields) and
    # rank is LEADER, not GRUNT: player alternates fast/charge
    # (base_stamina=1000, LEADER HP 191.19503205, comfortably survives);
    # opponent is the tank, base_stamina=400 (LEADER HP 78.17333823),
    # never-affordable charge move, opponent_shields=2. Cumulative damage
    # to the opponent mirrors the first test's player-side math (2
    # shielded charges + chip, then the 3rd lands unshielded at turn 9
    # for +100=108), fatal against 78.17.
    player = _priority_mon(1000, _SHIELD_FAST, _SHIELD_CHARGE)
    opponent = _priority_mon(400, _SHIELD_FAST, _NEVER_AFFORDABLE)

    result = simulate_battle(
        player,
        opponent,
        rank=ROCKET_RANK_LEADER,
        trainer_level=_PRIORITY_LEVEL,
        opponent_shields=2,
    )

    assert result.outcome == PLAYER_WIN
    assert result.turns_taken == 9
    assert result.opponent_shields_used == 2
    assert result.opponent_hp_remaining == 0


def test_leader_fight_uses_at_most_four_shields_total():
    # Both sides alternate fast/charge against each other (symmetric
    # fixture, base_stamina=400 each, LEADER HP 78.17333823 each).
    # Every Charged Attack (turns 3, 6, 9) lands on both sides
    # simultaneously (Phase B has no cross-side priority): both shield
    # turns 3 and 6 (1 damage each), both shields are exhausted by turn
    # 9, so turn 9's mutual Charged Attacks land unshielded (100 each) on
    # both sides simultaneously -- cumulative damage to each side is 108
    # by turn 9, exceeding 78.17 for both: a simultaneous double-KO,
    # which the engine's own documented tiebreak resolves as PLAYER_WIN.
    player = _priority_mon(400, _SHIELD_FAST, _SHIELD_CHARGE)
    opponent = _priority_mon(400, _SHIELD_FAST, _SHIELD_CHARGE)

    result = simulate_battle(
        player,
        opponent,
        rank=ROCKET_RANK_LEADER,
        trainer_level=_PRIORITY_LEVEL,
        player_shields=2,
        opponent_shields=2,
    )

    assert result.outcome == PLAYER_WIN
    assert result.turns_taken == 9
    assert result.player_shields_used == 2
    assert result.opponent_shields_used == 2
    assert result.player_hp_remaining == 0
    assert result.opponent_hp_remaining == 0
