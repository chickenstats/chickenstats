"""chickenstats.evolving_hockey: Prepare and aggregate EvolvingHockey data.

Provides utilities for cleaning raw EvolvingHockey.com exports and aggregating
them into the same individual, on-ice, line, and team stat formats used by
``chickenstats.chicken_nhl``.

Prepare raw EvolvingHockey play-by-play and shifts exports:
    >>> from chickenstats.evolving_hockey import prep_pbp
    >>> pbp = prep_pbp(raw_pbp, raw_shifts)

Aggregate individual and on-ice player stats:
    >>> from chickenstats.evolving_hockey import prep_stats
    >>> stats = prep_stats(pbp)

Aggregate goals-above-replacement metrics from EvolvingHockey's GAR/xGAR exports:
    >>> from chickenstats.evolving_hockey import prep_gar, prep_xgar
    >>> gar = prep_gar(skater_gar, goalie_gar)
    >>> xgar = prep_xgar(xgar_data)

Documentation: https://chickenstats.com/
Source Code: https://github.com/chickenandstats/chickenstats
"""

from chickenstats.evolving_hockey.pbp import prep_pbp
from chickenstats.evolving_hockey.stats import (
    prep_ind,
    prep_oi,
    prep_stats,
    prep_lines,
    prep_team_stats,
    prep_gar,
    prep_xgar,
)

__all__ = ["prep_pbp", "prep_ind", "prep_oi", "prep_stats", "prep_lines", "prep_team_stats", "prep_gar", "prep_xgar"]
