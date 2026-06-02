"""Hand-curated NHL API and HTML data corrections.

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
    if game_id == 2010021176 and event["event_idx"] == 213:
        event["player_3_api_id"] = 8467396
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2011020069 and event["event_idx"] == 660:
        event["player_1_api_id"] = 8473473

    if game_id == 2012020095 and event["event_idx"] == 139:
        event["player_3_api_id"] = 8468483
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2012020341 and event["event_idx"] == 656:
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2012020627 and event["event_idx"] == 621:
        event["player_3_api_id"] = 8462129
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2012020660 and event["event_idx"] == 377:
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2012020671 and event["event_idx"] == 680:
        event["player_2_api_id"] = 8470192
        event["player_2_type"] = "SERVED BY"

    if game_id == 2012030224 and event["event_idx"] == 594:
        event["player_3_api_id"] = 8475184
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2013020305 and event["event_idx"] == 392:
        event["player_3_api_id"] = 8475184
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2013030142 and event["event_idx"] == 727:
        event["player_3_api_id"] = 8470601
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2013030155 and event["event_idx"] == 309:
        event["player_3_api_id"] = 8476463
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2013020445 and event["event_idx"] == 617:
        event["player_1_api_id"], event["player_2_api_id"] = (event["player_2_api_id"], event["player_1_api_id"])

    if game_id == 2014020120:
        if event["event_idx"] == 661:
            event["player_3_api_id"] = 8476854
            event["player_3_type"] = "DRAWN BY"

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

    if game_id == 2014020417 and event["event_idx"] == 280:
        event["player_3_api_id"] = 8468501
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2014020506:
        if event["event_idx"] == 377:
            event["player_3_api_id"] = 8468208
            event["player_3_type"] = "DRAWN BY"

        if event["event_idx"] == 584:
            event["player_3_api_id"] = 8474613
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2014020939 and event["event_idx"] == 287:
        event["player_3_api_id"] = 8475218
        event["player_3_type"] = "DRAWN BY"

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

    if game_id == 2014021128 and event["event_idx"] == 280:
        event["player_3_api_id"] = 8471426
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2014021203 and event["event_idx"] == 344:
        event["player_3_api_id"] = 8466378
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2014030311 and event["event_idx"] == 346:
        event["player_3_api_id"] = 8474613
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2014030315 and event["event_idx"] == 69:
        event["player_3_api_id"] = 8474151
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2015020193 and event["event_idx"] == 389:
        event["player_1_api_id"] = 8475760

    if game_id == 2015020401 and event["event_idx"] == 167:
        event["player_3_api_id"] = 8470854
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2015020839 and event["event_idx"] == 417:
        event["player_3_api_id"] = 8476393
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2015020917 and event["event_idx"] == 162:
        del event["player_3_api_id"]
        del event["player_3_type"]

    if game_id == 2015021092 and event["event_idx"] == 199:
        event["player_3_api_id"] = 8474884
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2016020049 and event["event_idx"] == 347:
        event["player_3_api_id"] = 8475692
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2016020177 and event["event_idx"] == 494:
        event["period_seconds"] = 360
        event["game_seconds"] = 2760

    if game_id == 2016020256 and event["event_idx"] == 210:
        del event["player_3_api_id"]
        del event["player_3_type"]

    if game_id == 2016020326 and event["event_idx"] == 175:
        event["player_3_api_id"] = 8475855
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2016020433:
        if event["event_idx"] == 366:
            event["player_3_api_id"] = 8471686
            event["player_3_type"] = "DRAWN BY"

        # if event["event_idx"] == 364:
        #     del event["player_3_api_id"]
        #     del event["player_3_type"]

    if game_id == 2016020519 and event["event_idx"] == 335:
        event["player_3_api_id"] = 8471676
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2016020625 and event["event_idx"] == 630:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2016020883 and event["event_idx"] == 385:
        event["player_3_api_id"] = 8469521
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2016020963 and event["event_idx"] == 44:
        event["period_seconds"] = 40
        event["game_seconds"] = 40

    if game_id == 2016021111 and event["event_idx"] == 183:
        event["player_3_api_id"] = 8473504
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2016021165 and event["event_idx"] == 85:
        event["player_1_api_id"], event["player_2_api_id"] = (event["player_2_api_id"], event["player_1_api_id"])

    if game_id == 2016030216 and event["event_idx"] == 567:
        event["player_3_api_id"] = 8474151
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020033:
        if event["event_idx"] == 390:
            event["player_3_api_id"] = 8477964
            event["player_3_type"] = "DRAWN BY"

        if event["event_idx"] == 585:
            event["player_3_api_id"] = 8476892
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020096 and event["event_idx"] == 727:
        event["player_3_api_id"] = 8474066
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020209 and event["event_idx"] == 245:
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2017020233 and event["event_idx"] == 375:
        event["player_3_api_id"] = 8470638
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020548 and event["event_idx"] == 726:
        event["player_3_api_id"] = 8468493
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020601 and event["event_idx"] == 319:
        event["player_3_api_id"] = 8473449
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020615 and event["event_idx"] == 626:
        event["player_3_api_id"] = 8473546
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020796 and event["event_idx"] == 687:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2017020835 and event["event_idx"] == 560:
        event["player_3_api_id"] = 8477215
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020836 and event["event_idx"] == 273:
        event["player_3_api_id"] = 8476346
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2017021136:
        if event["event_idx"] == 193:
            event["player_3_api_id"] = 8479206
            event["player_3_type"] = "DRAWN BY"

        if event["event_idx"] == 262:
            event["player_3_api_id"] = 8475314
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017021161 and event["event_idx"] == 590:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2018020006 and event["event_idx"] == 683:
        event["player_3_api_id"] = 8475793
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020009 and event["event_idx"] == 421:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2018020049 and event["event_idx"] == 155:
        event["player_3_api_id"] = 8479353
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020115 and event["event_idx"] == 248:
        event["player_3_api_id"] = 8475692
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020122 and event["event_idx"] == 235:
        event["player_3_api_id"] = 8477996
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020153 and event["event_idx"] == 212:
        event["player_3_api_id"] = 8478458
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020211 and event["event_idx"] == 661:
        event["player_3_api_id"] = 8471217
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020309 and event["event_idx"] == 76:
        event["player_3_api_id"] = 8476918
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020363 and event["event_idx"] == 299:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2018020519 and event["event_idx"] == 417:
        event["player_3_api_id"] = 8477941
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020561 and event["event_idx"] == 500:
        event["player_3_api_id"] = 8474190
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020752 and event["event_idx"] == 41:
        event["player_3_api_id"] = 8476917
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020794 and event["event_idx"] == 182:
        event["player_3_api_id"] = 8470187
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020795 and event["event_idx"] == 354:
        event["player_3_api_id"] = 8476918
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020841 and event["event_idx"] == 227:
        event["player_3_api_id"] = 8476455
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020969 and event["event_idx"] == 575:
        event["player_3_api_id"] = 8474150
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018021087 and event["event_idx"] == 550:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2018021124 and event["event_idx"] == 237:
        event["player_3_api_id"] = 8479353
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2018021171 and event["event_idx"] == 551:
        event["player_3_api_id"] = 8471887
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2019020006 and event["event_idx"] == 288:
        event["player_3_api_id"] = 8478550
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2019020136 and event["event_idx"] == 424:
        event["player_3_api_id"] = 8478550
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2019020147 and event["event_idx"] == 28:
        event["player_3_api_id"] = 8478550
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2019020179 and event["event_idx"] == 573:
        event["player_2_api_id"] = event["player_1_api_id"]
        event["player_2_type"] = "SERVED BY"

        event["player_1"] = "BENCH"
        event["player_1_api_id"] = None
        event["player_1_eh_id"] = "BENCH"

    if game_id == 2019020239 and event["event_idx"] == 543:
        event["player_3_api_id"] = 8478463
        event["player_3_type"] = "DRAWN BY"

    if game_id == 2019020316 and event["event_idx"] == 428:
        event["player_3_api_id"] = event["player_2_api_id"]
        event["player_3_type"] = "SERVED BY"

        event["player_2_api_id"] = 8477903
        event["player_2_type"] = "DRAWN BY"

    if game_id == 2019020682 and event["event_idx"] == 382:
        event["player_3_api_id"] = 8478550
        event["player_3_type"] = "DRAWN BY"

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
    """Patch known data errors in a raw HTML event record.

    Corrects description strings and clock values for a small set of games
    where the NHL HTML report contains malformed or missing data (wrong team
    abbreviations, broken time strings, missing penalty details, etc.).
    """
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

    if game_id == 2013020083:
        event["time"] = event["time"].replace("-16:0-120:00", "5:000:00")

    if game_id == 2013020274:
        event["time"] = event["time"].replace("-16:0-120:00", "5:000:00")

    if game_id == 2013020644:
        event["time"] = event["time"].replace("-16:0-120:00", "5:000:00")

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

    if game_id == 2014021118:
        event["time"] = event["time"].replace("-16:0-120:00", "5:000:00")

    if game_id == 2015020193 and event["event_idx"] == 196:
        event["description"] = "FLA #27 BJUGSTAD, WRIST, OFF. ZONE, 16 FT."

    if game_id == 2015020904:
        event["time"] = event["time"].replace("-16:0-120:00", "5:000:00")

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

    if game_id == 2018020989:
        event["time"] = event["time"].replace("-16:0-120:00", "5:000:00")

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

    if game_id == 2021020224:
        event["description"] = event["description"].replace(
            " - MTL #60 BELZILE VS BOS #92 NOSEK", "MTL WON NEU. ZONE - MTL #60 BELZILE VS BOS #92 NOSEK"
        )

    if game_id == 2023020838:
        if event["event_idx"] == 216:
            event["description"] = "FLA #17 RODRIGUES HIGH-STICKING(2 MIN), NEU. ZONE DRAWN BY: BUF #72 THOMPSON"

    if game_id == 2023021279 and event["event_idx"] == 264:
        event["description"] = "PIT #10 O'CONNOR SLASHING(2 MIN), DEF. ZONE DRAWN BY: BOS #63 MARCHAND"

    return event


def html_rosters_fixes(game_id: int, player: dict) -> dict:
    """Patch known data errors in a raw HTML roster player record.

    Corrects player status fields for a small set of games where the NHL HTML
    roster report misclassifies players (e.g., scratches listed as active).
    """
    if game_id == 2019020665:
        scratches = ["ROSS JOHNSTON", "SEBASTIAN AHO", "CONNOR CARRICK", "JESPER BRATT", "JACK HUGHES"]

        if player["player_name"] in scratches:
            player["status"] = "SCRATCH"

    return player


def api_rosters_fixes(season: int, session: str, game_id: int) -> dict:
    """Return a missing player record for games where the NHL API omits a roster entry.

    The NHL API occasionally drops a player from ``rosterSpots`` entirely. This
    function returns a fully-formed player dict for such cases, or an empty dict
    if no fix is needed for the given ``game_id``.
    """
    new_player = {}

    if game_id == 2013020971:
        new_player = {
            "season": season,
            "session": session,
            "game_id": game_id,
            "team": "CBJ",
            "team_venue": "AWAY",
            "player_name": "NATHAN HORTON",
            "first_name": "NATHAN",
            "last_name": "HORTON",
            "api_id": 8470596,
            "eh_id": "NATHAN.HORTON",
            "team_jersey": "CBJ8",
            "jersey": 8,
            "position": "R",
            "headshot_url": "",
        }

    return new_player


def rosters_fixes(game_id: int, player_info: dict) -> dict:
    """Patch known data errors in a combined roster player record.

    Fills in missing ``api_id`` and ``headshot_url`` values for a small set of
    games where the API and HTML rosters cannot be automatically matched, leaving
    those fields blank after ``_combine_rosters``.
    """
    if game_id == 2015020508 and player_info["team_jersey"] == "ANA5":
        new_values = {"api_id": 8473560, "headshot_url": "https://assets.nhle.com/mugs/nhl/20152016/ANA/8473560.png"}

        player_info.update(new_values)

    if game_id == 2015021197 and player_info["team_jersey"] == "LAK13":
        new_values = {"api_id": 8475160, "headshot_url": "https://assets.nhle.com/mugs/nhl/20152016/LAK/8475160.png"}

        player_info.update(new_values)

    return player_info


def html_shifts_fixes(game_id: int, season: int, session: str, shifts: list, actives: dict, scratches: dict) -> list:
    """Adds missing shift records for known data gaps in the HTML shifts feed."""
    if game_id == 2020020860:
        new_shifts_data = {
            "DAL29": 5,
            "CHI60": 4,
            "DAL14": 27,
            "DAL21": 22,
            "DAL3": 28,
            "CHI5": 27,
            "CHI88": 26,
            "CHI12": 26,
        }
        for new_player, shift_count in new_shifts_data.items():
            player_info = actives.get(new_player) or scratches.get(new_player)
            if not player_info:
                continue
            start_time, end_time, duration, shift_start, shift_end = (
                ("0:00", "4:30", "4:30", "0:00 / 5:00", "4:30 / 0:30")
                if new_player in ["DAL29", "CHI60"]
                else ("3:47", "4:30", "00:43", "3:47 / 1:13", "4:30 / 0:30")
                if new_player in ["DAL14", "DAL21", "DAL3", "CHI5"]
                else ("3:51", "4:30", "00:39", "3:51 / 1:09", "4:30 / 0:30")
                if new_player == "CHI88"
                else ("4:14", "4:30", "00:16", "4:14 / 0:46", "4:30 / 0:30")
            )
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

    if game_id == 2020020865:
        new_shifts_data = {"MIN36": 17, "MIN24": 23, "MIN49": 15, "ANA42": 27, "ANA43": 22, "ANA67": 21}
        for new_player, shift_count in new_shifts_data.items():
            player_info = actives.get(new_player) or scratches.get(new_player)
            if not player_info:
                continue
            start_time, end_time, duration, shift_start, shift_end = (
                ("1:53", "2:46", "0:53", "1:53 / 3:07", "2:46 / 2:14")
                if new_player in ["MIN36", "MIN24", "MIN49"]
                else ("2:02", "2:46", "0:44", "2:02 / 0:58", "2:46 / 2:14")
                if new_player == "ANA42"
                else ("2:41", "2:46", "0:04", "2:41 / 2:19", "2:46 / 2:14")
                if new_player == "ANA67"
                else ("2:45", "2:46", "0:01", "2:45 / 2:15", "2:46 / 2:14")
            )
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

    if game_id == 2019020331:
        new_shifts_data = {"OTT44": 29}
        for new_player, shift_count in new_shifts_data.items():
            player_info = actives.get(new_player) or scratches.get(new_player)
            if not player_info:
                continue
            start_time, end_time, duration, shift_start, shift_end = (
                "0:00",
                "0:24",
                "0:24",
                "0:00 / 5:00",
                "0:24 / 4:36",
            )
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


def individual_shifts_fixes(game_id: int, player_name: str, shift_dict: dict) -> dict:
    """Patch known data errors in a single raw shift record.

    Corrects malformed field values (e.g., non-breaking-space period strings,
    wrong shift boundaries) for a small set of games where the NHL HTML shifts
    report contains bad data for specific players.
    """
    if game_id == 2025020551:
        if player_name == "SAM LAFFERTY" and str(shift_dict["period"]) == "\xa0":
            shift_dict["shift_count"] = "8"
            shift_dict["period"] = "1"
            shift_dict["shift_start"] = "16:46 / 3:16"
            shift_dict["shift_end"] = "17:45 / 2:15"

    return shift_dict
