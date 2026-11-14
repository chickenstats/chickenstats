# Changelog

Changes that affect users of the package, newest release first. Generated from commit subjects by git-cliff;
see CONTRIBUTING.md for the commit format.

## [1.9.0] - 2026-11-14

### Breaking changes

- Scrape games in progress when the NHL feeds are incomplete
  - in xg_fields, coords_x, coords_y, event_distance and abs_y_distance can now be null, and distance_from_last is null when the previous event has no coordinates. It was measured from center ice before.
- Stop counting shootout attempts as shots and goals
  - play_by_play has two new columns, shootout_attempt and shootout_goal. Goals, shots, Fenwick and Corsi in play_by_play, prep_stats, prep_lines and prep_team_stats no longer include shootout attempts, so team goals for a game decided in a shootout equal the score after overtime. xg_fields has no shootout rows.
- Give the shootout winner one goal in the running score
  - home_score, away_score, the score differences and the score states change on shootout rows. The last row of a game decided in a shootout now has the official final score.
- Set the other team's strength state on penalty shots and shootouts
  - opp_strength_state changes on penalty-shot and shootout rows (0v1) and on rows with an illegal skater count (ILLEGAL). On-ice stats split by strength state have new 0v1 rows for the defending team, and its 5v5 goals against drop by the penalty-shot goals.
- Put only the shooter and the goalie on ice for a penalty shot
  - on penalty-shot and shootout rows the on-ice columns, skater counts, teammates and opp_* columns hold only the shooter and the goalie in net. On-ice stats lose the penalty-shot goals for the other skaters, and prep_stints leaves penalty shots out of stints, as it already did for shootout attempts.
- Keep rows with events but no ice time in aggregated stats
  - prep_stats, prep_lines and prep_team_stats return rows with 0 ice time when they hold an event, e.g. 1v0 and 0v1 rows for a penalty shot. Their per-60 rates are not finite until the rates change that follows.
- Return null for rates and percentages with nothing to divide by
  - every *_p60 and *_percent column, take_percent included, is nullable and has no default. A percentage is null when both sides are 0 or a side is missing; a per-60 rate is null when toi is 0.
- Fill both sides of one-sided team stats before totals
  - prep_team_stats cf, ca, cf_adj, ca_adj and the zone faceoff totals change for groups where only one team has rows, and their percentages with them.
- Compute rolling rates and percentages from rolling sums
  - rolling_*_p60 and rolling_*_percent values change for any window whose games differ in ice time or in event totals.
- Keep float count columns when validating aggregated stats
  - aggregations of play-by-play with float count columns return the real counts instead of 0.
- Count a lost faceoff in the loser's zone
  - prep_ind iozfl and idzfl, and prep_lines and prep_team_stats ozfl, dzfl, ozf and dzf, change for every lost faceoff in an offensive or defensive zone.
- Use the roster name for a player in shifts and changes
  - player_name in shifts and changes, and in the CHANGE rows of play_by_play, now matches the roster spelling.
- Keep prep_oi rows that only have zone starts
  - prep_oi, and prep_stats through it, return extra rows when split by strength; 2023020001 goes from 122 to 131 rows.
- Stop crediting a bench minor's server with drawing it
  - prep_ind ipend0 through ipend10, and prep_stats through it, no longer count a bench minor for the player serving it.
- Count only penalty rows in the penalty columns
  - pen0 through pen10 in play_by_play, and the penalty columns built from them, are 0 on DELPEN rows.
- Score-adjust a blocked shot by the shooting team's strength
  - block_adj, corsi_adj and the adjusted columns built from them change for blocked shots on special teams.
- Count every blocked attempt in bsf and bsa
  - bsf, bsa and their adjusted, per-60 and percent columns change in chicken_nhl prep_stats, prep_lines and prep_team_stats, as does teammate_block in prep_stats. In 2023020001 Tampa Bay goes from 10 and 17 to 11 and 19. bsf and bsa trade places in the evolving_hockey prep_team_stats. opp_teammate_block and its versions are new columns.
- Make identity_columns a key of each aggregated frame
  - identity_columns returns forwards or defense for lines whatever the teammates flag, adds position for stats, and drops opp_team for team stats at season and session level when opposition is off. It has a new position argument.
- Leave out xG columns when play-by-play has no pred_goal
  - without pred_goal, the xG columns are missing from prep_ind, prep_oi, prep_stats, prep_lines and prep_team_stats instead of 0.0. A percentage with one side missing, such as base_xgf_percent without base_xg, is left out instead of null. With pred_goal but no pred_goal_adj, the adjusted xG columns are left out.
- Score-adjust supplied xG and give shootout attempts none
  - with pred_goal supplied, ixg_adj, xgf_adj, xga_adj and their per-60 and percent columns are computed instead of missing, and xG on shootout attempts no longer counts in any xG column.
- **evolving_hockey**: Keep raw values for states without weights
  - in prep_pbp, the adjusted columns for penalty shots and for states outside the weights table equal the raw values instead of 0, and change prep_stats, prep_lines and prep_team_stats through them.
- Keep every individual event in prep_stats
  - prep_stats and Scraper.stats return extra rows, with no ice time, for players credited with an event while not on the ice in that group, and their individual totals rise to match prep_ind.
- Count events that have no description in prep_ind
  - prep_ind, and prep_stats through it, count events whose description is missing, which raises individual totals for games where a report has blank descriptions.
- Read event and roster reports as UTF-8
  - description in play_by_play spells accented names correctly, so text that matched the garbled spelling no longer does.
- Credit the drawer of a bench penalty that has one
  - in play_by_play, player_2 and player_3 trade places on bench penalties that name a drawer, and prep_ind credits ipend0 through ipend10 to the drawer instead of the server.
- File a zone start under its faceoff's strength state
  - the strength state and on-ice columns of CHANGE rows in play_by_play change when both teams change at the same second, so zone starts by strength state move in prep_oi, prep_stats, prep_lines and prep_team_stats, and prep_stats loses its rows that held only zone starts (131 to 122 in 2023020001).
- Count supplied xG only on goals, shots and misses
  - with xG supplied, ixg, xgf, xga, a1_xg, a2_xg and their adjusted, per-60 and percent columns leave out xG on blocked shots and other non-shot rows, and NaN values are skipped instead of making the total NaN.
- Score-adjust base and context xG when they are supplied
  - with base_xg or context_xg supplied, base_ixg_adj, base_xgf_adj, base_xga_adj and their rates and percentages are computed instead of missing, and the context_*_adj columns are new.
- **viz**: Leave shootout attempts out of the shot chart and heatmap
  - plot_shot_chart and plot_density_heatmap draw fewer points for games decided in a shootout.
- Recompute the score adjustment on 2019-20 to 2025-26
  - every score-adjusted column changes, *_adj and the rates and percentages built from them, in play_by_play, the aggregation functions and evolving_hockey prep_pbp.
- Say a game has not started instead of failing on its response
  - play_by_play for a game that has not started raises GameNotStartedError instead of KeyError or an empty result, and Scraper lists it in failed_games.
- Fail a finished game when one of its reports cannot be read
  - a finished game with a missing or failed report, including the roster report, now fails instead of returning partial data, and Game raises ReportUnavailableError for it.
- Treat a cut-off HTML report as failed
  - a finished game whose report is cut off, or whose events report has no game end, now fails instead of returning partial data.
- Stop relabeling play-by-play bugs as data mismatches
  - Game.play_by_play no longer wraps errors from building play-by-play in DataMismatchError; the original exception is raised.
- Give each team its own zone starts in build_rapm_matrix
  - build_rapm_matrix raises InvalidInputError for stints without the four new columns, so stints from an earlier prep_stints need rebuilding, and its zone-start and strength-state columns now differ between a stint's two rows, which changes fitted coefficients.
- Give API events that arrive with no details their event code
  - in api_events, an event with no details has its upper-case code instead of the API's lower-case name.
- Scrape each game once, however its ID is written
  - Scraper.game_ids holds ints with repeats removed, and a game ID that is not a whole number raises InvalidGameIDError instead of being scraped and recorded as failed.
- Store each game's frames once, and together
  - changes, shifts, rosters and the event frames no longer repeat a game's rows when several are read from one Scraper.
- Stop play_by_play from rewriting a game's line changes
  - Game.changes after play_by_play keeps the values from the shift reports instead of the ones play-by-play filled in.
- Rebuild every aggregated result after add_games
  - after add_games, Scraper's aggregated results include the added games, and a result read back after being cleared uses its last arguments instead of the defaults.
- Raise for an unrecognized aggregation level
  - an unrecognized level raises InvalidInputError instead of being aggregated as season.
- List each failed game once until it scrapes
  - failed_games no longer repeats a game, drops a game once it scrapes, and returns a copy instead of the Scraper's own list.
- Match identity_columns' defaults to the prep functions
  - identity_columns defaults to level="game", score=False, teammates=False and opposition=False; pass them explicitly to keep the old key.
- Order on-ice lineups forwards, then defense, then goalies
  - the player order inside the on-ice lineup columns changes, so a string comparison against an older output no longer matches.
- Fetch a game again until the API reports it OFF
  - a Scraper fetches a game that is not OFF again on its next scrape, after add_games or from a cache, instead of keeping its first data.
- Keep each team's schedule whole, with every game type
  - an unknown team code raises InvalidTeamError, and an unknown session raises InvalidInputError instead of KeyError.
- Give a game that has not started null scores
  - home_score and away_score in Season.schedule() are null, not 0, for a game that has not started.
- Return the 4 Nations final, and refuse the 2004 season
  - sessions="FO" also returns the final, and Season(2004) raises InvalidSeasonError.
- Handle players with no team or no NHL stats
  - Player.current_team_id, current_team and the team name properties return None, instead of raising, for a player with no team.
- Bound the retry budget and stop a scrape when the NHL is down
  - a scrape where 5 games in a row fail on the network raises NHLUnavailableError instead of finishing with every game failed, and requests retry fewer times.
- Time out chickenstats API requests, and require a login
  - ChickenUser and ChickenStats raise AuthError when there is no login, and AuthError is now a ChickenstatsError.
- Identify chickenstats requests, and add a request throttle
  - ChickenSession's default User-Agent is chickenstats/<version> instead of a Chrome string.
- Draw one rolling line per team or player, and reject filters
  - plot_rolling_stats draws a separate line for each team or player in the frame, and raises InvalidInputError when team or player is given but the frame has no such column.
- Flip norm_coords by the end each team attacks
  - norm_coords_x and norm_coords_y keep a team's own-half events in its own half, and opponents' events in theirs, so those points move in plot_shot_chart and plot_density_heatmap.
- Open charts at the default dpi and close saved figures
  - plot_shot_chart, plot_density_heatmap, plot_line_network, plot_rolling_stats and plot_stat_comparison open new figures at matplotlib's dpi instead of 650, and close a figure they created after saving it to save_path; the returned Axes then belongs to a closed figure.
- Apply plot_line_network's toi_min to each player's total
  - plot_line_network's toi_min is a minimum on a player's total ice time, not on each row, so more players and lines appear in the graph for the same toi_min.
- Weight every attempt in cf_adj, ca_adj and icf_adj by Corsi
  - icf_adj, cf_adj and ca_adj change in prep_ind, prep_oi, prep_stats, prep_lines and prep_team_stats, as do their per-60 and percent columns. In 2023020001, Tampa Bay's 5v5 cf_adj goes from 42.632 to 42.987.
- Raise ReportUnavailableError only for a game the NHL marked OFF
  - Game no longer raises ReportUnavailableError for a game at FINAL, and Scraper no longer lists that game in failed_games. Its frames can be partial until the game is OFF and is fetched again.
- Raise InvalidGameIDError for a game the NHL API does not have
  - Game raises InvalidGameIDError instead of requests.JSONDecodeError for a game the API does not have, and Scraper no longer raises NHLUnavailableError when a range runs past the last game.
- List games that have not started apart from failed_games
  - failed_games no longer lists games that have not started; they are in Scraper.not_started_games, and the warning for them no longer says they failed.
- Fail an official game whose API response has no plays
  - Game.play_by_play raises ReportUnavailableError instead of returning no rows for an OFF game whose API response has no plays, and Scraper lists that game in failed_games.
- Remove cache= and overwrite= from Scraper, keep save() and load()
  - Scraper no longer takes cache= or overwrite=, and passing either raises TypeError. Use save(path) and Scraper.load(path), and save in batches to keep a long scrape safe from an interruption. add_games() no longer reads anything from disk. CacheFormatError is renamed SaveFormatError, and Scraper.load() refuses saves from 1.8 and caches from 1.9's development.
- Fail a finished game whose events or roster report has no rows
  - Game.html_events, Game.html_rosters and the frames built on them raise ReportUnavailableError for an official game whose events or roster report has no rows, instead of returning no rows, and Scraper lists that game in failed_games.
- Keep head-coach penalties and events with no team prefix
  - html_events and play_by_play gain these rows, so penalty minutes, event counts and the stats built on them can rise for games with such events. The saved test games have none, and their values are unchanged.
- Keep a penalty's server in player_3, apart from its drawer
  - on a penalty with a server and no drawer, player_2 and its _eh_id, _api_id, _position and _type columns are now null, and the server is in player_3. ipend counts in prep_ind and prep_stats drop for players who served an individual penalty.
- Give preseason and 4 Nations games their own overtime length
  - for preseason and 4 Nations games, game_seconds on shootout rows and the length of overtime shifts and events change, and team TOI in a preseason shootout drops from 80 to 65 minutes. Regular-season and playoff games are unchanged.
- Key shifts by jersey and repair a 0:00 end's duration
  - duration and duration_seconds change in shifts for shifts whose report end was 0:00 / 0:00, and so does the TOI built from them.
- Raise on play-by-play missing a column prep_* reads
  - a play-by-play frame missing a column these functions read now raises InvalidInputError, where it used to return wrong values or raise polars' ColumnNotFoundError.
- Reject a bad position, lineup_ids or flag in prep_* and identity
  - identity_columns raises InvalidInputError instead of ValueError for an unknown frame, and a prep_* or identity_columns call with a flag that is not a bool now raises instead of returning rows.
- Fill null adjusted xG from the raw xG, and drop empty xG columns
  - adjusted xG columns built from a null supplied adjustment now hold the weighted raw xG instead of 0.0, and the xG outputs of a column with no values are left out instead of being 0.0.
- Give prep_lines null for an empty lineup, not ''
  - prep_lines lineup and goalie columns are null instead of '' for an empty lineup or a pulled goalie.
- Give level='season' one row for the regular season and playoffs
  - at level='season' the prep_* outputs and Scraper's aggregated results have one row per season instead of one per session, and no session column; identity_columns(level='season') no longer includes session.
- Return session as a string from Season.schedule
  - session in Season.schedule() and multi_season_schedule() is a nullable string, not an int, and game_type is a new int column. Code that compares session to 2 or 3 should compare game_type instead.
- Refuse play-by-play from 1.8 in the prep functions
  - the prep functions raise InvalidInputError on play-by-play scraped by 1.8, so those games must be scraped again. play_by_play has a new cs_version column, and Scraper.load() refuses saves from earlier 1.9 development builds.
- Return null xG for seasons with no xG in the prep functions
  - xG columns are null, not 0.0, for a season the supplied xG does not cover, and build_rapm_matrix returns fewer rows for such a frame.
- Allow null logos in Season.schedule
  - home_logo, home_logo_dark, away_logo and away_logo_dark in Season.schedule() are nullable.
- Label stint strength home first and rename prep_stints columns
  - in prep_stints and Scraper.stints, strength_state is home then away. ozs and dzs are removed. toi is now toi_seconds, home_skaters and away_skaters are home_skater_ids and away_skater_ids, and home_goalies and away_goalies are home_goalie_ids and away_goalie_ids. strength_state is no longer a required input column.
- Give build_rapm_matrix full defensive columns
  - build_rapm_matrix leaves empty-net stints out of EV, PP and SH, and players holds everyone with enough time on either side, so offensive columns can be empty. In player_metrics, toi is now toi_seconds, and api_id, team and def_toi_seconds are new. build_position_map returns api_id as Int64.
- Measure long deflected shots to the far net
  - event_distance, event_angle, zone, danger and high_danger change on those shots.
- Place events after a same-second line change from the report
  - event_idx, and on-ice and strength columns, change on those events in play_by_play, which moves the stats built from them.
- Drop the empty change_off slots from play_by_play_ext
  - play_by_play_ext loses the change_off_1 to change_off_7 columns and their _eh_id, _api_id and _pos versions. SAVE_FORMAT is now 6, so saves from earlier 1.9 builds must be scraped again.
- Keep the full penalty name in play_by_play
  - penalty in html_events and play_by_play holds new names for those rows. MINOR, HEAD, BREAKAWAY and BENCH now appear only where they are the report's whole text, and a row where the report gives no name, which came back as the surname, is null. INSTIGATOR - MISCONDUCT and ABUSIVE LANGUAGE - MISCONDUCT are no longer named GAME MISCONDUCT.
- Stop naming ten-minute misconducts GAME MISCONDUCT in penalty
  - penalty is MISCONDUCT instead of GAME MISCONDUCT on those rows, so a filter on GAME MISCONDUCT finds fewer of them. pen10, ipent10, ipend10, pent10, pend10 and their per-60 versions keep their values, and they are still not a count of game misconducts.
- Reject a bad backend before any request
  - A bad backend now raises UnsupportedBackendError or ImportError from the constructor rather than on first use.
- Validate game IDs in Scraper with the parser Game uses
  - Scraper raises InvalidGameIDError at construction for an ID that is not 10 digits or has an unknown session, where it used to record the game in failed_games. convert_to_list raises InvalidInputError for a fractional float or a bool. InvalidGameIDError is now a subclass of InvalidInputError.
- Use the latest team list in Season for a year past the table
  - Season warns instead of raising for a year past the team table.
- Return Int64 for pandas integer columns with nulls
  - On the pandas backend an integer column with nulls, such as a player ID, is Int64 rather than float64, so a missing value is pd.NA.
- Treat a narwhals frame as narwhals when detecting the backend
  - add_schedule_context and the evolving_hockey functions, called with no backend, return a narwhals frame for a narwhals input, where they used to return a polars one.
- Render the login page without the cli extra
  - The cli extra is removed.
- Move python-dotenv to the dev group
  - python-dotenv is no longer installed with chickenstats.
- Support Python 3.11 through 3.14
  - Python 3.10 is no longer supported. The enums in chickenstats.utilities are StrEnum, so str(Backend.POLARS) is "polars".
- Bind cached API tokens to the host they were issued for
  - ChickenUser and ChickenStats raise AuthError for a host that is plain http and not local, and for a cached login when another host is configured. With no host set, a cached login's own host is used.
- Accept a Cloudflare service token as a complete credential
  - A client with a full Cloudflare service token ignores a cached login, so its access_token is None. A cached login no longer carries the Cloudflare headers.
- Lock ChickenUser.refresh so jobs can share a login
  - ChickenUser.refresh raises AuthError rather than RuntimeError with no refresh token.
- Honor the environment's proxy in the API client
  - Requests go through a proxy set in the environment, and the user agent changes.
- **evolving_hockey**: Credit events to the right player in prep_pbp
  - event_player_1, event_player_2, their _eh_id and _pos columns and opp_team change on most rows. Every stat built on them moves, as do zone_start, ozs and dzs for away teams, and every adjusted stat outside 5v5 and 4v4 with a lead of two or more. The season column of prep_gar and prep_xgar is now Int64.
- **evolving_hockey**: Match prep_stats, prep_lines to chicken_nhl
  - player names read 'NIKITA KUCHEROV', not 'NIKITA.KUCHEROV', in every name column, and player in prep_gar and prep_xgar comes from eh_id. eh_id collapses '..' and drops accents everywhere. iozfl, idzfl, ozfl and dzfl swap in prep_ind, prep_lines and prep_team_stats. level='season' has no session column. Null lineups replace 'EMPTY' in prep_lines. Shootout rows no longer count as goals, shots or attempts, and the shooting goalie loses a penalty shot's on-ice stats. Invalid position or columns values raise instead of returning data. prep_pbp adds shootout_attempt, shootout_goal, teammate_block and teammate_block_adj.
- **utilities**: Make DataFrameT a real alias for type checkers
  - chickenstats.utilities.DataFrameT is a string at runtime, for type checkers, so it can no longer be used with isinstance.
- Stop counting own goals as shots and keep every goal's team
  - shot, fenwick and corsi change for own goals, and event_team and the player columns are filled on goals that were empty before. xg_fields now requires fenwick, so own goals leave the xG sample.
- Reject an unknown situation in build_rapm_matrix
  - build_rapm_matrix raises for a situation other than EV, PP, SH or all.
- Write every shift duration as MM:SS in shifts
  - the duration column in shifts changes from M:SS to MM:SS on those rows.
- Tighten the inputs of the prep_* functions
  - pass level and the other options by keyword. A pandas frame raises InvalidInputError rather than AttributeError. The opposition docs for prep_team_stats now say it adds opp_team.
- Remove ChickenStats.check_team_stats_ids and check_line_ids
  - use check_team_stats_game_ids and check_lines_game_ids instead. There is no replacement that returns row IDs.
- Raise the dependency floors and cap each major version
  - chickenstats now needs polars 1.38.1 or later and below 2, pandera 0.32.1 or later, and chickenstats-api 0.1.8 or later.
- Give each player one stable position in build_position_map
  - position and player can differ from an earlier run for players with more than one value.
- **chicken_nhl**: Correct player names in reports before 2010-11
  - player_name and eh_id change in html_rosters and shifts for games before 2010-11. Later seasons do not change.
- **chicken_nhl**: Support games back to 2007-08 with ESPN coordinates
  - games from 2007-08 to 2009-10 no longer warn, and their play_by_play, html_events, rosters and xg_fields values change. The warning now applies before 2007-08. Later seasons do not change.
- Report cs_version as unknown when the package is not installed
  - cs_version is "unknown" instead of a hardcoded version when the package metadata is missing, and importing chickenstats no longer raises PackageNotFoundError in that case.
- Keep a game's frames from one fetch until Scraper.refresh
  - reading a frame no longer fetches a game that is not final. Call refresh() to get newer data.
- Raise typer to 0.16.0 so chickenstats --help works
  - chickenstats needs typer 0.16.0 or later.
- **chicken_nhl**: Give each player one name and one eh_id
  - eh_id is MATT.MURRAY2 for Matt Murray 8483575, who wears 32, and RYAN.JOHNSON2 for Ryan Johnson 8481564, from 2023-24 on. player_name is MAX CROZIER where it was MAXWELL CROZIER and MAXIM SHABANOV where it was MAX SHABANOV, in every frame that has names and in the evolving_hockey name mapping.
- **chicken_nhl**: Drop a scorer swap the NHL API no longer needs
  - in game 2016021165, Zdeno Chara's goal at 6:34 of the first period has coords_x 75 and coords_y -1 instead of null, player_1_api_id and player_2_api_id are Chara's and Brandon Carlo's, and the goal is in xg_fields.
- **chicken_nhl**: Keep stints of 0 seconds that hold a shot
  - prep_stints and Scraper.stints return a row with toi_seconds 0 for each stint whose events share one second and include a shot attempt or goal, and their shot and goal totals rise by those events.
- **chicken_nhl**: Give a scratch added to the API roster one row
  - in game 2013020971, rosters and Scraper.rosters return one CBJ8 row for Nathan Horton, with api_id 8470596, instead of two.
- **chicken_nhl**: Drop a penalty correction the NHL API contradicts
  - in game 2012020671, the New Jersey head coach's game misconduct at 19:25 of the third period has coords_x -8 and coords_y 42 instead of null.
- **chicken_nhl**: Give GOFF and EGT rows no team in html_events
  - html_events and Scraper.html_events return an empty event_team for GOFF and EGT rows instead of GAM or EME.
- **chicken_nhl**: Give Team.logo a logo for every former NHL team
  - Team.logo raises InvalidTeamError instead of requests.HTTPError for CAT, EDE, VIC, VMA and VMI.
- **api**: Keep ChickenStats.access_token current after a token refresh
  - ChickenStats.access_token now returns the token in use after a refresh instead of the one from login, and assigning to it raises AttributeError.
- **chicken_nhl**: Add zone starts to prep_lines and prep_team_stats
  - prep_lines and prep_team_stats now require the ozc, nzc, dzc and otf columns, which prep_oi already required. prep_lines also requires change_on_forwards_count or change_on_defense_count, and prep_team_stats requires change_on_count. A play-by-play frame without them raises InvalidInputError. Every Scraper play-by-play frame has them.
- **chicken_nhl**: Restore a blocked shot in play_by_play for 2022020673
  - for game 2022020673, html_events and play_by_play gain one BLOCK at 11:24 of the second period, with event_team VGK, Brayden McNabb as player_1, Aaron Ekblad as player_2 and coordinates (-55, 11) from the API. The faceoff before it has an event_length of 29 instead of 42. Aaron Ekblad's icf and FLA's cf and bsf gain one, and VGK's ca and bsa and the on-ice cf or ca of the skaters on the ice gain one.
- **chicken_nhl**: Keep the report's zone for a shot with no distance
  - in play_by_play, a shot, miss or goal with no distance in its report description keeps zone DEF when the report says DEF, and its danger and high_danger are 0. The danger and high-danger stats in prep_stats, prep_lines and prep_team_stats move with it.
- **evolving_hockey**: Add zone starts to prep_lines, prep_team_stats
  - prep_lines and prep_team_stats return four new columns, ozs, nzs, dzs and otf, and their schemas now require them. Both functions read players_on_pos, which every prep_pbp frame has.
- **chicken_nhl**: Stop doubling a 2021020224 faceoff description
  - the description of the 2021020224 faceoff at event_idx 286 in html_events and play_by_play is now "BOS WON NEU. ZONE - MTL #60 BELZILE VS BOS #92 NOSEK" instead of the doubled text.
- **chicken_nhl**: Keep Krejci as player_2 on the 2016021070 hit
  - for 2016021070 event_idx 206, the description in html_events and play_by_play is now "TOR #  HIT BOS #46 KREJCI, DEF. ZONE". player_2, player_2_eh_id and player_2_position are now DAVID KREJCI, DAVID.KREJCI and C, and play_by_play's player_2_api_id is 8471276. All were null before.
- **evolving_hockey**: Name missing input columns in line and team stats
  - prep_lines and prep_team_stats raise InvalidInputError instead of polars.exceptions.ColumnNotFoundError when the play-by-play lacks players_on_pos, ozs, nzs, dzs or otf, and prep_team_stats also when it lacks event_team or opp_team.
- **chicken_nhl**: Leave event_team null on a faceoff with no winner
  - in play_by_play, event_team and opp_team are null on a faceoff with no winner, where they were the home and away teams, and zone_start is null on the line changes at an end-zone faceoff with no winner, where both teams got the opposite of the report's zone. prep_stats, prep_ind, prep_oi, prep_lines and prep_team_stats no longer count that faceoff in ifow, ifol, fow, fol or the zone faceoff columns.
- **chicken_nhl**: Drop the assists on shootout goals in api_events
  - on shootout goals, player_2_api_id, player_2_type, player_3_api_id and player_3_type in play_by_play, and the player_2 and player_3 columns in api_events, are now null.
- **evolving_hockey**: Name missing input columns in prep_stats
  - prep_ind, prep_oi and prep_stats raise InvalidInputError instead of polars.exceptions.ColumnNotFoundError when the play-by-play lacks one of the columns above.
- **chicken_nhl**: Give every bench penalty a null player_1_position
  - Game.html_events, Game.html_events_df and Scraper.html_events return a null player_1_position instead of "" for a bench penalty that names no player.
- **chicken_nhl**: Give null for an unlisted player in html_events
  - Game.html_events, Game.html_events_df and Scraper.html_events return null instead of '' in player_1, player_1_eh_id, player_2, player_2_eh_id, player_3 and player_3_eh_id for a player on neither roster.
- **chicken_nhl**: Give null for an event with no team in html_events
  - Game.html_events, Game.html_events_df and Scraper.html_events return null instead of '' in event_team for an event with no team.
- **chicken_nhl**: Give null for a group nobody changed in changes
  - Game.changes, Game.changes_df and Scraper.changes return null instead of '' when the group is empty in change_on, change_off, change_on_positions and change_off_positions; in change_on_forwards, change_off_forwards, change_on_defense, change_off_defense, change_on_goalie and change_off_goalie; and in the _jersey, _eh_id and _api_id columns of each of these ten groups.
- **chicken_nhl**: Give null for a reason the API omits in api_events
  - Game.api_events, Game.api_events_df and Scraper.api_events return null instead of '' in stoppage_reason, stoppage_reason_secondary, miss_reason and penalty_reason when the NHL API gives no reason.
- **chicken_nhl**: Give null for a missing headshot_url in api_rosters
  - Game.api_rosters, Game.api_rosters_df, Scraper.api_rosters, Game.rosters, Game.rosters_df and Scraper.rosters return null instead of '' in headshot_url when the NHL API gives no headshot for a player.
- **chicken_nhl**: Give null for a missing streak_code in standings
  - Season.standings returns null instead of '' in streak_code when the NHL API gives no streak.
- **chicken_nhl**: Make Scraper prep_* method options keyword-only
  - pass the options of Scraper.prep_stats, Scraper.prep_lines, Scraper.prep_team_stats and Scraper.prep_stints by keyword, for example scraper.prep_stats(level="season"). A positional option raises TypeError.
- **evolving_hockey**: Make the prep_* function options keyword-only
  - pass the options of prep_pbp, prep_ind, prep_oi, prep_stats, prep_lines, prep_team_stats, prep_gar and prep_xgar in chickenstats.evolving_hockey by keyword, for example prep_stats(pbp, level="season") or prep_xgar(data, backend="pandas"). A positional option raises TypeError.
- **chicken_nhl**: Make the class constructor options keyword-only
  - pass the options of Game, Scraper, Scraper.load, Season, Season.schedule, Player and Team by keyword, for example Game(game_id, backend="pandas"), Scraper(game_ids, disable_progress_bar=True) or season.schedule("NSH", sessions="R"). A positional option raises TypeError.
- **chicken_nhl**: Make the chicken_nhl function options keyword-only
  - pass the options of prep_stints, prep_rolling_stats, multi_season_schedule, add_schedule_context, search_players, player_bios, rapm.build_rapm_matrix, contract.assert_chronological, contract.assert_unique_events and contract.build_pandera_schema by keyword, for example prep_stints(pbp, min_skaters=4), build_rapm_matrix(stints, metric="xgf", situation="EV") or assert_unique_events(df, what="play_by_play"). A positional option raises TypeError.
- **viz**: Make the options of the plot_* functions keyword-only
  - pass the arguments after the frame of plot_shot_chart, plot_density_heatmap, plot_line_network, plot_rolling_stats and plot_stat_comparison by keyword, for example plot_shot_chart(pbp, team="NSH") or plot_stat_comparison(lines, x="cf_p60", y="ff_p60"). A positional argument raises TypeError.
- **utilities**: Make the utilities function options keyword-only
  - pass the options of ChickenSession, track, norm_coords and convert_to_list by keyword, for example ChickenSession(user_agent="my-app"), track(games, description="Scraping") or norm_coords(data, normalization_column="event_team", normalization_value="NSH"). A positional option raises TypeError.
- **api**: Make the ChickenStats and ChickenUser options keyword-only
  - pass the arguments of ChickenUser and ChickenStats by keyword, for example ChickenStats(username="me", password="secret"), and pass every filter of the ChickenStats download_* and check_* methods after the first by keyword, for example cs.download_pbp(2024, sessions="R", game_id=2024020001). A positional option raises TypeError.
- **chicken_nhl**: Add game_id to play_by_play_ext
  - play_by_play_ext has a new game_id column (Int64, never null) between id and event_idx, on Scraper.play_by_play_ext, Game.play_by_play_ext and build_play_by_play_ext. Scraper.load raises SaveFormatError on a save written in format 6.
- **chicken_nhl**: Add games_played to the aggregated stats frames
  - chicken_nhl and evolving_hockey prep_stats, prep_ind, prep_oi, prep_lines and prep_team_stats, and Scraper.stats, ind_stats, oi_stats, lines and team_stats, return a new Int64, never-null games_played column after the identity columns and before toi (before g in ind_stats). Code that selects columns by position, or writes the frames to a table with a fixed schema, needs the new column.
- Require Python 3.11.5 or later
  - Python 3.11.0 to 3.11.4 are no longer supported; pip will not install chickenstats 1.9.0 on them. Python 3.11.5 and later are unchanged.

### Added

- Warn when a finished game has a faceoff with no winner
- Add Scraper.refresh to fetch games again
- Add Scraper.game_states and Scraper.provisional_games
- Add Scraper.failure_reasons with each failed game's error
- Add requests_session to search_players, Team and Scraper.load
- Add a public contract for play-by-play order and strength states
- Add chronological order tools to the play-by-play contract
- **chicken_nhl**: Infer the frame type of Scraper from backend
- **chicken_nhl**: Infer the frame type of Game from backend
- **chicken_nhl**: Infer frame types from backend for Season
- **api**: Infer the frame type of ChickenStats from backend
- **evolving_hockey**: Infer the returned frame type from backend
- Default Scraper.load to the directory save uses
- Add the prior shot's type to xg_fields
- Export polars_pandera_options from the contract module
- **chicken_nhl**: Add handedness, height and weight to Player
- **chicken_nhl**: Name every column of RapmMatrix.x in columns

### Fixed

- Return aggregated rows in the same order on every call
- Sort a lineup with a player who has no API ID
- Fill shootout_losses in Season.standings
- Let prep_rolling_stats take two games on one date
- Build each prep_stats result from one play-by-play download
- Mark a game final only after every stored type is fetched at OFF
- Keep a pickled or copied ChickenSession's throttle and timeout
- Scrape a game whose shifts put two goalies on the ice
- Scrape a shootout that has a line change in its period
- Make ChickenStats downloads work on every tier and survive errors
- Accept scalar arguments in ChickenStats downloads
- Move api_events_fixes to the player_2 drawer and player_3 server
- Keep events before a line change only half done in the report
- Stop reading a jersey number as a penalty length
- Warn for game IDs from before the 2010-11 season
- Warn when add_schedule_context gets a partial schedule
- Include pyarrow in the extras that call to_pandas
- Import chickenstats without loading matplotlib.pyplot
- Write the credentials file through a temporary file
- Count line changes only from before a shot's second
- Accept any sequence of game IDs in Scraper's types
- Collect lazy frames with the in-memory engine
- **api**: Tell an unverified login to verify its email
- Scrape eight games whose play-by-play report has no game end
- Scrape two 2007-08 games whose report swaps a hit's teams
- Scrape three pre-2010 games with shifts for a listed scratch
- Scrape two pre-2010 games whose report has no game end
- **chicken_nhl**: Raise InvalidInputError for pandas input everywhere
- **chicken_nhl**: Let prep_* turn off the download progress bar
- **api**: Return every ID from the ChickenStats check_* methods
- **chicken_nhl**: Drop shifts timed past their period's end in shifts
- **chicken_nhl**: Check Scraper.prep_stats arguments before scraping

### Performance

- Drop each Game once its frames are stored
- Read a game's state before requesting its HTML reports
- Fetch every held type of a game through one Game in refresh
- Keep a full-season prep_stats under 6 GB
- Validate aggregated frames with Polars before pandera
- Parse NHL HTML reports with lxml instead of BeautifulSoup
- Build play_by_play_ext rows without a pydantic model
- **evolving_hockey**: Validate prep_pbp output in one Polars pass
- **chicken_nhl**: Build an empty Scraper stats result only once
- **chicken_nhl**: Speed up schema preparation in prep_stats and others

### Documentation

- Show the six high-danger and shot-type percentages as nullable
- Say which arguments Scraper's result properties are built with
- Add the 1.8 to 1.9 upgrade page
- Bring the install notes up to date for 1.9
- Describe the frame types of the public classes
- Publish the support and deprecation policy
- Fix the examples that the polars default backend broke
- Replace the Blog tab with links to chickenstats.com
- **chicken_nhl**: Name the Game properties that have a _df version
- **chicken_nhl**: Stop pointing Player users at private attributes
- **chicken_nhl**: Document every column of the Scraper stats frames
- Add reference pages for exceptions and ChickenSession
- Rewrite the scrape_all.py example with the polars API
- Fix the schedule lookups in three example notebooks
- **chicken_nhl**: Say prep_* progress settings cover the download
- Document every public chicken_nhl function in the reference
- Replace the Sphinx roles left in chicken_nhl docstrings
- Add a reference index card for each chicken_nhl reference page
- Point README and llms.txt links at docs.chickenstats.com
- **api**: Correct the pred_goal limit in the ChickenStats docstring
- State that chickenstats is not affiliated with the NHL
- **chicken_nhl**: Describe each RapmMatrix field on the reference page
- **chicken_nhl**: Show the RAPM_METRICS and RAPM_SITUATIONS docstrings
- Publish a column table for every frame chickenstats returns
- Describe every column of Season.schedule, prep_gar and xg_fields
- Set units for penalty_length, penalty_duration and clock columns

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
