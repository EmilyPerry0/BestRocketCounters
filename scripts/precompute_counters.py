#!/usr/bin/env python3
"""Precompute the best player counters for one specific Rocket target.

Evaluates every real candidate Pokemon (every base species plus genuine
alt forms -- not cosmetic costumes, not Megas) at every one of its own
legal movesets, against every moveset the target could possibly have
(rocketLineups.json never tells us which one Niantic actually assigned),
and writes the top 10 unique species -- each at its own single best
moveset -- to a JSON file under data/counters/.

Usage:
    python scripts/precompute_counters.py

See /Users/emily/.claude/plans/dynamic-painting-widget.md for the full
design and the real-data checks (form-vs-costume detection, the
FRUSTRATION exclusion, etc.) behind the choices made here.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from battle.engine import PLAYER_WIN, ROCKET_RANK_GRUNT, simulate_battle
from battle.models import Move, Pokemon

GAME_MASTER_PATH = ROOT / "data" / "latest.json"
OUTPUT_DIR = ROOT / "data" / "counters"

# Species whose alt forms should collapse into a single top-10 slot (the
# best-scoring form only) rather than each counting as its own "unique
# Pokemon". Urshifu's two Battle Formes (Rapid Strike / Single Strike) are
# considered the same Pokemon by players -- unlike a real regional variant
# such as Alolan Raichu, which stays a distinct entry.
COLLAPSE_FORMS_FOR = {"URSHIFU"}

TARGET_SPECIES = "TEDDIURSA"
TARGET_RANK = ROCKET_RANK_GRUNT
TARGET_RANK_NAME = "GRUNT"
TRAINER_LEVEL = 80
CANDIDATE_LEVEL = 50
TOP_N = 10


@dataclass
class CandidateEntry:
    species: str
    display_name: str
    base_attack: int
    base_defense: int
    base_stamina: int
    types: list[str]
    fast_move_ids: list[str]
    charge_move_ids: list[str]


def load_game_master() -> list[dict]:
    with GAME_MASTER_PATH.open() as f:
        return json.load(f)


def build_move_lookup(game_master: list[dict]) -> dict[str, Move]:
    """move_id -> Move, from every moveSettings entry in the Game Master."""
    moves: dict[str, Move] = {}
    for entry in game_master:
        settings = entry.get("data", {}).get("moveSettings")
        if not settings or not isinstance(settings.get("movementId"), str):
            continue  # a couple of legacy entries have an int movementId, not a real move
        duration_ms = settings.get("durationMs")
        if duration_ms is None:
            continue
        moves[settings["movementId"]] = Move(
            move_id=settings["movementId"],
            type=settings["pokemonType"].replace("POKEMON_TYPE_", ""),
            power=settings.get("power", 0.0) or 0.0,
            duration_turns=duration_ms // 500,
            # A handful of moves (e.g. STRUGGLE) have no energyDelta in the
            # Game Master at all -- they don't use energy in the real game,
            # which doesn't fit our fast/charge energy_delta convention, so
            # 0 (always "affordable") is the closest fit, same precedent as
            # sample_data.py's own STRUGGLE constant.
            energy_delta=settings.get("energyDelta") or 0,
        )
    return moves


def _pokemon_types(settings: dict) -> list[str]:
    types = [settings.get("type"), settings.get("type2")]
    return [t.replace("POKEMON_TYPE_", "") for t in types if t]


def build_candidate_roster(
    game_master: list[dict], move_lookup: dict[str, Move]
) -> list[CandidateEntry]:
    """Every base species, plus any alt form whose stats or types differ
    from its own species' base entry (the rule that separates a real form
    -- Alolan Raichu, Rotom's formes, etc. -- from a cosmetic costume or
    the redundant "_NORMAL" duplicate every species has, which share the
    base's stats and types exactly). Megas never appear as their own
    pokemonSettings entries at all, so they're excluded just by not
    reading tempEvoOverrides.
    """
    by_species: dict[str, dict] = {}  # pokemonId -> its base pokemonSettings
    all_entries: list[tuple[str, dict]] = []  # (form_label, pokemonSettings)

    for entry in game_master:
        settings = entry.get("data", {}).get("pokemonSettings")
        if not settings or not settings.get("pokemonId"):
            continue
        species = settings["pokemonId"]
        form = settings.get("form")
        all_entries.append((form, settings))
        if form is None:
            by_species[species] = settings

    def stats_and_types(settings: dict) -> tuple:
        stats = settings.get("stats") or {}
        return (
            stats.get("baseAttack"),
            stats.get("baseDefense"),
            stats.get("baseStamina"),
            tuple(_pokemon_types(settings)),
        )

    candidates: list[CandidateEntry] = []
    seen_forms: set[str] = set()  # dedupe -- some entries are exact duplicates
    for form, settings in all_entries:
        species = settings["pokemonId"]
        base = by_species.get(species)
        if base is None or not base.get("stats"):
            continue  # no clean base entry for this species -- skip
        is_base = form is None
        if not is_base and stats_and_types(settings) == stats_and_types(base):
            continue  # cosmetic costume or "_NORMAL" duplicate -- skip

        key = form or species
        if key in seen_forms:
            continue
        seen_forms.add(key)

        stats = settings["stats"]
        # eliteQuickMove/eliteCinematicMove are legacy or Community Day
        # moves -- no longer taught by TM, but still legal via Elite TM (or
        # never removed from Pokemon that had them at release), so they're
        # real options for this Pokemon just like its regular moves (e.g.
        # Lucario's Force Palm, Charizard's Dragon Breath).
        fast_ids_raw = settings.get("quickMoves", []) + (
            settings.get("eliteQuickMove") or []
        )
        charge_ids_raw = settings.get("cinematicMoves", []) + (
            settings.get("eliteCinematicMove") or []
        )
        fast_ids = list(dict.fromkeys(m for m in fast_ids_raw if m in move_lookup))
        charge_ids = list(dict.fromkeys(m for m in charge_ids_raw if m in move_lookup))
        if not fast_ids or not charge_ids:
            print(f"skipping {key}: no usable moveset", file=sys.stderr)
            continue

        candidates.append(
            CandidateEntry(
                species=species,
                display_name=key,
                base_attack=stats["baseAttack"],
                base_defense=stats["baseDefense"],
                base_stamina=stats["baseStamina"],
                types=_pokemon_types(settings),
                fast_move_ids=fast_ids,
                charge_move_ids=charge_ids,
            )
        )
    return candidates


def build_target_movesets(
    game_master: list[dict], move_lookup: dict[str, Move], species: str
) -> list[Pokemon]:
    """Every legal fast x charge combination the target could have, as a
    Shadow Pokemon (rank/trainer_level are applied later, at simulate_battle
    call time, not baked into the Pokemon itself)."""
    settings = None
    for entry in game_master:
        s = entry.get("data", {}).get("pokemonSettings")
        if s and s.get("pokemonId") == species and s.get("form") is None:
            settings = s
            break
    if settings is None:
        raise ValueError(f"no base entry found for {species!r}")

    stats = settings["stats"]
    types = _pokemon_types(settings)
    # Elite/legacy moves are legal options here too -- see the matching
    # comment in build_candidate_roster. Teddiursa itself has none, but this
    # function is meant to generalize to other targets later.
    fast_ids_raw = settings["quickMoves"] + (settings.get("eliteQuickMove") or [])
    charge_ids_raw = settings["cinematicMoves"] + (
        settings.get("eliteCinematicMove") or []
    )
    fast_ids = list(dict.fromkeys(m for m in fast_ids_raw if m in move_lookup))
    charge_ids = list(dict.fromkeys(m for m in charge_ids_raw if m in move_lookup))

    return [
        Pokemon(
            species=species,
            level=20,  # unused by the Rocket stat formula -- placeholder
            types=types,
            base_attack=stats["baseAttack"],
            base_defense=stats["baseDefense"],
            base_stamina=stats["baseStamina"],
            fast_move=move_lookup[fast_id],
            charge_move=move_lookup[charge_id],
            is_shadow=True,
        )
        for fast_id in fast_ids
        for charge_id in charge_ids
    ]


def evaluate_candidate(
    candidate: CandidateEntry, move_lookup: dict[str, Move], targets: list[Pokemon]
) -> dict:
    """This candidate's single best moveset: for each of its own fast x
    charge combos, count wins across all target movesets and the average
    turns_taken among just the wins; keep the combo with the most wins,
    breaking ties by fewer average turns."""
    best = None
    for fast_id in candidate.fast_move_ids:
        for charge_id in candidate.charge_move_ids:
            player = Pokemon(
                species=candidate.species,
                level=CANDIDATE_LEVEL,
                types=candidate.types,
                base_attack=candidate.base_attack,
                base_defense=candidate.base_defense,
                base_stamina=candidate.base_stamina,
                fast_move=move_lookup[fast_id],
                charge_move=move_lookup[charge_id],
                is_shadow=False,
            )
            wins = 0
            turns_on_wins = []
            for target in targets:
                try:
                    result = simulate_battle(
                        player, target, rank=TARGET_RANK, trainer_level=TRAINER_LEVEL
                    )
                except RuntimeError:
                    # A genuine stalemate -- neither side can finish the other
                    # off within max_turns (e.g. a very weak candidate against
                    # a comparatively tanky target). Not a win.
                    continue
                if result.outcome == PLAYER_WIN:
                    wins += 1
                    turns_on_wins.append(result.turns_taken)

            avg_turns = (
                sum(turns_on_wins) / len(turns_on_wins) if turns_on_wins else None
            )
            score = (wins, -avg_turns if avg_turns is not None else float("-inf"))
            if best is None or score > best["_score"]:
                best = {
                    "species": candidate.species,
                    "display_name": candidate.display_name,
                    "fast_move": fast_id,
                    "charge_move": charge_id,
                    "wins": wins,
                    "movesets_evaluated": len(targets),
                    "average_turns_taken": avg_turns,
                    "_score": score,
                }
    return best


def main() -> None:
    game_master = load_game_master()
    move_lookup = build_move_lookup(game_master)
    candidates = build_candidate_roster(game_master, move_lookup)
    targets = build_target_movesets(game_master, move_lookup, TARGET_SPECIES)

    print(
        f"{len(candidates)} candidates, {len(targets)} target movesets", file=sys.stderr
    )

    results = [evaluate_candidate(c, move_lookup, targets) for c in candidates]
    results.sort(key=lambda r: r["_score"], reverse=True)

    deduped = []
    seen_collapsed_species = set()
    for r in results:
        if r["species"] in COLLAPSE_FORMS_FOR:
            if r["species"] in seen_collapsed_species:
                continue  # a lower-scoring form of an already-kept species
            seen_collapsed_species.add(r["species"])
        deduped.append(r)

    top = deduped[:TOP_N]
    for r in top:
        r.pop("_score")

    output = {
        "target": {
            "species": TARGET_SPECIES,
            "rank": TARGET_RANK_NAME,
            "trainer_level": TRAINER_LEVEL,
            "movesets_evaluated": len(targets),
        },
        "candidate_level": CANDIDATE_LEVEL,
        "top_counters": top,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"shadow_{TARGET_SPECIES.lower()}.json"
    with out_path.open("w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(f"wrote {out_path.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
