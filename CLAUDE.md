# chickenstats — Developer Guide

## Architecture Overview

The package has four submodules:

| Submodule | Role |
|-----------|------|
| `chicken_nhl` | NHL scraping and aggregation (Scraper, Season, Game, Player, Team) |
| `evolving_hockey` | Aggregation over EvolvingHockey.com CSV exports |
| `utilities` | Progress bars, HTTP session, enums, type aliases, coordinate helpers |
| `api` | Client for the chickenstats.com REST API (ChickenUser, ChickenStats) |

Top-level `chickenstats` re-exports the 5 main classes (`Scraper`, `Season`, `Game`, `Player`, `Team`) so users can do `from chickenstats import Scraper`. Everything else is accessed through the submodule path.

---

## chicken_nhl Module Map

### Public classes (defined in thin wrapper files, logic in mixins)

**`scraper.py`** — `Scraper(_ScraperCore, _ScraperRawMixin, _ScraperStatsMixin)`
- `_scraper_core.py` — constructor, `game_ids`, `add_games()`, `failed_games`, the `_scrape()` dispatch loop
- `_scraper_raw.py` — cached properties: `play_by_play`, `play_by_play_ext`, `api_events`, `html_events`, `rosters`, `shifts`, `changes`
- `_scraper_stats.py` — `prep_stats()`, `prep_lines()`, `prep_team_stats()` and their cached result properties

**`game.py`** — `Game(_GameCore, _GameAPIMixin, _GameHTMLMixin, _GameRostersMixin, _GamePBPMixin)`
- `_game_core.py` — constructor, metadata attributes (game_id, season, home_team, etc.), `prefetch()`
- `_game_api.py` — `api_events`, `api_rosters` cached properties
- `_game_html.py` — `html_events`, `html_rosters` cached properties (largest file, ~1200 lines)
- `_game_rosters.py` — `rosters` combined cached property
- `_game_pbp.py` — `shifts`, `changes`, `play_by_play`, `play_by_play_ext` cached properties

**`season.py`** — `Season` (self-contained, ~2300 lines)
- `schedule()` method, `standings` property

**`player.py`** — `Player` (self-contained, ~300 lines)
- NHL API landing page and game log endpoints

**`team.py`** — `Team` (self-contained, ~340 lines)
- Color lookup, logo download

### Internal files

| File | Contents |
|------|----------|
| `_corrections.py` | Hand-curated NHL API/HTML data corrections keyed by game ID. Each function patches one known data quality issue. Known-unfixable issues are documented as comments inside each function. |
| `_docstrings.py` | Centralized docstring registry. Column descriptions are stored here once and applied to methods via `@shared_doc(...)` so that the same field description stays in sync across Scraper and Game properties. |
| `_aggregation.py` | Core aggregation logic for `prep_ind`, `prep_oi`, `prep_stats`, `prep_lines`, `prep_team_stats`, `build_play_by_play_ext` (~1900 lines). |
| `_agg_constants.py` | Column groupings, stat column lists, and other constants used by `_aggregation.py`. |
| `_game_utils.py` | Shared utilities for game mixins: `load_score_adjustments()`, `prefetch_concurrent()`, event-processing helpers. |
| `_player_names.py` | Name normalization dictionaries: known misspellings, alternate spellings, and NHL API name overrides. |
| `_validation_schema.py` | Field definitions and schema-building functions for all output DataFrames. |
| `_validation_utils.py` | Helpers to convert Pydantic models to Pandera/Polars schemas. |
| `validation_polars.py` | Native Polars schema objects for each output DataFrame. |
| `validation_pandas.py` | Pandera schemas (Pandas) for each output DataFrame. |
| `validation_pydantic.py` | Pydantic models for raw API/HTML event and roster data (~830 lines). |

---

## Key Internal Patterns

### Mixin + type-checking stub

Both `Scraper` and `Game` use multiple inheritance to split logic across files without creating circular imports. Each mixin (`_ScraperRawMixin`, etc.) inherits from a base stub class (`_ScraperBase`) that is only populated under `TYPE_CHECKING`:

```python
class _ScraperBase:
    """Only exists under TYPE_CHECKING — zero runtime overhead."""
    if TYPE_CHECKING:
        game_ids: list
        _backend: str
        ...
```

This lets type checkers see cross-mixin attribute references without requiring runtime imports between mixins.

### `@shared_doc` decorator

Docstrings for properties that return large DataFrames (many columns) are stored as constants in `_docstrings.py` and applied via a decorator:

```python
@shared_doc(_SCRAPER_API_EVENTS_DOC)
def api_events(self):
    """api_events — docstring lives in _docstrings._SCRAPER_API_EVENTS_DOC."""
    ...
```

The decorator stamps the constant string onto the callable, so `help()` and mkdocstrings both see the full docstring. Field descriptions are written once and reused across `Scraper` and `Game` properties that produce the same output.

### Multi-backend support

All DataFrame-returning properties and methods accept a `backend` parameter (`"polars"`, `"pandas"`, `"pyarrow"`, `"narwhals"`). Internal computation always uses Polars; `_to_backend()` in `utilities/utilities.py` converts at the boundary.

### `_corrections.py` pattern

Each correction function has the signature `f(game_id, event_or_player_dict) -> dict`. The function checks `game_id` against known problematic game IDs and patches the dict in place, then returns it. No-op for all other games. Called inline during scraping in the `_game_*.py` mixins.

---

## Public API Entry Points

```python
# Primary entry points (also accessible as `from chickenstats import ...`)
from chickenstats.chicken_nhl import Scraper, Season, Game, Player, Team

# Standalone aggregation functions (for advanced use / non-Scraper workflows)
from chickenstats.chicken_nhl import prep_stats, prep_ind, prep_oi, prep_lines, prep_team_stats, build_play_by_play_ext

# EvolvingHockey.com data
from chickenstats.evolving_hockey import prep_pbp, prep_stats, prep_gar, prep_xgar

# Utilities (progress bars, enums, type alias, session)
from chickenstats.utilities import Scraper, AggLevel, Backend, DataFrameT, ChickenSession

# chickenstats.com API client
from chickenstats.api import ChickenUser, ChickenStats
```

---

## Testing

Tests live in `tests/` with subdirectories mirroring the package structure:

```
tests/
  tests_chicken_nhl/   — Scraper, Season, Game, Player, Team, aggregation, corrections, validation
  tests_evolving_hockey/
  tests_api/
  tests_utilities/
```

**Markers:**
- `regression` — tests for specific historical game IDs; run with `-m regression`
- `live` — integration tests requiring a live API endpoint; excluded by default

**Coverage:** 80% minimum enforced via `pyproject.toml` `[tool.coverage.report]`.

Run tests: `pytest` (uses settings from `pyproject.toml`, parallel by default via xdist).

---

## Naming Conventions

- Public modules: no prefix (`scraper.py`, `season.py`, `team.py`)
- Internal implementation: `_` prefix (`_game_html.py`, `_aggregation.py`)
- Mixin classes: `_<Module>Mixin` suffix (`_ScraperRawMixin`)
- Base stubs: `_<Module>Base` suffix (`_ScraperBase`, `_GameBase`)
- Test files mirror the module they test: `test_scraper.py`, `test_corrections.py`
