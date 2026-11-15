"""Build the schema reference pages and the schema snapshot from the package's schemas.

Each output frame has a page under docs/reference/schemas/ listing its columns in order, with
dtype, nullability, unit and description, and an entry in tests/data/schema_snapshot.json. Both
are written from the schema dictionaries the package validates its output with, and the
descriptions come from the docstring registries. test_schema_catalog.py fails when either is out
of date, and the frame tests fail when a frame's output differs from the snapshot, so a change to
a column has to be made here, on purpose.

    uv run python scripts/schema_catalog.py          # list what is out of date
    uv run python scripts/schema_catalog.py --write  # and rewrite it
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import polars as pl
from pydantic import BaseModel

from chickenstats.chicken_nhl import _docstrings as docs
from chickenstats.chicken_nhl import player
from chickenstats.chicken_nhl import _validation_schema as nhl_schema
from chickenstats.chicken_nhl import validation_polars as nhl_polars
from chickenstats.chicken_nhl import validation_pydantic as models
from chickenstats.chicken_nhl._validation_utils import _get_base_type_and_nullable
from chickenstats.evolving_hockey import _docstrings as eh_docs
from chickenstats.evolving_hockey import _validation_schema as eh_schema

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "docs" / "reference" / "schemas"
SNAPSHOT = ROOT / "tests" / "data" / "schema_snapshot.json"

Descriptions = Mapping[str, tuple[str, str]]
# The schemas hold both dtype classes (pl.Int64) and instances (pl.List(pl.String))
PolarsDtype = pl.DataType | type[pl.DataType]


@dataclass(frozen=True)
class Column:
    """One column of an output frame."""

    name: str
    dtype: PolarsDtype
    nullable: bool
    unit: str
    description: str


@dataclass(frozen=True)
class Frame:
    """One output frame: where it comes from and how to build its columns."""

    key: str
    title: str
    returned_by: str
    columns: Callable[[], dict[str, tuple[PolarsDtype, bool]]]
    descriptions: Descriptions

    @property
    def page(self) -> str:
        """The page's path under docs/reference/schemas."""
        return f"{self.key.replace('.', '_')}.md"


# -----------------------------------------------------------------------------
# Columns from the two kinds of schema the package declares
# -----------------------------------------------------------------------------


def from_model(schema: Mapping[str, PolarsDtype], model: type[BaseModel]) -> Callable:
    """Columns of a frame validated with a native polars schema built from a pydantic model."""

    def build() -> dict[str, tuple[PolarsDtype, bool]]:
        nullable = {name: _get_base_type_and_nullable(f.annotation)[1] for name, f in model.model_fields.items()}
        return {name: (dtype, nullable[name]) for name, dtype in schema.items()}

    return build


def from_fields(fields: Mapping[str, dict]) -> Callable:
    """Columns of a frame validated with a pandera schema built from a field dictionary."""

    def build() -> dict[str, tuple[PolarsDtype, bool]]:
        return {
            name: (
                pl.List(pl.String) if field["dtype"] is list else nhl_schema.polars_dtype_map[field["dtype"]],
                field["nullable"],
            )
            for name, field in fields.items()
        }

    return build


def from_registry(schema: Mapping[str, PolarsDtype], fields: Descriptions) -> Callable:
    """Columns of a frame built with a plain polars schema, nullable where its registry type allows None."""

    def build() -> dict[str, tuple[PolarsDtype, bool]]:
        return {name: (dtype, "None" in fields[name][0]) for name, dtype in schema.items()}

    return build


# -----------------------------------------------------------------------------
# Units, which no schema carries
# -----------------------------------------------------------------------------

UNITS = {
    "toi": "minutes",
    "toi_all": "minutes",
    "toi_ev": "minutes",
    "toi_pp": "minutes",
    "toi_sh": "minutes",
    "play_speed": "feet per second",
    "penalty_length": "minutes",
    "penalty_duration": "minutes",
    "age": "years",
    "height_in_inches": "inches",
    "height_in_centimeters": "centimeters",
    "weight_in_pounds": "pounds",
    "weight_in_kilograms": "kilograms",
    # Clock readings kept as text
    "period_time": "MM:SS",
    "clock_time": "MM:SS",
    "duration": "MM:SS",
    "shift_start": "MM:SS",
    "shift_end": "MM:SS",
    "event_length": "seconds",
    "event_distance": "feet",
    "pbp_distance": "feet",
    "prior_event_distance": "feet",
    "distance_from_last": "feet",
    "abs_y_distance": "feet",
    "coords_x": "feet",
    "coords_y": "feet",
    "event_angle": "degrees",
    "prior_event_angle": "degrees",
    "prior_coords_x": "feet",
    "prior_coords_y": "feet",
    "lateral_move": "feet",
    "lateral_speed": "feet per second",
    "rebound_angle_change": "degrees",
    "rebound_angle_speed": "degrees per second",
}


# Units that differ by frame
FRAME_UNITS = {"chicken_nhl.shifts": {"start_time": "MM:SS", "end_time": "MM:SS"}}


def unit(name: str) -> str:
    """The unit of a column, from its name; empty for counts, labels and IDs."""
    if name in UNITS:
        return UNITS[name]
    if name.endswith("_seconds") or name.startswith("seconds_since_"):
        return "seconds"
    if name.endswith("_p60"):
        return "per 60 minutes"
    if name.endswith("_percent"):
        return "share, 0 to 1"
    return ""


# -----------------------------------------------------------------------------
# The frames
# -----------------------------------------------------------------------------

# Fallback descriptions for columns a frame's own registry leaves out
_CHICKEN_NHL_FALLBACK: Descriptions = (
    docs._PBP_FIELDS
    | docs._API_EVENTS_FIELDS
    | docs._API_ROSTERS_FIELDS
    | docs._HTML_EVENTS_FIELDS
    | docs._HTML_ROSTERS_FIELDS
    | docs._ROSTERS_FIELDS
)
_STINTS = (
    docs._STINTS_CONTEXT_FIELDS | docs._STINTS_PERSONNEL_FIELDS | docs._STINTS_STAT_FIELDS | docs._STINTS_MODEL_FIELDS
)

FRAMES: tuple[Frame, ...] = (
    Frame(
        "chicken_nhl.play_by_play",
        "play_by_play",
        "`Scraper.play_by_play`, `Game.play_by_play_df`",
        from_model(nhl_polars.pbp_polars_schema, models.PBPEvent),
        docs._PBP_FIELDS,
    ),
    Frame(
        "chicken_nhl.play_by_play_ext",
        "play_by_play_ext",
        "`Scraper.play_by_play_ext`, `build_play_by_play_ext`",
        from_model(nhl_polars.pbp_ext_polars_schema, models.PBPEventExt),
        docs._PBP_EXT_FIELDS,
    ),
    Frame(
        "chicken_nhl.xg_fields",
        "xg_fields",
        "`Scraper.xg_fields`, `Game.xg_fields_df`",
        from_model(nhl_polars.xg_polars_schema, models.XGFields),
        docs._XG_FIELDS,
    ),
    Frame(
        "chicken_nhl.api_events",
        "api_events",
        "`Scraper.api_events`, `Game.api_events_df`",
        from_model(nhl_polars.api_events_polars_schema, models.APIEvent),
        docs._API_EVENTS_FIELDS,
    ),
    Frame(
        "chicken_nhl.api_rosters",
        "api_rosters",
        "`Scraper.api_rosters`, `Game.api_rosters_df`",
        from_model(nhl_polars.api_rosters_polars_schema, models.APIRosterPlayer),
        docs._API_ROSTERS_FIELDS,
    ),
    Frame(
        "chicken_nhl.html_events",
        "html_events",
        "`Scraper.html_events`, `Game.html_events_df`",
        from_model(nhl_polars.html_events_polars_schema, models.HTMLEvent),
        docs._HTML_EVENTS_FIELDS,
    ),
    Frame(
        "chicken_nhl.html_rosters",
        "html_rosters",
        "`Scraper.html_rosters`, `Game.html_rosters_df`",
        from_model(nhl_polars.html_rosters_polars_schema, models.HTMLRosterPlayer),
        docs._HTML_ROSTERS_FIELDS,
    ),
    Frame(
        "chicken_nhl.rosters",
        "rosters",
        "`Scraper.rosters`, `Game.rosters_df`",
        from_model(nhl_polars.rosters_polars_schema, models.RosterPlayer),
        docs._ROSTERS_FIELDS,
    ),
    Frame(
        "chicken_nhl.shifts",
        "shifts",
        "`Scraper.shifts`, `Game.shifts_df`",
        from_model(nhl_polars.shifts_polars_schema, models.PlayerShift),
        docs._SHIFTS_FIELDS,
    ),
    Frame(
        "chicken_nhl.changes",
        "changes",
        "`Scraper.changes`, `Game.changes_df`",
        from_model(nhl_polars.changes_polars_schema, models.ChangeEvent),
        docs._CHANGES_FIELDS,
    ),
    Frame(
        "chicken_nhl.stats",
        "stats",
        "`Scraper.stats`, `prep_stats`",
        from_fields(nhl_schema.stats_fields),
        docs._STATS_RETURN_FIELDS,
    ),
    Frame(
        "chicken_nhl.ind_stats",
        "ind_stats",
        "`Scraper.ind_stats`, `prep_ind`",
        from_fields(nhl_schema.ind_stats_fields),
        docs._IND_STATS_RETURN_FIELDS,
    ),
    Frame(
        "chicken_nhl.oi_stats",
        "oi_stats",
        "`Scraper.oi_stats`, `prep_oi`",
        from_fields(nhl_schema.oi_stats_fields),
        docs._OI_STATS_RETURN_FIELDS,
    ),
    Frame(
        "chicken_nhl.lines",
        "lines",
        "`Scraper.lines`, `prep_lines`",
        from_fields(nhl_schema.line_stats_fields),
        docs._LINES_RETURN_FIELDS,
    ),
    Frame(
        "chicken_nhl.team_stats",
        "team_stats",
        "`Scraper.team_stats`, `prep_team_stats`",
        from_fields(nhl_schema.team_stats_fields),
        docs._TEAM_STATS_RETURN_FIELDS,
    ),
    Frame(
        "chicken_nhl.stints",
        "stints",
        "`Scraper.stints`, `prep_stints`",
        from_fields(nhl_schema.stints_fields),
        _STINTS,
    ),
    Frame(
        "chicken_nhl.schedule",
        "schedule",
        "`Season.schedule`, `multi_season_schedule`",
        from_model(nhl_polars.schedule_polars_schema, models.ScheduleGame),
        docs._SCHEDULE_FIELDS,
    ),
    Frame(
        "chicken_nhl.standings",
        "standings",
        "`Season.standings`",
        from_model(nhl_polars.standings_polars_schema, models.StandingsTeam),
        docs._STANDINGS_FIELDS,
    ),
    Frame(
        "chicken_nhl.search_players",
        "search_players",
        "`search_players`",
        from_registry(player._SEARCH_RESULT_SCHEMA, docs._SEARCH_PLAYERS_FIELDS),
        docs._SEARCH_PLAYERS_FIELDS,
    ),
    Frame(
        "chicken_nhl.player_bios",
        "player_bios",
        "`player_bios`",
        from_registry(player._BIO_SCHEMA, docs._PLAYER_BIOS_FIELDS),
        docs._PLAYER_BIOS_FIELDS,
    ),
    Frame(
        "chicken_nhl.player_profiles",
        "player_profiles",
        "`player_profiles`",
        from_registry(player._PROFILE_SCHEMA, docs._PLAYER_PROFILES_FIELDS),
        docs._PLAYER_PROFILES_FIELDS,
    ),
    Frame(
        "evolving_hockey.pbp",
        "play-by-play",
        "`evolving_hockey.prep_pbp`",
        from_fields(eh_schema.pbp_fields),
        eh_docs._PBP_FIELDS,
    ),
    Frame(
        "evolving_hockey.stats",
        "stats",
        "`evolving_hockey.prep_stats`",
        from_fields(eh_schema.stats_fields),
        docs._STATS_RETURN_FIELDS,
    ),
    Frame(
        "evolving_hockey.ind_stats",
        "ind_stats",
        "`evolving_hockey.prep_ind`",
        from_fields(eh_schema.ind_stats_fields),
        docs._IND_STATS_RETURN_FIELDS,
    ),
    Frame(
        "evolving_hockey.oi_stats",
        "oi_stats",
        "`evolving_hockey.prep_oi`",
        from_fields(eh_schema.oi_stats_fields),
        docs._OI_STATS_RETURN_FIELDS,
    ),
    Frame(
        "evolving_hockey.lines",
        "lines",
        "`evolving_hockey.prep_lines`",
        from_fields(eh_schema.line_stats_fields),
        docs._LINES_RETURN_FIELDS,
    ),
    Frame(
        "evolving_hockey.team_stats",
        "team_stats",
        "`evolving_hockey.prep_team_stats`",
        from_fields(eh_schema.team_stats_fields),
        docs._TEAM_STATS_RETURN_FIELDS,
    ),
    Frame(
        "evolving_hockey.gar",
        "gar",
        "`evolving_hockey.prep_gar`",
        from_fields(eh_schema.gar_fields),
        eh_docs._GAR_FIELDS,
    ),
    Frame(
        "evolving_hockey.xgar",
        "xgar",
        "`evolving_hockey.prep_xgar`",
        from_fields(eh_schema.xgar_fields),
        eh_docs._XGAR_FIELDS,
    ),
)


def description(frame: Frame, name: str) -> str:
    """A column's description, or an empty string where no registry has one."""
    fallback = _CHICKEN_NHL_FALLBACK if frame.key.startswith("chicken_nhl.") else {}
    return frame.descriptions.get(name, fallback.get(name, ("", "")))[1]


def columns(frame: Frame) -> list[Column]:
    """A frame's columns, in order."""
    return [
        Column(name, dtype, nullable, FRAME_UNITS.get(frame.key, {}).get(name, unit(name)), description(frame, name))
        for name, (dtype, nullable) in frame.columns().items()
    ]


# -----------------------------------------------------------------------------
# Writing the pages and the snapshot
# -----------------------------------------------------------------------------

STABILITY = """\
Each page lists a frame's columns in the order the frame returns them. A frame returns only the
columns its options ask for, and the rest keep their order. For example, `game_id` and `game_date`
appear only at game and period level, `session` is left out at season level, the lineup columns
appear only with `teammates=True` or `opposition=True`, and the `base_xg` and `context_xg`
columns appear only when play-by-play has them.

These pages are the contract for what each frame returns, with the pandas, pyarrow and narwhals
backends converting the dtypes shown here:

- Adding, removing, renaming or moving a column, or changing its dtype, nullability or unit, is a
  breaking change. It is listed under "Breaking changes" in the changelog for its release.
- A test compares every frame with a checked-in snapshot of these tables, so none of these changes
  can ship by accident.
"""

GENERATED = "<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->"


def escape(text: str) -> str:
    """Text that fits in one table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


def page(frame: Frame) -> str:
    """The reference page of one frame."""
    module = frame.key.split(".")[0]
    lines = [
        "---",
        "icon: material/table",
        f'description: "Columns, dtypes and nullability of {frame.title} in chickenstats.{module}"',
        "---",
        "",
        GENERATED,
        "",
        f"# :material-table: **{module}: {frame.title}**",
        "",
        f"Returned by {frame.returned_by}. See [Output schemas](index.md) for what these columns promise.",
        "",
    ]
    frame_columns = columns(frame)
    # A frame no registry describes gets no empty Description column
    described = any(column.description for column in frame_columns)
    headers = ["#", "Column", "Dtype", "Nullable", "Unit"] + (["Description"] if described else [])
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|--:|" + "|".join("-" * (len(header) + 2) for header in headers[1:]) + "|")
    for number, column in enumerate(frame_columns, start=1):
        cells = [str(number), f"`{column.name}`", f"`{column.dtype}`", "yes" if column.nullable else "no", column.unit]
        if described:
            cells.append(escape(column.description))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def index_page() -> str:
    """The page that lists every frame and states the stability rule."""
    lines = [
        "---",
        "icon: material/table-cog",
        'description: "The columns, dtypes and nullability of every frame chickenstats returns"',
        "---",
        "",
        GENERATED,
        "",
        "# :material-table-cog: **Output schemas**",
        "",
        STABILITY,
        "| Frame | Returned by | Columns |",
        "|-------|-------------|--------:|",
    ]
    for frame in FRAMES:
        module = frame.key.split(".")[0]
        lines.append(f"| [{module}: {frame.title}]({frame.page}) | {frame.returned_by} | {len(frame.columns())} |")
    return "\n".join(lines) + "\n"


def pages() -> dict[Path, str]:
    """Every page, by path."""
    built = {PAGES_DIR / frame.page: page(frame) for frame in FRAMES}
    built[PAGES_DIR / "index.md"] = index_page()
    return built


def snapshot() -> str:
    """The snapshot file: each frame's columns as name, dtype and nullability, one column per line."""
    blocks = []
    for frame in FRAMES:
        rows = ",\n".join(f"    {json.dumps([c.name, str(c.dtype), c.nullable])}" for c in columns(frame))
        blocks.append(f'  "{frame.key}": [\n{rows}\n  ]')
    return "{\n" + ",\n".join(blocks) + "\n}\n"


def outdated() -> dict[Path, str]:
    """Every file whose checked-in text differs from what this script writes."""
    wanted = {**pages(), SNAPSHOT: snapshot()}
    return {
        path: text for path, text in wanted.items() if not path.exists() or path.read_text(encoding="utf-8") != text
    }


def main() -> int:
    """List the files that are out of date, and rewrite them with --write."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="rewrite the files that are out of date")
    args = parser.parse_args()

    stale = outdated()
    pages_now = {path.name for path in PAGES_DIR.glob("*.md")} if PAGES_DIR.exists() else set()
    unused = pages_now - {path.name for path in pages()}
    for path in stale:
        print(f"{'writing' if args.write else 'out of date'}: {path.relative_to(ROOT)}")
    for name in sorted(unused):
        print(f"no longer a frame: docs/reference/schemas/{name}")

    if args.write:
        for path, text in stale.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        return 0

    return 1 if stale or unused else 0


if __name__ == "__main__":
    sys.exit(main())
