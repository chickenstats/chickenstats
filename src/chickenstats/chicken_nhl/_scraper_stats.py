from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from typing_extensions import Self
    import pandas as pd
    import pyarrow as pa

import polars as pl
import narwhals as nw

from chickenstats.chicken_nhl._aggregation import prep_ind, prep_oi, _merge_stats, prep_lines, prep_team_stats
from chickenstats.chicken_nhl._docstrings import (
    shared_doc,
    _IND_STATS_DOC,
    _OI_STATS_DOC,
    _PREP_STATS_DOC,
    _STATS_DOC,
    _PREP_LINES_DOC,
    _LINES_DOC,
    _PREP_TEAM_STATS_DOC,
    _TEAM_STATS_DOC,
)
from chickenstats.chicken_nhl._scraper_core import _ScraperBase
from chickenstats.utilities.enums import AggLevel
from chickenstats.utilities.utilities import ChickenProgressIndeterminate, _to_polars, _to_backend


class _ScraperStatsMixin(_ScraperBase):
    def _prep_ind(
        self,
        level: AggLevel | Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
        df: pl.DataFrame | None = None,
    ) -> None:
        """Compute and cache individual stats from play-by-play data.

        Internal method called by ``prep_stats``. Results are stored in ``self._ind_stats``
        and exposed through the ``ind_stats`` property. See ``ind_stats`` for full field descriptions.

        Parameters:
            level: Aggregation level — one of ``'period'``, ``'game'``, ``'session'``, ``'season'``
            strength_state: Whether to split by strength state. Default ``True``
            score: Whether to split by score state. Default ``False``
            teammates: Whether to split by teammate lineup. Default ``False``
            opposition: Whether to split by opposing lineup. Default ``False``
            df: Pre-fetched play-by-play DataFrame; scrapes if ``None``
        """
        ind_stats = prep_ind(
            df if df is not None else _to_polars(self.play_by_play),
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
        )

        self._ind_stats = ind_stats

    @property
    @shared_doc(_IND_STATS_DOC)
    def ind_stats(self) -> pl.DataFrame | pd.DataFrame | pa.Table | nw.DataFrame:
        """ind_stats — docstring lives in _docstrings._IND_STATS_DOC."""
        if self._is_empty(self._ind_stats):
            self._prep_ind()

        return _to_backend(self._ind_stats, self._backend)

    def _prep_oi(
        self,
        level: AggLevel | Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
        df: pl.DataFrame | None = None,
        df_ext: pl.DataFrame | None = None,
    ) -> None:
        """Compute and cache on-ice stats from play-by-play data.

        Internal method called by ``prep_stats``. Results are stored in ``self._oi_stats``
        and exposed through the ``oi_stats`` property. See ``oi_stats`` for full field descriptions.

        Parameters:
            level: Aggregation level — one of ``'period'``, ``'game'``, ``'session'``, ``'season'``
            strength_state: Whether to split by strength state. Default ``True``
            score: Whether to split by score state. Default ``False``
            teammates: Whether to split by teammate lineup. Default ``False``
            opposition: Whether to split by opposing lineup. Default ``False``
            df: Pre-fetched play-by-play DataFrame; scrapes if ``None``
            df_ext: Pre-fetched extended play-by-play DataFrame; scrapes if ``None``
        """
        oi_stats = prep_oi(
            df=df if df is not None else _to_polars(self.play_by_play),
            df_ext=df_ext if df_ext is not None else _to_polars(self.play_by_play_ext),
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
        )

        self._oi_stats = oi_stats

    @property
    @shared_doc(_OI_STATS_DOC)
    def oi_stats(self) -> pl.DataFrame | pd.DataFrame | pa.Table | nw.DataFrame:
        """oi_stats — docstring lives in _docstrings._OI_STATS_DOC."""
        if self._is_empty(self._oi_stats):
            self._prep_oi()

        return _to_backend(self._oi_stats, self._backend)

    def _prep_stats(
        self,
        level: AggLevel | Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
    ) -> None:
        """Compute and cache individual + on-ice stats from play-by-play data.

        Internal method called by ``prep_stats``. Runs ``_prep_ind`` and ``_prep_oi``
        concurrently via ``ThreadPoolExecutor``. See ``stats`` for full field descriptions.

        Parameters:
            level: Aggregation level — one of ``'period'``, ``'game'``, ``'session'``, ``'season'``
            strength_state: Whether to split by strength state. Default ``True``
            score: Whether to split by score state. Default ``False``
            teammates: Whether to split by teammate lineup. Default ``False``
            opposition: Whether to split by opposing lineup. Default ``False``
        """
        ind_empty = self._is_empty(self._ind_stats)
        oi_empty = self._is_empty(self._oi_stats)

        if ind_empty and oi_empty:
            pbp = _to_polars(self.play_by_play)
            pbp_ext = _to_polars(self.play_by_play_ext)
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(self._prep_ind, level, strength_state, score, teammates, opposition, pbp),
                    executor.submit(self._prep_oi, level, strength_state, score, teammates, opposition, pbp, pbp_ext),
                ]
                for future in as_completed(futures):
                    future.result()
        elif ind_empty:
            pbp = _to_polars(self.play_by_play)
            self._prep_ind(
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
                df=pbp,
            )
        elif oi_empty:
            pbp = _to_polars(self.play_by_play)
            pbp_ext = _to_polars(self.play_by_play_ext)
            self._prep_oi(
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
                df=pbp,
                df_ext=pbp_ext,
            )

        stats = _merge_stats(ind_stats_df=self._ind_stats, oi_stats_df=self._oi_stats)

        self._stats = stats

    @shared_doc(_PREP_STATS_DOC)
    def prep_stats(
        self,
        level: AggLevel | Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
        disable_progress_bar: bool | None = None,
        transient_progress_bar: bool | None = None,
    ) -> Self:
        """prep_stats — docstring lives in _docstrings._PREP_STATS_DOC."""
        levels = self._stats_levels

        if (
            levels.level != level
            or levels.strength_state != strength_state
            or levels.score != score
            or levels.teammates != teammates
            or levels.opposition != opposition
        ):
            self._clear_stats()
            self._stats_levels.level = level
            self._stats_levels.strength_state = strength_state
            self._stats_levels.score = score
            self._stats_levels.teammates = teammates
            self._stats_levels.opposition = opposition

        empty_stats = self._is_empty(self._stats)

        if empty_stats:
            with ChickenProgressIndeterminate(
                disable=self.disable_progress_bar if disable_progress_bar is None else disable_progress_bar,
                transient=self.transient_progress_bar if transient_progress_bar is None else transient_progress_bar,
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

        return self

    @property
    @shared_doc(_STATS_DOC)
    def stats(self) -> pl.DataFrame | pd.DataFrame | pa.Table | nw.DataFrame:
        """Stats — docstring lives in _docstrings._STATS_DOC."""
        if self._is_empty(self._stats):
            self.prep_stats()

        return _to_backend(self._stats, self._backend)

    def _clear_stats(self):
        """Method to clear stats dataframes. Nested within `prep_stats` method."""
        self._stats = pl.DataFrame()
        self._oi_stats = pl.DataFrame()
        self._ind_stats = pl.DataFrame()

    def _prep_lines(
        self,
        position: Literal["f", "d"] = "f",
        level: AggLevel | Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
    ) -> None:
        """Compute and cache line-level stats from play-by-play data.

        Internal method called by ``prep_lines``. Results are stored in ``self._lines``
        and exposed through the ``lines`` property. See ``lines`` for full field descriptions.

        Parameters:
            position: Position group — ``'f'`` for forwards, ``'d'`` for defense. Default ``'f'``
            level: Aggregation level — one of ``'period'``, ``'game'``, ``'session'``, ``'season'``
            strength_state: Whether to split by strength state. Default ``True``
            score: Whether to split by score state. Default ``False``
            teammates: Whether to split by teammate lineup. Default ``False``
            opposition: Whether to split by opposing lineup. Default ``False``
        """
        pbp = _to_polars(self.play_by_play)
        pbp_ext = _to_polars(self.play_by_play_ext)
        lines = prep_lines(
            df=pbp,
            df_ext=pbp_ext,
            position=position,
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
        )

        self._lines = lines

    @shared_doc(_PREP_LINES_DOC)
    def prep_lines(
        self,
        position: Literal["f", "d"] = "f",
        level: AggLevel | Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
        disable_progress_bar: bool | None = None,
        transient_progress_bar: bool | None = None,
    ) -> Self:
        """prep_lines — docstring lives in _docstrings._PREP_LINES_DOC."""
        levels = self._lines_levels

        if (
            levels.position != position
            or levels.level != level
            or levels.strength_state != strength_state
            or levels.score != score
            or levels.teammates != teammates
            or levels.opposition != opposition
        ):
            self._lines = pl.DataFrame()
            self._lines_levels.position = position
            self._lines_levels.level = level
            self._lines_levels.strength_state = strength_state
            self._lines_levels.score = score
            self._lines_levels.teammates = teammates
            self._lines_levels.opposition = opposition

        empty_lines = self._is_empty(self._lines)

        if empty_lines:
            with ChickenProgressIndeterminate(
                disable=self.disable_progress_bar if disable_progress_bar is None else disable_progress_bar,
                transient=self.transient_progress_bar if transient_progress_bar is None else transient_progress_bar,
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

        return self

    @property
    @shared_doc(_LINES_DOC)
    def lines(self) -> pl.DataFrame | pd.DataFrame | pa.Table | nw.DataFrame:
        """Lines — docstring lives in _docstrings._LINES_DOC."""
        if self._is_empty(self._lines):
            self.prep_lines()

        return _to_backend(self._lines, self._backend)

    def _prep_team_stats(
        self,
        level: AggLevel | Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        opposition: bool = False,
        score: bool = False,
    ) -> None:
        """Compute and cache team-level stats from play-by-play data.

        Internal method called by ``prep_team_stats``. Results are stored in ``self._team_stats``
        and exposed through the ``team_stats`` property. See ``team_stats`` for full field descriptions.

        Parameters:
            level: Aggregation level — one of ``'period'``, ``'game'``, ``'session'``, ``'season'``
            strength_state: Whether to split by strength state. Default ``True``
            opposition: Whether to split by opposing lineup. Default ``False``
            score: Whether to split by score state. Default ``False``
        """
        pbp = _to_polars(self.play_by_play)
        pbp_ext = _to_polars(self.play_by_play_ext)
        team_stats = prep_team_stats(
            df=pbp, df_ext=pbp_ext, level=level, strength_state=strength_state, opposition=opposition, score=score
        )

        self._team_stats = team_stats

    @shared_doc(_PREP_TEAM_STATS_DOC)
    def prep_team_stats(
        self,
        level: AggLevel | Literal["period", "game", "session", "season"] = "game",
        strength_state: bool = True,
        opposition: bool = False,
        score: bool = False,
        disable_progress_bar: bool | None = None,
        transient_progress_bar: bool | None = None,
    ) -> Self:
        """prep_team_stats — docstring lives in _docstrings._PREP_TEAM_STATS_DOC."""
        levels = self._team_stats_levels

        if (
            levels.level != level
            or levels.score != score
            or levels.strength_state != strength_state
            or levels.opposition != opposition
        ):
            self._team_stats = pl.DataFrame()
            self._team_stats_levels.level = level
            self._team_stats_levels.score = score
            self._team_stats_levels.strength_state = strength_state
            self._team_stats_levels.opposition = opposition

        empty_team_stats = self._is_empty(self._team_stats)

        if empty_team_stats:
            with ChickenProgressIndeterminate(
                disable=self.disable_progress_bar if disable_progress_bar is None else disable_progress_bar,
                transient=self.transient_progress_bar if transient_progress_bar is None else transient_progress_bar,
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

        return self

    @property
    @shared_doc(_TEAM_STATS_DOC)
    def team_stats(self) -> pl.DataFrame | pd.DataFrame | pa.Table | nw.DataFrame:
        """team_stats — docstring lives in _docstrings._TEAM_STATS_DOC."""
        if self._is_empty(self._team_stats):
            self.prep_team_stats()

        return _to_backend(self._team_stats, self._backend)
