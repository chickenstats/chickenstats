from typing import Literal

import pandas as pd
import polars as pl
import narwhals as nw

from chickenstats.chicken_nhl.game import Game

from chickenstats.chicken_nhl._aggregation import (
    prep_ind_polars,
    prep_oi_polars,
    prep_stats_polars,
    prep_lines_polars,
    prep_team_stats_polars,
    prep_ind_pandas,
    prep_oi_pandas,
    prep_stats_pandas,
    prep_lines_pandas,
    prep_team_stats_pandas,
)
from chickenstats.chicken_nhl._helpers import convert_to_list

# These are dictionaries of names that are used throughout the module
from chickenstats.chicken_nhl.validation import (
    APIEventSchemaPolars,
    APIRosterSchemaPolars,
    ChangesSchemaPolars,
    HTMLEventSchemaPolars,
    HTMLRosterSchemaPolars,
    PBPExtSchemaPolars,
    PBPSchemaPolars,
    RosterSchemaPolars,
    ShiftsSchemaPolars,
)
from chickenstats.utilities.utilities import ChickenProgress, ChickenProgressIndeterminate, ChickenSession


class Scraper:
    # noinspection GrazieInspection
    """Class instance for scraping play-by-play and other data for NHL games.

    Parameters:
        game_ids (list[str | float | int] | pd.Series | str | float | int):
            List of 10-digit game identifier, e.g., `[2023020001, 2023020002, 2023020003]`
        disable_progress_bar (bool):
            If true, disables the progress bar
        backend (None | str):
            Whether to use pandas or polars as backend for data manipulation. Defaults to pandas

    Attributes:
        game_ids (list):
            Game IDs that the Scraper will access, e.g., `[2023020001, 2023020002, 2023020003]`

    Examples:
        First, instantiate the Scraper object
        >>> game_ids = list(range(2023020001, 2023020011))
        >>> scraper = Scraper(game_ids)

        Scrape play-by-play information
        >>> pbp = scraper.play_by_play

        The object stores information from each component of the play-by-play data
        >>> shifts = scraper.shifts
        >>> rosters = scraper.rosters
        >>> changes = scraper.changes

        Access data from API or HTML endpoints, or both
        >>> api_events = scraper.api_events
        >>> api_rosters = scraper.api_rosters
        >>> html_events = scraper.html_events
        >>> html_rosters = scraper.html_rosters

    """

    def __init__(
        self,
        game_ids: list[str | float | int] | pd.Series | str | float | int,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
        backend: Literal["pandas", "polars", "pyarrow", "narwhals"] = "polars",
    ):
        """Instantiates a Scraper object for a given game ID or list / list-like object of game IDs."""
        game_ids = convert_to_list(game_ids, "game ID")

        self._backend: Literal["pandas", "polars", "pyarrow", "narwhals"] = backend

        self.disable_progress_bar: bool = disable_progress_bar
        self.transient_progress_bar: bool = transient_progress_bar

        self.game_ids: list = game_ids
        self._scraped_games: list = []
        self._bad_games: list = []

        self._requests_session: ChickenSession = ChickenSession()

        self._api_events: list = []
        self._scraped_api_events: list = []

        self._api_rosters: list = []
        self._scraped_api_rosters: list = []

        self._changes: list = []
        self._scraped_changes: list = []

        self._html_events: list = []
        self._scraped_html_events: list = []

        self._html_rosters: list = []
        self._scraped_html_rosters: list = []

        self._rosters: list = []
        self._scraped_rosters: list = []

        self._shifts: list = []
        self._scraped_shifts: list = []

        self._play_by_play: list = []
        self._play_by_play_ext: list = []
        self._scraped_play_by_play: list = []

        if self._backend == "polars":
            dataframe = pl.DataFrame()

        if self._backend == "pandas":
            dataframe = pd.DataFrame()

        self._ind_stats: pl.DataFrame | pd.DataFrame = dataframe
        self._oi_stats: pl.DataFrame | pd.DataFrame = dataframe
        self._zones: pl.DataFrame | pd.DataFrame = dataframe
        self._stats: pl.DataFrame | pd.DataFrame = dataframe
        self._stats_levels: dict = {
            "level": None,
            "strength_state": None,
            "score": None,
            "teammates": None,
            "opposition": None,
        }

        self._lines: pl.DataFrame | pd.DataFrame = dataframe
        self._lines_levels: dict = {
            "position": None,
            "level": None,
            "strength_state": None,
            "score": None,
            "teammates": None,
            "opposition": None,
        }

        self._team_stats: pl.DataFrame | pd.DataFrame = dataframe
        self._team_stats_levels: dict = {
            "level": None,
            "strength_state": None,
            "score": None,
            "strengths": None,
            "opposition": None,
        }

    def _scrape(
        self,
        scrape_type: Literal[
            "api_events", "api_rosters", "changes", "html_events", "html_rosters", "play_by_play", "shifts", "rosters"
        ],
    ) -> None:
        """Method for scraping any data. Iterates through a list of game IDs using Game objects.

        For more information and usage, see https://chickenstats.com/latest/contribute/contribute/.

        Examples:
            First, instantiate the Scraper object
            >>> game_ids = list(range(2023020001, 2023020011))
            >>> scraper = Scraper(game_ids)

            Before scraping the data, any of the storage objects are None
            >>> scraper._shifts  # Returns None
            >>> scraper._play_by_play  # Also returns None

            You can use the `_scrape` method to get any data
            >>> scraper._scrape("html_events")
            >>> scraper._html_events  # Returns data as a list
            >>> scraper.html_events  # Returns data as a Pandas DataFrame
        """
        pbar_stubs = {
            "api_events": "API events",
            "api_rosters": "API rosters",
            "changes": "changes",
            "html_events": "HTML events",
            "html_rosters": "HTML rosters",
            "play_by_play": "play-by-play data",
            "shifts": "shifts",
            "rosters": "rosters",
        }

        if scrape_type == "api_events":
            game_ids = [x for x in self.game_ids if x not in self._scraped_api_events]

        if scrape_type == "api_rosters":
            game_ids = [x for x in self.game_ids if x not in self._scraped_api_rosters]

        if scrape_type == "changes":
            game_ids = [x for x in self.game_ids if x not in self._scraped_changes]

        if scrape_type == "html_events":
            game_ids = [x for x in self.game_ids if x not in self._scraped_html_events]

        if scrape_type == "html_rosters":
            game_ids = [x for x in self.game_ids if x not in self._scraped_html_rosters]

        if scrape_type == "play_by_play":
            game_ids = [x for x in self.game_ids if x not in self._scraped_play_by_play]

        if scrape_type == "shifts":
            game_ids = [x for x in self.game_ids if x not in self._scraped_shifts]

        if scrape_type == "rosters":
            game_ids = [x for x in self.game_ids if x not in self._scraped_rosters]

        with self._requests_session as s:
            with ChickenProgress(disable=self.disable_progress_bar, transient=self.transient_progress_bar) as progress:
                pbar_stub = pbar_stubs[scrape_type]

                pbar_message = f"Downloading {pbar_stub} for {game_ids[0]}..."

                game_task = progress.add_task(pbar_message, total=len(game_ids))

                for idx, game_id in enumerate(game_ids):
                    game = Game(game_id, s)

                    if scrape_type == "api_events":
                        if game_id in self._scraped_api_events:  # Not covered by tests
                            continue

                        else:
                            if game_id in self._scraped_api_rosters:  # Not covered by tests
                                game._api_rosters = [x for x in self._api_rosters if x["game_id"] == game_id]
                                game._api_rosters_processed = True

                            self._api_events.extend(game.api_events)
                            self._scraped_api_events.append(game_id)

                            if game_id not in self._scraped_api_rosters:
                                self._api_rosters.extend(game.api_rosters)
                                self._scraped_api_rosters.append(game_id)

                    if scrape_type == "api_rosters":
                        if game_id in self._scraped_api_rosters:  # Not covered by tests
                            continue

                        else:
                            self._api_rosters.extend(game.api_rosters)
                            self._scraped_api_rosters.append(game_id)

                    if scrape_type == "changes":
                        if game_id in self._scraped_changes:  # Not covered by tests
                            continue

                        else:
                            if game_id in self._scraped_rosters:  # Not covered by tests
                                game._rosters = [x for x in self._rosters if x["game_id"] == game_id]
                                game._rosters_processed = True

                            else:
                                if game_id in self._scraped_html_rosters:
                                    game._html_rosters = [x for x in self._html_rosters if x["game_id"] == game_id]
                                    game._html_rosters_processed = True

                                if game_id in self._scraped_api_rosters:
                                    game._api_rosters = [x for x in self._api_rosters if x["game_id"] == game_id]
                                    game._api_rosters_processed = True

                            if game_id in self._scraped_shifts:  # Not covered by tests
                                game._shifts = [x for x in self._shifts if x["game_id"] == game_id]
                                game._shifts_processed = True

                            self._changes.extend(game.changes)
                            self._scraped_changes.append(game_id)

                            if game_id not in self._scraped_rosters:
                                self._rosters.extend(game.rosters)
                                self._scraped_rosters.append(game_id)

                            if game_id not in self._scraped_html_rosters:
                                self._html_rosters.extend(game.html_rosters)
                                self._scraped_html_rosters.append(game_id)

                            if game_id not in self._scraped_api_rosters:
                                self._api_rosters.extend(game.api_rosters)
                                self._scraped_api_rosters.append(game_id)

                            if game_id not in self._scraped_shifts:
                                self._shifts.extend(game.shifts)
                                self._scraped_shifts.append(game_id)

                    if scrape_type == "html_events":
                        if game_id in self._scraped_html_events:  # Not covered by tests
                            continue

                        else:
                            if game_id in self._scraped_html_rosters:  # Not covered by tests
                                game._html_rosters = [x for x in self._html_rosters if x["game_id"] == game_id]
                                game._html_rosters_processed = True

                            self._html_events.extend(game.html_events)
                            self._scraped_html_events.append(game_id)

                            if game_id not in self._scraped_html_rosters:
                                self._html_rosters.extend(game.html_rosters)
                                self._scraped_html_rosters.append(game_id)

                    if scrape_type == "html_rosters":
                        if game_id in self._scraped_html_rosters:  # Not covered by tests
                            continue

                        else:
                            self._html_rosters.extend(game.html_rosters)
                            self._scraped_html_rosters.append(game_id)

                    if scrape_type == "play_by_play":
                        if game_id in self._scraped_play_by_play:  # Not covered by tests
                            continue

                        else:
                            if game_id in self._scraped_rosters:  # Not covered by tests
                                game._rosters = [x for x in self._rosters if x["game_id"] == game_id]
                                game._rosters_processed = True

                            else:
                                if game_id in self._scraped_html_rosters:  # Not covered by tests
                                    game._html_rosters = [x for x in self._html_rosters if x["game_id"] == game_id]
                                    game._html_rosters_processed = True

                                if game_id in self._scraped_api_rosters:  # Not covered by tests
                                    game._api_rosters = [x for x in self._api_rosters if x["game_id"] == game_id]
                                    game._api_rosters_processed = True

                            if game_id in self._scraped_changes:  # Not covered by tests
                                game._changes = [x for x in self._changes if x["game_id"] == game_id]
                                game._changes_processed = True

                            else:
                                if game_id in self._scraped_api_rosters:  # Not covered by tests
                                    game._api_rosters = [x for x in self._api_rosters if x["game_id"] == game_id]
                                    game._api_rosters_processed = True

                                if game_id in self._scraped_html_rosters:
                                    game._html_rosters = [x for x in self._html_rosters if x["game_id"] == game_id]
                                    game._html_rosters_processed = True

                                if game_id in self._scraped_shifts:  # Not covered by tests
                                    game._shifts = [x for x in self._shifts if x["game_id"] == game_id]
                                    game._shifts_processed = True

                            if game_id in self._scraped_html_events:  # Not covered by tests
                                game._html_events = [x for x in self._html_events if x["game_id"] == game_id]
                                game._html_events_processed = True

                            else:
                                if game_id in self._scraped_html_rosters:
                                    game._html_rosters = [x for x in self._html_rosters if x["game_id"] == game_id]
                                    game._html_rosters_processed = True

                            if game_id in self._scraped_api_events:  # Not covered by tests
                                game._api_events = [x for x in self._api_events if x["game_id"] == game_id]
                                game._api_events_processed = True

                            else:
                                if game_id in self._scraped_api_rosters:
                                    game._api_rosters = [x for x in self._api_rosters if x["game_id"] == game_id]
                                    game._api_rosters_processed = True

                            self._play_by_play.extend(game.play_by_play)
                            self._play_by_play_ext.extend(game.play_by_play_ext)
                            self._scraped_play_by_play.append(game_id)

                            if game_id not in self._scraped_html_rosters:
                                self._html_rosters.extend(game.html_rosters)
                                self._scraped_html_rosters.append(game_id)

                            if game_id not in self._scraped_api_rosters:
                                self._api_rosters.extend(game.api_rosters)
                                self._scraped_api_rosters.append(game_id)

                            if game_id not in self._scraped_rosters:
                                self._rosters.extend(game.rosters)
                                self._scraped_rosters.append(game_id)

                            if game_id not in self._scraped_shifts:
                                self._shifts.extend(game.shifts)
                                self._scraped_shifts.append(game_id)

                            if game_id not in self._scraped_changes:
                                self._changes.extend(game.changes)
                                self._scraped_changes.append(game_id)

                            if game_id not in self._scraped_html_events:
                                self._html_events.extend(game.html_events)
                                self._scraped_html_events.append(game_id)

                            if game_id not in self._scraped_api_events:
                                self._api_events.extend(game.api_events)
                                self._scraped_api_events.append(game_id)

                    if scrape_type == "rosters":
                        if game_id in self._scraped_rosters:  # Not covered by tests
                            continue

                        else:
                            if game_id in self._scraped_rosters:  # Not covered by tests
                                game._rosters = [x for x in self._rosters if x["game_id"] == game_id]
                                game._rosters_processed = True

                            else:
                                if game_id in self._scraped_html_rosters:  # Not covered by tests
                                    game._html_rosters = [x for x in self._html_rosters if x["game_id"] == game_id]
                                    game._html_rosters_processed = True

                                if game_id in self._scraped_api_rosters:  # Not covered by tests
                                    game._api_rosters = [x for x in self._api_rosters if x["game_id"] == game_id]
                                    game._api_rosters_processed = True

                            self._rosters.extend(game.rosters)
                            self._scraped_rosters.append(game_id)

                            if game_id not in self._scraped_html_rosters:
                                self._html_rosters.extend(game.html_rosters)
                                self._scraped_html_rosters.append(game_id)

                            if game_id not in self._scraped_api_rosters:
                                self._api_rosters.extend(game.api_rosters)
                                self._scraped_api_rosters.append(game_id)

                    if scrape_type == "shifts":
                        if game_id in self._scraped_shifts:  # Not covered by tests
                            continue

                        else:
                            if game_id in self._scraped_rosters:  # Not covered by tests
                                game._rosters = [x for x in self._rosters if x["game_id"] == game_id]
                                game._rosters_processed = True

                            else:
                                if game_id in self._scraped_html_rosters:  # Not covered by tests
                                    game._html_rosters = [x for x in self._html_rosters if x["game_id"] == game_id]
                                    game._html_rosters_processed = True

                                if game_id in self._scraped_api_rosters:  # Not covered by tests
                                    game._api_rosters = [x for x in self._api_rosters if x["game_id"] == game_id]
                                    game._api_rosters_processed = True

                            self._shifts.extend(game.shifts)
                            self._scraped_shifts.append(game_id)

                            if game_id not in self._scraped_rosters:
                                self._rosters.extend(game.rosters)

                                self._scraped_rosters.append(game_id)

                            if game_id not in self._scraped_html_rosters:
                                self._html_rosters.extend(game.html_rosters)

                                self._scraped_html_rosters.append(game_id)

                            if game_id not in self._scraped_api_rosters:
                                self._api_rosters.extend(game.api_rosters)

                                self._scraped_api_rosters.append(game_id)

                    if game_id != self.game_ids[-1]:
                        pbar_message = f"Downloading {pbar_stub} for {self.game_ids[idx + 1]}..."

                    else:
                        pbar_message = f"Finished downloading {pbar_stub}"

                    progress.update(game_task, description=pbar_message, advance=1, refresh=True)

    def _finalize_dataframe(self, data, schema):
        """Method to return a pandas or polars dataframe, depending on user preference."""
        df = pl.from_dicts(data=data, schema=schema)

        if self._backend != "polars":
            df = nw.from_native(df)

            if self._backend == "pandas":
                df = df.to_pandas()

            elif self._backend == "pyarrow":
                df = df.to_arrow()

        return df

    def add_games(self, game_ids: list[int | str | float] | int) -> None:
        """Method to add games to the Scraper.

        Parameters:
            game_ids (list or int or float or str):
                List-like object of or single 10-digit game identifier, e.g., 2023020001

        Examples:
            Instantiate Scraper
            >>> game_ids = list(range(2023020001, 2023020011))
            >>> scraper = Scraper(game_ids)

            Scrape something
            >>> scraper.play_by_play

            Add games
            >>> scraper.add_games(2023020011)

            Scrape some more
            >>> scraper.play_by_play


        """
        if isinstance(game_ids, str | int):  # Not covered by tests
            game_ids = [game_ids]

        game_ids = [int(x) for x in game_ids if x not in self.game_ids]  # Not covered by tests

        self.game_ids.extend(game_ids)  # Not covered by tests

    @property
    def api_events(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas DataFrame of events scraped from API endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_idx (int):
                Index ID for event, e.g., 689
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., GOAL
            event_code (str):
                Code to indicate type of event that occured, e.g., 505
            description (str | None):
                Description of the event, e.g., None
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., D
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_team_jersey (str):
                Combination of team and jersey used for player identification purposes, e.g, NSH35
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_2_api_id (str | None):
                NHL API ID for player_2, e.g., None
            player_2_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            player_3_api_id (str | None):
                NHL API ID for player_3, e.g., None
            player_3_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            strength (int):
                Code to indication strength state, e.g., 1560
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            miss_reason (str | None):
                Reason shot missed, e.g., None
            opp_goalie (str | None):
                Opposing goalie, e.g., None
            opp_goalie_eh_id (str | None):
                Evolving Hockey ID for opposing goalie, e.g., None
            opp_goalie_api_id (str | None):
                NHL API ID for opposing goalie, e.g., None
            opp_goalie_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            event_team_id (int):
                NHL ID for the event team, e.g., 18
            stoppage_reason (str | None):
                Reason the play was stopped, e.g., None
            stoppage_reason_secondary (str | None):
                Secondary reason play was stopped, e.g., None
            penalty_type (str | None):
                Type of penalty taken, e.g., None
            penalty_reason (str | None):
                Reason for the penalty, e.g., None
            penalty_duration (int | None):
                Duration of the penalty, e.g., None
            home_team_defending_side (str):
                Side of the ice the home team is defending, e.g., right
            version (int):
                Increases with simultaneous events, used for combining events in the scraper, e.g., 1

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.api_events

        """
        if not self._api_events:
            self._scrape("api_events")

        df = self._finalize_dataframe(data=self._api_events, schema=APIEventSchemaPolars)

        return df

    @property
    def api_rosters(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of players scraped from API endpoint.

        Returns:
            Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            position (str):
                Player's position, e.g., L
            first_name (str):
                Player's first name, e.g., FILIP
            last_name (str):
                Player's last name, e.g., FORSBERG
            headshot_url (str):
                URL to retreive player's headshot

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.api_rosters
        """
        if not self._api_rosters:
            self._scrape("api_rosters")

        df = self._finalize_dataframe(data=self._api_rosters, schema=APIRosterSchemaPolars)

        return df

    @property
    def changes(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of changes scraped from HTML shifts & roster endpoints.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., CHANGE
            event_type (str):
                Type of change that occurred, e.g., AWAY CHANGE
            description (str | None):
                Description of the event, e.g.,
                PLAYERS ON: MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
                / PLAYERS OFF: YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            change_on_count (int):
                Number of players on, e.g., 4
            change_off_count (int):
                Number of players off, e.g., 4
            change_on (str):
                Names of players on, e.g., MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
            change_on_jersey (str):
                Combination of jerseys and numbers for the players on, e.g., NSH14, NSH19, NSH64, NSH95
            change_on_eh_id (str):
                Evolving Hockey IDs of the players on, e.g.,
                MATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE
            change_on_positions (str):
                Positions of the players on, e.g., D, C, C, C
            change_off (str):
                Names of players off, e.g., YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            change_off_jersey (str):
                Combination of jerseys and numbers for the players off, e.g., NSH7, NSH9, NSH33, NSH92
            change_off_eh_id (str):
                Evolving Hockey IDs of the players off, e.g.,
                YANNICK.WEBER, FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN
            change_off_positions (str):
                Positions of the players off, e.g., D, L, L, C
            change_on_forwards_count (int):
                Number of forwards on, e.g.,
            change_off_forwards_count (int):
                Number of forwards off, e.g., 3
            change_on_forwards (str):
                Names of forwards on, e.g., CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
            change_on_forwards_jersey (str):
                Combination of jerseys and numbers for the forwards on, e.g., NSH19, NSH64, NSH95
            change_on_forwards_eh_id (str):
                Evolving Hockey IDs of the forwards on, e.g.,
                CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE
            change_off_forwards (str):
                Names of forwards off, e.g., FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            change_off_forwards_jersey (str):
                Combination of jerseys and numbers for the forwards off, e.g., NSH9, NSH33, NSH92
            change_off_forwards_eh_id (str):
                Evolving Hockey IDs of the forwards off, e.g.,
                FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN
            change_on_defense_count (int):
                Number of defense on, e.g., 1
            change_off_defense_count (int):
                Number of defense off, e.g., 1
            change_on_defense (str):
                Names of defense on, e.g., MATTIAS EKHOLM
            change_on_defense_jersey (str):
                Combination of jerseys and numbers for the defense on, e.g., NSH14
            change_on_defense_eh_id (str):
                Evolving Hockey IDs of the defense on, e.g., MATTIAS.EKHOLM
            change_off_defense (str):
                Names of defense off, e.g., YANNICK WEBER
            change_off_defense_jersey (str):
                Combination of jerseys and numbers for the defense off, e.g., NSH7
            change_off_defebse_eh_id (str):
                Evolving Hockey IDs of the defebse off, e.g., YANNICK.WEBER
            change_on_goalie_count (int):
                Number of goalies on, e.g., 0
            change_off_goalie_count (int):
                Number of goalies off, e.g., 0
            change_on_goalies (str):
                Names of goalies on, e.g., None
            change_on_goalies_jersey (str):
                Combination of jerseys and numbers for the goalies on, e.g., None
            change_on_goalies_eh_id (str):
                Evolving Hockey IDs of the goalies on, e.g., None
            change_off_goalies (str):
                Names of goalies off, e.g., None
            change_off_goalies_jersey (str):
                Combination of jerseys and numbers for the goalies off, e.g., None
            change_off_goalies_eh_id (str):
                Evolving Hockey IDs of the goalies off, e.g., None
            is_home (int):
                Dummy indicator whether change team is home, e.g., 0
            is_away (int):
                Dummy indicator whether change team is away, e.g., 1
            team_venue (str):
                Whether team is home or away, e.g., AWAY

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.changes
        """
        # TODO: Add API ID columns to documentation

        if not self._changes:
            self._scrape("changes")

        df = self._finalize_dataframe(data=self._changes, schema=ChangesSchemaPolars)

        return df

    @property
    def html_events(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of events scraped from HTML endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_idx (int):
                Index ID for event, e.g., 331
            period (int):
                Period number of the event, e.g., 3
            period_time (str):
                Time elapsed in the period, e.g., 19:38
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            penalty_length (str | None):
                Duration of the penalty, e.g., None
            penalty (str | None):
                Reason for the penalty, e.g., None
            strength (str | None):
                Code to indication strength state, e.g., EV
            away_skaters (str):
                Away skaters on-ice, e.g., 13C, 19C, 64C, 14D, 59D, 35G
            home_skaters (str):
                Home skaters on-ice, e.g., 19C, 77C, 12R, 88R, 2D, 56D
            version (int):
                Increases with simultaneous events, used for combining events in the scraper, e.g., 1

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.html_events

        """
        if not self._html_events:
            self._scrape("html_events")

        df = self._finalize_dataframe(data=self._html_events, schema=HTMLEventSchemaPolars)

        return df

    @property
    def html_rosters(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of players scraped from HTML endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            jersey (int):
                Player's jersey number, e.g., 9
            position (str):
                Player's position, e.g., L
            starter (int):
                Whether the player started the game, e.g., 0
            status (str):
                Whether player is active or scratched, e.g., ACTIVE

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.html_rosters

        """
        if not self._html_rosters:
            self._scrape("html_rosters")

        df = self._finalize_dataframe(data=self._html_rosters, schema=HTMLRosterSchemaPolars)

        return df

    @property
    def play_by_play(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of play-by-play data.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            game_date (str):
                Date game was played, e.g., 2020-01-09
            event_idx (int):
                Index ID for event, e.g., 667
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            strength_state (str):
                Strength state, e.g., 5vE
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            opp_team (str):
                Opposing team, e.g., CHI
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            danger (int):
                Whether shot event occurred from danger area, e.g., 0
            high_danger (int):
                Whether shot event occurred from high-danger area, e.g., 0
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_eh_id_api (str):
                Evolving Hockey ID for player_1 from the api_events (for debugging), e.g., PEKKA.RINNE
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_eh_id_api (str | None):
                Evolving Hockey ID for player_2 from the api_events (for debugging), e.g., None
            player_2_api_id (int | None):
                NHL API ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_eh_id_api (str | None):
                Evolving Hockey ID for player_3 from the api_events (for debugging), e.g., None
            player_3_api_id (int | None):
                NHL API ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            score_state (str):
                Score of the game from event team's perspective, e.g., 4v2
            score_diff (int):
                Score differential from event team's perspective, e.g., 2
            forwards_percent (float):
                Percentage of skaters (i.e., excluding goalies) on-ice that play forward positions (e.g., F, C, L, R)
            opp_forwards_percent (float):
                Percentage of opposing skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            event_length (int):
                Time elapsed prior to next event, e.g., 5
            event_distance (float | None):
                Calculated distance of event from goal, e.g, 185.32673849177834
            pbp_distance (int):
                Distance of event from goal from description, e.g., 185
            event_angle (float | None):
                Angle of event towards goal, e.g., 57.52880770915151
            penalty (str | None):
                Name of penalty, e.g., None
            penalty_length (int | None):
                Duration of penalty, e.g., None
            home_score (int):
                Home team's score, e.g., 2
            home_score_diff (int):
                Home team's score differential, e.g., -2
            away_score (int):
                Away team's score, e.g., 4
            away_score_diff (int):
                Away team's score differential, e.g., 2
            is_home (int):
                Whether event team is home, e.g., 0
            is_away (int):
                Whether event is away, e.g., 1
            home_team (str):
                Home team, e.g., CHI
            away_team (str):
                Away team, e.g., NSH
            home_skaters (int):
                Number of home team skaters on-ice (excl. goalies), e.g., 6
            away_skaters (int):
                Number of away team skaters on-ice (excl. goalies), e.g., 5
            home_on (list | str | None):
                Name of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            home_on_eh_id (list | str | None):
                Evolving Hockey IDs of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_on_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            home_on_positions (list | str | None):
                Positions of home team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            away_on (list | str | None):
                Name of away team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            away_on_eh_id (list | str | None):
                Evolving Hockey IDs of away team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            away_on_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            away_on_positions (list | str | None):
                Positions of away team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            event_team_skaters (int | None):
                Number of event team skaters on-ice (excl. goalies), e.g., 5
            teammates (list | str | None):
                Name of event team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            teammates_eh_id (list | str | None):
                Evolving Hockey IDs of event team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            teammates_api_id (list | str | None = None):
                NHL API IDs of event team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            teammates_positions (list | str | None):
                Positions of event team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            own_goalie (list | str | None):
                Name of the event team's goalie, e.g., PEKKA RINNE
            own_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the event team's goalie, e.g., PEKKA.RINNE
            own_goalie_api_id (list | str | None):
                NHL API ID of the event team's goalie, e.g., 8471469
            forwards (list | str | None):
                Name of event team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            forwards_eh_id (list | str | None):
                Evolving Hockey IDs of event team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            forwards_api_id (list | str | None):
                NHL API IDs of event team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            forwards_count (int):
                Number of teammate skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            defense (list | str | None):
                Name of event team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            defense_eh_id (list | str | None):
                Evolving Hockey IDs of event team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            defense_api_id (list | str | None):
                NHL API IDs of event team's skaters on-ice, e.g., 8475218, 8474600
            defense_count (int):
                Number of teammate skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            opp_strength_state (str | None):
                Strength state from opposing team's perspective, e.g., Ev5
            opp_score_state (str | None):
                Score state from opposing team's perspective, e.g., 2v4
            opp_score_diff (int | None):
                Score differential from opposing team's perspective, e.g., -2
            opp_team_skaters (int | None):
                Number of opposing team skaters on-ice (excl. goalies), e.g., 6
            opp_team_on (list | str | None):
                Name of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            opp_team_on_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_team_on_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            opp_team_on_positions (list | str | None):
                Positions of opposing team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            opp_goalie (list | str | None):
                Name of the opposing team's goalie, e.g., None
            opp_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the opposing team's goalie, e.g., None
            opp_goalie_api_id (list | str | None):
                NHL API ID of the opposing team's goalie, e.g., None
            opp_forwards (list | str | None):
                Name of opposing team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            opp_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            opp_forwards_api_id (list | str | None):
                NHL API IDs of opposing team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            opp_forwards_count (int):
                Number of opposing skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            opp_defense (list | str | None):
                Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            opp_defense_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_defense_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979
            opp_defense_count (int):
                Number of opposing skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            home_forwards (list | str | None):
                Name of home team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            home_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of home team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            home_forwards_api_id (list | str | None = None):
                NHL API IDs of home team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            home_forwards_count (int):
                Number of home skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            home_forwards_percent (float):
                Percentage of home skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            home_defense (list | str | None):
                Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            home_defense_eh_id (list | str | None):
                Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_defense_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979
            home_defense_count (int):
                Number of home skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            home_defense_percent (float):
                Percentage of home skaters (i.e., excluding goalies) on-ice that play defensive positions (e.g., D)
            home_goalie (list | str | None):
                Name of the home team's goalie, e.g., None
            home_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the home team's goalie, e.g., None
            home_goalie_api_id (list | str | None):
                NHL API ID of the home team's goalie, e.g., None
            away_forwards (list | str | None):
                Name of away team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            away_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of away team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            away_forwards_api_id (list | str | None):
                NHL API IDs of away team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            away_forwards_count (int):
                Number of away skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            away_forwards_percent (float):
                Percentage of away skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            away_defense (list | str | None):
                Name of away team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            away_defense_eh_id (list | str | None):
                Evolving Hockey IDs of away team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            away_defense_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice, e.g., 8475218, 8474600
            away_defense_count (int):
                Number of away skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            away_defense_percent (float):
                Percentage of away skaters (i.e., excluding goalies) on-ice that play defensive positions (e.g., D)
            away_goalie (list | str | None):
                Name of the away team's goalie, e.g., PEKKA RINNE
            away_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the away team's goalie, e.g., PEKKA.RINNE
            away_goalie_api_id (list | str | None):
                NHL API ID of the away team's goalie, e.g., 8471469
            change_on_count (int | None):
                Number of players on, e.g., None
            change_off_count (int | None):
                Number of players off, e.g., None
            change_on (list | str | None):
                Names of the players on, e.g., None
            change_on_eh_id (list | str | None):
                Evolving Hockey IDs of the players on, e.g., None
            change_on_api_id (list | str | None):
                NHL API IDs of the players on, e.g., None
            change_on_positions (list | str | None):
                Postions of the players on, e.g., None
            change_off (list | str | None):
                Names of the players off, e.g., None
            change_off_eh_id (list | str | None):
                Evolving Hockey IDs of the players off, e.g., None
            change_off_api_id (list | str | None):
                NHL API IDs of the players off, e.g., None
            change_off_positions (list | str | None):
                Positions of the players off, e.g., None
            change_on_forwards_count (int | None):
                Number of forwards changing on, e.g., None
            change_off_forwards_count (int | None):
                Number of forwards off, e.g., None
            change_on_forwards (list | str | None):
                Names of the forwards on, e.g., None
            change_on_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards on, e.g., None
            change_on_forwards_api_id (list | str | None):
                NHL API IDs of the forwards on, e.g., None
            change_off_forwards (list | str | None):
                Names of the forwards off, e.g., None
            change_off_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards off, e.g., None
            change_off_forwards_api_id (list | str | None):
                NHL API IDs of the forwards off, e.g., None
            change_on_defense_count (int | None):
                Number of defense on, e.g., None
            change_off_defense_count (int | None):
                Number of defense off, e.g., None
            change_on_defense (list | str | None):
                Names of the defense on, e.g., None
            change_on_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense on, e.g., None
            change_on_defense_api_id (list | str | None):
                NHL API IDs of the defense on, e.g., None
            change_off_defense (list | str | None):
                Names of the defense off, e.g., None
            change_off_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense off, e.g., None
            change_off_defense_api_id (list | str | None):
                NHL API IDs of the defense off, e.g., None
            change_on_goalie_count (int | None):
                Number of goalies on, e.g., None
            change_off_goalie_count (int | None):
                Number of goalies off, e.g., None
            change_on_goalie (list | str | None):
                Name of goalie on, e.g., None
            change_on_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie on, e.g., None
            change_on_goalie_api_id (list | str | None):
                NHL API ID of the goalie on, e.g., None
            change_off_goalie (list | str | None):
                Name of the goalie off, e.g., None
            change_off_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie off, e.g., None
            change_off_goalie_api_id (list | str | None):
                NHL API ID of the goalie off, e.g., None
            pred_goal (float):
                xG value for a given shot attempt, e.g., 0.489021
            pred_goal_adj (float):
                Score- and venue-adjusted xG value for a given shot attempt,
                e.g., 0.489021
            goal (int):
                Dummy indicator whether event is a goal, e.g., 1
            goal_adj (float):
                Score- and venue-adjusted value for a goal, e.g., 1.0
            hd_goal (int):
                Dummy indicator whether event is a high-danger goal, e.g., 0
            shot (int):
                Dummy indicator whether event is a shot, e.g., 1
            shot_adj (float):
                Score- and venue-adjusted value for a shot, e.g., 1.0
            hd_shot (int):
                Dummy indicator whether event is a high-danger shot, e.g., 0
            miss (int):
                Dummy indicator whether event is a miss, e.g., 0
            miss_adj (float):
                Score- and venue-adjusted value for a missed shot, e.g., 0.0
            hd_miss (int):
                Dummy indicator whether event is a high-danger missed shot, e.g., 0
            fenwick (int):
                Dummy indicator whether event is a fenwick event, e.g., 1
            fenwick_adj (float):
                Score- and venue-adjusted value for a fenwick event, e.g., 1.0
            hd_fenwick (int):
                Dummy indicator whether event is a high-danger fenwick event, e.g., 0
            corsi (int):
                Dummy indicator whether event is a corsi event, e.g., 1
            corsi_adj (float):
                Score- and venue-adjusted value for a corsi event, e.g., 1.0
            block (int):
                Dummy indicator whether event is a block, e.g., 0
            block_adj (float):
                Score- and venue-adjusted value for a blocked shot, e.g., 0.0
            teammate_block (int):
                Dummy indicator whether event is a shot blocked by a teammate, e.g., 0
            teammate_block_adj (float):
                Score- and venue-adjusted value for a shot blocked by a teammate, e.g., 0.0
            hit (int):
                Dummy indicator whether event is a hit, e.g., 0
            give (int):
                Dummy indicator whether event is a give, e.g., 0
            take (int):
                Dummy indicator whether event is a take, e.g., 0
            fac (int):
                Dummy indicator whether event is a faceoff, e.g., 0
            penl (int):
                Dummy indicator whether event is a penalty, e.g., 0
            change (int):
                Dummy indicator whether event is a change, e.g., 0
            stop (int):
                Dummy indicator whether event is a stop, e.g., 0
            chl (int):
                Dummy indicator whether event is a challenge, e.g., 0
            ozf (int):
                Dummy indicator whether event is a offensive zone faceoff, e.g., 0
            nzf (int):
                Dummy indicator whether event is a neutral zone faceoff, e.g., 0
            dzf (int):
                Dummy indicator whether event is a defensive zone faceoff, e.g., 0
            ozc (int):
                Dummy indicator whether event is a offensive zone change, e.g., 0
            nzc (int):
                Dummy indicator whether event is a neutral zone change, e.g., 0
            dzc (int):
                Dummy indicator whether event is a defensive zone change, e.g., 0
            otf (int):
                Dummy indicator whether event is an on-the-fly change, e.g., 0
            pen0 (int):
                Dummy indicator whether event is a penalty, e.g., 0
            pen2 (int):
                Dummy indicator whether event is a minor penalty, e.g., 0
            pen4 (int):
                Dummy indicator whether event is a double minor penalty, e.g., 0
            pen5 (int):
                Dummy indicator whether event is a major penalty, e.g., 0
            pen10 (int):
                Dummy indicator whether event is a game misconduct penalty, e.g., 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.play_by_play

        """
        # TODO: Add change on / change off API ID columns to documentation

        if self.game_ids != self._scraped_play_by_play:
            self._scrape("play_by_play")

        df = self._finalize_dataframe(data=self._play_by_play, schema=PBPSchemaPolars)

        return df

    @property
    def play_by_play_ext(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of play-by-play data.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            game_date (str):
                Date game was played, e.g., 2020-01-09
            event_idx (int):
                Index ID for event, e.g., 667
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            strength_state (str):
                Strength state, e.g., 5vE
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            opp_team (str):
                Opposing team, e.g., CHI
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            danger (int):
                Whether shot event occurred from danger area, e.g., 0
            high_danger (int):
                Whether shot event occurred from high-danger area, e.g., 0
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_eh_id_api (str):
                Evolving Hockey ID for player_1 from the api_events (for debugging), e.g., PEKKA.RINNE
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_eh_id_api (str | None):
                Evolving Hockey ID for player_2 from the api_events (for debugging), e.g., None
            player_2_api_id (int | None):
                NHL API ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_eh_id_api (str | None):
                Evolving Hockey ID for player_3 from the api_events (for debugging), e.g., None
            player_3_api_id (int | None):
                NHL API ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            score_state (str):
                Score of the game from event team's perspective, e.g., 4v2
            score_diff (int):
                Score differential from event team's perspective, e.g., 2
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            event_length (int):
                Time elapsed since previous event, e.g., 5
            event_distance (float | None):
                Calculated distance of event from goal, e.g, 185.32673849177834
            pbp_distance (int):
                Distance of event from goal from description, e.g., 185
            event_angle (float | None):
                Angle of event towards goal, e.g., 57.52880770915151
            penalty (str | None):
                Name of penalty, e.g., None
            penalty_length (int | None):
                Duration of penalty, e.g., None
            home_score (int):
                Home team's score, e.g., 2
            home_score_diff (int):
                Home team's score differential, e.g., -2
            away_score (int):
                Away team's score, e.g., 4
            away_score_diff (int):
                Away team's score differential, e.g., 2
            is_home (int):
                Whether event team is home, e.g., 0
            is_away (int):
                Whether event is away, e.g., 1
            home_team (str):
                Home team, e.g., CHI
            away_team (str):
                Away team, e.g., NSH
            home_skaters (int):
                Number of home team skaters on-ice (excl. goalies), e.g., 6
            away_skaters (int):
                Number of away team skaters on-ice (excl. goalies), e.g., 5
            home_on (list | str | None):
                Name of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            home_on_eh_id (list | str | None):
                Evolving Hockey IDs of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_on_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            home_on_positions (list | str | None):
                Positions of home team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            away_on (list | str | None):
                Name of away team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            away_on_eh_id (list | str | None):
                Evolving Hockey IDs of away team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            away_on_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            away_on_positions (list | str | None):
                Positions of away team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            event_team_skaters (int | None):
                Number of event team skaters on-ice (excl. goalies), e.g., 5
            teammates (list | str | None):
                Name of event team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            teammates_eh_id (list | str | None):
                Evolving Hockey IDs of event team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            teammates_api_id (list | str | None = None):
                NHL API IDs of event team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            teammates_positions (list | str | None):
                Positions of event team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            own_goalie (list | str | None):
                Name of the event team's goalie, e.g., PEKKA RINNE
            own_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the event team's goalie, e.g., PEKKA.RINNE
            own_goalie_api_id (list | str | None):
                NHL API ID of the event team's goalie, e.g., 8471469
            forwards (list | str | None):
                Name of event team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            forwards_eh_id (list | str | None):
                Evolving Hockey IDs of event team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            forwards_api_id (list | str | None):
                NHL API IDs of event team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            defense (list | str | None):
                Name of event team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            defense_eh_id (list | str | None):
                Evolving Hockey IDs of event team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            defense_api_id (list | str | None):
                NHL API IDs of event team's skaters on-ice, e.g., 8475218, 8474600
            opp_strength_state (str | None):
                Strength state from opposing team's perspective, e.g., Ev5
            opp_score_state (str | None):
                Score state from opposing team's perspective, e.g., 2v4
            opp_score_diff (int | None):
                Score differential from opposing team's perspective, e.g., -2
            opp_team_skaters (int | None):
                Number of opposing team skaters on-ice (excl. goalies), e.g., 6
            opp_team_on (list | str | None):
                Name of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            opp_team_on_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_team_on_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            opp_team_on_positions (list | str | None):
                Positions of opposing team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            opp_goalie (list | str | None):
                Name of the opposing team's goalie, e.g., None
            opp_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the opposing team's goalie, e.g., None
            opp_goalie_api_id (list | str | None):
                NHL API ID of the opposing team's goalie, e.g., None
            opp_forwards (list | str | None):
                Name of opposing team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            opp_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            opp_forwards_api_id (list | str | None):
                NHL API IDs of opposing team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            opp_defense (list | str | None):
                Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            opp_defense_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_defense_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979
            home_forwards (list | str | None):
                Name of home team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            home_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of home team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            home_forwards_api_id (list | str | None = None):
                NHL API IDs of home team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            home_defense (list | str | None):
                Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            home_defense_eh_id (list | str | None):
                Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_defense_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979
            home_goalie (list | str | None):
                Name of the home team's goalie, e.g., None
            home_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the home team's goalie, e.g., None
            home_goalie_api_id (list | str | None):
                NHL API ID of the home team's goalie, e.g., None
            away_forwards (list | str | None):
                Name of away team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            away_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of away team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            away_forwards_api_id (list | str | None):
                NHL API IDs of away team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            away_defense (list | str | None):
                Name of away team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            away_defense_eh_id (list | str | None):
                Evolving Hockey IDs of away team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            away_defense_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice, e.g., 8475218, 8474600
            away_goalie (list | str | None):
                Name of the away team's goalie, e.g., PEKKA RINNE
            away_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the away team's goalie, e.g., PEKKA.RINNE
            away_goalie_api_id (list | str | None):
                NHL API ID of the away team's goalie, e.g., 8471469
            change_on_count (int | None):
                Number of players on, e.g., None
            change_off_count (int | None):
                Number of players off, e.g., None
            change_on (list | str | None):
                Names of the players on, e.g., None
            change_on_eh_id (list | str | None):
                Evolving Hockey IDs of the players on, e.g., None
            change_on_positions (list | str | None):
                Postions of the players on, e.g., None
            change_off (list | str | None):
                Names of the players off, e.g., None
            change_off_eh_id (list | str | None):
                Evolving Hockey IDs of the players off, e.g., None
            change_off_positions (list | str | None):
                Positions of the players off, e.g., None
            change_on_forwards_count (int | None):
                Number of forwards changing on, e.g., None
            change_off_forwards_count (int | None):
                Number of forwards off, e.g., None
            change_on_forwards (list | str | None):
                Names of the forwards on, e.g., None
            change_on_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards on, e.g., None
            change_off_forwards (list | str | None):
                Names of the forwards off, e.g., None
            change_off_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards off, e.g., None
            change_on_defense_count (int | None):
                Number of defense on, e.g., None
            change_off_defense_count (int | None):
                Number of defense off, e.g., None
            change_on_defense (list | str | None):
                Names of the defense on, e.g., None
            change_on_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense on, e.g., None
            change_off_defense (list | str | None):
                Names of the defense off, e.g., None
            change_off_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense off, e.g., None
            change_on_goalie_count (int | None):
                Number of goalies on, e.g., None
            change_off_goalie_count (int | None):
                Number of goalies off, e.g., None
            change_on_goalie (list | str | None):
                Name of goalie on, e.g., None
            change_on_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie on, e.g., None
            change_off_goalie (list | str | None):
                Name of the goalie off, e.g., None
            change_off_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie off, e.g., None
            goal (int):
                Dummy indicator whether event is a goal, e.g., 1
            shot (int):
                Dummy indicator whether event is a shot, e.g., 1
            miss (int):
                Dummy indicator whether event is a miss, e.g., 0
            fenwick (int):
                Dummy indicator whether event is a fenwick event, e.g., 1
            corsi (int):
                Dummy indicator whether event is a corsi event, e.g., 1
            block (int):
                Dummy indicator whether event is a block, e.g., 0
            hit (int):
                Dummy indicator whether event is a hit, e.g., 0
            give (int):
                Dummy indicator whether event is a give, e.g., 0
            take (int):
                Dummy indicator whether event is a take, e.g., 0
            fac (int):
                Dummy indicator whether event is a faceoff, e.g., 0
            penl (int):
                Dummy indicator whether event is a penalty, e.g., 0
            change (int):
                Dummy indicator whether event is a change, e.g., 0
            stop (int):
                Dummy indicator whether event is a stop, e.g., 0
            chl (int):
                Dummy indicator whether event is a challenge, e.g., 0
            ozf (int):
                Dummy indicator whether event is a offensive zone faceoff, e.g., 0
            nzf (int):
                Dummy indicator whether event is a neutral zone faceoff, e.g., 0
            dzf (int):
                Dummy indicator whether event is a defensive zone faceoff, e.g., 0
            ozc (int):
                Dummy indicator whether event is a offensive zone change, e.g., 0
            nzc (int):
                Dummy indicator whether event is a neutral zone change, e.g., 0
            dzc (int):
                Dummy indicator whether event is a defensive zone change, e.g., 0
            otf (int):
                Dummy indicator whether event is an on-the-fly change, e.g., 0
            pen0 (int):
                Dummy indicator whether event is a penalty, e.g., 0
            pen2 (int):
                Dummy indicator whether event is a minor penalty, e.g., 0
            pen4 (int):
                Dummy indicator whether event is a double minor penalty, e.g., 0
            pen5 (int):
                Dummy indicator whether event is a major penalty, e.g., 0
            pen10 (int):
                Dummy indicator whether event is a game misconduct penalty, e.g., 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.play_by_play

        """
        # TODO: Update documentation for extended version of play_by_play

        if self.game_ids != self._scraped_play_by_play:
            self._scrape("play_by_play")

        df = self._finalize_dataframe(data=self._play_by_play_ext, schema=PBPExtSchemaPolars)

        return df

    @property
    def rosters(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of players scraped from API & HTML endpoints.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            api_id (int | None):
                Player's NHL API ID, e.g., 8476887
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            jersey (int):
                Player's jersey number, e.g., 9
            position (str):
                Player's position, e.g., L
            starter (int):
                Whether the player started the game, e.g., 0
            status (str):
                Whether player is active or scratched, e.g., ACTIVE
            headshot_url (str | None):
                URL to get player's headshot, e.g., https://assets.nhle.com/mugs/nhl/20192020/NSH/8476887.png

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.rosters

        """
        if not self._rosters:
            self._scrape("rosters")

        df = self._finalize_dataframe(data=self._rosters, schema=RosterSchemaPolars)

        return df

    @property
    def shifts(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of shifts scraped from HTML endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            position (str):
                Player's position, e.g., L
            jersey (int):
                Player's jersey number, e.g., 9
            shift_count (int):
                Shift number for that player, e.g., 1
            period (int):
                Period number for the shift, e.g., 1
            start_time (str):
                Time shift started, e.g., 0:00
            end_time (str):
                Time shift ended, e.g., 0:18
            duration (str):
                Length of shift, e.g, 00:18
            start_time_seconds (int):
                Time shift started in seconds, e.g., 0
            end_time_seconds (int):
                Time shift ended in seconds, e.g., 18
            duration_seconds (int):
                Length of shift in seconds, e.g., 18
            shift_start (str):
                Time the shift started as the original string, e.g., 0:00 / 20:00
            shift_end (str):
                Time the shift ended as the original string, e.g., 0:18 / 19:42
            goalie (int):
                Whether player is a goalie, e.g., 0
            is_home (int):
                Whether player is home e.g., 0
            is_away (int):
                Whether player is away, e.g., 1
            team_venue (str):
                Whether player is home or away, e.g., AWAY

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.shifts

        """
        if not self._shifts:
            self._scrape("shifts")

        df = self._finalize_dataframe(data=self._shifts, schema=ShiftsSchemaPolars)

        return df

    def _prep_ind(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
    ) -> None:
        """Prepares DataFrame of individual stats from play-by-play data.

        Nested within `prep_stats` method.

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            strength_state (bool):
                Determines if stats account for strength state
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            g (int):
                Individual goals scored, e.g, 0
            g_adj (float):
                Score- and venue-adjusted individual goals scored, e.g., 0.0
            ihdg (int):
                Individual high-danger goals scored, e.g, 0
            a1 (int):
                Individual primary assists, e.g, 0
            a2 (int):
                Individual secondary assists, e.g, 0
            ixg (float):
                Individual xG for, e.g, 1.014336
            ixg_adj (float):
                Score- and venue-adjusted indiviudal xG for, e.g., 1.101715
            isf (int):
                Individual shots taken, e.g, 3
            isf_adj (float):
                Score- and venue-adjusted individual shots taken, e.g., 3.262966
            ihdsf (int):
                High-danger shots taken, e.g, 3
            imsf (int):
                Individual missed shots, e.g, 0
            imsf_adj (float):
                Score- and venue-adjusted individual missed shots, e.g., 0.0
            ihdm (int):
                High-danger missed shots, e.g, 0
            iff (int):
                Individual fenwick for, e.g., 3
            iff_adj (float):
                Score- and venue-adjusted individual fenwick events, e.g., 3.279018
            ihdf (int):
                High-danger fenwick events for, e.g., 3
            isb (int):
                Shots taken that were blocked, e.g, 0
            isb_adj (float):
                Score- and venue-adjusted individual shots blocked, e.g, 0.0
            icf (int):
                Individual corsi for, e.g., 3
            icf_adj (float):
                Score- and venue-adjusted individual corsi events, e.g, 3.279018
            ibs (int):
                Individual shots blocked on defense, e.g, 0
            ibs_adj (float):
                Score- and venue-adjusted shots blocked, e.g., 0.0
            igive (int):
                Individual giveaways, e.g, 0
            itake (int):
                Individual takeaways, e.g, 0
            ihf (int):
                Individual hits for, e.g, 0
            iht (int):
                Individual hits taken, e.g, 0
            ifow (int):
                Individual faceoffs won, e.g, 0
            ifol (int):
                Individual faceoffs lost, e.g, 0
            iozfw (int):
                Individual faceoffs won in offensive zone, e.g, 0
            iozfl (int):
                Individual faceoffs lost in offensive zone, e.g, 0
            inzfw (int):
                Individual faceoffs won in neutral zone, e.g, 0
            inzfl (int):
                Individual faceoffs lost in neutral zone, e.g, 0
            idzfw (int):
                Individual faceoffs won in defensive zone, e.g, 0
            idzfl (int):
                Individual faceoffs lost in defensive zone, e.g, 0
            a1_xg (float):
                xG on primary assists, e.g, 0
            a2_xg (float):
                xG on secondary assists, e.g, 0
            ipent0 (int):
                Individual penalty shots against, e.g, 0
            ipent2 (int):
                Individual minor penalties taken, e.g, 0
            ipent4 (int):
                Individual double minor penalties taken, e.g, 0
            ipent5 (int):
                Individual major penalties taken, e.g, 0
            ipent10 (int):
                Individual game misconduct penalties taken, e.g, 0
            ipend0 (int):
                Individual penalty shots drawn, e.g, 0
            ipend2 (int):
                Individual minor penalties taken, e.g, 0
            ipend4 (int):
                Individual double minor penalties drawn, e.g, 0
            ipend5 (int):
                Individual major penalties drawn, e.g, 0
            ipend10 (int):
                Individual game misconduct penalties drawn, e.g, 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Aggregates individual stats to game level
            >>> scraper._prep_ind(level="game")

            Aggregates individual stats to season level
            >>> scraper._prep_ind(level="season")

            Aggregates individual stats to game level, accounting for teammates on-ice
            >>> scraper._prep_ind(level="game", teammates=True)

        """
        if self._backend == "polars":
            ind_stats = prep_ind_polars(
                self.play_by_play,
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
            )

        if self._backend == "pandas":
            ind_stats = prep_ind_pandas(
                self.play_by_play,
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
            )

        self._ind_stats = ind_stats

    @property
    def ind_stats(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of individual stats aggregated from play-by-play data.

        Nested within `prep_stats` method.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            g (int):
                Individual goals scored, e.g, 0
            g_adj (float):
                Score- and venue-adjusted individual goals scored, e.g., 0.0
            ihdg (int):
                Individual high-danger goals scored, e.g, 0
            a1 (int):
                Individual primary assists, e.g, 0
            a2 (int):
                Individual secondary assists, e.g, 0
            ixg (float):
                Individual xG for, e.g, 1.014336
            ixg_adj (float):
                Score- and venue-adjusted indiviudal xG for, e.g., 1.101715
            isf (int):
                Individual shots taken, e.g, 3
            isf_adj (float):
                Score- and venue-adjusted individual shots taken, e.g., 3.262966
            ihdsf (int):
                High-danger shots taken, e.g, 3
            imsf (int):
                Individual missed shots, e.g, 0
            imsf_adj (float):
                Score- and venue-adjusted individual missed shots, e.g., 0.0
            ihdm (int):
                High-danger missed shots, e.g, 0
            iff (int):
                Individual fenwick for, e.g., 3
            iff_adj (float):
                Score- and venue-adjusted individual fenwick events, e.g., 3.279018
            ihdf (int):
                High-danger fenwick events for, e.g., 3
            isb (int):
                Shots taken that were blocked, e.g, 0
            isb_adj (float):
                Score- and venue-adjusted individual shots blocked, e.g, 0.0
            icf (int):
                Individual corsi for, e.g., 3
            icf_adj (float):
                Score- and venue-adjusted individual corsi events, e.g, 3.279018
            ibs (int):
                Individual shots blocked on defense, e.g, 0
            ibs_adj (float):
                Score- and venue-adjusted shots blocked, e.g., 0.0
            igive (int):
                Individual giveaways, e.g, 0
            itake (int):
                Individual takeaways, e.g, 0
            ihf (int):
                Individual hits for, e.g, 0
            iht (int):
                Individual hits taken, e.g, 0
            ifow (int):
                Individual faceoffs won, e.g, 0
            ifol (int):
                Individual faceoffs lost, e.g, 0
            iozfw (int):
                Individual faceoffs won in offensive zone, e.g, 0
            iozfl (int):
                Individual faceoffs lost in offensive zone, e.g, 0
            inzfw (int):
                Individual faceoffs won in neutral zone, e.g, 0
            inzfl (int):
                Individual faceoffs lost in neutral zone, e.g, 0
            idzfw (int):
                Individual faceoffs won in defensive zone, e.g, 0
            idzfl (int):
                Individual faceoffs lost in defensive zone, e.g, 0
            a1_xg (float):
                xG on primary assists, e.g, 0
            a2_xg (float):
                xG on secondary assists, e.g, 0
            ipent0 (int):
                Individual penalty shots against, e.g, 0
            ipent2 (int):
                Individual minor penalties taken, e.g, 0
            ipent4 (int):
                Individual double minor penalties taken, e.g, 0
            ipent5 (int):
                Individual major penalties taken, e.g, 0
            ipent10 (int):
                Individual game misconduct penalties taken, e.g, 0
            ipend0 (int):
                Individual penalty shots drawn, e.g, 0
            ipend2 (int):
                Individual minor penalties taken, e.g, 0
            ipend4 (int):
                Individual double minor penalties drawn, e.g, 0
            ipend5 (int):
                Individual major penalties drawn, e.g, 0
            ipend10 (int):
                Individual game misconduct penalties drawn, e.g, 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.ind_stats

        """
        if self._backend == "polars":
            if self._ind_stats.is_empty():
                self._prep_ind()

        if self._backend == "pandas":
            if self._ind_stats.empty:
                self._prep_ind()

        return self._ind_stats

    def _prep_oi(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
    ) -> None:
        """Prepares DataFrame of on-ice stats from play-by-play data.

        Nested within `prep_stats` method.

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            strength_state (bool):
                Determines if stats account for strength state
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.366730
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 4.350622
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            ozs (int):
                Offensive zone starts, e.g, 0
            nzs (int):
                Neutral zone starts, e.g, 0
            dzs (int):
                Defenzive zone starts, e.g, 0
            otf (int):
                On-the-fly starts, e.g, 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Prepares on-ice dataframe with default options
            >>> scraper._prep_oi()

            On-ice statistics, aggregated to season level
            >>> scraper._prep_oi(level="season")

            On-ice statistics, aggregated to game level, accounting for teammates
            >>> scraper._prep_oi(level="game", teammates=True)

        """
        if self._backend == "polars":
            oi_stats = prep_oi_polars(
                df=self.play_by_play,
                df_ext=self.play_by_play_ext,
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
            )

        if self._backend == "pandas":
            oi_stats = prep_oi_pandas(
                df=self.play_by_play,
                df_ext=self.play_by_play_ext,
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
            )

        self._oi_stats = oi_stats

    @property
    def oi_stats(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of on-ice stats aggregated from play-by-play data.

        Nested within `prep_stats` method.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.366730
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 4.350622
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            ozs (int):
                Offensive zone starts, e.g, 0
            nzs (int):
                Neutral zone starts, e.g, 0
            dzs (int):
                Defenzive zone starts, e.g, 0
            otf (int):
                On-the-fly starts, e.g, 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.ind_stats

        """
        if self._backend == "polars":
            if self._oi_stats.is_empty():
                self._prep_oi()

        if self._backend == "pandas":
            if self._oi_stats.empty:
                self._prep_oi()

        return self._oi_stats

    def _prep_stats(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
    ) -> None:
        """Prepares DataFrame of individual and on-ice stats from play-by-play data.

        Nested within `prep_stats` method.

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            strength_state (bool):
                Determines if stats account for strength state
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            g (int):
                Individual goals scored, e.g, 0
            g_adj (float):
                Score- and venue-adjusted individual goals scored, e.g., 0.0
            ihdg (int):
                Individual high-danger goals scored, e.g, 0
            a1 (int):
                Individual primary assists, e.g, 0
            a2 (int):
                Individual secondary assists, e.g, 0
            ixg (float):
                Individual xG for, e.g, 1.014336
            ixg_adj (float):
                Score- and venue-adjusted indiviudal xG for, e.g., 1.101715
            isf (int):
                Individual shots taken, e.g, 3
            isf_adj (float):
                Score- and venue-adjusted individual shots taken, e.g., 3.262966
            ihdsf (int):
                High-danger shots taken, e.g, 3
            imsf (int):
                Individual missed shots, e.g, 0
            imsf_adj (float):
                Score- and venue-adjusted individual missed shots, e.g., 0.0
            ihdm (int):
                High-danger missed shots, e.g, 0
            iff (int):
                Individual fenwick for, e.g., 3
            iff_adj (float):
                Score- and venue-adjusted individual fenwick events, e.g., 3.279018
            ihdf (int):
                High-danger fenwick events for, e.g., 3
            isb (int):
                Shots taken that were blocked, e.g, 0
            isb_adj (float):
                Score- and venue-adjusted individual shots blocked, e.g, 0.0
            icf (int):
                Individual corsi for, e.g., 3
            icf_adj (float):
                Score- and venue-adjusted individual corsi events, e.g, 3.279018
            ibs (int):
                Individual shots blocked on defense, e.g, 0
            ibs_adj (float):
                Score- and venue-adjusted shots blocked, e.g., 0.0
            igive (int):
                Individual giveaways, e.g, 0
            itake (int):
                Individual takeaways, e.g, 0
            ihf (int):
                Individual hits for, e.g, 0
            iht (int):
                Individual hits taken, e.g, 0
            ifow (int):
                Individual faceoffs won, e.g, 0
            ifol (int):
                Individual faceoffs lost, e.g, 0
            iozfw (int):
                Individual faceoffs won in offensive zone, e.g, 0
            iozfl (int):
                Individual faceoffs lost in offensive zone, e.g, 0
            inzfw (int):
                Individual faceoffs won in neutral zone, e.g, 0
            inzfl (int):
                Individual faceoffs lost in neutral zone, e.g, 0
            idzfw (int):
                Individual faceoffs won in defensive zone, e.g, 0
            idzfl (int):
                Individual faceoffs lost in defensive zone, e.g, 0
            a1_xg (float):
                xG on primary assists, e.g, 0
            a2_xg (float):
                xG on secondary assists, e.g, 0
            ipent0 (int):
                Individual penalty shots against, e.g, 0
            ipent2 (int):
                Individual minor penalties taken, e.g, 0
            ipent4 (int):
                Individual double minor penalties taken, e.g, 0
            ipent5 (int):
                Individual major penalties taken, e.g, 0
            ipent10 (int):
                Individual game misconduct penalties taken, e.g, 0
            ipend0 (int):
                Individual penalty shots drawn, e.g, 0
            ipend2 (int):
                Individual minor penalties taken, e.g, 0
            ipend4 (int):
                Individual double minor penalties drawn, e.g, 0
            ipend5 (int):
                Individual major penalties drawn, e.g, 0
            ipend10 (int):
                Individual game misconduct penalties drawn, e.g, 0
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.366730
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 4.350622
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            ozs (int):
                Offensive zone starts, e.g, 0
            nzs (int):
                Neutral zone starts, e.g, 0
            dzs (int):
                Defenzive zone starts, e.g, 0
            otf (int):
                On-the-fly starts, e.g, 0
            g_p60 (float):
                Goals scored per 60 minutes
            ihdg_p60 (float):
                Individual high-danger goals scored per 60
            a1_p60 (float):
                Primary assists per 60 minutes
            a2_p60 (float):
                Secondary per 60 minutes
            ixg_p60 (float):
                Individual xG for per 60 minutes
            isf_p60 (float):
                Individual shots for per 60 minutes
            ihdsf_p60 (float):
                Individual high-danger shots for per 60 minutes
            imsf_p60 (float):
                Individual missed shorts for per 60 minutes
            ihdm_p60 (float):
                Individual high-danger missed shots for per 60 minutes
            iff_p60 (float):
                Individual fenwick for per 60 minutes
            ihdff_p60 (float):
                Individual high-danger fenwick for per 60 minutes
            isb_p60 (float):
                Individual shots blocked (for) per 60 minutes
            icf_p60 (float):
                Individual corsi for per 60 minutes
            ibs_p60 (float):
                Individual blocked shots (against) per 60 minutes
            igive_p60 (float):
                Individual giveaways per 60 minutes
            itake_p60 (float):
                Individual takeaways per 60 minutes
            ihf_p60 (float):
                Individual hits for per 60 minutes
            iht_p60 (float):
                Individual hits taken per 60 minutes
            a1_xg_p60 (float):
                Individual primary assists' xG per 60 minutes
            a2_xg_p60 (float):
                Individual secondary assists' xG per 60 minutes
            ipent0_p60 (float):
                Individual penalty shots taken per 60 minutes
            ipent2_p60 (float):
                Individual minor penalties taken per 60 minutes
            ipent4_p60 (float):
                Individual double minor penalties taken per 60 minutes
            ipent5_p60 (float):
                Individual major penalties taken per 60 minutes
            ipent10_p60 (float):
                Individual game misconduct pentalties taken per 60 minutes
            ipend0_p60 (float):
                Individual penalty shots drawn per 60 minutes
            ipend2_p60 (float):
                Individual minor penalties drawn per 60 minutes
            ipend4_p60 (float):
                Individual double minor penalties drawn per 60 minutes
            ipend5_p60 (float):
                Individual major penalties drawn per 60 minutes
            ipend10_p60 (float):
                Individual game misconduct penalties drawn per 60 minutes
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF /
                (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF /
                (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF /
                (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
                HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Prepares individual and on-ice dataframe with default options
            >>> scraper._prep_stats()

            Individual and on-ice statistics, aggregated to season level
            >>> scraper._prep_stats(level="season")

            Individual and on-ice statistics, aggregated to game level, accounting for teammates
            >>> scraper._prep_stats(level="game", teammates=True)

        """
        if self._backend == "polars":
            if self._ind_stats.is_empty():
                self._prep_ind(
                    level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
                )

            if self._oi_stats.is_empty():
                self._prep_oi(
                    level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
                )

        if self._backend == "pandas":
            if self._ind_stats.empty:
                self._prep_ind(
                    level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
                )

            if self._oi_stats.empty:
                self._prep_oi(
                    level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
                )

        if self._backend == "polars":
            stats = prep_stats_polars(ind_stats_df=self.ind_stats, oi_stats_df=self.oi_stats)

        if self._backend == "pandas":
            stats = prep_stats_pandas(ind_stats_df=self.ind_stats, oi_stats_df=self.oi_stats)

        self._stats = stats

    def prep_stats(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
    ) -> None:
        """Prepares DataFrame of individual and on-ice stats from play-by-play data.

        Used to prepare, or reset prepared data for later analysis

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            strength_state (bool):
                Determines if stats account for strength state
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice
            disable_progress_bar (bool):
                Determines whether to display the progress bar

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            g (int):
                Individual goals scored, e.g, 0
            g_adj (float):
                Score- and venue-adjusted individual goals scored, e.g., 0.0
            ihdg (int):
                Individual high-danger goals scored, e.g, 0
            a1 (int):
                Individual primary assists, e.g, 0
            a2 (int):
                Individual secondary assists, e.g, 0
            ixg (float):
                Individual xG for, e.g, 1.014336
            ixg_adj (float):
                Score- and venue-adjusted indiviudal xG for, e.g., 1.101715
            isf (int):
                Individual shots taken, e.g, 3
            isf_adj (float):
                Score- and venue-adjusted individual shots taken, e.g., 3.262966
            ihdsf (int):
                High-danger shots taken, e.g, 3
            imsf (int):
                Individual missed shots, e.g, 0
            imsf_adj (float):
                Score- and venue-adjusted individual missed shots, e.g., 0.0
            ihdm (int):
                High-danger missed shots, e.g, 0
            iff (int):
                Individual fenwick for, e.g., 3
            iff_adj (float):
                Score- and venue-adjusted individual fenwick events, e.g., 3.279018
            ihdf (int):
                High-danger fenwick events for, e.g., 3
            isb (int):
                Shots taken that were blocked, e.g, 0
            isb_adj (float):
                Score- and venue-adjusted individual shots blocked, e.g, 0.0
            icf (int):
                Individual corsi for, e.g., 3
            icf_adj (float):
                Score- and venue-adjusted individual corsi events, e.g, 3.279018
            ibs (int):
                Individual shots blocked on defense, e.g, 0
            ibs_adj (float):
                Score- and venue-adjusted shots blocked, e.g., 0.0
            igive (int):
                Individual giveaways, e.g, 0
            itake (int):
                Individual takeaways, e.g, 0
            ihf (int):
                Individual hits for, e.g, 0
            iht (int):
                Individual hits taken, e.g, 0
            ifow (int):
                Individual faceoffs won, e.g, 0
            ifol (int):
                Individual faceoffs lost, e.g, 0
            iozfw (int):
                Individual faceoffs won in offensive zone, e.g, 0
            iozfl (int):
                Individual faceoffs lost in offensive zone, e.g, 0
            inzfw (int):
                Individual faceoffs won in neutral zone, e.g, 0
            inzfl (int):
                Individual faceoffs lost in neutral zone, e.g, 0
            idzfw (int):
                Individual faceoffs won in defensive zone, e.g, 0
            idzfl (int):
                Individual faceoffs lost in defensive zone, e.g, 0
            a1_xg (float):
                xG on primary assists, e.g, 0
            a2_xg (float):
                xG on secondary assists, e.g, 0
            ipent0 (int):
                Individual penalty shots against, e.g, 0
            ipent2 (int):
                Individual minor penalties taken, e.g, 0
            ipent4 (int):
                Individual double minor penalties taken, e.g, 0
            ipent5 (int):
                Individual major penalties taken, e.g, 0
            ipent10 (int):
                Individual game misconduct penalties taken, e.g, 0
            ipend0 (int):
                Individual penalty shots drawn, e.g, 0
            ipend2 (int):
                Individual minor penalties taken, e.g, 0
            ipend4 (int):
                Individual double minor penalties drawn, e.g, 0
            ipend5 (int):
                Individual major penalties drawn, e.g, 0
            ipend10 (int):
                Individual game misconduct penalties drawn, e.g, 0
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.366730
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 4.350622
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            ozs (int):
                Offensive zone starts, e.g, 0
            nzs (int):
                Neutral zone starts, e.g, 0
            dzs (int):
                Defenzive zone starts, e.g, 0
            otf (int):
                On-the-fly starts, e.g, 0
            g_p60 (float):
                Goals scored per 60 minutes
            ihdg_p60 (float):
                Individual high-danger goals scored per 60
            a1_p60 (float):
                Primary assists per 60 minutes
            a2_p60 (float):
                Secondary per 60 minutes
            ixg_p60 (float):
                Individual xG for per 60 minutes
            isf_p60 (float):
                Individual shots for per 60 minutes
            ihdsf_p60 (float):
                Individual high-danger shots for per 60 minutes
            imsf_p60 (float):
                Individual missed shorts for per 60 minutes
            ihdm_p60 (float):
                Individual high-danger missed shots for per 60 minutes
            iff_p60 (float):
                Individual fenwick for per 60 minutes
            ihdff_p60 (float):
                Individual high-danger fenwick for per 60 minutes
            isb_p60 (float):
                Individual shots blocked (for) per 60 minutes
            icf_p60 (float):
                Individual corsi for per 60 minutes
            ibs_p60 (float):
                Individual blocked shots (against) per 60 minutes
            igive_p60 (float):
                Individual giveaways per 60 minutes
            itake_p60 (float):
                Individual takeaways per 60 minutes
            ihf_p60 (float):
                Individual hits for per 60 minutes
            iht_p60 (float):
                Individual hits taken per 60 minutes
            a1_xg_p60 (float):
                Individual primary assists' xG per 60 minutes
            a2_xg_p60 (float):
                Individual secondary assists' xG per 60 minutes
            ipent0_p60 (float):
                Individual penalty shots taken per 60 minutes
            ipent2_p60 (float):
                Individual minor penalties taken per 60 minutes
            ipent4_p60 (float):
                Individual double minor penalties taken per 60 minutes
            ipent5_p60 (float):
                Individual major penalties taken per 60 minutes
            ipent10_p60 (float):
                Individual game misconduct pentalties taken per 60 minutes
            ipend0_p60 (float):
                Individual penalty shots drawn per 60 minutes
            ipend2_p60 (float):
                Individual minor penalties drawn per 60 minutes
            ipend4_p60 (float):
                Individual double minor penalties drawn per 60 minutes
            ipend5_p60 (float):
                Individual major penalties drawn per 60 minutes
            ipend10_p60 (float):
                Individual game misconduct penalties drawn per 60 minutes
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF /
                (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF /
                (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF /
                (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
                HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Prepares individual and on-ice dataframe with default options
            >>> scraper.prep_stats()

            Individual and on-ice statistics, aggregated to season level
            >>> scraper.prep_stats(level="season")

            Individual and on-ice statistics, aggregated to game level, accounting for teammates
            >>> scraper.prep_stats(level="game", teammates=True)

        """
        levels = self._stats_levels

        empty_stats = False

        if (
            levels["level"] != level
            or levels["strength_state"] != strength_state
            or levels["score"] != score
            or levels["teammates"] != teammates
            or levels["opposition"] != opposition
        ):
            self._clear_stats()

            new_values = {
                "level": level,
                "strength_state": strength_state,
                "score": score,
                "teammates": teammates,
                "opposition": opposition,
            }

            self._stats_levels.update(new_values)

        if self._backend == "polars":
            if self._stats.is_empty():
                empty_stats = True

        if self._backend == "pandas":
            if self._stats.empty:
                empty_stats = True

        if empty_stats:
            if not disable_progress_bar:
                disable_progress_bar = self.disable_progress_bar

            if not transient_progress_bar:
                transient_progress_bar = self.transient_progress_bar

            with ChickenProgressIndeterminate(
                disable=disable_progress_bar, transient=transient_progress_bar
            ) as progress:
                pbar_message = "Prepping stats data..."
                progress_task = progress.add_task(pbar_message, total=None, refresh=True)

                progress.start_task(progress_task)
                progress.update(progress_task, total=1, description=pbar_message, refresh=True)

                self._prep_stats(
                    level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
                )

                progress.update(
                    progress_task,
                    description="Finished prepping stats data",
                    completed=True,
                    advance=True,
                    refresh=True,
                )

    @property
    def stats(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of individual & on-ice stats aggregated from play-by-play data.

        Determine level of aggregation using prep_stats method.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            g (int):
                Individual goals scored, e.g, 0
            g_adj (float):
                Score- and venue-adjusted individual goals scored, e.g., 0.0
            ihdg (int):
                Individual high-danger goals scored, e.g, 0
            a1 (int):
                Individual primary assists, e.g, 0
            a2 (int):
                Individual secondary assists, e.g, 0
            ixg (float):
                Individual xG for, e.g, 1.014336
            ixg_adj (float):
                Score- and venue-adjusted indiviudal xG for, e.g., 1.101715
            isf (int):
                Individual shots taken, e.g, 3
            isf_adj (float):
                Score- and venue-adjusted individual shots taken, e.g., 3.262966
            ihdsf (int):
                High-danger shots taken, e.g, 3
            imsf (int):
                Individual missed shots, e.g, 0
            imsf_adj (float):
                Score- and venue-adjusted individual missed shots, e.g., 0.0
            ihdm (int):
                High-danger missed shots, e.g, 0
            iff (int):
                Individual fenwick for, e.g., 3
            iff_adj (float):
                Score- and venue-adjusted individual fenwick events, e.g., 3.279018
            ihdf (int):
                High-danger fenwick events for, e.g., 3
            isb (int):
                Shots taken that were blocked, e.g, 0
            isb_adj (float):
                Score- and venue-adjusted individual shots blocked, e.g, 0.0
            icf (int):
                Individual corsi for, e.g., 3
            icf_adj (float):
                Score- and venue-adjusted individual corsi events, e.g, 3.279018
            ibs (int):
                Individual shots blocked on defense, e.g, 0
            ibs_adj (float):
                Score- and venue-adjusted shots blocked, e.g., 0.0
            igive (int):
                Individual giveaways, e.g, 0
            itake (int):
                Individual takeaways, e.g, 0
            ihf (int):
                Individual hits for, e.g, 0
            iht (int):
                Individual hits taken, e.g, 0
            ifow (int):
                Individual faceoffs won, e.g, 0
            ifol (int):
                Individual faceoffs lost, e.g, 0
            iozfw (int):
                Individual faceoffs won in offensive zone, e.g, 0
            iozfl (int):
                Individual faceoffs lost in offensive zone, e.g, 0
            inzfw (int):
                Individual faceoffs won in neutral zone, e.g, 0
            inzfl (int):
                Individual faceoffs lost in neutral zone, e.g, 0
            idzfw (int):
                Individual faceoffs won in defensive zone, e.g, 0
            idzfl (int):
                Individual faceoffs lost in defensive zone, e.g, 0
            a1_xg (float):
                xG on primary assists, e.g, 0
            a2_xg (float):
                xG on secondary assists, e.g, 0
            ipent0 (int):
                Individual penalty shots against, e.g, 0
            ipent2 (int):
                Individual minor penalties taken, e.g, 0
            ipent4 (int):
                Individual double minor penalties taken, e.g, 0
            ipent5 (int):
                Individual major penalties taken, e.g, 0
            ipent10 (int):
                Individual game misconduct penalties taken, e.g, 0
            ipend0 (int):
                Individual penalty shots drawn, e.g, 0
            ipend2 (int):
                Individual minor penalties taken, e.g, 0
            ipend4 (int):
                Individual double minor penalties drawn, e.g, 0
            ipend5 (int):
                Individual major penalties drawn, e.g, 0
            ipend10 (int):
                Individual game misconduct penalties drawn, e.g, 0
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.366730
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 4.350622
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            ozs (int):
                Offensive zone starts, e.g, 0
            nzs (int):
                Neutral zone starts, e.g, 0
            dzs (int):
                Defenzive zone starts, e.g, 0
            otf (int):
                On-the-fly starts, e.g, 0
            g_p60 (float):
                Goals scored per 60 minutes
            ihdg_p60 (float):
                Individual high-danger goals scored per 60
            a1_p60 (float):
                Primary assists per 60 minutes
            a2_p60 (float):
                Secondary per 60 minutes
            ixg_p60 (float):
                Individual xG for per 60 minutes
            isf_p60 (float):
                Individual shots for per 60 minutes
            ihdsf_p60 (float):
                Individual high-danger shots for per 60 minutes
            imsf_p60 (float):
                Individual missed shorts for per 60 minutes
            ihdm_p60 (float):
                Individual high-danger missed shots for per 60 minutes
            iff_p60 (float):
                Individual fenwick for per 60 minutes
            ihdff_p60 (float):
                Individual high-danger fenwick for per 60 minutes
            isb_p60 (float):
                Individual shots blocked (for) per 60 minutes
            icf_p60 (float):
                Individual corsi for per 60 minutes
            ibs_p60 (float):
                Individual blocked shots (against) per 60 minutes
            igive_p60 (float):
                Individual giveaways per 60 minutes
            itake_p60 (float):
                Individual takeaways per 60 minutes
            ihf_p60 (float):
                Individual hits for per 60 minutes
            iht_p60 (float):
                Individual hits taken per 60 minutes
            a1_xg_p60 (float):
                Individual primary assists' xG per 60 minutes
            a2_xg_p60 (float):
                Individual secondary assists' xG per 60 minutes
            ipent0_p60 (float):
                Individual penalty shots taken per 60 minutes
            ipent2_p60 (float):
                Individual minor penalties taken per 60 minutes
            ipent4_p60 (float):
                Individual double minor penalties taken per 60 minutes
            ipent5_p60 (float):
                Individual major penalties taken per 60 minutes
            ipent10_p60 (float):
                Individual game misconduct pentalties taken per 60 minutes
            ipend0_p60 (float):
                Individual penalty shots drawn per 60 minutes
            ipend2_p60 (float):
                Individual minor penalties drawn per 60 minutes
            ipend4_p60 (float):
                Individual double minor penalties drawn per 60 minutes
            ipend5_p60 (float):
                Individual major penalties drawn per 60 minutes
            ipend10_p60 (float):
                Individual game misconduct penalties drawn per 60 minutes
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e.,
                HDGF / (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e.,
                HDSF / (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e.,
                HDFF / (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
                HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Returns individual and on-ice stats with default options
            >>> scraper.stats

            Resets individual and on-ice stats to period level, accounting for teammates on-ice
            >>> scraper.prep_stats(level="period", teammates=True)
            >>> scraper.stats

            Resets individual and on-ice stats to season level, accounting for teammates on-ice and score state
            >>> scraper.prep_stats(level="season", teammates=True, score=True)
            >>> scraper.stats

        """
        empty_stats = False

        if self._backend == "polars":
            if self._stats.is_empty():
                empty_stats = True

        if self._backend == "pandas":
            if self._stats.empty:
                empty_stats = True

        if empty_stats:
            self.prep_stats()

        if self._backend == "polars":
            df = self._stats.clone()

        if self._backend == "pandas":
            df = self._stats.copy()

        return df

    def _clear_stats(self):
        """Method to clear stats dataframes. Nested within `prep_stats` method."""
        if self._backend == "polars":
            self._stats = pl.DataFrame()
            self._oi_stats = pl.DataFrame()
            self._ind_stats = pl.DataFrame()

        if self._backend == "pandas":
            self._stats = pd.DataFrame()
            self._oi_stats = pd.DataFrame()
            self._ind_stats = pd.DataFrame()

    def _prep_lines(
        self,
        position: Literal["f", "d"] = "f",
        level: Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
    ) -> None:
        """Prepares DataFrame of line-level stats from play-by-play data.

        Nested within `prep_lines` method.

        Parameters:
            position (str):
                Determines what positions to aggregate. One of F or D
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            strength_state (bool):
                Determines if stats account for strength state
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.366730
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 4.350622
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF /
                (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF /
                (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF /
                (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
                HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Prepares on-ice, line-level dataframe with default options
            >>> scraper._prep_lines()

            Line-level statistics, aggregated to season level
            >>> scraper._prep_lines(level="season")

            Line-level statistics, aggregated to game level, accounting for teammates
            >>> scraper._prep_lines(level="game", teammates=True)

        """
        if self._backend == "polars":
            lines = prep_lines_polars(
                df=self.play_by_play,
                df_ext=self.play_by_play_ext,
                position=position,
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
            )

        if self._backend == "pandas":
            lines = prep_lines_pandas(
                df=self.play_by_play,
                df_ext=self.play_by_play_ext,
                position=position,
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
            )

        self._lines = lines

    def prep_lines(
        self,
        position: Literal["f", "d"] = "f",
        level: Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
    ) -> None:
        """Prepares DataFrame of line-level stats from play-by-play data.

        Used to prepare, or reset prepared data for later analysis

        Parameters:
            position (str):
                Determines what positions to aggregate. One of F or D
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            strength_state (bool):
                Determines if stats account for strength state
            score (bool):
                Determines if stats account  for score state
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice
            disable_progress_bar (bool):
                Determines whether to display the progress bar

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.366730
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 4.350622
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF /
                (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF /
                (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF /
                (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
                HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Prepares on-ice, line-level dataframe with default options
            >>> scraper.prep_lines()

            Line-level statistics, aggregated to season level
            >>> scraper.prep_lines(level="season")

            Line-level statistics, aggregated to game level, accounting for teammates
            >>> scraper.prep_lines(level="game", teammates=True)

        """
        levels = self._lines_levels

        if (
            levels["position"] != position
            or levels["level"] != level
            or levels["strength_state"] != strength_state
            or levels["score"] != score
            or levels["teammates"] != teammates
            or levels["opposition"] != opposition
        ):
            if self._backend == "polars":
                self._lines = pl.DataFrame()

            if self._backend == "pandas":
                self._lines = pd.DataFrame()

            new_values = {
                "position": position,
                "level": level,
                "strength_state": strength_state,
                "score": score,
                "teammates": teammates,
                "opposition": opposition,
            }

            self._lines_levels.update(new_values)

        empty_lines = False

        if self._backend == "polars":
            if self._lines.is_empty():
                empty_lines = True

        if self._backend == "pandas":
            if self._lines.empty:
                empty_lines = True

        if empty_lines:
            if not disable_progress_bar:
                disable_progress_bar = self.disable_progress_bar

            if not transient_progress_bar:
                transient_progress_bar = self.transient_progress_bar

            with ChickenProgressIndeterminate(
                disable=disable_progress_bar, transient=transient_progress_bar
            ) as progress:
                pbar_message = "Prepping lines data..."
                progress_task = progress.add_task(pbar_message, total=None, refresh=True)

                progress.start_task(progress_task)
                progress.update(progress_task, total=1, description=pbar_message, refresh=True)

                self._prep_lines(
                    level=level,
                    position=position,
                    strength_state=strength_state,
                    score=score,
                    teammates=teammates,
                    opposition=opposition,
                )

                progress.update(
                    progress_task,
                    description="Finished prepping lines data",
                    completed=True,
                    advance=True,
                    refresh=True,
                )

    @property
    def lines(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of line-level stats aggregated from play-by-play data.

        Determine level of aggregation using `prep_lines` method.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.366730
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 4.350622
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF /
                (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF /
                (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF /
                (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
                HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Returns line stats with default options
            >>> scraper.lines

            Resets line stats to period level, accounting for teammates on-ice
            >>> scraper.prep_lines(level="period", teammates=True)
            >>> scraper.lines

            Resets line stats to season level, accounting for teammates on-ice and score state
            >>> scraper.prep_lines(level="season", teammates=True, score=True)
            >>> scraper.lines

        """
        empty_lines = False

        if self._backend == "polars":
            if self._lines.is_empty():
                empty_lines = True

        if self._backend == "pandas":
            if self._lines.empty:
                empty_lines = True

        if empty_lines:
            self.prep_lines()

        if self._backend == "polars":
            df = self._lines.clone()

        if self._backend == "pandas":
            df = self._lines.copy()

        return df

    def _prep_team_stats(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        opposition: bool = False,
        score: bool = False,
    ) -> None:
        """Prepares DataFrame of team stats from play-by-play data.

        Nested within `prep_team_stats` method.

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            strength_state (bool):
                Determines if stats account for strength state
            opposition (bool):
                Determines if stats account for opponents on ice
            score (bool):
                Determines if stats account for score state

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            toi (float):
                Time on-ice, in minutes, e.g, 1.100000
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.271583
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.381123
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 5
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 5.438277
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 5
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 5.46503
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 5
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 5.46503
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 4
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 2
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 2
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 1
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 1
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 1
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF /
                (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF /
                (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF /
                (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
                HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Team dataframe with default options
            >>> scraper._prep_team_stats()

            Team statistics, aggregated to season level
            >>> scraper._prep_team_stats(level="season")

            Team statistics, aggregated to game level, accounting for teammates
            >>> scraper._prep_team_stats(level="game", teammates=True)

        """
        if self._backend == "polars":
            team_stats = prep_team_stats_polars(
                df=self.play_by_play,
                df_ext=self.play_by_play_ext,
                level=level,
                strength_state=strength_state,
                opposition=opposition,
                score=score,
            )

        if self._backend == "pandas":
            team_stats = prep_team_stats_pandas(
                df=self.play_by_play,
                df_ext=self.play_by_play_ext,
                level=level,
                strength_state=strength_state,
                opposition=opposition,
                score=score,
            )

        self._team_stats = team_stats

    def prep_team_stats(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        opposition: bool = False,
        score: bool = False,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
    ) -> None:
        """Prepares DataFrame of team stats from play-by-play data.

        Used to prepare, or reset prepared data for later analysis

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            strength_state (bool):
                Determines if stats account for strength state
            opposition (bool):
                Determines if stats account for opponents on ice
            score (bool):
                Determines if stats account for score state
            disable_progress_bar (bool):
                Determines whether to display the progress bar

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            toi (float):
                Time on-ice, in minutes, e.g, 1.100000
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.271583
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.381123
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 5
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 5.438277
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 5
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 5.46503
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 5
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 5.46503
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 4
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 2
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 2
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 1
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 1
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 1
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF /
                (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF /
                (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF /
                (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
                HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Team dataframe with default options
            >>> scraper.prep_team_stats()

            Team statistics, aggregated to season level
            >>> scraper.prep_team_stats(level="season")

            Team statistics, aggregated to game level, accounting for teammates
            >>> scraper.prep_team_stats(level="game", teammates=True)

        """
        levels = self._team_stats_levels

        if (
            levels["level"] != level
            or levels["score"] != score
            or levels["strength_state"] != strength_state
            or levels["opposition"] != opposition
        ):
            if self._backend == "polars":
                self._team_stats = pl.DataFrame()

            if self._backend == "pandas":
                self._team_stats = pd.DataFrame()

            new_values = {"level": level, "score": score, "strengths": strength_state, "opposition": opposition}

            self._team_stats_levels.update(new_values)

        empty_team_stats = False

        if self._backend == "polars":
            if self._team_stats.is_empty():
                empty_team_stats = True

        if self._backend == "pandas":
            if self._team_stats.empty:
                empty_team_stats = True

        if empty_team_stats:
            if not disable_progress_bar:
                disable_progress_bar = self.disable_progress_bar

            if not transient_progress_bar:
                transient_progress_bar = self.transient_progress_bar

            with ChickenProgressIndeterminate(
                disable=disable_progress_bar, transient=transient_progress_bar
            ) as progress:
                pbar_message = "Prepping team stats data..."
                progress_task = progress.add_task(pbar_message, total=None, refresh=True)

                progress.start_task(progress_task)
                progress.update(progress_task, total=1, description=pbar_message, refresh=True)

                self._prep_team_stats(level=level, score=score, strength_state=strength_state, opposition=opposition)

                progress.update(
                    progress_task,
                    description="Finished prepping team stats data",
                    completed=True,
                    advance=True,
                    refresh=True,
                )

    @property
    def team_stats(self) -> pl.DataFrame | pd.DataFrame:
        """Pandas Dataframe of teams stats aggregated from play-by-play data.

        Determine level of aggregation using `prep_team_stats` method.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            toi (float):
                Time on-ice, in minutes, e.g, 1.100000
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            gf_adj (float):
                Score- and venue-adjusted goals for (on-ice), e.g., 0.0
            ga_adj (float):
                Score- and venue-adjusted goals against (on-ice), e.g., 0.0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.271583
            xga (float):
                xG against (on-ice), e.g, 0.000000
            xgf_adj (float):
                Score- and venue-adjusted xG for (on-ice), e.g., 1.381123
            xga_adj (float):
                Score- and venue-adjusted xG against (on-ice), e.g., 0.0
            sf (int):
                Shots for (on-ice), e.g, 5
            sa (int):
                Shots against (on-ice), e.g, 0
            sf_adj (float):
                Score- and venue-adjusted shots for (on-ice), e.g., 5.438277
            sa_adj (float):
                Score- and venue-adjusted shots against (on-ice), e.g., 0.0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 5
            fa (int):
                Fenwick against (on-ice), e.g, 0
            ff_adj (float):
                Score- and venue-adjusted fenwick events for (on-ice), e.g., 5.46503
            fa_adj (float):
                Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 5
            ca (int):
                Corsi against (on-ice), e.g, 0
            cf_adj (float):
                Score- and venue-adjusted corsi events for (on-ice), e.g., 5.46503
            ca_adj (float):
                Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            bsf_adj (float):
                Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
            bsa_adj (float):
                Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            msf_adj (float):
                Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
            msa_adj (float):
                Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            teammate_block_adj (float):
                Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 4
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 2
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 2
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 1
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 1
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 1
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF /
                (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF /
                (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF /
                (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
                HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Returns team stats with default options
            >>> scraper.team_stats

            Resets team stats to season level, accounting for opposing team
            >>> scraper.prep_team_stats(level="season", opposition=True)
            >>> scraper.team_stats

            Resets team stats to season level, accounting for opposing team and score state
            >>> scraper.prep_team_stats(level="season", opposition=True, score=True)
            >>> scraper.team_stats

        """
        empty_team_stats = False

        if self._backend == "polars":
            if self._team_stats.is_empty():
                empty_team_stats = True

        if self._backend == "pandas":
            if self._team_stats.empty:
                empty_team_stats = True

        if empty_team_stats:
            self.prep_team_stats()

        if self._backend == "polars":
            df = self._team_stats.clone()

        if self._backend == "pandas":
            df = self._team_stats.copy()

        return df
