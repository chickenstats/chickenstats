import pytest

from chickenstats.chicken_nhl._corrections import (
    api_events_fixes,
    api_rosters_fixes,
    html_events_fixes,
    html_rosters_fixes,
    html_shifts_fixes,
    individual_shifts_fixes,
    rosters_fixes,
)


# ---------------------------------------------------------------------------
# html_rosters_fixes
# ---------------------------------------------------------------------------


class TestHtmlRostersFixes:
    @pytest.mark.parametrize(
        "player_name", ["ROSS JOHNSTON", "SEBASTIAN AHO", "CONNOR CARRICK", "JESPER BRATT", "JACK HUGHES"]
    )
    def test_scratches_get_scratch_status(self, player_name):
        player = {"player_name": player_name, "status": "ACTIVE"}
        result = html_rosters_fixes(game_id=2019020665, player=player)
        assert result["status"] == "SCRATCH"

    def test_non_scratch_player_unchanged(self):
        player = {"player_name": "TAYLOR HALL", "status": "ACTIVE"}
        result = html_rosters_fixes(game_id=2019020665, player=player)
        assert result["status"] == "ACTIVE"

    def test_different_game_id_not_affected(self):
        player = {"player_name": "ROSS JOHNSTON", "status": "ACTIVE"}
        result = html_rosters_fixes(game_id=2023020001, player=player)
        assert result["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# api_rosters_fixes
# ---------------------------------------------------------------------------


class TestApiRostersFixes:
    def test_game_2013020971_returns_horton(self):
        result = api_rosters_fixes(season=20132014, session="R", game_id=2013020971)
        assert result["player_name"] == "NATHAN HORTON"
        assert result["api_id"] == 8470596
        assert result["team"] == "CBJ"

    def test_game_2013020971_all_required_fields(self):
        result = api_rosters_fixes(season=20132014, session="R", game_id=2013020971)
        required_fields = [
            "season",
            "session",
            "game_id",
            "team",
            "team_venue",
            "player_name",
            "first_name",
            "last_name",
            "api_id",
            "eh_id",
            "team_jersey",
            "jersey",
            "position",
            "headshot_url",
        ]
        for field in required_fields:
            assert field in result

    def test_game_2013020971_passes_season_and_session(self):
        result = api_rosters_fixes(season=20132014, session="R", game_id=2013020971)
        assert result["season"] == 20132014
        assert result["session"] == "R"
        assert result["game_id"] == 2013020971

    def test_other_game_returns_empty_dict(self):
        result = api_rosters_fixes(season=20232024, session="R", game_id=2023020001)
        assert result == {}


# ---------------------------------------------------------------------------
# rosters_fixes
# ---------------------------------------------------------------------------


class TestRostersFixes:
    def test_game_2015020508_ana5_updates_api_id(self):
        player_info = {"team_jersey": "ANA5", "api_id": None, "headshot_url": ""}
        result = rosters_fixes(game_id=2015020508, player_info=player_info)
        assert result["api_id"] == 8473560

    def test_game_2015020508_ana5_updates_headshot(self):
        player_info = {"team_jersey": "ANA5", "api_id": None, "headshot_url": ""}
        result = rosters_fixes(game_id=2015020508, player_info=player_info)
        assert "8473560" in result["headshot_url"]

    def test_game_2015020508_other_jersey_unchanged(self):
        player_info = {"team_jersey": "ANA10", "api_id": 9999999, "headshot_url": ""}
        result = rosters_fixes(game_id=2015020508, player_info=player_info)
        assert result["api_id"] == 9999999

    def test_game_2015021197_lak13_updates_api_id(self):
        player_info = {"team_jersey": "LAK13", "api_id": None, "headshot_url": ""}
        result = rosters_fixes(game_id=2015021197, player_info=player_info)
        assert result["api_id"] == 8475160

    def test_game_2015021197_lak13_updates_headshot(self):
        player_info = {"team_jersey": "LAK13", "api_id": None, "headshot_url": ""}
        result = rosters_fixes(game_id=2015021197, player_info=player_info)
        assert "8475160" in result["headshot_url"]

    def test_game_2015021197_other_jersey_unchanged(self):
        player_info = {"team_jersey": "LAK10", "api_id": 9999999, "headshot_url": ""}
        result = rosters_fixes(game_id=2015021197, player_info=player_info)
        assert result["api_id"] == 9999999

    def test_other_game_id_unchanged(self):
        player_info = {"team_jersey": "ANA5", "api_id": 9999999, "headshot_url": ""}
        result = rosters_fixes(game_id=2023020001, player_info=player_info)
        assert result["api_id"] == 9999999


# ---------------------------------------------------------------------------
# shifts_fixes
# ---------------------------------------------------------------------------


class TestShiftsFixes:
    def test_sam_lafferty_nbsp_period_gets_fixed(self):
        shift = {"period": "\xa0", "shift_count": "", "shift_start": "", "shift_end": ""}
        result = individual_shifts_fixes(game_id=2025020551, player_name="SAM LAFFERTY", shift_dict=shift)
        assert result["period"] == "1"
        assert result["shift_count"] == "8"
        assert result["shift_start"] == "16:46 / 3:16"
        assert result["shift_end"] == "17:45 / 2:15"

    def test_sam_lafferty_normal_period_unchanged(self):
        shift = {"period": "2", "shift_count": "5", "shift_start": "10:00 / 10:00", "shift_end": "11:00 / 9:00"}
        result = individual_shifts_fixes(game_id=2025020551, player_name="SAM LAFFERTY", shift_dict=shift)
        assert result["period"] == "2"

    def test_other_player_unchanged(self):
        shift = {"period": "\xa0", "shift_count": "", "shift_start": "", "shift_end": ""}
        result = individual_shifts_fixes(game_id=2025020551, player_name="TYLER MOTTE", shift_dict=shift)
        assert result["period"] == "\xa0"

    def test_other_game_id_unchanged(self):
        shift = {"period": "\xa0", "shift_count": "", "shift_start": "", "shift_end": ""}
        result = individual_shifts_fixes(game_id=2023020001, player_name="SAM LAFFERTY", shift_dict=shift)
        assert result["period"] == "\xa0"


# ---------------------------------------------------------------------------
# api_events_fixes — description correction patches
# ---------------------------------------------------------------------------


class TestHtmlEventsFixes:
    def test_game_2023020838_event_216_description_patched(self):
        event = {"event_idx": 216, "description": ""}
        result = html_events_fixes(game_id=2023020838, event=event)
        assert "RODRIGUES" in result["description"]
        assert "HIGH-STICKING" in result["description"]

    def test_game_2023020838_other_event_unchanged(self):
        event = {"event_idx": 100, "description": "original"}
        result = html_events_fixes(game_id=2023020838, event=event)
        assert result["description"] == "original"

    def test_game_2023021279_event_264_description_patched(self):
        event = {"event_idx": 264, "description": ""}
        result = html_events_fixes(game_id=2023021279, event=event)
        assert "O'CONNOR" in result["description"]
        assert "SLASHING" in result["description"]

    def test_game_2023021279_other_event_unchanged(self):
        event = {"event_idx": 100, "description": "original"}
        result = html_events_fixes(game_id=2023021279, event=event)
        assert result["description"] == "original"

    def test_description_replace_2011020069(self):
        event = {"event_idx": 312, "description": "BOS # HIT"}
        result = html_events_fixes(game_id=2011020069, event=event)
        assert "LUCIC" in result["description"]

    def test_full_description_set_2011020553(self):
        event = {"event_idx": 294, "description": ""}
        result = html_events_fixes(game_id=2011020553, event=event)
        assert "BARCH" in result["description"]

    def test_nested_description_2012020660(self):
        event = {"event_idx": 150, "description": ""}
        result = html_events_fixes(game_id=2012020660, event=event)
        assert "ZIDLICKY" in result["description"]

    def test_dict_replace_2012020018(self):
        event = {"event_idx": 1, "description": "EDM #9 SHOT"}
        result = html_events_fixes(game_id=2012020018, event=event)
        assert "VAN #9" in result["description"]
        assert "EDM #9" not in result["description"]

    @pytest.mark.parametrize(
        "game_id", [2013020083, 2013020274, 2013020644, 2014021118, 2015020904, 2017020463, 2018020989]
    )
    def test_time_replace(self, game_id):
        event = {"event_idx": 1, "time": "-16:0-120:00"}
        result = html_events_fixes(game_id=game_id, event=event)
        assert result["time"] != "-16:0-120:00"

    def test_period_and_time_2013020971(self):
        event = {"event_idx": 1, "period": 0, "time": ""}
        result = html_events_fixes(game_id=2013020971, event=event)
        assert result["period"] == 1
        assert result["time"] == "0:0020:00"

    @pytest.mark.parametrize(
        "game_id,event_idx,substr",
        [
            (2014020120, 341, "SCOTT"),
            (2014020600, 328, "BLOCKED"),
            (2014020672, 297, "SUTTER"),
            (2015020193, 196, "BJUGSTAD"),
            (2015020917, 76, "SPURGEON"),
            (2016020256, 117, "TATAR"),
            (2016020625, 311, "OLEKSY"),
            (2016021070, 206, "DEF. ZONE"),
            (2017020796, 338, "JENSEN"),
            (2018020009, 231, "DEBRINCAT"),
            (2017021161, 253, "BITETTO"),
            (2018020363, 156, "WOOD"),
            (2018021087, 289, "MILLER"),
            (2019020179, 259, "KARLSSON"),
            (2019020316, 212, "GUDBRANSON"),
        ],
    )
    def test_full_description_patches(self, game_id, event_idx, substr):
        event = {"event_idx": event_idx, "description": ""}
        result = html_events_fixes(game_id=game_id, event=event)
        assert substr in result["description"]

    @pytest.mark.parametrize(
        "game_id,description,expected_substr",
        [
            (2016021127, "BOS #55 ACCIARI ( MIN), DEF. ZONE", "(10 MIN)"),
            (2018021133, "WSH TAKEAWAY - #71 CIRELLI", "TBL TAKEAWAY"),
            (2021020224, " - MTL #60 BELZILE VS BOS #92 NOSEK", "MTL WON NEU. ZONE"),
        ],
    )
    def test_description_replace_patterns(self, game_id, description, expected_substr):
        event = {"event_idx": 1, "description": description}
        result = html_events_fixes(game_id=game_id, event=event)
        assert expected_substr in result["description"]

    def test_time_replace_2017020463(self):
        event = {"event_idx": 1, "time": "-16:0-120:00"}
        result = html_events_fixes(game_id=2017020463, event=event)
        assert result["time"] == "2:022:58"

    def test_unknown_game_unchanged(self):
        event = {"event_idx": 1, "description": "original", "time": "0:00"}
        result = html_events_fixes(game_id=2023020001, event=event)
        assert result["description"] == "original"
        assert result["time"] == "0:00"


# ---------------------------------------------------------------------------
# api_events_fixes
# ---------------------------------------------------------------------------


class TestApiEventsFixes:
    def test_unknown_game_unchanged(self):
        event = {"event_idx": 999, "foo": "bar"}
        result = api_events_fixes(game_id=2023020001, event=event)
        assert result == {"event_idx": 999, "foo": "bar"}

    @pytest.mark.parametrize(
        "game_id,event_idx,expected_api_id",
        [
            (2010021176, 213, 8467396),
            (2012020095, 139, 8468483),
            (2012020627, 621, 8462129),
            (2012030224, 594, 8475184),
            (2013020305, 392, 8475184),
            (2013030142, 727, 8470601),
            (2013030155, 309, 8476463),
            (2014020120, 661, 8476854),
            (2014020417, 280, 8468501),
            (2014020506, 377, 8468208),
            (2014020506, 584, 8474613),
            (2014020939, 287, 8475218),
            (2014021128, 280, 8471426),
            (2014021203, 344, 8466378),
            (2014030311, 346, 8474613),
            (2014030315, 69, 8474151),
            (2015020401, 167, 8470854),
            (2015020839, 417, 8476393),
            (2015021092, 199, 8474884),
            (2016020049, 347, 8475692),
            (2016020326, 175, 8475855),
            (2016020433, 366, 8471686),
            (2016020519, 335, 8471676),
            (2016020883, 385, 8469521),
            (2016021111, 183, 8473504),
            (2016030216, 567, 8474151),
            (2017020033, 390, 8477964),
            (2017020033, 585, 8476892),
            (2017020096, 727, 8474066),
            (2017020233, 375, 8470638),
            (2017020548, 726, 8468493),
            (2017020601, 319, 8473449),
            (2017020615, 626, 8473546),
            (2017020835, 560, 8477215),
            (2017020836, 273, 8476346),
            (2017021136, 193, 8479206),
            (2017021136, 262, 8475314),
            (2018020006, 683, 8475793),
            (2018020049, 155, 8479353),
            (2018020115, 248, 8475692),
            (2018020122, 235, 8477996),
            (2018020153, 212, 8478458),
            (2018020211, 661, 8471217),
            (2018020309, 76, 8476918),
            (2018020519, 417, 8477941),
            (2018020561, 500, 8474190),
            (2018020752, 41, 8476917),
            (2018020794, 182, 8470187),
            (2018020795, 354, 8476918),
            (2018020841, 227, 8476455),
            (2018020969, 575, 8474150),
            (2018021124, 237, 8479353),
            (2018021171, 551, 8471887),
            (2019020006, 288, 8478550),
            (2019020136, 424, 8478550),
            (2019020147, 28, 8478550),
            (2019020239, 543, 8478463),
            (2019020682, 382, 8478550),
        ],
    )
    def test_drawn_by_player_3(self, game_id, event_idx, expected_api_id):
        result = api_events_fixes(game_id=game_id, event={"event_idx": event_idx})
        assert result["player_3_api_id"] == expected_api_id
        assert result["player_3_type"] == "DRAWN BY"

    @pytest.mark.parametrize(
        "game_id,event_idx,expected_api_id",
        [(2011020069, 660, 8473473), (2015020193, 389, 8475760), (2021020482, 250, 8477465)],
    )
    def test_player_1_api_id_fix(self, game_id, event_idx, expected_api_id):
        result = api_events_fixes(game_id=game_id, event={"event_idx": event_idx})
        assert result["player_1_api_id"] == expected_api_id

    @pytest.mark.parametrize("game_id,event_idx", [(2012020341, 656), (2012020660, 377), (2017020209, 245)])
    def test_bench_fix(self, game_id, event_idx):
        result = api_events_fixes(game_id=game_id, event={"event_idx": event_idx})
        assert result["player_1"] == "BENCH"
        assert result["player_1_api_id"] is None
        assert result["player_1_eh_id"] == "BENCH"

    def test_player_2_served_by_2012020671(self):
        result = api_events_fixes(game_id=2012020671, event={"event_idx": 680})
        assert result["player_2_api_id"] == 8470192
        assert result["player_2_type"] == "SERVED BY"

    @pytest.mark.parametrize("game_id,event_idx", [(2013020445, 617), (2016021165, 85)])
    def test_swap_player_1_player_2(self, game_id, event_idx):
        event = {"event_idx": event_idx, "player_1_api_id": 111, "player_2_api_id": 222}
        result = api_events_fixes(game_id=game_id, event=event)
        assert result["player_1_api_id"] == 222
        assert result["player_2_api_id"] == 111

    @pytest.mark.parametrize("game_id,event_idx", [(2015020917, 162), (2016020256, 210)])
    def test_delete_player_3(self, game_id, event_idx):
        event = {"event_idx": event_idx, "player_3_api_id": 9999, "player_3_type": "DRAWN BY"}
        result = api_events_fixes(game_id=game_id, event=event)
        assert "player_3_api_id" not in result
        assert "player_3_type" not in result

    @pytest.mark.parametrize(
        "game_id,event_idx,period_seconds,game_seconds",
        [
            (2014020356, 599, 970, 3370),
            (2014020356, 603, 1002, 3402),
            (2014020945, 585, 1069, 3469),
            (2014021127, 754, 1124, 3524),
            (2014021127, 756, 1125, 3525),
            (2014021127, 755, 1127, 3527),
            (2016020177, 494, 360, 2760),
            (2016020963, 44, 40, 40),
            (2020020456, 360, 1068, 2268),
            (2020020860, 705, 270, 3870),
        ],
    )
    def test_time_fixes(self, game_id, event_idx, period_seconds, game_seconds):
        result = api_events_fixes(game_id=game_id, event={"event_idx": event_idx})
        assert result["period_seconds"] == period_seconds
        assert result["game_seconds"] == game_seconds

    def test_multi_event_game_2014020120_idx720(self):
        original_p1 = 8471234
        event = {"event_idx": 720, "player_1_api_id": original_p1}
        result = api_events_fixes(game_id=2014020120, event=event)
        assert result["player_3_api_id"] == original_p1
        assert result["player_3_type"] == "SERVED BY"
        assert result["player_1_api_id"] == 8473492

    @pytest.mark.parametrize(
        "game_id,event_idx",
        [
            (2016020625, 630),
            (2017020796, 687),
            (2017021161, 590),
            (2018020009, 421),
            (2018021087, 550),
            (2018020363, 299),
            (2019020179, 573),
        ],
    )
    def test_bench_with_player_copy(self, game_id, event_idx):
        event = {"event_idx": event_idx, "player_1_api_id": 8471234}
        result = api_events_fixes(game_id=game_id, event=event)
        assert result["player_1"] == "BENCH"
        assert result["player_1_api_id"] is None

    def test_complex_swap_2019020316(self):
        event = {"event_idx": 428, "player_2_api_id": 8471111}
        result = api_events_fixes(game_id=2019020316, event=event)
        assert result["player_3_api_id"] == 8471111
        assert result["player_3_type"] == "SERVED BY"
        assert result["player_2_api_id"] == 8477903
        assert result["player_2_type"] == "DRAWN BY"

    @pytest.mark.parametrize(
        "event_idx,expected_api_id", [(407, 8475799), (409, 8479987), (411, 8479987), (413, 8475790), (415, 8476988)]
    )
    def test_player_2_api_id_multi_events_2020020846(self, event_idx, expected_api_id):
        result = api_events_fixes(game_id=2020020846, event={"event_idx": event_idx})
        assert result["player_2_api_id"] == expected_api_id


# ---------------------------------------------------------------------------
# html_shifts_fixes
# ---------------------------------------------------------------------------


def _shift_player(team_jersey: str, team: str | None = None, venue: str = "HOME") -> dict:
    return {
        "team_name": f"{team or team_jersey[:3]} TEAM",
        "team": team or team_jersey[:3],
        "team_venue": venue,
        "player_name": f"PLAYER {team_jersey}",
        "team_jersey": team_jersey,
        "jersey": int(team_jersey[3:]),
    }


class TestHtmlShiftsFixes:
    def test_unknown_game_unchanged(self):
        shifts = [{"period": 1}]
        result = html_shifts_fixes(2023020001, 20232024, "R", shifts, {}, {})
        assert result == [{"period": 1}]

    def test_game_2020020860_player_not_found_skipped(self):
        result = html_shifts_fixes(2020020860, 20202021, "R", [], {}, {})
        assert result == []

    def test_game_2020020860_player_in_actives(self):
        actives = {k: _shift_player(k) for k in ["DAL29", "CHI60", "DAL14", "DAL21", "DAL3", "CHI5", "CHI88", "CHI12"]}
        result = html_shifts_fixes(2020020860, 20202021, "R", [], actives, {})
        assert len(result) == 8

    def test_game_2020020860_player_in_scratches(self):
        scratches = {"DAL29": _shift_player("DAL29")}
        result = html_shifts_fixes(2020020860, 20202021, "R", [], {}, scratches)
        assert len(result) == 1
        assert result[0]["player_name"] == "PLAYER DAL29"

    def test_game_2020020860_time_branches(self):
        actives = {k: _shift_player(k) for k in ["DAL29", "DAL14", "CHI88", "CHI12"]}
        result = html_shifts_fixes(2020020860, 20202021, "R", [], actives, {})
        times = {s["player_name"].split()[-1]: s["start_time"] for s in result}
        assert times["DAL29"] == "0:00"
        assert times["DAL14"] == "3:47"
        assert times["CHI88"] == "3:51"
        assert times["CHI12"] == "4:14"

    def test_game_2020020865_player_in_actives(self):
        actives = {k: _shift_player(k) for k in ["MIN36", "MIN24", "MIN49", "ANA42", "ANA43", "ANA67"]}
        result = html_shifts_fixes(2020020865, 20202021, "R", [], actives, {})
        assert len(result) == 6

    def test_game_2020020865_time_branches(self):
        actives = {k: _shift_player(k) for k in ["MIN36", "ANA42", "ANA67", "ANA43"]}
        result = html_shifts_fixes(2020020865, 20202021, "R", [], actives, {})
        times = {s["player_name"].split()[-1]: s["start_time"] for s in result}
        assert times["MIN36"] == "1:53"
        assert times["ANA42"] == "2:02"
        assert times["ANA67"] == "2:41"
        assert times["ANA43"] == "2:45"

    def test_game_2020020865_player_not_found_skipped(self):
        result = html_shifts_fixes(2020020865, 20202021, "R", [], {}, {})
        assert result == []

    def test_game_2019020331_adds_shift(self):
        actives = {"OTT44": _shift_player("OTT44", team="OTT")}
        result = html_shifts_fixes(2019020331, 20192020, "R", [], actives, {})
        assert len(result) == 1
        assert result[0]["shift_count"] == 29
        assert result[0]["period"] == 4
        assert result[0]["start_time"] == "0:00"

    def test_game_2019020331_player_not_found_skipped(self):
        result = html_shifts_fixes(2019020331, 20192020, "R", [], {}, {})
        assert result == []

    def test_existing_shifts_preserved(self):
        existing = [{"period": 1, "player_name": "EXISTING"}]
        actives = {"DAL29": _shift_player("DAL29")}
        result = html_shifts_fixes(2020020860, 20202021, "R", existing, actives, {})
        assert result[0]["player_name"] == "EXISTING"
        assert len(result) > 1
