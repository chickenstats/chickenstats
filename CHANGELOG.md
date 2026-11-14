# Changelog

Changes that affect users of the package, newest release first. Generated from commit subjects by git-cliff;
see CONTRIBUTING.md for the commit format.

## [1.8.3] - 2026-10-04

### Added

- Add the 2026 season, use live standings until a season ends

### Fixed

- Handle empty API responses, cap pred_goal page size at the server limit

## [1.8.2] - 2026-10-03

### Added

- Add identity_columns for the keys that identify aggregated rows

### Documentation

- Fix reference rendering for inherited members and shared docstrings

## [1.8.1] - 2026-08-26

### Added

- Brand the CLI login callback page, add optional cli extra
- Add rosters, shifts, changes, games, and players download methods
- Refresh expired access tokens automatically on 401
- Bump chickenstats_api to 0.1.7, update players filters to lists
- Add prep_stints aggregation, rapm matrix module and extra

### Fixed

- Pin explode empty_as_null ahead of Polars 2.0, assert expected scrape warnings
- Make Corsi against symmetric with opposing Corsi for

### Documentation

- Fix remaining codecov and shields.io badges pointing at the old org
- Correct season examples to 8-digit IDs

## [1.8.0] - 2026-08-14

### Added

- **core**: Align scraper, api, and evolving_hockey modules for v1.8.0
- **core**: Add automated data lineage tracking and gzip score adjustments
- Surface goal highlight clip URLs in play-by-play data
- Add Scraper.save()/Scraper.load() for persisting scraped data
- Add multi_season_schedule() for cross-season convenience
- Add prep_rolling_stats() for trailing rolling-window stat averages
- Add add_schedule_context() for rest-day and back-to-back context
- Case-insensitive team lookup with fuzzy-match suggestions
- Add search_players() to resolve player names to api_id
- Add chicken_nhl.viz plotting module
- Add cache/overwrite constructor args with cross-fetch cache reuse
- Chickenstats login CLI (browser OAuth) + cached-credential support
- Wire in real Google OAuth Desktop app Client ID
- Add chickenstats login --password

### Fixed

- Updating CI tests
- Updating for tox changes
- API keyword arguments
- Update utilities.py
- Error with type checking and pre-commit
- Update zensical url
- **styles**: Prevent crash during matplotlib style registration on modern v3.9+ versions
- Sync dark-mode preference with chickenstats.com and api.chickenstats.com
- Declare tzdata as a direct dependency
- Update docs url
- Aggregations and builder list
- Fix for tox
- Avoid KeyError on DELPEN events with no parsed penalty name
- Chickenstats_api 0.1.5 method/kwarg drift, missing norm_coords export
- Apply score-adjustment is_home flip once per play, not per column
- Guard 0-for-0 division in _prep_oi_percent to avoid NaN
- Handle period >= 5 shift-clock repair to prevent UnboundLocalError
- Handle float year input in Season.__init__
- Raise for any unsupported season year, not just non-adjacent ones
- Raise on unrecognized player slot column in prep_oi
- Handle missing hyphen in _return_name_html without crashing
- Distinguish expected failures from bugs in _scrape_single_game
- Log prefetch task failures at WARNING instead of DEBUG
- Restore give/take columns to the on-ice stats schema
- Add schema validation to evolving_hockey prep_gar/prep_xgar
- Raise on malformed EH season format in prep_gar/prep_xgar
- Make _right join-suffix reliance explicit in _aggregation.py
- Stop closing shared ChickenSession between scrape phases
- Stop using session as a per-call context manager in Player/Season
- Reuse a session and cache Team.logo instead of refetching
- Add raise_for_status() to HTTP calls in player/team/season
- Wire up _api_constants.py, fixing download_pbp's oversized default limit
- Route ChickenStats._finalize_dataframe through shared _to_backend
- Tighten exception messages and add structured attributes
- Minor ergonomics and cleanup polish
- Reject ambiguous multi-row-per-game input in prep_rolling_stats
- Raise UnsupportedBackendError on unrecognized backend instead of silently returning polars
- Restore game_date_dt_local to Season.schedule() output
- Requiring strict dictionary construction
- Updating hero branding
- Validate PBPEvent.session against allowed session codes
- Always define Team alt-color attributes to avoid AttributeError
- Season.py schedule scraping bugs (magic season literal, teams=None crash)
- Correct xg_fields_df and rosters_df return type annotations
- Enable griffe force_inspection for runtime-assigned docstrings; trim comments
- Send client_secret on Google's authorization_code token exchange
- Use chickenstats_api 0.1.6's login_verify_token/login_refresh instead of raw HTTP
- Declare pandas in the plotting extra
- Make pandera.pandas import lazy in chicken_nhl schema
- Document cache and overwrite params on Scraper

### Performance

- Defer per-slot aggregation in prep_oi to a single group_by per category
- Cache Game instances per game_id on Scraper
- Vectorize null-column check in _finalize_dataframe
- Make evolving_hockey score-adjustment weights load lazy

### Documentation

- Update guides, tutorials, and roadmap for v1.8.0 release
- Remove xG content, add citation
- Clarify ChickenSession thread-safety invariant
- Remove stray 'Not covered by tests' comments
- Fill in missing API ID column docs, resolving 4 TODOs
- Update CLAUDE.md module map for _game_html.py split and new features
- Simplify two 'worker method' docstring openers
- Fix typos, canonicalize GitHub org links, drop stale content

## [1.7.9.29] - 2026-06-02

### Added

- Adding team_stats upload
- Adding experiments.py
- Adding env file for experiments
- Adding limit functionality
- Adding API wrapper
- Adding ID generator utilities
- Adding module-level track function
- Custom ChickenTimeRemaining column in progress bar
- Updating scrape_data to write parquet files
- Moving old versions of process and experiments
- Building cascade xG model
- Adding process data scripts for env and inf xg
- Creating a script to finalize inf_xg
- Last commit of xG model before moving behind paywall
- Adding base_xg and pred_goal capabilities
- Adding chickenstats-xg
- Adding chickenstats xG fields
- New chickenstats API sdk

### Fixed

- Update new_release
- Bug with API ID fallback
- Re-ordering based on API ID
- Updating season dtype
- Aggregation error with team stats
- Updating examples env.example
- Updating filepaths for data workflows
- Updating dotenv
- Updating season column dtype
- Adding proper env variables
- Adding errors and type validation
- Adding parquet to gitignore
- Adding old schema so they don't have to be recreated
- Importing from local directory
- De-duplicate change players
- Moving xG validation
- Moving xg.py closer to xg scripts
- Updating RAPM target metrics and player ID columns
- Updating experiments.py
- Updating rolling stats for env_xg
- Updating experiments.py
- Updating naming conventions
- Adding session as categorical column
- Addressing play speed nulls
- Addressing bugs with monotone constraints
- Sorting data before saving
- Updating leakage of uv environments
- Removing xG features
- Updating pre-commit
- Cleaning up dependencies
- Updating logo url
- Addressing type checking errors

### Documentation

- Updating evolving_hockey docs
- Update readme
- Updating index
- Updating chicken_nhl guide

## [1.7.9.28] - 2026-04-17

### Added

- Dumping failed games to json

### Fixed

- Comprehensive dev dependencies
- Updating _validation_utils
- Updating team_stats
- Updating dtypes and group columns
- Updating tests suite
- Updating polars aggregation
- Updating adjusted corsi calculations
- Updating change events in pbp
- Updating testing exceptions
- Adding missing shifts for several games
- Aligning xg prep functions
- Removing pandera polars performance warning
- Removing print debug statement
- Adding _to_backend utility
- Moving score adjustments calculations
- Adding dummy columns

### Documentation

- Creating _docstrings.py
- Update _fixes.py
- Updating game.py for shared docstring conventions
- Updating docstrings and code comments
- Adding shared docstrings
- Updating docstrings and comments
- Updating validation docstrings and comments
- Updating utilities docstrings and comments
- Updating scraper docstrings and comments
- Updating team and player docstrings and comments
- Updating progress bar documentation

## [1.7.4] - 2023-12-28
