# BestRocketCounters
this project aims to find the best counters for efficienty defeating team go rocket members in pokemon go.

## Development Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then run the tests:

```
pytest tests/test_battle.py -v
```

## Data Sources

- Pokemon Game Master data is synced from [PokeMiners/game_masters](https://github.com/PokeMiners/game_masters).
- Team GO Rocket lineup data is synced from [ScrapedDuck](https://github.com/bigfoott/ScrapedDuck), which scrapes it from [LeekDuck.com](https://leekduck.com) (with permission). Per ScrapedDuck's usage terms, credit goes to **ScrapedDuck** and **[LeekDuck.com](https://leekduck.com)**, who provide the underlying data.
- Rocket pokemon cp is calculated from the formula derived by u/Venonic in [this](https://www.reddit.com/r/TheSilphRoad/comments/122pfk8/current_team_rocket_cp_formula_march_2023/) reddit post.
- Rocket pokemon cp calculations are aided by the lovely people of the silph road who found the rCPM values for each trainer level. thank you for all of your hard work! I am not sure who actually did this, though, so contact me if you know and I can credit them properly! I think it may be reddit user u/eli5questions. Spreadsheet linked [here](https://docs.google.com/spreadsheets/d/1bzvqxonUnsTJzfHz-whT1YcyqXIKs5BIQ-F7ALRIwiI/edit?gid=509177191#gid=509177191)

## Disclaimer
BestRocketCounters is not affiliated with The Pokémon Company, Niantic, Scopely, Pokémon Go, or any other such entities.
Pokémon is a trademark of Nintendo. All such trademarks are the property of their respective owners.