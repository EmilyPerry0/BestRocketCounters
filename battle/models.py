"""Plain data containers for the battle simulator.

These are just schema -- no battle logic lives here. That's the job of
battle/engine.py (not implemented yet; see tests/test_battle.py for the
expected behavior).
"""
from dataclasses import dataclass


@dataclass
class Move:
    move_id: str
    type: str  # e.g. "FIGHTING" -- matches a key in the type effectiveness chart
    power: float
    duration_turns: int  # durationMs / 500, one turn = 500ms
    energy_delta: int  # positive for fast moves (energy gained), negative for charge moves (energy cost)


@dataclass
class Pokemon:
    species: str
    level: int
    types: list[str]
    base_attack: int
    base_defense: int
    base_stamina: int
    fast_move: Move
    charge_move: Move
    is_shadow: bool = False
