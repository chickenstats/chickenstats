---
icon: material/arrow-up-bold-circle
description: "What changes when you upgrade from chickenstats 1.8 to 1.9"
---

# :material-arrow-up-bold-circle: **Upgrading to 1.9**

chickenstats 1.9 fixes numbers that did not match the NHL's, and makes the scraper fail loudly
instead of returning partial data quietly. Many of those fixes change what a function returns:
a count, a column, a type, whether a value can be null, or which error is raised. This page
lists every one of those changes, grouped by the part of the package you use.

If you have saved or cached data from 1.8, scrape it again with 1.9. Numbers from the two
versions do not mix: the cache refuses files from 1.8, and play-by-play from 1.8 gives 1.8's
numbers when you aggregate it.

Each entry links to the commit that made the change.

## Scraping and play-by-play

- **Scrape games in progress when the NHL feeds are incomplete** ([`416e8d00`](https://github.com/chickenstats/chickenstats/commit/416e8d00))

    In xg_fields, coords_x, coords_y, event_distance and abs_y_distance can now be null, and distance_from_last is null when the previous event has no coordinates. It was measured from center ice before.

- **Give preseason and 4 Nations games their own overtime length** ([`2dc09c7f`](https://github.com/chickenstats/chickenstats/commit/2dc09c7f))

    For preseason and 4 Nations games, game_seconds on shootout rows and the length of overtime shifts and events change, and team TOI in a preseason shootout drops from 80 to 65 minutes. Regular-season and playoff games are unchanged.

- **Give the shootout winner one goal in the running score** ([`e140f967`](https://github.com/chickenstats/chickenstats/commit/e140f967))

    home_score, away_score, the score differences and the score states change on shootout rows. The last row of a game decided in a shootout now has the official final score.

- **Keep head-coach penalties and events with no team prefix** ([`2fe7ab33`](https://github.com/chickenstats/chickenstats/commit/2fe7ab33))

    html_events and play_by_play gain these rows, so penalty minutes, event counts and the stats built on them can rise for games with such events. The saved test games have none, and their values are unchanged.

- **Keep a penalty's server in player_3, apart from its drawer** ([`7c001829`](https://github.com/chickenstats/chickenstats/commit/7c001829))

    On a penalty with a server and no drawer, player_2 and its _eh_id, _api_id, _position and _type columns are now null, and the server is in player_3. ipend counts in prep_ind and prep_stats drop for players who served an individual penalty.

- **Set the other team's strength state on penalty shots and shootouts** ([`1c6f09cf`](https://github.com/chickenstats/chickenstats/commit/1c6f09cf))

    opp_strength_state changes on penalty-shot and shootout rows (0v1) and on rows with an illegal skater count (ILLEGAL). On-ice stats split by strength state have new 0v1 rows for the defending team, and its 5v5 goals against drop by the penalty-shot goals.

- **Key shifts by jersey and repair a 0:00 end's duration** ([`cd0c5f64`](https://github.com/chickenstats/chickenstats/commit/cd0c5f64))

    Duration and duration_seconds change in shifts for shifts whose report end was 0:00 / 0:00, and so does the TOI built from them.

- **Use the roster name for a player in shifts and changes** ([`bd73d79d`](https://github.com/chickenstats/chickenstats/commit/bd73d79d))

    player_name in shifts and changes, and in the CHANGE rows of play_by_play, now matches the roster spelling.

- **Score-adjust a blocked shot by the shooting team's strength** ([`08b14a15`](https://github.com/chickenstats/chickenstats/commit/08b14a15))

    block_adj, corsi_adj and the adjusted columns built from them change for blocked shots on special teams.

- **Read event and roster reports as UTF-8** ([`1d481dfc`](https://github.com/chickenstats/chickenstats/commit/1d481dfc))

    Description in play_by_play spells accented names correctly, so text that matched the garbled spelling no longer does.

- **Credit the drawer of a bench penalty that has one** ([`4326bc3f`](https://github.com/chickenstats/chickenstats/commit/4326bc3f))

    In play_by_play, player_2 and player_3 trade places on bench penalties that name a drawer, and prep_ind credits ipend0 through ipend10 to the drawer instead of the server.

- **File a zone start under its faceoff's strength state** ([`c4b4e169`](https://github.com/chickenstats/chickenstats/commit/c4b4e169))

    The strength state and on-ice columns of CHANGE rows in play_by_play change when both teams change at the same second, so zone starts by strength state move in prep_oi, prep_stats, prep_lines and prep_team_stats, and prep_stats loses its rows that held only zone starts (131 to 122 in 2023020001).

- **Say a game has not started instead of failing on its response** ([`4235d4ed`](https://github.com/chickenstats/chickenstats/commit/4235d4ed))

    play_by_play for a game that has not started raises GameNotStartedError instead of KeyError or an empty result, and Scraper lists it in failed_games.

- **List games that have not started apart from failed_games** ([`e05756b3`](https://github.com/chickenstats/chickenstats/commit/e05756b3))

    failed_games no longer lists games that have not started; they are in Scraper.not_started_games, and the warning for them no longer says they failed.

- **Fail a finished game when one of its reports cannot be read** ([`9baac73f`](https://github.com/chickenstats/chickenstats/commit/9baac73f))

    A finished game with a missing or failed report, including the roster report, now fails instead of returning partial data, and Game raises ReportUnavailableError for it.

- **Fail an official game whose API response has no plays** ([`c706d7fd`](https://github.com/chickenstats/chickenstats/commit/c706d7fd))

    Game.play_by_play raises ReportUnavailableError instead of returning no rows for an OFF game whose API response has no plays, and Scraper lists that game in failed_games.

- **Fail a finished game whose events or roster report has no rows** ([`daa52adf`](https://github.com/chickenstats/chickenstats/commit/daa52adf))

    Game.html_events, Game.html_rosters and the frames built on them raise ReportUnavailableError for an official game whose events or roster report has no rows, instead of returning no rows, and Scraper lists that game in failed_games.

- **Raise ReportUnavailableError only for a game the NHL marked OFF** ([`46418fed`](https://github.com/chickenstats/chickenstats/commit/46418fed))

    Game no longer raises ReportUnavailableError for a game at FINAL, and Scraper no longer lists that game in failed_games. Its frames can be partial until the game is OFF and is fetched again.

- **Raise InvalidGameIDError for a game the NHL API does not have** ([`3f13e1d6`](https://github.com/chickenstats/chickenstats/commit/3f13e1d6))

    Game raises InvalidGameIDError instead of requests.JSONDecodeError for a game the API does not have, and Scraper no longer raises NHLUnavailableError when a range runs past the last game.

- **Treat a cut-off HTML report as failed** ([`81394cd0`](https://github.com/chickenstats/chickenstats/commit/81394cd0))

    A finished game whose report is cut off, or whose events report has no game end, now fails instead of returning partial data.

- **Give API events that arrive with no details their event code** ([`6b268cae`](https://github.com/chickenstats/chickenstats/commit/6b268cae))

    In api_events, an event with no details has its upper-case code instead of the API's lower-case name.

- **Store each game's frames once, and together** ([`5b8a99eb`](https://github.com/chickenstats/chickenstats/commit/5b8a99eb))

    changes, shifts, rosters and the event frames no longer repeat a game's rows when several are read from one Scraper.

- **Stop play_by_play from rewriting a game's line changes** ([`85d303cd`](https://github.com/chickenstats/chickenstats/commit/85d303cd))

    Game.changes after play_by_play keeps the values from the shift reports instead of the ones play-by-play filled in.

- **Order on-ice lineups forwards, then defense, then goalies** ([`1dc7980b`](https://github.com/chickenstats/chickenstats/commit/1dc7980b))

    The player order inside the on-ice lineup columns changes, so a string comparison against an older output no longer matches.

- **Fetch a game again until the API reports it OFF** ([`d0a180b3`](https://github.com/chickenstats/chickenstats/commit/d0a180b3))

    A Scraper fetches a game that is not OFF again on its next scrape, after add_games or from a cache, instead of keeping its first data.

- **Return only the requested games from a cache** ([`37799696`](https://github.com/chickenstats/chickenstats/commit/37799696))

    Scraper(game_ids, cache=path) no longer adds the cache's other games to game_ids or to its frames.

- **Bound the retry budget and stop a scrape when the NHL is down** ([`eba44f51`](https://github.com/chickenstats/chickenstats/commit/eba44f51))

    A scrape where 5 games in a row fail on the network raises NHLUnavailableError instead of finishing with every game failed, and requests retry fewer times.

## Aggregated stats

- **Stop counting shootout attempts as shots and goals** ([`cb053f66`](https://github.com/chickenstats/chickenstats/commit/cb053f66))

    play_by_play has two new columns, shootout_attempt and shootout_goal. Goals, shots, Fenwick and Corsi in play_by_play, prep_stats, prep_lines and prep_team_stats no longer include shootout attempts, so team goals for a game decided in a shootout equal the score after overtime. xg_fields has no shootout rows.

- **Put only the shooter and the goalie on ice for a penalty shot** ([`4618a52b`](https://github.com/chickenstats/chickenstats/commit/4618a52b))

    On penalty-shot and shootout rows the on-ice columns, skater counts, teammates and opp_* columns hold only the shooter and the goalie in net. On-ice stats lose the penalty-shot goals for the other skaters, and prep_stints leaves penalty shots out of stints, as it already did for shootout attempts.

- **Keep rows with events but no ice time in aggregated stats** ([`0e884a61`](https://github.com/chickenstats/chickenstats/commit/0e884a61))

    prep_stats, prep_lines and prep_team_stats return rows with 0 ice time when they hold an event, e.g. 1v0 and 0v1 rows for a penalty shot. Their per-60 rates are not finite until the rates change that follows.

- **Return null for rates and percentages with nothing to divide by** ([`36ecbcf9`](https://github.com/chickenstats/chickenstats/commit/36ecbcf9))

    Every *_p60 and *_percent column, take_percent included, is nullable and has no default. A percentage is null when both sides are 0 or a side is missing; a per-60 rate is null when toi is 0.

- **Fill both sides of one-sided team stats before totals** ([`b2a1da4d`](https://github.com/chickenstats/chickenstats/commit/b2a1da4d))

    prep_team_stats cf, ca, cf_adj, ca_adj and the zone faceoff totals change for groups where only one team has rows, and their percentages with them.

- **Compute rolling rates and percentages from rolling sums** ([`3e9c5d2e`](https://github.com/chickenstats/chickenstats/commit/3e9c5d2e))

    rolling_*_p60 and rolling_*_percent values change for any window whose games differ in ice time or in event totals.

- **Keep float count columns when validating aggregated stats** ([`86faef33`](https://github.com/chickenstats/chickenstats/commit/86faef33))

    Aggregations of play-by-play with float count columns return the real counts instead of 0.

- **Count a lost faceoff in the loser's zone** ([`5bbdca25`](https://github.com/chickenstats/chickenstats/commit/5bbdca25))

    prep_ind iozfl and idzfl, and prep_lines and prep_team_stats ozfl, dzfl, ozf and dzf, change for every lost faceoff in an offensive or defensive zone.

- **Keep prep_oi rows that only have zone starts** ([`9b3497f2`](https://github.com/chickenstats/chickenstats/commit/9b3497f2))

    prep_oi, and prep_stats through it, return extra rows when split by strength; 2023020001 goes from 122 to 131 rows.

- **Stop crediting a bench minor's server with drawing it** ([`d50d12e6`](https://github.com/chickenstats/chickenstats/commit/d50d12e6))

    prep_ind ipend0 through ipend10, and prep_stats through it, no longer count a bench minor for the player serving it.

- **Count only penalty rows in the penalty columns** ([`cc1ed339`](https://github.com/chickenstats/chickenstats/commit/cc1ed339))

    pen0 through pen10 in play_by_play, and the penalty columns built from them, are 0 on DELPEN rows.

- **Count every blocked attempt in bsf and bsa** ([`0b77c39b`](https://github.com/chickenstats/chickenstats/commit/0b77c39b))

    bsf, bsa and their adjusted, per-60 and percent columns change in chicken_nhl prep_stats, prep_lines and prep_team_stats, as does teammate_block in prep_stats. In 2023020001 Tampa Bay goes from 10 and 17 to 11 and 19. bsf and bsa trade places in the evolving_hockey prep_team_stats. opp_teammate_block and its versions are new columns.

- **Make identity_columns a key of each aggregated frame** ([`e64b104a`](https://github.com/chickenstats/chickenstats/commit/e64b104a))

    identity_columns returns forwards or defense for lines whatever the teammates flag, adds position for stats, and drops opp_team for team stats at season and session level when opposition is off. It has a new position argument.

- **Leave out xG columns when play-by-play has no pred_goal** ([`321f4013`](https://github.com/chickenstats/chickenstats/commit/321f4013))

    Without pred_goal, the xG columns are missing from prep_ind, prep_oi, prep_stats, prep_lines and prep_team_stats instead of 0.0. A percentage with one side missing, such as base_xgf_percent without base_xg, is left out instead of null. With pred_goal but no pred_goal_adj, the adjusted xG columns are left out.

- **Score-adjust supplied xG and give shootout attempts none** ([`142f07e6`](https://github.com/chickenstats/chickenstats/commit/142f07e6))

    With pred_goal supplied, ixg_adj, xgf_adj, xga_adj and their per-60 and percent columns are computed instead of missing, and xG on shootout attempts no longer counts in any xG column.

- **Keep every individual event in prep_stats** ([`1248c553`](https://github.com/chickenstats/chickenstats/commit/1248c553))

    prep_stats and Scraper.stats return extra rows, with no ice time, for players credited with an event while not on the ice in that group, and their individual totals rise to match prep_ind.

- **Count events that have no description in prep_ind** ([`58b51f58`](https://github.com/chickenstats/chickenstats/commit/58b51f58))

    prep_ind, and prep_stats through it, count events whose description is missing, which raises individual totals for games where a report has blank descriptions.

- **Count supplied xG only on goals, shots and misses** ([`bcb14902`](https://github.com/chickenstats/chickenstats/commit/bcb14902))

    With xG supplied, ixg, xgf, xga, a1_xg, a2_xg and their adjusted, per-60 and percent columns leave out xG on blocked shots and other non-shot rows, and NaN values are skipped instead of making the total NaN.

- **Score-adjust base and context xG when they are supplied** ([`1640f9e2`](https://github.com/chickenstats/chickenstats/commit/1640f9e2))

    With base_xg or context_xg supplied, base_ixg_adj, base_xgf_adj, base_xga_adj and their rates and percentages are computed instead of missing, and the context_*_adj columns are new.

- **Weight every attempt in cf_adj, ca_adj and icf_adj by Corsi** ([`bc310ad8`](https://github.com/chickenstats/chickenstats/commit/bc310ad8))

    icf_adj, cf_adj and ca_adj change in prep_ind, prep_oi, prep_stats, prep_lines and prep_team_stats, as do their per-60 and percent columns. In 2023020001, Tampa Bay's 5v5 cf_adj goes from 42.632 to 42.987.

- **Recompute the score adjustment on 2019-20 to 2025-26** ([`4e7ee664`](https://github.com/chickenstats/chickenstats/commit/4e7ee664))

    Every score-adjusted column changes, *_adj and the rates and percentages built from them, in play_by_play, the aggregation functions and evolving_hockey prep_pbp.

- **Rebuild every aggregated result after add_games** ([`6ef9ce97`](https://github.com/chickenstats/chickenstats/commit/6ef9ce97))

    After add_games, Scraper's aggregated results include the added games, and a result read back after being cleared uses its last arguments instead of the defaults.

- **Raise for an unrecognized aggregation level** ([`7f43f909`](https://github.com/chickenstats/chickenstats/commit/7f43f909))

    An unrecognized level raises InvalidInputError instead of being aggregated as season.

- **Raise on play-by-play missing a column prep_* reads** ([`bedaa302`](https://github.com/chickenstats/chickenstats/commit/bedaa302))

    A play-by-play frame missing a column these functions read now raises InvalidInputError, where it used to return wrong values or raise polars' ColumnNotFoundError.

- **Reject a bad position, lineup_ids or flag in prep_* and identity** ([`0d258e91`](https://github.com/chickenstats/chickenstats/commit/0d258e91))

    identity_columns raises InvalidInputError instead of ValueError for an unknown frame, and a prep_* or identity_columns call with a flag that is not a bool now raises instead of returning rows.

- **Match identity_columns' defaults to the prep functions** ([`8bda05b6`](https://github.com/chickenstats/chickenstats/commit/8bda05b6))

    identity_columns defaults to level="game", score=False, teammates=False and opposition=False; pass them explicitly to keep the old key.

## Saving and the cache

- **Scrape each game once, however its ID is written** ([`ec9ea733`](https://github.com/chickenstats/chickenstats/commit/ec9ea733))

    Scraper.game_ids holds ints with repeats removed, and a game ID that is not a whole number raises InvalidGameIDError instead of being scraped and recorded as failed.

- **List each failed game once until it scrapes** ([`f5a37405`](https://github.com/chickenstats/chickenstats/commit/f5a37405))

    failed_games no longer repeats a game, drops a game once it scrapes, and returns a copy instead of the Scraper's own list.

- **Write the cache one game at a time, and refuse old caches** ([`94063db7`](https://github.com/chickenstats/chickenstats/commit/94063db7))

    Caches use a new layout, and a cache written by an earlier version raises CacheFormatError; pass overwrite=True to replace it. overwrite=True now removes the old cache's files on construction.

- **Remove cache= and overwrite= from Scraper, keep save() and load()** ([`ddbb5ee6`](https://github.com/chickenstats/chickenstats/commit/ddbb5ee6))

    Scraper no longer takes cache= or overwrite=, and passing either raises TypeError. Use save(path) and Scraper.load(path), and save in batches to keep a long scrape safe from an interruption. add_games() no longer reads anything from disk. CacheFormatError is renamed SaveFormatError, and Scraper.load() refuses saves from 1.8 and caches from 1.9's development.

## Season, Player and Team

- **Keep each team's schedule whole, with every game type** ([`64c4d3f3`](https://github.com/chickenstats/chickenstats/commit/64c4d3f3))

    An unknown team code raises InvalidTeamError, and an unknown session raises InvalidInputError instead of KeyError.

- **Give a game that has not started null scores** ([`bfedd45f`](https://github.com/chickenstats/chickenstats/commit/bfedd45f))

    home_score and away_score in Season.schedule() are null, not 0, for a game that has not started.

- **Return the 4 Nations final, and refuse the 2004 season** ([`19270273`](https://github.com/chickenstats/chickenstats/commit/19270273))

    sessions="FO" also returns the final, and Season(2004) raises InvalidSeasonError.

- **Handle players with no team or no NHL stats** ([`1cd0d06b`](https://github.com/chickenstats/chickenstats/commit/1cd0d06b))

    Player.current_team_id, current_team and the team name properties return None, instead of raising, for a player with no team.

- **Identify chickenstats requests, and add a request throttle** ([`202a7f4a`](https://github.com/chickenstats/chickenstats/commit/202a7f4a))

    ChickenSession's default User-Agent is chickenstats/<version> instead of a Chrome string.

- **Fill shootout_losses in Season.standings** ([`f19b69b3`](https://github.com/chickenstats/chickenstats/commit/f19b69b3))

    The standings' shootout_losses column was always null. It now holds each team's shootout losses.

## Network and utilities

- **Stop relabeling play-by-play bugs as data mismatches** ([`261ec154`](https://github.com/chickenstats/chickenstats/commit/261ec154))

    Game.play_by_play no longer wraps errors from building play-by-play in DataMismatchError; the original exception is raised.

- **Flip norm_coords by the end each team attacks** ([`ba527873`](https://github.com/chickenstats/chickenstats/commit/ba527873))

    norm_coords_x and norm_coords_y keep a team's own-half events in its own half, and opponents' events in theirs, so those points move in plot_shot_chart and plot_density_heatmap.

## Charts

- **Leave shootout attempts out of the shot chart and heatmap** ([`c588cff3`](https://github.com/chickenstats/chickenstats/commit/c588cff3))

    plot_shot_chart and plot_density_heatmap draw fewer points for games decided in a shootout.

- **Draw one rolling line per team or player, and reject filters** ([`2c8a3677`](https://github.com/chickenstats/chickenstats/commit/2c8a3677))

    plot_rolling_stats draws a separate line for each team or player in the frame, and raises InvalidInputError when team or player is given but the frame has no such column.

- **Open charts at the default dpi and close saved figures** ([`ef12d58d`](https://github.com/chickenstats/chickenstats/commit/ef12d58d))

    plot_shot_chart, plot_density_heatmap, plot_line_network, plot_rolling_stats and plot_stat_comparison open new figures at matplotlib's dpi instead of 650, and close a figure they created after saving it to save_path; the returned Axes then belongs to a closed figure.

- **Apply plot_line_network's toi_min to each player's total** ([`afeab03e`](https://github.com/chickenstats/chickenstats/commit/afeab03e))

    plot_line_network's toi_min is a minimum on a player's total ice time, not on each row, so more players and lines appear in the graph for the same toi_min.

## RAPM

- **Give each team its own zone starts in build_rapm_matrix** ([`e7c11bc7`](https://github.com/chickenstats/chickenstats/commit/e7c11bc7))

    build_rapm_matrix raises InvalidInputError for stints without the four new columns, so stints from an earlier prep_stints need rebuilding, and its zone-start and strength-state columns now differ between a stint's two rows, which changes fitted coefficients.

## The chickenstats.com API client

- **Time out chickenstats API requests, and require a login** ([`aadcd078`](https://github.com/chickenstats/chickenstats/commit/aadcd078))

    ChickenUser and ChickenStats raise AuthError when there is no login, and AuthError is now a ChickenstatsError.

## evolving_hockey

- **Keep raw values for states without weights** ([`5a1501f5`](https://github.com/chickenstats/chickenstats/commit/5a1501f5))

    In prep_pbp, the adjusted columns for penalty shots and for states outside the weights table equal the raw values instead of 0, and change prep_stats, prep_lines and prep_team_stats through them.
