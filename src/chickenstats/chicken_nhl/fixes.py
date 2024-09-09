def api_events_fixes(game_id: int, event: dict) -> dict:
    """Fixes API event errors..

    Known errors that have no fix:

    2021020562 | CHL at 2898 game seconds is not in API events feed
    2021020767 | CHL at 3598 game seconds is not in API events feed
    2021020882 | SHOT at 249, 1785, & 1786 game seconds are not in API events feed
    2021020894 | SHOT by Boldy at 3507 game seconds is not in API events feed
    """
    if game_id == 2010021176:
        if event["event_idx"] == 213:
            event["player_3_api_id"] = 8467396
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2011020069:
        if event["event_idx"] == 660:
            event["player_1_api_id"] = 8473473

    if game_id == 2012020095:
        if event["event_idx"] == 139:
            event["player_3_api_id"] = 8468483
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2012020341:
        if event["event_idx"] == 656:
            event["player_1"] = "BENCH"
            event["player_1_api_id"] = "BENCH"
            event["player_1_eh_id"] = "BENCH"

    if game_id == 2012020627:
        if event["event_idx"] == 621:
            event["player_3_api_id"] = 8462129
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2012020660:
        if event["event_idx"] == 377:
            event["player_1"] = "BENCH"
            event["player_1_api_id"] = "BENCH"
            event["player_1_eh_id"] = "BENCH"

    if game_id == 2012020671:
        if event["event_idx"] == 680:
            event["player_2_api_id"] = 8470192
            event["player_2_type"] = "SERVED BY"

    if game_id == 2012030224:
        if event["event_idx"] == 594:
            event["player_3_api_id"] = 8475184
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2013020305:
        if event["event_idx"] == 392:
            event["player_3_api_id"] = 8475184
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2013030142:
        if event["event_idx"] == 727:
            event["player_3_api_id"] = 8470601
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2013030155:
        if event["event_idx"] == 309:
            event["player_3_api_id"] = 8476463
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2013020445:
        if event["event_idx"] == 617:
            event["player_1_api_id"], event["player_2_api_id"] = (
                event["player_2_api_id"],
                event["player_1_api_id"],
            )

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

    if game_id == 2014020417:
        if event["event_idx"] == 280:
            event["player_3_api_id"] = 8468501
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2014020506:
        if event["event_idx"] == 377:
            event["player_3_api_id"] = 8468208
            event["player_3_type"] = "DRAWN BY"

        if event["event_idx"] == 584:
            event["player_3_api_id"] = 8474613
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2014020939:
        if event["event_idx"] == 287:
            event["player_3_api_id"] = 8475218
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2014020945:
        if event["event_idx"] == 585:
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

    if game_id == 2014021128:
        if event["event_idx"] == 280:
            event["player_3_api_id"] = 8471426
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2014021203:
        if event["event_idx"] == 344:
            event["player_3_api_id"] = 8466378
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2014030311:
        if event["event_idx"] == 346:
            event["player_3_api_id"] = 8474613
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2014030315:
        if event["event_idx"] == 69:
            event["player_3_api_id"] = 8474151
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2015020193:
        if event["event_idx"] == 389:
            event["player_1_api_id"] = 8475760

    if game_id == 2015020401:
        if event["event_idx"] == 167:
            event["player_3_api_id"] = 8470854
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2015020839:
        if event["event_idx"] == 417:
            event["player_3_api_id"] = 8476393
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2015020917:
        if event["event_idx"] == 162:
            del event["player_3_api_id"]
            del event["player_3_type"]

    if game_id == 2015021092:
        if event["event_idx"] == 199:
            event["player_3_api_id"] = 8474884
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2016020049:
        if event["event_idx"] == 347:
            event["player_3_api_id"] = 8475692
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2016020177:
        if event["event_idx"] == 494:
            event["period_seconds"] = 360
            event["game_seconds"] = 2760

    if game_id == 2016020256:
        if event["event_idx"] == 210:
            del event["player_3_api_id"]
            del event["player_3_type"]

    if game_id == 2016020326:
        if event["event_idx"] == 175:
            event["player_3_api_id"] = 8475855
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2016020433:
        if event["event_idx"] == 366:
            event["player_3_api_id"] = 8471686
            event["player_3_type"] = "DRAWN BY"

        if event["event_idx"] == 364:
            del event["player_3_api_id"]
            del event["player_3_type"]

    if game_id == 2016020519:
        if event["event_idx"] == 335:
            event["player_3_api_id"] = 8471676
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2016020625:
        if event["event_idx"] == 630:
            event["player_2_api_id"] = event["player_1_api_id"]
            event["player_1"] = "BENCH"
            event["player_1_api_id"] = "BENCH"
            event["player_1_eh_id"] = "BENCH"

    if game_id == 2016020883:
        if event["event_idx"] == 385:
            event["player_3_api_id"] = 8469521
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2016020963:
        if event["event_idx"] == 44:
            event["period_seconds"] = 40
            event["game_seconds"] = 40

    if game_id == 2016021111:
        if event["event_idx"] == 183:
            event["player_3_api_id"] = 8473504
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2016021165:
        if event["event_idx"] == 85:
            event["player_1_api_id"], event["player_2_api_id"] = (
                event["player_2_api_id"],
                event["player_1_api_id"],
            )

    if game_id == 2016030216:
        if event["event_idx"] == 567:
            event["player_3_api_id"] = 8474151
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020033:
        if event["event_idx"] == 390:
            event["player_3_api_id"] = 8477964
            event["player_3_type"] = "DRAWN BY"

        if event["event_idx"] == 585:
            event["player_3_api_id"] = 8476892
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020096:
        if event["event_idx"] == 727:
            event["player_3_api_id"] = 8474066
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020209:
        if event["event_idx"] == 245:
            event["player_1"] = "BENCH"
            event["player_1_api_id"] = "BENCH"
            event["player_1_eh_id"] = "BENCH"

    if game_id == 2017020233:
        if event["event_idx"] == 375:
            event["player_3_api_id"] = 8470638
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020548:
        if event["event_idx"] == 726:
            event["player_3_api_id"] = 8468493
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020601:
        if event["event_idx"] == 319:
            event["player_3_api_id"] = 8473449
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020615:
        if event["event_idx"] == 626:
            event["player_3_api_id"] = 8473546
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020796:
        if event["event_idx"] == 687:
            event["player_2_api_id"] = event["player_1_api_id"]
            event["player_1"] = "BENCH"
            event["player_1_api_id"] = "BENCH"
            event["player_1_eh_id"] = "BENCH"

    if game_id == 2017020835:
        if event["event_idx"] == 560:
            event["player_3_api_id"] = 8477215
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017020836:
        if event["event_idx"] == 273:
            event["player_3_api_id"] = 8476346
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017021136:
        if event["event_idx"] == 193:
            event["player_3_api_id"] = 8479206
            event["player_3_type"] = "DRAWN BY"

        if event["event_idx"] == 262:
            event["player_3_api_id"] = 8475314
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2017021161:
        if event["event_idx"] == 590:
            event["player_2_api_id"] = event["player_1_api_id"]
            event["player_1"] = "BENCH"
            event["player_1_api_id"] = "BENCH"
            event["player_1_eh_id"] = "BENCH"

    if game_id == 2018020006:
        if event["event_idx"] == 683:
            event["player_3_api_id"] = 8475793
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020009:
        if event["event_idx"] == 421:
            event["player_2_api_id"] = event["player_1_api_id"]
            event["player_1"] = "BENCH"
            event["player_1_api_id"] = "BENCH"
            event["player_1_eh_id"] = "BENCH"

    if game_id == 2018020049:
        if event["event_idx"] == 155:
            event["player_3_api_id"] = 8479353
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020115:
        if event["event_idx"] == 248:
            event["player_3_api_id"] = 8475692
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020122:
        if event["event_idx"] == 235:
            event["player_3_api_id"] = 8477996
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020153:
        if event["event_idx"] == 212:
            event["player_3_api_id"] = 8478458
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020211:
        if event["event_idx"] == 661:
            event["player_3_api_id"] = 8471217
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020309:
        if event["event_idx"] == 76:
            event["player_3_api_id"] = 8476918
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020363:
        if event["event_idx"] == 299:
            event["player_2_api_id"] = event["player_1_api_id"]
            event["player_1"] = "BENCH"
            event["player_1_api_id"] = "BENCH"
            event["player_1_eh_id"] = "BENCH"

    if game_id == 2018020519:
        if event["event_idx"] == 417:
            event["player_3_api_id"] = 8477941
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020561:
        if event["event_idx"] == 500:
            event["player_3_api_id"] = 8474190
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020752:
        if event["event_idx"] == 41:
            event["player_3_api_id"] = 8476917
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020794:
        if event["event_idx"] == 182:
            event["player_3_api_id"] = 8470187
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020795:
        if event["event_idx"] == 354:
            event["player_3_api_id"] = 8476918
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020841:
        if event["event_idx"] == 227:
            event["player_3_api_id"] = 8476455
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018020969:
        if event["event_idx"] == 575:
            event["player_3_api_id"] = 8474150
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018021087:
        if event["event_idx"] == 550:
            event["player_2_api_id"] = event["player_1_api_id"]
            event["player_1"] = "BENCH"
            event["player_1_api_id"] = "BENCH"
            event["player_1_eh_id"] = "BENCH"

    if game_id == 2018021124:
        if event["event_idx"] == 237:
            event["player_3_api_id"] = 8479353
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2018021171:
        if event["event_idx"] == 551:
            event["player_3_api_id"] = 8471887
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2019020006:
        if event["event_idx"] == 288:
            event["player_3_api_id"] = 8478550
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2019020136:
        if event["event_idx"] == 424:
            event["player_3_api_id"] = 8478550
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2019020147:
        if event["event_idx"] == 28:
            event["player_3_api_id"] = 8478550
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2019020179:
        if event["event_idx"] == 573:
            event["player_2_api_id"] = event["player_1_api_id"]
            event["player_2_type"] = "SERVED BY"

            event["player_1"] = "BENCH"
            event["player_1_api_id"] = "BENCH"
            event["player_1_eh_id"] = "BENCH"

    if game_id == 2019020239:
        if event["event_idx"] == 543:
            event["player_3_api_id"] = 8478463
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2019020316:
        if event["event_idx"] == 428:
            event["player_3_api_id"] = event["player_2_api_id"]
            event["player_3_type"] = "SERVED BY"

            event["player_2_api_id"] = 8477903
            event["player_2_type"] = "DRAWN BY"

    if game_id == 2019020682:
        if event["event_idx"] == 382:
            event["player_3_api_id"] = 8478550
            event["player_3_type"] = "DRAWN BY"

    if game_id == 2020020456:
        if event["event_idx"] == 360:
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

    if game_id == 2020020860:
        if event["event_idx"] == 705:
            event["period_seconds"] = 270
            event["game_seconds"] = 3870

    if game_id == 2021020482:
        if event["event_idx"] == 250:
            event["player_1_api_id"] = 8477465

    return event


def html_events_fixes(game_id: int, event: dict) -> dict:
    """Fixes HTML event errors."""
    if game_id == 2011020069:
        if event["event_idx"] == 312:
            event["description"] = event["description"].replace(
                "BOS #", "BOS #17 LUCIC "
            )

    if game_id == 2011020553:
        if event["event_idx"] == 294:
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

    if game_id == 2013020971:
        if event["event_idx"] == 1:
            event["period"] = 1

            event["time"] = "0:0020:00"

    if game_id == 2014020120:
        if event["event_idx"] == 341:
            event["description"] = (
                "SJS TEAM PLAYER LEAVES BENCH - BENCH(2 MIN), OFF. ZONE SJS SERVED BY: #20 SCOTT DRAWN BY: "
                "ANA #47 LINDHOLM"
            )

    if game_id == 2014020600:
        if event["event_idx"] == 328:
            event["description"] = "CAR # BLOCKED BY BUF #6 WEBER, WRIST, DEF. ZONE"

    if game_id == 2014020672:
        if event["event_idx"] == 297:
            event["description"] = "NYR #22 HIT PIT #16 SUTTER, DEF. ZONE"

    if game_id == 2014021118:
        event["time"] = event["time"].replace("-16:0-120:00", "5:000:00")

    if game_id == 2015020193:
        if event["event_idx"] == 196:
            event["description"] = "FLA #27 BJUGSTAD, WRIST, OFF. ZONE, 16 FT."

    if game_id == 2015020904:
        event["time"] = event["time"].replace("-16:0-120:00", "5:000:00")

    if game_id == 2015020917:
        if event["event_idx"] == 76:
            event["description"] = (
                "WSH #43 WILSON TRIPPING(2 MIN) OFF. ZONE DRAWN BY: MIN #46 SPURGEON"
            )

    if game_id == 2016020256:
        if event["event_idx"] == 117:
            event["description"] = (
                "WSH #14 WILLIAMS ROUGHING(2 MIN) NEU. ZONE DRAWN BY: DET #21 TATAR"
            )

    if game_id == 2016020625:
        if event["event_idx"] == 311:
            event["description"] = (
                "PIT HEAD COACH GAME MISCONDUCT(0 MIN) PIT SERVED BY: #61 OLEKSY, NEU. ZONE"
            )

    if game_id == 2016021070:
        if event["event_idx"] == 206:
            event["description"] = "TOR # HIT BOS # , DEF. ZONE"

    if game_id == 2016021127:
        event["description"] = event["description"].replace(
            "BOS #55 ACCIARI ( MIN), DEF. ZONE",
            "BOS #55 ACCIARI MISCONDUCT (10 MIN), DEF. ZONE",
        )

    if game_id == 2017020463:
        event["time"] = event["time"].replace("-16:0-120:00", "2:022:58")

    if game_id == 2017020796:
        if event["event_idx"] == 338:
            event["description"] = (
                "DET HEAD COACH GAME MISCONDUCT(0 MIN) DET SERVED BY: #3 JENSEN, NEU. ZONE"
            )

    if game_id == 2018020009:
        if event["event_idx"] == 231:
            event["description"] = (
                "CHI TEAM FACE-OFF VIOLATION(2 MIN) CHI SERVED BY: #12 DEBRINCAT"
            )

    if game_id == 2018020989:
        event["time"] = event["time"].replace("-16:0-120:00", "5:000:00")

    if game_id == 2017021161:
        if event["event_idx"] == 253:
            event["description"] = (
                "NSH HEAD COACH GAME MISCONDUCT(0 MIN) NSH SERVED BY: #2 BITETTO, NEU. ZONE"
            )

    if game_id == 2018020363:
        if event["event_idx"] == 156:
            event["description"] = (
                "NJD TEAM TOO MANY MEN/ICE(2 MIN) NJD SERVED BY: #44 WOOD, OFF. ZONE"
            )

    if game_id == 2018021087:
        if event["event_idx"] == 289:
            event["description"] = (
                "TBL TEAM DELAY OF GAME(2 MIN) TBL SERVED BY: #10 MILLER, DEF. ZONE"
            )

    if game_id == 2018021133:
        event["description"] = event["description"].replace(
            "WSH TAKEAWAY - #71 CIRELLI", "TBL TAKEAWAY - #71 CIRELLI"
        )

    if game_id == 2019020179:
        if event["event_idx"] == 259:
            event["description"] = (
                "SJS HEAD COACH GAME MISCONDUCT (0 MIN), SERVED BY: #65 KARLSSON, DEF. ZONE"
            )

    if game_id == 2019020316:
        if event["event_idx"] == 212:
            event["description"] = (
                "ANA #6 GUDBRANSON ROUGHING(2 MIN) SERVED BY: #24 ROWNEY, DEF. ZONE DRAWN BY: WSH #21 HATHAWAY"
            )

    if game_id == 2021020224:
        event["description"] = event["description"].replace(
            " - MTL #60 BELZILE VS BOS #92 NOSEK",
            "MTL WON NEU. ZONE - MTL #60 BELZILE VS BOS #92 NOSEK",
        )

    if game_id == 2023020838:
        if event["event_idx"] == 216:
            event["description"] = (
                "FLA #17 RODRIGUES HIGH-STICKING(2 MIN), NEU. ZONE DRAWN BY: BUF #72 THOMPSON"
            )

    if game_id == 2023021279:
        if event["event_idx"] == 264:
            event["description"] = (
                "PIT #10 O'CONNOR SLASHING(2 MIN), DEF. ZONE DRAWN BY: BOS #63 MARCHAND"
            )

    return event


def html_rosters_fixes(game_id: int, player: dict) -> dict:
    """Fixes HTML rosters errors."""
    if game_id == 2019020665:
        scratches = [
            "ROSS JOHNSTON",
            "SEBASTIAN AHO",
            "CONNOR CARRICK",
            "JESPER BRATT",
            "JACK HUGHES",
        ]

        if player["player_name"] in scratches:
            player["status"] = "SCRATCH"

    return player


def rosters_fixes(game_id: int, player_info: dict) -> dict:
    """Docstring."""
    if game_id == 2015020508:
        if player_info["team_jersey"] == "ANA5":
            new_values = {
                "api_id": 8473560,
                "headshot_url": "https://assets.nhle.com/mugs/nhl/20152016/ANA/8473560.png",
            }

            player_info.update(new_values)

    if game_id == 2015021197:
        if player_info["team_jersey"] == "LAK13":
            new_values = {
                "api_id": 8475160,
                "headshot_url": "https://assets.nhle.com/mugs/nhl/20152016/LAK/8475160.png",
            }

            player_info.update(new_values)

    return player_info
