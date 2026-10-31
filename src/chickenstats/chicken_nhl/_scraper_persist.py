from __future__ import annotations

import errno
import hashlib
import json
import os
import sys
import warnings
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import polars as pl

from chickenstats.chicken_nhl._scraper_core import (
    _SCRAPE_REGISTRY,
    FINAL_STATE,
    _ScraperBase,
    _user_stacklevel,
    normalize_game_ids,
)
from chickenstats.exceptions import CacheFormatError
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.utilities import data_directory

if TYPE_CHECKING:
    from typing_extensions import Self

# Raised whenever what a cache stores changes; a cache in any other format is refused, never cast (R29)
CACHE_FORMAT = 3

_META_FILE = "_meta.json"
_LOCK_FILE = ".meta.lock"


def _split_by_game(frame: pl.DataFrame) -> dict[int, pl.DataFrame]:
    """One type's saved rows, split by game.

    play_by_play_ext has no game_id column; its id is the game ID followed by a four-digit event index.
    """
    game_id = pl.col("game_id") if "game_id" in frame.columns else pl.col("id") // 10_000
    keyed = frame.with_columns(_game=game_id)
    return {key: rows.drop("_game") for (key,), rows in keyed.partition_by("_game", as_dict=True).items()}


def _replace_file(path: Path, write: Callable[[Path], object]) -> None:
    """Write a file under a temporary name and swap it in, so a reader never sees it half-written (N54)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        write(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _meta_lock(path: Path) -> Iterator[None]:
    """Hold an exclusive lock on the cache in path, so two Scrapers update ``_meta.json`` one at a time (bA-06)."""
    path.mkdir(parents=True, exist_ok=True)
    with open(path / _LOCK_FILE, "a+b") as handle:
        if sys.platform == "win32":
            import msvcrt

            # LK_LOCK gives up after ten seconds, so keep waiting while another Scraper writes
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError as error:
                    if error.errno != errno.EDEADLK:
                        raise
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _schema_hash() -> str:
    """A short hash of every cached type's column names and data types, so a cache with other columns is refused."""
    schemas = {key: {name: str(dtype) for name, dtype in spec.schema.items()} for key, spec in _SCRAPE_REGISTRY.items()}
    return hashlib.sha256(json.dumps(schemas, sort_keys=True).encode()).hexdigest()[:16]


def _read_meta(path: Path) -> dict | None:
    """The cache's metadata, or None if the directory holds no cache.

    Raises:
        CacheFormatError: If the cache was written in another format, such as by chickenstats before 1.9.0.
    """
    file = path / _META_FILE
    if not file.exists():
        return None

    meta = json.loads(file.read_text())
    if meta.get("format") != CACHE_FORMAT:
        raise CacheFormatError(
            f"The cache in {path} was written by another version of chickenstats and cannot be read. Delete it, "
            "or pass overwrite=True to replace it.",
            path=path,
        )
    if meta.get("schema") != _schema_hash():
        raise CacheFormatError(
            f"The cache in {path} stores columns that this version of chickenstats does not write and cannot be "
            "read. Delete it, or pass overwrite=True to replace it.",
            path=path,
        )
    return meta


def _new_meta(backend: str) -> dict:
    return {
        "format": CACHE_FORMAT,
        "schema": _schema_hash(),
        "backend": backend,
        "game_ids": [],
        "games": {},
        "failed": {},
        "reasons": {},
    }


def _update_meta(path: Path, backend: str, record: Callable[[dict], object]) -> None:
    """Re-read ``_meta.json`` under the lock, apply record to it and write it back.

    Another Scraper can write to the same directory between two of this one's writes, so the metadata is read
    from disk each time rather than kept in memory, and neither drops the other's games (bA-06, in-07).
    """
    with _meta_lock(path):
        meta = _read_meta(path) or _new_meta(backend)
        record(meta)
        _replace_file(path / _META_FILE, lambda file: file.write_text(json.dumps(meta, indent=2)))


def _remove_cache_files(path: Path) -> None:
    """Remove the files an existing cache's ``_meta.json`` lists, and the metadata itself; with none, nothing.

    ``cache=True`` uses ``./data``, which can hold the user's own files, such as a ``play_by_play.parquet``, so
    only the files a cache recorded are removed, and the directory itself is kept (in-01).
    """
    file = path / _META_FILE
    if not file.exists():
        return

    with _meta_lock(path):
        meta = json.loads(file.read_text())
        if "games" in meta:
            files = [
                path / key / name
                for game_id, entry in meta["games"].items()
                for key in entry.get("types", [])
                for name in (f"{game_id}.parquet", f".{game_id}.parquet.tmp")
            ]
        else:
            # chickenstats before 1.9.0 wrote one file per type next to _meta.json
            files = [path / f"{key}.parquet" for key in _SCRAPE_REGISTRY]

        for listed in files:
            listed.unlink(missing_ok=True)
        for key in _SCRAPE_REGISTRY:
            folder = path / key
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
        file.unlink()


class _ScraperPersistMixin(_ScraperBase):
    def save(self, path: str | Path | None = None) -> Path:
        """Save all currently-scraped raw data to disk as parquet files.

        Writes one parquet file per game and data type, in a folder per type, then ``_meta.json``, which
        records each game's types, API state and failures. Games already saved in the directory by another
        Scraper are kept.

        Parameters:
            path (str | Path | None):
                Directory to save into. Created if it doesn't exist. Defaults to
                ``data_directory()`` (``./data`` in the current working directory).

        Returns:
            Path: The directory the data was saved to.

        Raises:
            CacheFormatError: If the directory holds a cache in another format.

        Examples:
            >>> from chickenstats.chicken_nhl import Scraper
            >>> scraper = Scraper([2023020001, 2023020002])
            >>> pbp = scraper.play_by_play
            >>> save_path = scraper.save("my_scrape")
        """
        target = Path(path) if path is not None else data_directory()
        target.mkdir(parents=True, exist_ok=True)

        for game_id in self.game_ids:
            self._write_frames(target, game_id, _SCRAPE_REGISTRY)

        def record(meta: dict) -> None:
            for game_id in self.game_ids:
                self._record_game(meta, game_id)

        _update_meta(target, self._backend, record)

        return target

    def _write_frames(self, path: Path, game_id: int, keys: Iterable[str]) -> None:
        """Write game_id's frames for keys under path, before the metadata lists them."""
        for key in keys:
            frame = getattr(self, _SCRAPE_REGISTRY[key].list_attr).get(game_id)
            if frame is not None:
                _replace_file(path / key / f"{game_id}.parquet", frame.write_parquet)

    def _record_game(self, meta: dict, game_id: int) -> None:
        """Record game_id's types, state and failures in meta, keeping the types another Scraper saved (tu-08)."""
        if game_id not in meta["game_ids"]:
            meta["game_ids"].append(game_id)
        types = [key for key, spec in _SCRAPE_REGISTRY.items() if game_id in getattr(self, spec.list_attr)]
        if types:
            current = version("chickenstats")
            # A game is saved as OFF only once every type is, so a type fetched earlier is fetched again on load
            state = self._game_states.get(game_id)
            if state == FINAL_STATE and not self._fetched_final(game_id):
                state = None
            saved = meta["games"].get(str(game_id), {})
            kept = [key for key in saved.get("types", []) if key not in types]
            # The kept types are final only if the Scraper that saved them fetched them at OFF with this version
            if kept and (saved.get("state") != FINAL_STATE or saved.get("version") != current):
                state = None
            types = [key for key in _SCRAPE_REGISTRY if key in types or key in kept]
            # The version that wrote a game, since a later one can change its values without changing the schema
            meta["games"][str(game_id)] = {"state": state, "types": types, "version": current}
        failed = self._failed_types.get(game_id)
        # A cache from before reasons were saved has no "reasons" key
        reasons = meta.setdefault("reasons", {})
        if failed:
            meta["failed"][str(game_id)] = sorted(failed)
            if game_id in self._failure_reasons:
                reasons[str(game_id)] = self._failure_reasons[game_id]
        else:
            meta["failed"].pop(str(game_id), None)
            reasons.pop(str(game_id), None)

    def _cache_game(self, game_id: int, keys: Iterable[str]) -> None:
        """Write one game to the cache as soon as its scrape ends, so an interrupted run keeps it (N53).

        The game's files are written before ``_meta.json``, and only files the metadata lists are loaded, so
        a run stopped between the two loads as if the game had not been scraped.
        """
        if self._cache_dir is None:
            return
        self._write_frames(self._cache_dir, game_id, keys)
        _update_meta(self._cache_dir, self._backend, lambda meta: self._record_game(meta, game_id))

    def _clear_cache(self, path: Path) -> None:
        """Remove an existing cache's files, for overwrite=True (R38)."""
        _remove_cache_files(path)

    def _apply_cache(
        self, path: Path, meta: dict | None = None, add_cached_games: bool = True, only: list[int] | None = None
    ) -> None:
        """Populate ``self`` with cached data previously written by :meth:`save`.

        Loads the raw parquet data for the Scraper's games and marks them as already scraped.

        Parameters:
            path (Path): Directory previously written by :meth:`save`.
            meta (dict | None): Already-read ``_meta.json`` contents, if the caller has
                them; read from ``path`` otherwise.
            add_cached_games (bool): Extend ``self.game_ids`` with every cached game (cached
                first), as :meth:`load` does. ``cache=`` passes ``False``, so a Scraper asked for
                one game returns that game (N84).
            only (list[int] | None): Read only these games, so the frames already held for the others are
                kept. ``add_games()`` passes the games it adds (bA-07).
        """
        meta = meta or _read_meta(path)
        if meta is None:
            return

        if add_cached_games:
            cached_ids = normalize_game_ids(meta["game_ids"]) if meta["game_ids"] else []
            self.game_ids = list(dict.fromkeys([*cached_ids, *self.game_ids]))
        scope = set(self.game_ids if only is None else only)
        games = {int(game_id): entry for game_id, entry in meta["games"].items() if int(game_id) in scope}

        for key, spec in _SCRAPE_REGISTRY.items():
            # A listed file that is missing is left out, so its game is fetched again
            files = {
                game_id: path / key / f"{game_id}.parquet" for game_id, entry in games.items() if key in entry["types"]
            }
            present = {game_id: file for game_id, file in files.items() if file.exists()}
            frame = pl.read_parquet(list(present.values())) if present else pl.DataFrame(schema=spec.schema)
            by_game = _split_by_game(frame)
            stored: dict[int, pl.DataFrame] = getattr(self, spec.list_attr)
            for game_id in present:
                stored[game_id] = by_game.get(game_id, pl.DataFrame(schema=spec.schema))

        # A game written by another version keeps its frames but not its state, so it is fetched again (C1)
        current = version("chickenstats")
        other = {game_id: entry.get("version") for game_id, entry in games.items() if entry.get("version") != current}
        if other:
            warnings.warn(
                f"{len(other)} cached game(s) were written by chickenstats {sorted(set(map(str, other.values())))}, "
                f"not {current}. They are treated as provisional, so the next scrape or refresh() fetches them again.",
                UserWarning,
                stacklevel=_user_stacklevel(),
            )
        for game_id in other:
            games[game_id] = {**games[game_id], "state": None}

        # A game with no recorded state is provisional, so it is fetched again on its next scrape
        self._game_states.update({game_id: entry["state"] for game_id, entry in games.items() if entry["state"]})
        self._final_types.update(
            {game_id: set(entry["types"]) for game_id, entry in games.items() if entry["state"] == FINAL_STATE}
        )

        for game_id, types in meta["failed"].items():
            if int(game_id) in scope:
                self._failed_types.setdefault(int(game_id), set()).update(types)
                if int(game_id) not in self._bad_games:
                    self._bad_games.append(int(game_id))
                reason = meta.get("reasons", {}).get(game_id)
                if reason:
                    self._failure_reasons[int(game_id)] = reason

    @classmethod
    def load(
        cls,
        path: str | Path,
        game_ids: list | None = None,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
        backend: Backend | Literal["pandas", "polars", "pyarrow", "narwhals"] | None = None,
    ) -> Self:
        """Load a Scraper from data previously written by :meth:`save`.

        Already-cached games are marked as scraped, except a game that was not final when it was saved, which
        is fetched again on its next scrape. ``game_ids`` not present in the cache are added and scraped on
        next access.

        Parameters:
            path (str | Path):
                Directory previously written by :meth:`save`.
            game_ids (list | None):
                Additional game IDs to scrape beyond what's cached. Defaults to ``None``
                (only the cached games).
            disable_progress_bar (bool):
                Suppress the Rich progress bar globally for this instance. Default ``False``.
            transient_progress_bar (bool):
                Clear the progress bar from the terminal after it completes. Default ``False``.
            backend (str | None):
                DataFrame backend for all returned data. Defaults to whatever backend the
                saved Scraper used.

        Returns:
            Scraper: A new instance with the cached data pre-loaded.

        Raises:
            CacheFormatError: If the cache was written in another format, such as by chickenstats before 1.9.0.

        Examples:
            >>> from chickenstats.chicken_nhl import Scraper
            >>> scraper = Scraper.load("my_scrape")
            >>> pbp = scraper.play_by_play  # no network calls for already-cached games

            Extend with new games — only the new ones get scraped
            >>> scraper = Scraper.load("my_scrape", game_ids=[2023020003])
            >>> pbp = scraper.play_by_play
        """
        source = Path(path)
        meta = _read_meta(source)
        if meta is None:
            raise FileNotFoundError(f"No chickenstats cache in {source}")

        extra_ids: list[str | float | int] = list(normalize_game_ids(game_ids)) if game_ids else []

        scraper = cls(
            extra_ids,
            disable_progress_bar=disable_progress_bar,
            transient_progress_bar=transient_progress_bar,
            backend=backend or meta.get("backend", "polars"),
        )
        scraper._apply_cache(source, meta=meta)

        return scraper
