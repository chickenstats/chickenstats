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
versions do not mix: `Scraper.load()` refuses saves from 1.8, and the `prep_*` functions raise
an error on play-by-play from 1.8.

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

- **Measure long deflected shots to the far net** ([`8daa317d`](https://github.com/chickenstats/chickenstats/commit/8daa317d))

    event_distance, event_angle, zone, danger and high_danger change on long tips, deflections and pokes that were measured to the near net, so a few high-danger chances and the xG inputs built from them move.

- **Place events after a same-second line change from the report** ([`b3474aa1`](https://github.com/chickenstats/chickenstats/commit/b3474aa1))

    event_idx, and the on-ice and strength columns, change on events the NHL's report places after a line change in the same second, about 2% of play events, so stats by strength state and on-ice stats move slightly.

- **Drop the empty change_off slots from play_by_play_ext** ([`cf213d4b`](https://github.com/chickenstats/chickenstats/commit/cf213d4b))

    play_by_play_ext loses the change_off_1 to change_off_7 columns and their _eh_id, _api_id and _pos versions. SAVE_FORMAT is now 6, so saves from earlier 1.9 builds must be scraped again.

- **Keep the full penalty name in play_by_play** ([`56703910`](https://github.com/chickenstats/chickenstats/commit/56703910))

    penalty in html_events and play_by_play holds the report's full text instead of its last word: HIGH-STICKING - DOUBLE MINOR, not MINOR. About 1.8% of penalties change, and no count moves.

- **Stop naming ten-minute misconducts GAME MISCONDUCT in penalty** ([`50f601ab`](https://github.com/chickenstats/chickenstats/commit/50f601ab))

    penalty is MISCONDUCT on ten-minute misconducts and GAME MISCONDUCT only when the report says so. pen10 and the ipent10, ipend10, pent10 and pend10 columns keep their values, and they count every 10-minute penalty, not game misconducts.

- **Stop reading a jersey number as a penalty length** ([`cdc9cca3`](https://github.com/chickenstats/chickenstats/commit/cdc9cca3))

    A penalty to a player such as #34 MINTYUKOV had a penalty_length of 34 and was in no count. Those penalties now have their real length, so a few pen0 to pen10 counts rise.

- **Validate game IDs in Scraper with the parser Game uses** ([`24a720c1`](https://github.com/chickenstats/chickenstats/commit/24a720c1))

    A bad game ID now raises when you create the Scraper.

- **Stop counting own goals as shots and keep every goal's team** ([`d2c11c9b`](https://github.com/chickenstats/chickenstats/commit/d2c11c9b))

    shot, fenwick and corsi change for own goals, and event_team and the player columns are filled on goals that were empty before. xg_fields now requires fenwick, so own goals leave the xG sample.

- **Write every shift duration as MM:SS in shifts** ([`64042525`](https://github.com/chickenstats/chickenstats/commit/64042525))

    The duration column in shifts changes from M:SS to MM:SS on those rows.

- **Correct player names in reports before 2010-11** ([`b22d84d2`](https://github.com/chickenstats/chickenstats/commit/b22d84d2))

    player_name and eh_id change in html_rosters and shifts for games before 2010-11. Later seasons do not change.

- **Give each player one name and one eh_id** ([`b7fac368`](https://github.com/chickenstats/chickenstats/commit/b7fac368))

    eh_id is MATT.MURRAY2 for Matt Murray 8483575, who wears 32, and RYAN.JOHNSON2 for Ryan Johnson 8481564, from 2023-24 on. player_name is MAX CROZIER where it was MAXWELL CROZIER and MAXIM SHABANOV where it was MAX SHABANOV, in every frame that has names and in the evolving_hockey name mapping.

- **Drop a scorer swap the NHL API no longer needs** ([`92429706`](https://github.com/chickenstats/chickenstats/commit/92429706))

    In game 2016021165, Zdeno Chara's goal at 6:34 of the first period has coords_x 75 and coords_y -1 instead of null, player_1_api_id and player_2_api_id are Chara's and Brandon Carlo's, and the goal is in xg_fields.

- **Give a scratch added to the API roster one row** ([`2606e077`](https://github.com/chickenstats/chickenstats/commit/2606e077))

    In game 2013020971, rosters and Scraper.rosters return one CBJ8 row for Nathan Horton, with api_id 8470596, instead of two.

- **Drop a penalty correction the NHL API contradicts** ([`80d3ad75`](https://github.com/chickenstats/chickenstats/commit/80d3ad75))

    In game 2012020671, the New Jersey head coach's game misconduct at 19:25 of the third period has coords_x -8 and coords_y 42 instead of null.

- **Support games back to 2007-08 with ESPN coordinates** ([`c0e177e9`](https://github.com/chickenstats/chickenstats/commit/c0e177e9))

    Games from 2007-08 to 2009-10 no longer warn, and their play_by_play, html_events, rosters and xg_fields values change. The warning now applies before 2007-08. Later seasons do not change.

- **Keep a game's frames from one fetch until Scraper.refresh** ([`41ec08e0`](https://github.com/chickenstats/chickenstats/commit/41ec08e0))

    Reading a frame no longer fetches a game that is not final. Call refresh() to get newer data.

- **Give GOFF and EGT rows no team in html_events** ([`f97718d0`](https://github.com/chickenstats/chickenstats/commit/f97718d0))

    html_events and Scraper.html_events return an empty event_team for GOFF and EGT rows instead of GAM or EME.

- **Restore a blocked shot in play_by_play for 2022020673** ([`427d284f`](https://github.com/chickenstats/chickenstats/commit/427d284f))

    For game 2022020673, html_events and play_by_play gain one BLOCK at 11:24 of the second period, with event_team VGK, Brayden McNabb as player_1, Aaron Ekblad as player_2 and coordinates (-55, 11) from the API. The faceoff before it has an event_length of 29 instead of 42. Aaron Ekblad's icf and FLA's cf and bsf gain one, and VGK's ca and bsa and the on-ice cf or ca of the skaters on the ice gain one.

- **Keep the report's zone for a shot with no distance** ([`3fca17f0`](https://github.com/chickenstats/chickenstats/commit/3fca17f0))

    In play_by_play, a shot, miss or goal with no distance in its report description keeps zone DEF when the report says DEF, and its danger and high_danger are 0. The danger and high-danger stats in prep_stats, prep_lines and prep_team_stats move with it.

- **Stop doubling a 2021020224 faceoff description** ([`08975caa`](https://github.com/chickenstats/chickenstats/commit/08975caa))

    The description of the 2021020224 faceoff at event_idx 286 in html_events and play_by_play is now "BOS WON NEU. ZONE - MTL #60 BELZILE VS BOS #92 NOSEK" instead of the doubled text.

- **Keep Krejci as player_2 on the 2016021070 hit** ([`ead06da4`](https://github.com/chickenstats/chickenstats/commit/ead06da4))

    For 2016021070 event_idx 206, the description in html_events and play_by_play is now "TOR # HIT BOS #46 KREJCI, DEF. ZONE". player_2, player_2_eh_id and player_2_position are now DAVID KREJCI, DAVID.KREJCI and C, and play_by_play's player_2_api_id is 8471276. All were null before.

- **Drop the assists on shootout goals in api_events** ([`eb940f7a`](https://github.com/chickenstats/chickenstats/commit/eb940f7a))

    On shootout goals, player_2_api_id, player_2_type, player_3_api_id and player_3_type in play_by_play, and the player_2 and player_3 columns in api_events, are now null.

- **Give every bench penalty a null player_1_position** ([`58df6d4d`](https://github.com/chickenstats/chickenstats/commit/58df6d4d))

    Game.html_events, Game.html_events_df and Scraper.html_events return a null player_1_position instead of "" for a bench penalty that names no player.

- **Give null for an unlisted player in html_events** ([`44ec27d3`](https://github.com/chickenstats/chickenstats/commit/44ec27d3))

    Game.html_events, Game.html_events_df and Scraper.html_events return null instead of '' in player_1, player_1_eh_id, player_2, player_2_eh_id, player_3 and player_3_eh_id for a player on neither roster.

- **Give null for an event with no team in html_events** ([`d85384fb`](https://github.com/chickenstats/chickenstats/commit/d85384fb))

    Game.html_events, Game.html_events_df and Scraper.html_events return null instead of '' in event_team for an event with no team.

- **Give null for a reason the API omits in api_events** ([`5545a978`](https://github.com/chickenstats/chickenstats/commit/5545a978))

    Game.api_events, Game.api_events_df and Scraper.api_events return null instead of '' in stoppage_reason, stoppage_reason_secondary, miss_reason and penalty_reason when the NHL API gives no reason.

- **Give null for a missing headshot_url in api_rosters** ([`0d1e564f`](https://github.com/chickenstats/chickenstats/commit/0d1e564f))

    Game.api_rosters, Game.api_rosters_df, Scraper.api_rosters, Game.rosters, Game.rosters_df and Scraper.rosters return null instead of '' in headshot_url when the NHL API gives no headshot for a player.

- **Make the class constructor options keyword-only** ([`b8a81d5d`](https://github.com/chickenstats/chickenstats/commit/b8a81d5d))

    Pass the options of Game, Scraper, Scraper.load, Season, Season.schedule, Player and Team by keyword, for example Game(game_id, backend="pandas"), Scraper(game_ids, disable_progress_bar=True) or season.schedule("NSH", sessions="R"). A positional option raises TypeError.


- **Give null for a group nobody changed in changes** ([`7eb78000`](https://github.com/chickenstats/chickenstats/commit/7eb78000))

    Game.changes, Game.changes_df and Scraper.changes return null instead of '' when the group is empty in change_on, change_off, change_on_positions and change_off_positions; in change_on_forwards, change_off_forwards, change_on_defense, change_off_defense, change_on_goalie and change_off_goalie; and in the _jersey, _eh_id and _api_id columns of each of these ten groups.

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

- **Give prep_lines null for an empty lineup, not ''** ([`f994a477`](https://github.com/chickenstats/chickenstats/commit/f994a477))

    prep_lines lineup and goalie columns are null instead of '' for an empty lineup or a pulled goalie.

- **Give level='season' one row for the regular season and playoffs** ([`2e1198ca`](https://github.com/chickenstats/chickenstats/commit/2e1198ca))

    At level='season' the prep_* outputs and Scraper's aggregated results have one row per season instead of one per session, and no session column; identity_columns(level='season') no longer includes session.

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

- **Fill null adjusted xG from the raw xG, and drop empty xG columns** ([`9a74b116`](https://github.com/chickenstats/chickenstats/commit/9a74b116))

    Adjusted xG columns built from a null supplied adjustment now hold the weighted raw xG instead of 0.0, and the xG outputs of a column with no values are left out instead of being 0.0.

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

- **Refuse play-by-play from 1.8 in the prep functions** ([`be9177bf`](https://github.com/chickenstats/chickenstats/commit/be9177bf))

    The prep functions raise InvalidInputError on play-by-play scraped by 1.8, so those games must be scraped again. play_by_play has a new cs_version column, and Scraper.load() refuses saves from earlier 1.9 development builds.

- **Return null xG for seasons with no xG in the prep functions** ([`6b363ff4`](https://github.com/chickenstats/chickenstats/commit/6b363ff4))

    xG columns are null, not 0.0, for a season the supplied xG does not cover, and build_rapm_matrix returns fewer rows for such a frame.

- **Label stint strength home first and rename prep_stints columns** ([`07e66a06`](https://github.com/chickenstats/chickenstats/commit/07e66a06))

    In prep_stints and Scraper.stints, strength_state is home then away. ozs and dzs are removed. toi is now toi_seconds, home_skaters and away_skaters are home_skater_ids and away_skater_ids, and home_goalies and away_goalies are home_goalie_ids and away_goalie_ids. strength_state is no longer a required input column.

- **Tighten the inputs of the prep_* functions** ([`1058e71e`](https://github.com/chickenstats/chickenstats/commit/1058e71e))

    Pass level and the other options by keyword. A pandas frame raises InvalidInputError rather than AttributeError. The opposition docs for prep_team_stats now say it adds opp_team.

- **Add zone starts to prep_lines and prep_team_stats** ([`5340bb4c`](https://github.com/chickenstats/chickenstats/commit/5340bb4c))

    prep_lines and prep_team_stats now require the ozc, nzc, dzc and otf columns, which prep_oi already required. prep_lines also requires change_on_forwards_count or change_on_defense_count, and prep_team_stats requires change_on_count. A play-by-play frame without them raises InvalidInputError. Every Scraper play-by-play frame has them.

- **Leave event_team null on a faceoff with no winner** ([`407e96d3`](https://github.com/chickenstats/chickenstats/commit/407e96d3))

    In play_by_play, event_team and opp_team are null on a faceoff with no winner, where they were the home and away teams, and zone_start is null on the line changes at an end-zone faceoff with no winner, where both teams got the opposite of the report's zone. prep_stats, prep_ind, prep_oi, prep_lines and prep_team_stats no longer count that faceoff in ifow, ifol, fow, fol or the zone faceoff columns.

- **Make Scraper prep_* method options keyword-only** ([`bacc6f55`](https://github.com/chickenstats/chickenstats/commit/bacc6f55))

    Pass the options of Scraper.prep_stats, Scraper.prep_lines, Scraper.prep_team_stats and Scraper.prep_stints by keyword, for example scraper.prep_stats(level="season"). A positional option raises TypeError.

- **Add games_played to the aggregated stats frames** ([`dc38953c`](https://github.com/chickenstats/chickenstats/commit/dc38953c))

    chicken_nhl and evolving_hockey prep_stats, prep_ind, prep_oi, prep_lines and prep_team_stats, and Scraper.stats, ind_stats, oi_stats, lines and team_stats, return a new Int64, never-null games_played column after the identity columns and before toi (before g in ind_stats). Code that selects columns by position, or writes the frames to a table with a fixed schema, needs the new column.

## Saving and the cache

- **Scrape each game once, however its ID is written** ([`ec9ea733`](https://github.com/chickenstats/chickenstats/commit/ec9ea733))

    Scraper.game_ids holds ints with repeats removed, and a game ID that is not a whole number raises InvalidGameIDError instead of being scraped and recorded as failed.

- **List each failed game once until it scrapes** ([`f5a37405`](https://github.com/chickenstats/chickenstats/commit/f5a37405))

    failed_games no longer repeats a game, drops a game once it scrapes, and returns a copy instead of the Scraper's own list.

- **Write the cache one game at a time, and refuse old caches** ([`94063db7`](https://github.com/chickenstats/chickenstats/commit/94063db7))

    Caches use a new layout, and a cache written by an earlier version raises CacheFormatError; pass overwrite=True to replace it. overwrite=True now removes the old cache's files on construction.

- **Remove cache= and overwrite= from Scraper, keep save() and load()** ([`ddbb5ee6`](https://github.com/chickenstats/chickenstats/commit/ddbb5ee6))

    Scraper no longer takes cache= or overwrite=, and passing either raises TypeError. Use save(path) and Scraper.load(path), and save in batches to keep a long scrape safe from an interruption. add_games() no longer reads anything from disk. CacheFormatError is renamed SaveFormatError, and Scraper.load() refuses saves from 1.8 and caches from 1.9's development.

- **Report cs_version as unknown when the package is not installed** ([`7a25e5a9`](https://github.com/chickenstats/chickenstats/commit/7a25e5a9))

    cs_version is "unknown" instead of a hardcoded version when the package metadata is missing, and importing chickenstats no longer raises PackageNotFoundError in that case.

- **Add game_id to play_by_play_ext** ([`faee5cf5`](https://github.com/chickenstats/chickenstats/commit/faee5cf5))

    play_by_play_ext has a new game_id column (Int64, never null) between id and event_idx, on Scraper.play_by_play_ext, Game.play_by_play_ext and build_play_by_play_ext. Scraper.load raises SaveFormatError on a save written in format 6.

## Season, Player and Team

- **Keep each team's schedule whole, with every game type** ([`64c4d3f3`](https://github.com/chickenstats/chickenstats/commit/64c4d3f3))

    An unknown team code raises InvalidTeamError, and an unknown session raises InvalidInputError instead of KeyError.

- **Give a game that has not started null scores** ([`bfedd45f`](https://github.com/chickenstats/chickenstats/commit/bfedd45f))

    home_score and away_score in Season.schedule() are null, not 0, for a game that has not started.

- **Return the 4 Nations final, and refuse the 2004 season** ([`19270273`](https://github.com/chickenstats/chickenstats/commit/19270273))

    sessions="FO" also returns the final, and Season(2004) raises InvalidSeasonError.

- **Return session as a string from Season.schedule** ([`2c416b68`](https://github.com/chickenstats/chickenstats/commit/2c416b68))

    session in Season.schedule() and multi_season_schedule() is a nullable string, not an int, and game_type is a new int column. Code that compares session to 2 or 3 should compare game_type instead.

- **Allow null logos in Season.schedule** ([`5f74493e`](https://github.com/chickenstats/chickenstats/commit/5f74493e))

    home_logo, home_logo_dark, away_logo and away_logo_dark in Season.schedule() are nullable.

- **Handle players with no team or no NHL stats** ([`1cd0d06b`](https://github.com/chickenstats/chickenstats/commit/1cd0d06b))

    Player.current_team_id, current_team and the team name properties return None, instead of raising, for a player with no team.

- **Identify chickenstats requests, and add a request throttle** ([`202a7f4a`](https://github.com/chickenstats/chickenstats/commit/202a7f4a))

    ChickenSession's default User-Agent is chickenstats/<version> instead of a Chrome string.

- **Fill shootout_losses in Season.standings** ([`f19b69b3`](https://github.com/chickenstats/chickenstats/commit/f19b69b3))

    The standings' shootout_losses column was always null. It now holds each team's shootout losses.

- **Reject a bad backend before any request** ([`8575914c`](https://github.com/chickenstats/chickenstats/commit/8575914c))

    A bad backend now raises UnsupportedBackendError or ImportError from the constructor rather than on first use.

- **Use the latest team list in Season for a year past the table** ([`14ea58fe`](https://github.com/chickenstats/chickenstats/commit/14ea58fe))

    Season warns instead of raising for a year past the team table.

- **Give Team.logo a logo for every former NHL team** ([`f92b9f34`](https://github.com/chickenstats/chickenstats/commit/f92b9f34))

    Team.logo raises InvalidTeamError instead of requests.HTTPError for CAT, EDE, VIC, VMA and VMI.

- **Give null for a missing streak_code in standings** ([`074eb93a`](https://github.com/chickenstats/chickenstats/commit/074eb93a))

    Season.standings returns null instead of '' in streak_code when the NHL API gives no streak.

- **Make the chicken_nhl function options keyword-only** ([`f972b283`](https://github.com/chickenstats/chickenstats/commit/f972b283))

    Pass the options of prep_stints, prep_rolling_stats, multi_season_schedule, add_schedule_context, search_players, player_bios, rapm.build_rapm_matrix, contract.assert_chronological, contract.assert_unique_events and contract.build_pandera_schema by keyword, for example prep_stints(pbp, min_skaters=4), build_rapm_matrix(stints, metric="xgf", situation="EV") or assert_unique_events(df, what="play_by_play"). A positional option raises TypeError.

- **Make the utilities function options keyword-only** ([`a3876fe4`](https://github.com/chickenstats/chickenstats/commit/a3876fe4))

    Pass the options of ChickenSession, track, norm_coords and convert_to_list by keyword, for example ChickenSession(user_agent="my-app"), track(games, description="Scraping") or norm_coords(data, normalization_column="event_team", normalization_value="NSH"). A positional option raises TypeError.

## Network and utilities

- **Infer the frame type from backend** ([`ebfaa42a`](https://github.com/chickenstats/chickenstats/commit/ebfaa42a))

    Type checkers now see the frame type for the backend you ask for: `Scraper(ids).play_by_play` is a polars DataFrame and `Scraper(ids, backend="pandas").play_by_play` is a pandas DataFrame. The same holds for pyarrow and narwhals, and for `Season`, `Game`, `ChickenStats` and the evolving_hockey functions. Pass `backend` by keyword; a backend held in a variable, or `Scraper.load()` without one, gives `Any`. `chickenstats.utilities.DataFrameT` is a string at runtime, so it can no longer be used with `isinstance`.

- **Stop relabeling play-by-play bugs as data mismatches** ([`261ec154`](https://github.com/chickenstats/chickenstats/commit/261ec154))

    Game.play_by_play no longer wraps errors from building play-by-play in DataMismatchError; the original exception is raised.

- **Flip norm_coords by the end each team attacks** ([`ba527873`](https://github.com/chickenstats/chickenstats/commit/ba527873))

    norm_coords_x and norm_coords_y keep a team's own-half events in its own half, and opponents' events in theirs, so those points move in plot_shot_chart and plot_density_heatmap.

- **Return Int64 for pandas integer columns with nulls** ([`6a1adf10`](https://github.com/chickenstats/chickenstats/commit/6a1adf10))

    On backend="pandas", integer columns with nulls are Int64, so a missing value is pd.NA.

- **Move python-dotenv to the dev group** ([`d421b2f2`](https://github.com/chickenstats/chickenstats/commit/d421b2f2))

    python-dotenv is no longer installed with chickenstats.

- **Support Python 3.11 through 3.14** ([`56bb2318`](https://github.com/chickenstats/chickenstats/commit/56bb2318))

    Python 3.11 is now the minimum, and 3.14 is supported.

- **Treat a narwhals frame as narwhals when detecting the backend** ([`1e34084a`](https://github.com/chickenstats/chickenstats/commit/1e34084a))

    add_schedule_context and the evolving_hockey functions, called with no backend, return a narwhals frame for a narwhals input, where they used to return a polars one.

- **Make DataFrameT a real alias for type checkers** ([`1d43f934`](https://github.com/chickenstats/chickenstats/commit/1d43f934))

    chickenstats.utilities.DataFrameT is a string at runtime, for type checkers, so it can no longer be used with isinstance.

## Charts

- **Leave shootout attempts out of the shot chart and heatmap** ([`c588cff3`](https://github.com/chickenstats/chickenstats/commit/c588cff3))

    plot_shot_chart and plot_density_heatmap draw fewer points for games decided in a shootout.

- **Draw one rolling line per team or player, and reject filters** ([`2c8a3677`](https://github.com/chickenstats/chickenstats/commit/2c8a3677))

    plot_rolling_stats draws a separate line for each team or player in the frame, and raises InvalidInputError when team or player is given but the frame has no such column.

- **Open charts at the default dpi and close saved figures** ([`ef12d58d`](https://github.com/chickenstats/chickenstats/commit/ef12d58d))

    plot_shot_chart, plot_density_heatmap, plot_line_network, plot_rolling_stats and plot_stat_comparison open new figures at matplotlib's dpi instead of 650, and close a figure they created after saving it to save_path; the returned Axes then belongs to a closed figure.

- **Apply plot_line_network's toi_min to each player's total** ([`afeab03e`](https://github.com/chickenstats/chickenstats/commit/afeab03e))

    plot_line_network's toi_min is a minimum on a player's total ice time, not on each row, so more players and lines appear in the graph for the same toi_min.

- **Make the options of the plot_* functions keyword-only** ([`b21dcf3d`](https://github.com/chickenstats/chickenstats/commit/b21dcf3d))

    Pass the arguments after the frame of plot_shot_chart, plot_density_heatmap, plot_line_network, plot_rolling_stats and plot_stat_comparison by keyword, for example plot_shot_chart(pbp, team="NSH") or plot_stat_comparison(lines, x="cf_p60", y="ff_p60"). A positional argument raises TypeError.

## RAPM

- **Give each team its own zone starts in build_rapm_matrix** ([`e7c11bc7`](https://github.com/chickenstats/chickenstats/commit/e7c11bc7))

    build_rapm_matrix raises InvalidInputError for stints without the four new columns, so stints from an earlier prep_stints need rebuilding, and its zone-start and strength-state columns now differ between a stint's two rows, which changes fitted coefficients.

- **Give build_rapm_matrix full defensive columns** ([`828981af`](https://github.com/chickenstats/chickenstats/commit/828981af))

    build_rapm_matrix leaves empty-net stints out of EV, PP and SH, and players holds everyone with enough time on either side, so offensive columns can be empty. In player_metrics, toi is now toi_seconds, and api_id, team and def_toi_seconds are new. build_position_map returns api_id as Int64.

- **Reject an unknown situation in build_rapm_matrix** ([`4463d5ca`](https://github.com/chickenstats/chickenstats/commit/4463d5ca))

    build_rapm_matrix raises for a situation other than EV, PP, SH or all.

- **Give each player one stable position in build_position_map** ([`6351e520`](https://github.com/chickenstats/chickenstats/commit/6351e520))

    Position and player can differ from an earlier run for players with more than one value.

- **Keep stints of 0 seconds that hold a shot** ([`5953b402`](https://github.com/chickenstats/chickenstats/commit/5953b402))

    prep_stints and Scraper.stints return a row with toi_seconds 0 for each stint whose events share one second and include a shot attempt or goal, and their shot and goal totals rise by those events.

## The chickenstats.com API client

- **Time out chickenstats API requests, and require a login** ([`aadcd078`](https://github.com/chickenstats/chickenstats/commit/aadcd078))

    ChickenUser and ChickenStats raise AuthError when there is no login, and AuthError is now a ChickenstatsError.

- **Render the login page without the cli extra** ([`801f6f23`](https://github.com/chickenstats/chickenstats/commit/801f6f23))

    The cli extra is gone. chickenstats login works on a plain install.

- **Bind cached API tokens to the host they were issued for** ([`1d29e748`](https://github.com/chickenstats/chickenstats/commit/1d29e748))

    A cached login is only sent to the host it was made on, and plain http is refused except for localhost.

- **Accept a Cloudflare service token as a complete credential** ([`f5e46925`](https://github.com/chickenstats/chickenstats/commit/f5e46925))

    A Cloudflare service token is the credential for pipelines. Set the client ID and secret, and no login is needed.

- **Lock ChickenUser.refresh so jobs can share a login** ([`0f78b81c`](https://github.com/chickenstats/chickenstats/commit/0f78b81c))

    ChickenUser.refresh raises AuthError rather than RuntimeError with no refresh token.

- **Honor the environment's proxy in the API client** ([`6a3fc9b7`](https://github.com/chickenstats/chickenstats/commit/6a3fc9b7))

    Requests go through a proxy set in the environment, and the user agent changes.

- **Remove ChickenStats.check_team_stats_ids and check_line_ids** ([`390231d7`](https://github.com/chickenstats/chickenstats/commit/390231d7))

    Use check_team_stats_game_ids and check_lines_game_ids instead. There is no replacement that returns row IDs.

- **Keep ChickenStats.access_token current after a token refresh** ([`dc1a7e9c`](https://github.com/chickenstats/chickenstats/commit/dc1a7e9c))

    ChickenStats.access_token now returns the token in use after a refresh instead of the one from login, and assigning to it raises AttributeError.

- **Make the ChickenStats and ChickenUser options keyword-only** ([`c4675ece`](https://github.com/chickenstats/chickenstats/commit/c4675ece))

    Pass the arguments of ChickenUser and ChickenStats by keyword, for example ChickenStats(username="me", password="secret"), and pass every filter of the ChickenStats download_* and check_* methods after the first by keyword, for example cs.download_pbp(2024, sessions="R", game_id=2024020001). A positional option raises TypeError.

## evolving_hockey

- **Credit events to the right player in prep_pbp** ([`1f90ab2c`](https://github.com/chickenstats/chickenstats/commit/1f90ab2c))

    event_player_1 and event_player_2 are no longer swapped, so goals, assists and every individual stat change, and S.J, N.J, T.B and L.A games stop splitting into two team codes. Stored results should be rebuilt.

- **Match prep_stats and prep_lines to chicken_nhl** ([`f2189290`](https://github.com/chickenstats/chickenstats/commit/f2189290))

    Name columns read NIKITA KUCHEROV, and eh_id collapses `..` and drops accents, so it joins prep_gar and prep_xgar, whose season is now an integer. level="season" returns one row per player with no session column, shootout rows move to shootout_attempt and shootout_goal, and prep_lines uses null instead of EMPTY.

- **Keep raw values for states without weights** ([`5a1501f5`](https://github.com/chickenstats/chickenstats/commit/5a1501f5))

    In prep_pbp, the adjusted columns for penalty shots and for states outside the weights table equal the raw values instead of 0, and change prep_stats, prep_lines and prep_team_stats through them.

- **Add zone starts to prep_lines, prep_team_stats** ([`3d385634`](https://github.com/chickenstats/chickenstats/commit/3d385634))

    prep_lines and prep_team_stats return four new columns, ozs, nzs, dzs and otf, and their schemas now require them. Both functions read players_on_pos, which every prep_pbp frame has.

- **Name missing input columns in line and team stats** ([`679207a9`](https://github.com/chickenstats/chickenstats/commit/679207a9))

    prep_lines and prep_team_stats raise InvalidInputError instead of polars.exceptions.ColumnNotFoundError when the play-by-play lacks players_on_pos, ozs, nzs, dzs or otf, and prep_team_stats also when it lacks event_team or opp_team.

- **Name missing input columns in prep_stats** ([`c52d2ebc`](https://github.com/chickenstats/chickenstats/commit/c52d2ebc))

    prep_ind, prep_oi and prep_stats raise InvalidInputError instead of polars.exceptions.ColumnNotFoundError when the play-by-play lacks a column they read: season, event_type, event_player_1 to event_player_3, event_on_1 to event_on_7 or opp_on_1 to opp_on_7, and for prep_stats also event_team, players_on, players_on_eh_id, players_on_pos, ozs, nzs, dzs or otf.

- **Make the prep_* function options keyword-only** ([`ccd66614`](https://github.com/chickenstats/chickenstats/commit/ccd66614))

    Pass the options of prep_pbp, prep_ind, prep_oi, prep_stats, prep_lines, prep_team_stats, prep_gar and prep_xgar in chickenstats.evolving_hockey by keyword, for example prep_stats(pbp, level="season") or prep_xgar(data, backend="pandas"). A positional option raises TypeError.

## Dependencies

- **Raise the dependency floors and cap each major version** ([`c08175e1`](https://github.com/chickenstats/chickenstats/commit/c08175e1))

    chickenstats now needs polars 1.38.1 or later and below 2, pandera 0.32.1 or later, and chickenstats-api 0.1.8 or later.

- **Raise typer to 0.16.0 so chickenstats --help works** ([`37df1504`](https://github.com/chickenstats/chickenstats/commit/37df1504))

    chickenstats needs typer 0.16.0 or later.
