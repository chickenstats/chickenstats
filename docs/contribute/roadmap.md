---
icon: octicons/project-roadmap-16
description: "Roadmap for chickenstats development"
---

# :octicons-project-roadmap-16: **Roadmap**

`chickenstats` is an imperfect library with big ambitions and is actively seeking contributions in various ways.
Below are what I think are both the most interesting and would advance the library furthest. 

## :material-numeric-1-circle: **Research and analytics**

"Priority 1A" for the `chickenstats` library is to improve the existing and introduce additional 
statistics and evaluation tools - this was the original goal of the entire project.

The below are just an initial starting point - please feel free to leverage the library for
whatever research you find most interesting. 

- [ ] Regularized Adjusted Plus-Minus (RAPM) / Adjusted Plus-Minus (APM)
- [ ] Goals Above Replacement (GAR) / xG Above Replacement (xGAR)
- [ ] Wins Above Replacement (WAR)

## :material-numeric-2-circle: **Concurrent scraping**

Concurrent fetching within a single game has landed: the `Game` object's `prefetch()` method
(`chickenstats.chicken_nhl._game_core._GameCore.prefetch`) runs its four independent network fetches -
API events/rosters, HTML events, HTML rosters, and shifts - in parallel using a `ThreadPoolExecutor`
(`prefetch_concurrent()` in `_game_utils.py`), instead of sequentially. The `Scraper` object's internal
pipeline (`_pbp_pipeline` on each `Game`) uses the same concurrent prefetch before merging the results into
`play_by_play`.

What's still sequential, and remains "Priority 1B":

1. The `Scraper` object still loops through its list of game IDs one game at a time (`_scraper_core.py`'s
`_scrape()` method) - concurrency currently only applies *within* a single game's network fetches, not
*across* the games in a `Scraper`. Extending concurrency (via threads, `aiohttp`, or multiprocessing) across
games is the next opportunity for a substantial speedup on multi-game scrapes.
2. The CPU-bound processing steps that run after fetching - merging events, tracking cumulative game state,
and calculating xG - are still single-threaded per game.

### Speed improvements

The `chickenstats.chicken_nhl.play_by_play` property scrapes data from seven endpoints before consolidating
into a final play-by-play dataframe, as illustrated by the diagram below - the four independent fetches
(api events + rosters, html events, html rosters, home/away shifts) are the ones `prefetch()` now runs
concurrently.

``` mermaid
graph LR
  subgraph "raw data"
    html_events_raw(html events endpoint)
    html_rosters_raw(html rosters endpoint)
    html_home_shifts_raw(html home shifts endpoint)
    html_away_shifts_raw(html away shifts endpoint)
    api_rosters_raw(api rosters endpoint)
    api_events_raw(api events endpoint)
    game_info_raw(api game info endpoint)
  end
  subgraph "initial processing"
    html_rosters(html rosters df)
    html_events(html events df)
    api_rosters(api rosters df)
    api_events(api events df)
    shifts(shifts df)
    changes(changes df)
    rosters(rosters df)
  end
  subgraph "final dataframe"
    play_by_play(combined play-by-play df)
  end
    
  html_events_raw(html events endpoint) --> html_events(html events df);
  html_home_shifts_raw --> shifts(shifts df);
  html_away_shifts_raw --> shifts(shifts df);
  shifts --> changes(changes df);
  html_rosters_raw --> html_rosters(html rosters df)
  html_rosters --> rosters(rosters df);
  changes --> play_by_play(combined play-by-play df);
  rosters --> changes(changes df);
  rosters --> play_by_play;
  html_rosters --> html_events;
  html_events --> play_by_play;
  api_events_raw(api events endpoint) --> api_events(api events df);
  game_info_raw(api game info endpoint) --> api_events;
  api_events --> play_by_play(combined play-by-play);
  api_rosters_raw(api rosters endpoint) --> api_rosters(api rosters df);
  api_rosters --> rosters;
  api_rosters --> api_events;
```

### Library extensibility

The library was designed with concurrent fetching and clearly-separated processing steps in mind - each raw
data source has its own `_fetch_*` method, and processing is split into discrete `_munge_*`/`_merge_*`/`_track_*`
methods rather than one monolithic function. The below code snippet is taken from the `Game` object's
`_pbp_pipeline` cached property (the internal orchestrator that `play_by_play`, `play_by_play_ext`, and
`xg_fields` all read from) and demonstrates this point:

```python
@cached_property
def _pbp_pipeline(self) -> tuple[list, list, list]:
    """Hidden Master Pipeline: Orchestrates merging, state tracking, and xG calculation."""
    prefetch_concurrent(self._fetch_api_data, self._fetch_html_events, self._fetch_html_rosters, self._fetch_shifts) # (1)!
    api_events = self.api_events
    html_events = self.html_events
    changes = self.changes
    rosters = self.rosters

    actives = {p["team_jersey"]: p for p in self.rosters if p.get("team_jersey") and p.get("status") == "ACTIVE"}

    if not html_events or not api_events:
        return [], [], []

    merged_events = self._merge_pbp_events(html_events, api_events, changes, rosters) # (2)!
    stateful_events = self._track_pbp_state(merged_events, actives) # (3)!
    final_pbp, final_ext, final_xg = self._calculate_pbp_xg(stateful_events) # (4)!

    return final_pbp, final_ext, final_xg # (5)!
```

1. The four independent raw fetches run concurrently via `prefetch_concurrent()` (a thin wrapper around
`ThreadPoolExecutor`) before any processing starts
2. HTML events, API events, and line changes are merged into one sorted event list
3. Cumulative game state (score, on-ice players, strength state, event flags) is tracked across the merged
events in a single sequential pass
4. xG features are calculated and the final `play_by_play`, `play_by_play_ext`, and `xg_fields` records are
built and validated together
5. The result is cached as a tuple so all three downstream properties reuse it instead of re-running the
pipeline

Because fetching is already concurrent and the processing steps are cleanly separated, the next opportunities
are extending concurrency across the games in a `Scraper`'s game-ID list (currently a sequential loop, see
above), and profiling/optimizing the per-event Python loops inside `_merge_pbp_events`, `_track_pbp_state`, and
`_calculate_pbp_xg`, which are the remaining CPU-bound cost per game. This chicken is happy to take feedback if
either turns out to be harder than expected :fontawesome-solid-face-smile:

## :material-numeric-3-circle: **Refactoring for speed / reliability**

- [ ] Generally clean up chicken's gross (self-taught) code
- [ ] Reduce the number of loops across all functions
    - [ ] Play-by-play functions are especially egregious here - the method loops through every player
      in the roster once and every event multiple times
