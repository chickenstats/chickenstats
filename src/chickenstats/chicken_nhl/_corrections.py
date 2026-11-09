"""Corrections for known errors in the NHL API and HTML feeds.

Each function accepts a game ID and a raw event/player/shift dict, applies any
known corrections for that specific game, and returns the corrected dict unchanged
if no correction applies. Corrections are keyed by game ID and event index.

Known data issues that have no fix (e.g., missing events in the NHL API feed) are
documented as comments inside the relevant function.
"""

from collections.abc import Callable, Mapping


# A fix that reads another field of the event is a function; every other fix is a mapping of field values.
_BENCH: Mapping[str, object] = {"player_1": "BENCH", "player_1_api_id": None, "player_1_eh_id": "BENCH"}


def _swap_player_1_and_2(event: dict) -> None:
    event["player_1_api_id"], event["player_2_api_id"] = (event["player_2_api_id"], event["player_1_api_id"])


def _bench_with_player_1_as_player_2(event: dict) -> None:
    event["player_2_api_id"] = event["player_1_api_id"]
    event.update(_BENCH)


def _bench_with_player_1_serving(event: dict) -> None:
    event["player_3_api_id"] = event["player_1_api_id"]
    event["player_3_type"] = "SERVED BY"
    event.update(_BENCH)


def _player_1_serving_for_8473492(event: dict) -> None:
    event["player_3_api_id"] = event["player_1_api_id"]
    event["player_3_type"] = "SERVED BY"
    event["player_1_api_id"] = 8473492


def _drop_player_3(event: dict) -> None:
    del event["player_3_api_id"]
    del event["player_3_type"]


# game_id -> event_idx -> the field values to set, or a function that patches the event
_API_EVENTS_FIXES: dict[int, dict[int, Mapping[str, object] | Callable[[dict], None]]] = {
    2011020069: {660: {"player_1_api_id": 8473473}},
    2012020660: {377: _BENCH},
    2013020445: {617: _swap_player_1_and_2},
    2014020120: {720: _player_1_serving_for_8473492},
    2014020356: {
        599: {"period_seconds": 970, "game_seconds": 3370},
        603: {"period_seconds": 1002, "game_seconds": 3402},
    },
    2014020945: {585: {"period_seconds": 1069, "game_seconds": 3469}},
    2014021127: {
        754: {"period_seconds": 1124, "game_seconds": 3524},
        756: {"period_seconds": 1125, "game_seconds": 3525},
        755: {"period_seconds": 1127, "game_seconds": 3527},
    },
    2015020193: {389: {"player_1_api_id": 8475760}},
    2015020917: {162: _drop_player_3},
    2016020177: {494: {"period_seconds": 360, "game_seconds": 2760}},
    2016020256: {210: _drop_player_3},
    2016020625: {630: _bench_with_player_1_as_player_2},
    2016020963: {44: {"period_seconds": 40, "game_seconds": 40}},
    2017020209: {245: _BENCH},
    2017020796: {687: _bench_with_player_1_as_player_2},
    2017021161: {590: _bench_with_player_1_as_player_2},
    2018020009: {421: _bench_with_player_1_as_player_2},
    2018020363: {299: _bench_with_player_1_as_player_2},
    2018021087: {550: _bench_with_player_1_as_player_2},
    2019020179: {573: _bench_with_player_1_serving},
    2019020316: {428: {"player_2_api_id": 8477903, "player_2_type": "DRAWN BY"}},
    2020020456: {360: {"period_seconds": 1068, "game_seconds": 2268}},
    2020020846: {
        407: {"player_2_api_id": 8475799},
        409: {"player_2_api_id": 8479987},
        411: {"player_2_api_id": 8479987},
        413: {"player_2_api_id": 8475790},
        415: {"player_2_api_id": 8476988},
    },
    2020020860: {705: {"period_seconds": 270, "game_seconds": 3870}},
    2021020482: {250: {"player_1_api_id": 8477465}},
}


def api_events_fixes(game_id: int, event: dict) -> dict:
    # noinspection GrazieStyle
    """Fixes API event errors.

    Known errors that have no fix:

    2021020562 | CHL at 2898 game seconds is not in API events feed
    2021020767 | CHL at 3598 game seconds is not in API events feed
    """
    game_fixes = _API_EVENTS_FIXES.get(game_id)
    if game_fixes is None:
        return event

    fix = game_fixes.get(event["event_idx"])
    if isinstance(fix, Mapping):
        event.update(fix)
    elif fix is not None:
        fix(event)

    return event


def html_events_fixes(game_id: int, event: dict) -> dict:
    """Fix known errors (e.g., wrong team abbreviations) in raw HTML event feed.

    Known errors that have no fix:

    2015020150 | Jimmy Hayes has 5 shots on goal from 12:45 to 12:48 of the 3rd, two of them exact duplicates,
                 but the API agrees and its running count of BOS shots goes from 20 to 24, so the NHL counted them
    """
    # Hits whose report puts each player on the other's team, crediting a scratched player
    swapped_hits = {
        (2007020665, 224): "SJS #3 MURRAY HIT TOR #11 TLUSTY, OFF. ZONE",
        (2007020688, 67): "MIN #26 FOSTER HIT CGY #40 TANGUAY, OFF. ZONE",
    }
    if (game_id, event["event_idx"]) in swapped_hits:
        event["description"] = swapped_hits[(game_id, event["event_idx"])]

    if game_id == 2011020069 and event["event_idx"] == 312:
        event["description"] = event["description"].replace("BOS #", "BOS #17 LUCIC ")

    if game_id == 2011020553 and event["event_idx"] == 294:
        event["description"] = "FLA #21 BARCH (10 MIN)"

    if game_id == 2012020660:
        if event["event_idx"] == 150:
            event["description"] = (
                "NJD BENCH PS-HOOKING ON BREAKAWAY(0 MIN) NJD SERVED BY: #2 ZIDLICKY DRAWN BY: FLA #42 HOWDEN"
            )

    if game_id == 2012020018:
        bad_names = {"EDM #9": "VAN #9", "VAN #93": "EDM #93", "VAN #94": "EDM #94"}

        for bad_name, good_name in bad_names.items():
            event["description"] = event["description"].replace(bad_name, good_name)

    if game_id == 2013020971 and event["event_idx"] == 1:
        event["period"] = 1

        event["time"] = "0:0020:00"

    if game_id == 2014020120:
        if event["event_idx"] == 341:
            event["description"] = (
                "SJS TEAM PLAYER LEAVES BENCH - BENCH(2 MIN), OFF. ZONE SJS SERVED BY: #20 SCOTT DRAWN BY: "
                "ANA #47 LINDHOLM"
            )

    if game_id == 2014020600 and event["event_idx"] == 328:
        event["description"] = "CAR # BLOCKED BY BUF #6 WEBER, WRIST, DEF. ZONE"

    if game_id == 2014020672 and event["event_idx"] == 297:
        event["description"] = "NYR #22 HIT PIT #16 SUTTER, DEF. ZONE"

    if game_id == 2015020193 and event["event_idx"] == 196:
        event["description"] = "FLA #27 BJUGSTAD, WRIST, OFF. ZONE, 16 FT."

    if game_id == 2015020917 and event["event_idx"] == 76:
        event["description"] = "WSH #43 WILSON TRIPPING(2 MIN) OFF. ZONE DRAWN BY: MIN #46 SPURGEON"

    if game_id == 2016020256 and event["event_idx"] == 117:
        event["description"] = "WSH #14 WILLIAMS ROUGHING(2 MIN) NEU. ZONE DRAWN BY: DET #21 TATAR"

    if game_id == 2016020625 and event["event_idx"] == 311:
        event["description"] = "PIT HEAD COACH GAME MISCONDUCT(0 MIN) PIT SERVED BY: #61 OLEKSY, NEU. ZONE"

    if game_id == 2016021127:
        event["description"] = event["description"].replace(
            "BOS #55 ACCIARI ( MIN), DEF. ZONE", "BOS #55 ACCIARI MISCONDUCT (10 MIN), DEF. ZONE"
        )

    if game_id == 2017020463:
        event["time"] = event["time"].replace("-16:0-120:00", "2:022:58")

    if game_id == 2017020796 and event["event_idx"] == 338:
        event["description"] = "DET HEAD COACH GAME MISCONDUCT(0 MIN) DET SERVED BY: #3 JENSEN, NEU. ZONE"

    if game_id == 2018020009 and event["event_idx"] == 231:
        event["description"] = "CHI TEAM FACE-OFF VIOLATION(2 MIN) CHI SERVED BY: #12 DEBRINCAT"

    if game_id == 2017021161 and event["event_idx"] == 253:
        event["description"] = "NSH HEAD COACH GAME MISCONDUCT(0 MIN) NSH SERVED BY: #2 BITETTO, NEU. ZONE"

    if game_id == 2018020363 and event["event_idx"] == 156:
        event["description"] = "NJD TEAM TOO MANY MEN/ICE(2 MIN) NJD SERVED BY: #44 WOOD, OFF. ZONE"

    if game_id == 2018021087 and event["event_idx"] == 289:
        event["description"] = "TBL TEAM DELAY OF GAME(2 MIN) TBL SERVED BY: #10 MILLER, DEF. ZONE"

    if game_id == 2018021133:
        event["description"] = event["description"].replace("WSH TAKEAWAY - #71 CIRELLI", "TBL TAKEAWAY - #71 CIRELLI")

    if game_id == 2019020179 and event["event_idx"] == 259:
        event["description"] = "SJS HEAD COACH GAME MISCONDUCT (0 MIN), SERVED BY: #65 KARLSSON, DEF. ZONE"

    if game_id == 2019020316:
        if event["event_idx"] == 212:
            event["description"] = (
                "ANA #6 GUDBRANSON ROUGHING(2 MIN) SERVED BY: #24 ROWNEY, DEF. ZONE DRAWN BY: WSH #21 HATHAWAY"
            )

    if game_id == 2021020224 and event["event_idx"] == 230:
        event["description"] = event["description"].replace(
            " - MTL #60 BELZILE VS BOS #92 NOSEK", "MTL WON NEU. ZONE - MTL #60 BELZILE VS BOS #92 NOSEK"
        )

    # The report writes Aaron Ekblad's shot blocked by Brayden McNabb as a VGK miss with no shooter
    # The two spaces after BY are how the report's other blocks are written
    if game_id == 2022020673 and event["event_idx"] == 208:
        event["event"] = "BLOCK"
        event["description"] = "FLA #5 EKBLAD BLOCKED BY  VGK #3 MCNABB, SLAP, DEF. ZONE"

    if game_id == 2023020838:
        if event["event_idx"] == 216:
            event["description"] = "FLA #17 RODRIGUES HIGH-STICKING(2 MIN), NEU. ZONE DRAWN BY: BUF #72 THOMPSON"

    if game_id == 2023021279 and event["event_idx"] == 264:
        event["description"] = "PIT #10 O'CONNOR SLASHING(2 MIN), DEF. ZONE DRAWN BY: BOS #63 MARCHAND"

    return event


# HTML events left out, by game and event_idx
DROPPED_HTML_EVENTS: frozenset[tuple[int, int]] = frozenset(
    {
        # The report has a MISS with no shooter here, and the API has no event to match it
        (2022020194, 134)
    }
)

# Hits whose report leaves out the hitter's number, by game and event_idx, so the one player named was hit
HITS_WITHOUT_HITTER: frozenset[tuple[int, int]] = frozenset({(2016021070, 206)})


def html_rosters_fixes(game_id: int, player: dict) -> dict:
    """Fix known errors (e.g., scratches listed as active) in the raw HTML roster feed."""
    if game_id == 2019020665:
        scratches = ["ROSS JOHNSTON", "SEBASTIAN AHO", "CONNOR CARRICK", "JESPER BRATT", "JACK HUGHES"]

        if player["player_name"] in scratches:
            player["status"] = "SCRATCH"

    # Listed as scratches, but the shift and play-by-play reports put them on the ice
    if (game_id, player["player_name"]) in {
        (2008020160, "BRENT BURNS"),
        (2009020079, "DEREK BOOGAARD"),
        (2009020439, "MATT D'AGOSTINI"),
    }:
        player["status"] = "ACTIVE"

    return player


# Players who played but are missing from the API's rosterSpots, by game: team, venue, name, api_id, jersey, position
_MISSING_API_PLAYERS: dict[int, tuple[str, str, str, int, int, str]] = {
    2008020160: ("MIN", "AWAY", "BRENT BURNS", 8470613, 8, "D"),
    2009020079: ("MIN", "AWAY", "DEREK BOOGAARD", 8469647, 24, "L"),
    2009020439: ("MTL", "AWAY", "MATT D'AGOSTINI", 8471851, 36, "R"),
    2013020971: ("CBJ", "AWAY", "NATHAN HORTON", 8470596, 8, "R"),
}


def api_rosters_fixes(season: int, session: str, game_id: int) -> dict:
    """Fix known errors (e.g., missing from rosterSpots) in the raw API roster feed."""
    if game_id not in _MISSING_API_PLAYERS:
        return {}

    team, venue, player_name, api_id, jersey, position = _MISSING_API_PLAYERS[game_id]
    first_name, last_name = player_name.split(" ", 1)

    return {
        "season": season,
        "session": session,
        "game_id": game_id,
        "team": team,
        "team_venue": venue,
        "player_name": player_name,
        "first_name": first_name,
        "last_name": last_name,
        "api_id": api_id,
        "eh_id": f"{first_name}.{last_name}",
        "team_jersey": f"{team}{jersey}",
        "jersey": jersey,
        "position": position,
        "headshot_url": None,
    }


# Official games whose PL report has no GEND row, though the report is complete
GAMES_WITHOUT_GEND: frozenset[int] = frozenset(
    {
        2007020066,
        2009021157,
        2015020410,
        2017020008,
        2020020526,
        2020020529,
        2020020810,
        2020020824,
        2020020833,
        2020020858,
        2020020860,
        2020020865,
    }
)

# Players the API and HTML rosters cannot be matched on, by game and team jersey
_ROSTER_FIXES: dict[tuple[int, str], dict] = {
    (2015020508, "ANA5"): {
        "api_id": 8473560,
        "headshot_url": "https://assets.nhle.com/mugs/nhl/20152016/ANA/8473560.png",
    },
    (2015021197, "LAK13"): {
        "api_id": 8475160,
        "headshot_url": "https://assets.nhle.com/mugs/nhl/20152016/LAK/8475160.png",
    },
}


def rosters_fixes(game_id: int, player_info: dict) -> dict:
    """Fix known errors (e.g., cannot match API and HTML players) when combining rosters."""
    player_info.update(_ROSTER_FIXES.get((game_id, player_info["team_jersey"]), {}))

    return player_info


# Overtime shifts missing from the HTML report, by game: each group's start_time, end_time, duration,
# shift_start and shift_end, then the team jersey and shift number of each player who had that shift
_MISSING_OVERTIME_SHIFTS: dict[int, tuple[tuple[tuple[str, str, str, str, str], dict[str, int]], ...]] = {
    2019020331: ((("0:00", "0:24", "0:24", "0:00 / 5:00", "0:24 / 4:36"), {"OTT44": 29}),),
    2020020860: (
        (("0:00", "4:30", "4:30", "0:00 / 5:00", "4:30 / 0:30"), {"DAL29": 5, "CHI60": 4}),
        (("3:47", "4:30", "00:43", "3:47 / 1:13", "4:30 / 0:30"), {"DAL14": 27, "DAL21": 22, "DAL3": 28, "CHI5": 27}),
        (("3:51", "4:30", "00:39", "3:51 / 1:09", "4:30 / 0:30"), {"CHI88": 26}),
        (("4:14", "4:30", "00:16", "4:14 / 0:46", "4:30 / 0:30"), {"CHI12": 26}),
    ),
    2020020865: (
        (("1:53", "2:46", "0:53", "1:53 / 3:07", "2:46 / 2:14"), {"MIN36": 17, "MIN24": 23, "MIN49": 15}),
        (("2:02", "2:46", "0:44", "2:02 / 0:58", "2:46 / 2:14"), {"ANA42": 27}),
        (("2:45", "2:46", "0:01", "2:45 / 2:15", "2:46 / 2:14"), {"ANA43": 22}),
        (("2:41", "2:46", "0:04", "2:41 / 2:19", "2:46 / 2:14"), {"ANA67": 21}),
    ),
}


def html_shifts_fixes(game_id: int, season: int, session: str, shifts: list, actives: dict, scratches: dict) -> list:
    """Fix known errors (e.g., missing shifts) in the raw HTML shifts feed.

    Known errors that have no fix, so these official games fail with ReportUnavailableError:

    2007020011 | TH and TV reports have no shifts
    2007021119 | PL report stops during the shootout, with no period end
    2007021178 | PL report stops at 10:32 of the 2nd, and TH and TV stop near it
    2008020259 | PL report has no events, and TH and TV have no shifts
    2008020409 | PL report has no events, and TH and TV have no shifts
    2008021077 | PL report has no events, and TH and TV have no shifts
    2008030311 | TH and TV reports have no shifts
    2009020081 | PL report stops at the opening faceoff, and TH and TV have no shifts
    2009020658 | TH and TV reports have no shifts
    2009020885 | TH and TV reports have no shifts

    Known errors that have no fix, so the games are kept with too many skaters on the ice:

    2011020696 | Shifts that overlap by 4 seconds put 6 skaters on the ice, for WSH from 12:30 to 12:34 of the 2nd
                 (Semin with Wideman and Alzner) and once for CAR in the 1st, and no report says which shift is wrong
    2020020150 | NYI have 6 skaters from 2:52 to 3:12 of the 2nd with no penalty, because Beauvillier's shift runs
                 from 1:31 to 3:45 in both the TH report and the shiftcharts API, so neither shows when he left
    """
    # The TV report lists one stray shift for COL's Ryan Smyth, numbered 1, under MIN. His TH shifts run 1 to 28
    if game_id == 2007030174:
        shifts = [shift for shift in shifts if shift["team_jersey"] != "MIN94"]

    for times, players in _MISSING_OVERTIME_SHIFTS.get(game_id, ()):
        start_time, end_time, duration, shift_start, shift_end = times
        for new_player, shift_count in players.items():
            player_info = actives.get(new_player) or scratches.get(new_player)
            if not player_info:
                continue
            shifts.append(
                {
                    "shift_count": shift_count,
                    "period": 4,
                    "shift_start": shift_start,
                    "shift_end": shift_end,
                    "duration": duration,
                    "season": season,
                    "session": session,
                    "game_id": game_id,
                    "team_name": player_info.get("team_name"),
                    "team": player_info.get("team"),
                    "team_venue": player_info.get("team_venue"),
                    "player_name": player_info.get("player_name"),
                    "team_jersey": player_info.get("team_jersey"),
                    "jersey": player_info.get("jersey"),
                    "start_time": start_time,
                    "end_time": end_time,
                }
            )

    return shifts
