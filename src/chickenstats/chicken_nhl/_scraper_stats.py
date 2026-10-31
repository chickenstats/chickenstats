from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from typing_extensions import Self

import polars as pl

from chickenstats.chicken_nhl._aggregation import (
    prep_ind,
    prep_oi,
    _merge_stats,
    prep_lines,
    prep_stints,
    prep_team_stats,
)
from chickenstats.chicken_nhl._docstrings import (
    shared_doc,
    _IND_STATS_DOC,
    _OI_STATS_DOC,
    _PREP_STATS_DOC,
    _STATS_DOC,
    _PREP_LINES_DOC,
    _LINES_DOC,
    _PREP_STINTS_DOC,
    _STINTS_DOC,
    _PREP_TEAM_STATS_DOC,
    _TEAM_STATS_DOC,
)
from chickenstats.chicken_nhl._scraper_core import _ScraperBase
from chickenstats.utilities.enums import AggLevel, LinesLevels, StatsLevels, StintsLevels, TeamStatsLevels
from chickenstats.utilities.types import DataFrameT
from chickenstats.utilities.utilities import ChickenProgressIndeterminate, _to_backend


def _last_arguments(levels: object) -> dict[str, Any]:
    """The arguments a result was last built with, so rebuilding it after add_games keeps them.

    Empty until the matching prep_* has run, so the first build uses that function's defaults.
    """
    return {name: value for name, value in asdict(levels).items() if value is not None}  # ty: ignore[invalid-argument-type]


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
            df if df is not None else self._play_by_play_snapshot()[0],
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
        )

        self._ind_stats = ind_stats

    @property
    @shared_doc(_IND_STATS_DOC)
    def ind_stats(self) -> DataFrameT:
        """ind_stats — docstring lives in _docstrings._IND_STATS_DOC."""
        if self._is_empty(self._ind_stats):
            self._prep_ind(**_last_arguments(self._stats_levels))

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
        if df is None or df_ext is None:
            df, df_ext = self._play_by_play_snapshot()
        oi_stats = prep_oi(
            df=df,
            df_ext=df_ext,
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
        )

        self._oi_stats = oi_stats

    @property
    @shared_doc(_OI_STATS_DOC)
    def oi_stats(self) -> DataFrameT:
        """oi_stats — docstring lives in _docstrings._OI_STATS_DOC."""
        if self._is_empty(self._oi_stats):
            self._prep_oi(**_last_arguments(self._stats_levels))

        return _to_backend(self._oi_stats, self._backend)

    def _with_spinner(
        self,
        noun: str,
        prep: Callable[[], None],
        disable_progress_bar: bool | None,
        transient_progress_bar: bool | None,
    ) -> None:
        """Run prep under an indeterminate progress bar for the noun being prepped."""
        with ChickenProgressIndeterminate(
            disable=self.disable_progress_bar if disable_progress_bar is None else disable_progress_bar,
            transient=self.transient_progress_bar if transient_progress_bar is None else transient_progress_bar,
        ) as progress:
            pbar_message = f"Prepping {noun} data..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            prep()

            progress.update(
                progress_task, description=f"Finished prepping {noun} data", completed=True, advance=True, refresh=True
            )

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
        pbp, pbp_ext = self._play_by_play_snapshot()
        ind_empty = self._is_empty(self._ind_stats)
        oi_empty = self._is_empty(self._oi_stats)

        if ind_empty and oi_empty:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(self._prep_ind, level, strength_state, score, teammates, opposition, pbp),
                    executor.submit(self._prep_oi, level, strength_state, score, teammates, opposition, pbp, pbp_ext),
                ]
                for future in as_completed(futures):
                    future.result()
        elif ind_empty:
            self._prep_ind(
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
                df=pbp,
            )
        elif oi_empty:
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
        requested = StatsLevels(
            level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
        )

        if requested != self._stats_levels:
            self._clear_stats()
            self._stats_levels = requested

        if self._is_empty(self._stats):
            self._with_spinner(
                "stats",
                lambda: self._prep_stats(
                    level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
                ),
                disable_progress_bar,
                transient_progress_bar,
            )

        return self

    @property
    @shared_doc(_STATS_DOC)
    def stats(self) -> DataFrameT:
        """Stats — docstring lives in _docstrings._STATS_DOC."""
        if self._is_empty(self._stats):
            self.prep_stats(**_last_arguments(self._stats_levels))

        return _to_backend(self._stats, self._backend)

    def _clear_stats(self) -> None:
        """Reset cached stats dataframes. Called from ``prep_stats``."""
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
        pbp, pbp_ext = self._play_by_play_snapshot()
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
        requested = LinesLevels(
            position=position,
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
        )

        if requested != self._lines_levels:
            self._lines = pl.DataFrame()
            self._lines_levels = requested

        if self._is_empty(self._lines):
            self._with_spinner(
                "lines",
                lambda: self._prep_lines(
                    level=level,
                    position=position,
                    strength_state=strength_state,
                    score=score,
                    teammates=teammates,
                    opposition=opposition,
                ),
                disable_progress_bar,
                transient_progress_bar,
            )

        return self

    @property
    @shared_doc(_LINES_DOC)
    def lines(self) -> DataFrameT:
        """Lines — docstring lives in _docstrings._LINES_DOC."""
        if self._is_empty(self._lines):
            self.prep_lines(**_last_arguments(self._lines_levels))

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
        pbp, pbp_ext = self._play_by_play_snapshot()
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
        requested = TeamStatsLevels(level=level, strength_state=strength_state, score=score, opposition=opposition)

        if requested != self._team_stats_levels:
            self._team_stats = pl.DataFrame()
            self._team_stats_levels = requested

        if self._is_empty(self._team_stats):
            self._with_spinner(
                "team stats",
                lambda: self._prep_team_stats(
                    level=level, score=score, strength_state=strength_state, opposition=opposition
                ),
                disable_progress_bar,
                transient_progress_bar,
            )

        return self

    @property
    @shared_doc(_TEAM_STATS_DOC)
    def team_stats(self) -> DataFrameT:
        """team_stats — docstring lives in _docstrings._TEAM_STATS_DOC."""
        if self._is_empty(self._team_stats):
            self.prep_team_stats(**_last_arguments(self._team_stats_levels))

        return _to_backend(self._team_stats, self._backend)

    def _prep_stints(self, min_skaters: int = 3) -> None:
        """Compute and cache RAPM stints from play-by-play data.

        Internal method called by ``prep_stints``. Results are stored in ``self._stints``
        and exposed through the ``stints`` property. See ``stints`` for full field descriptions.

        Parameters:
            min_skaters: Minimum skaters per side for a stint to be kept. Default ``3``
        """
        self._stints = prep_stints(self._play_by_play_snapshot()[0], min_skaters=min_skaters)

    @shared_doc(_PREP_STINTS_DOC)
    def prep_stints(
        self, min_skaters: int = 3, disable_progress_bar: bool | None = None, transient_progress_bar: bool | None = None
    ) -> Self:
        """prep_stints — docstring lives in _docstrings._PREP_STINTS_DOC."""
        requested = StintsLevels(min_skaters=min_skaters)

        if requested != self._stints_levels:
            self._stints = pl.DataFrame()
            self._stints_levels = requested

        if self._is_empty(self._stints):
            self._with_spinner(
                "stints",
                lambda: self._prep_stints(min_skaters=min_skaters),
                disable_progress_bar,
                transient_progress_bar,
            )

        return self

    @property
    @shared_doc(_STINTS_DOC)
    def stints(self) -> DataFrameT:
        """Stints — docstring lives in _docstrings._STINTS_DOC."""
        if self._is_empty(self._stints):
            self.prep_stints(**_last_arguments(self._stints_levels))

        return _to_backend(self._stints, self._backend)
