from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from functools import partial
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from typing import Self

import polars as pl

from chickenstats.chicken_nhl._aggregation import (
    prep_ind,
    prep_oi,
    _check_position,
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
from chickenstats.chicken_nhl._agg_constants import check_group_args
from chickenstats.chicken_nhl._scraper_core import _ScraperBase
from chickenstats.utilities.enums import AggLevel, LinesLevels, StatsLevels, StintsLevels, TeamStatsLevels
from chickenstats.utilities.types import FrameT
from chickenstats.utilities.utilities import ChickenProgressIndeterminate, _to_backend


def _last_arguments(levels: object) -> dict[str, Any]:
    """The arguments a result was last built with, so rebuilding it after add_games keeps them.

    Empty until the matching prep_* has run, so the first build uses that function's defaults.
    """
    return {name: value for name, value in asdict(levels).items() if value is not None}  # ty: ignore[invalid-argument-type]


class _ScraperStatsMixin(_ScraperBase[FrameT]):
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
    def ind_stats(self) -> FrameT:
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
    def oi_stats(self) -> FrameT:
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
        """Run prep under an indeterminate progress bar for the noun being prepped.

        The progress settings passed here also hold for any download prep starts.
        """
        settings = self.disable_progress_bar, self.transient_progress_bar
        if disable_progress_bar is not None:
            self.disable_progress_bar = disable_progress_bar
        if transient_progress_bar is not None:
            self.transient_progress_bar = transient_progress_bar

        try:
            with ChickenProgressIndeterminate(
                disable=self.disable_progress_bar, transient=self.transient_progress_bar
            ) as progress:
                pbar_message = f"Prepping {noun} data..."
                progress_task = progress.add_task(pbar_message, total=None, refresh=True)

                progress.start_task(progress_task)
                progress.update(progress_task, total=1, description=pbar_message, refresh=True)

                prep()

                progress.update(
                    progress_task,
                    description=f"Finished prepping {noun} data",
                    completed=True,
                    advance=True,
                    refresh=True,
                )
        finally:
            self.disable_progress_bar, self.transient_progress_bar = settings

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
        levels = dict(
            level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
        )
        tasks = []
        if self._is_empty(self._ind_stats):
            tasks.append(partial(self._prep_ind, **levels, df=pbp))
        if self._is_empty(self._oi_stats):
            tasks.append(partial(self._prep_oi, **levels, df=pbp, df_ext=pbp_ext))

        if tasks:
            with ThreadPoolExecutor(max_workers=2) as executor:
                for future in as_completed([executor.submit(task) for task in tasks]):
                    future.result()

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
        # Checked before scraping so a bad argument fails at once, with the message prep_ind gives
        check_group_args(level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition)
        requested = StatsLevels(
            level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
        )

        return self._rebuild(
            "stats",
            ("_stats", "_ind_stats", "_oi_stats"),
            "_stats_levels",
            requested,
            self._prep_stats,
            disable_progress_bar,
            transient_progress_bar,
        )

    @property
    @shared_doc(_STATS_DOC)
    def stats(self) -> FrameT:
        """Stats — docstring lives in _docstrings._STATS_DOC."""
        if self._is_empty(self._stats):
            self.prep_stats(**_last_arguments(self._stats_levels))

        return _to_backend(self._stats, self._backend)

    def _rebuild(
        self,
        noun: str,
        frame_attrs: tuple[str, ...],
        levels_attr: str,
        requested: object,
        prep: Callable[..., None],
        disable_progress_bar: bool | None,
        transient_progress_bar: bool | None,
    ) -> Self:
        """Run prep with the requested levels, unless the result was already built with them.

        The first of frame_attrs holds the result; any others are parts of it that are reset with it.
        """
        if requested != getattr(self, levels_attr):
            for frame_attr in frame_attrs:
                setattr(self, frame_attr, pl.DataFrame())
            setattr(self, levels_attr, requested)

        if self._is_empty(getattr(self, frame_attrs[0])):
            self._with_spinner(
                noun,
                lambda: prep(**asdict(requested)),  # ty: ignore[invalid-argument-type]
                disable_progress_bar,
                transient_progress_bar,
            )

        return self

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
        # Checked before scraping so a bad argument fails at once, with the message prep_lines gives
        _check_position(position)
        check_group_args(level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition)
        requested = LinesLevels(
            position=position,
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
        )

        return self._rebuild(
            "lines",
            ("_lines",),
            "_lines_levels",
            requested,
            self._prep_lines,
            disable_progress_bar,
            transient_progress_bar,
        )

    @property
    @shared_doc(_LINES_DOC)
    def lines(self) -> FrameT:
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
            opposition: Whether to add ``opp_team``, for one row per opponent. Default ``False``
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
        # Checked before scraping so a bad argument fails at once, with the message prep_team_stats gives
        check_group_args(level, strength_state=strength_state, score=score)
        requested = TeamStatsLevels(level=level, strength_state=strength_state, score=score, opposition=opposition)

        return self._rebuild(
            "team stats",
            ("_team_stats",),
            "_team_stats_levels",
            requested,
            self._prep_team_stats,
            disable_progress_bar,
            transient_progress_bar,
        )

    @property
    @shared_doc(_TEAM_STATS_DOC)
    def team_stats(self) -> FrameT:
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

        return self._rebuild(
            "stints",
            ("_stints",),
            "_stints_levels",
            requested,
            self._prep_stints,
            disable_progress_bar,
            transient_progress_bar,
        )

    @property
    @shared_doc(_STINTS_DOC)
    def stints(self) -> FrameT:
        """Stints — docstring lives in _docstrings._STINTS_DOC."""
        if self._is_empty(self._stints):
            self.prep_stints(**_last_arguments(self._stints_levels))

        return _to_backend(self._stints, self._backend)
