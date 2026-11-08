"""Corrections for known errors in the NHL API and HTML feeds.

Each function accepts a game ID and a raw event/player/shift dict, applies any
known corrections for that specific game, and returns the corrected dict unchanged
if no correction applies. Corrections are keyed by game ID and event index.

Known data issues that have no fix (e.g., missing events in the NHL API feed) are
documented as comments inside the relevant function.
"""


def api_events_fixes(game_id: int, event: dict) -> dict:
    # noinspection GrazieStyle
    """Fixes API event errors.

    Known errors that have no fix:

    2021020562 | CHL at 2898 game seconds is not in API events feed
    2021020767 | CHL at 3598 game seconds is not in API events feed
    2021020882 | SHOT at 249, 1785, & 1786 game seconds are not in API events feed
    2021020894 | SHOT by Boldy at 3507 game seconds is not in API events feed
    """
    if game_id == 2011020069 and event["event_idx"] == 660:
        event["player_1_api_id"] = 8473473

    if game_id == 2012020660 and event["event_idx"] == 377:
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2013020445 and event["event_idx"] == 617:
        event["player_1_api_id"], event["player_2_api_id"] = (event["player_2_api_id"], event["player_1_api_id"])

    if game_id == 2014020120:
        if event["event_idx"] == 661:
            event["player_2_api_id"] = 8476854
            event["player_2_type"] = "DRAWN BY"

        if event["event_idx"] == 720:
            event["player_3_api_id"] = event["player_1_api_id"]
            event["player_3_type"] = "SERVED BY"

            event["player_1_api_id"] = 8473492

    if game_id == 2014020356:
        if event["event_idx"] == 599:
            event["period_seconds"] = 970
            event["game_seconds"] = 3370

        if event["event_idx"] == 603:
            event["period_seconds"] = 1002
            event["game_seconds"] = 3402

    if game_id == 2014020945 and event["event_idx"] == 585:
        event["period_seconds"] = 1069
        event["game_seconds"] = 3469

    if game_id == 2014021127:
        if event["event_idx"] == 754:
            event["period_seconds"] = 1124
            event["game_seconds"] = 3524

        if event["event_idx"] == 756:
            event["period_seconds"] = 1125
            event["game_seconds"] = 3525

        if event["event_idx"] == 755:
            event["period_seconds"] = 1127
            event["game_seconds"] = 3527

    if game_id == 2015020193 and event["event_idx"] == 389:
        event["player_1_api_id"] = 8475760

    if game_id == 2015020917 and event["event_idx"] == 162:
        del event["player_3_api_id"]
        del event["player_3_type"]

    if game_id == 2016020177 and event["event_idx"] == 494:
        event["period_seconds"] = 360
        event["game_seconds"] = 2760

    if game_id == 2016020256 and event["event_idx"] == 210:
        del event["player_3_api_id"]
        del event["player_3_type"]

    if game_id == 2016020625 and event["event_idx"] == 630:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2016020963 and event["event_idx"] == 44:
        event["period_seconds"] = 40
        event["game_seconds"] = 40

    if game_id == 2017020209 and event["event_idx"] == 245:
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2017020796 and event["event_idx"] == 687:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2017021161 and event["event_idx"] == 590:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2018020009 and event["event_idx"] == 421:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2018020363 and event["event_idx"] == 299:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2018021087 and event["event_idx"] == 550:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2019020179 and event["event_idx"] == 573:
        event["player_3_api_id"] = event["player_1_api_id"]
        event["player_3_type"] = "SERVED BY"

        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2019020316 and event["event_idx"] == 428:
        event["player_2_api_id"] = 8477903
        event["player_2_type"] = "DRAWN BY"

    if game_id == 2020020456 and event["event_idx"] == 360:
        event["period_seconds"] = 1068
        event["game_seconds"] = 2268

    if game_id == 2020020846:
        if event["event_idx"] == 407:
            event["player_2_api_id"] = 8475799

        if event["event_idx"] == 409:
            event["player_2_api_id"] = 8479987

        if event["event_idx"] == 411:
            event["player_2_api_id"] = 8479987

        if event["event_idx"] == 413:
            event["player_2_api_id"] = 8475790

        if event["event_idx"] == 415:
            event["player_2_api_id"] = 8476988

    if game_id == 2020020860 and event["event_idx"] == 705:
        event["period_seconds"] = 270
        event["game_seconds"] = 3870

    if game_id == 2021020482 and event["event_idx"] == 250:
        event["player_1_api_id"] = 8477465

    return event


def html_events_fixes(game_id: int, event: dict) -> dict:
    """Fix known errors (e.g., wrong team abbreviations) in raw HTML event feed."""
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

    if game_id == 2016021070 and event["event_idx"] == 206:
        event["description"] = "TOR # HIT BOS # , DEF. ZONE"

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
        "headshot_url": "",
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
