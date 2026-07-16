import importlib.resources
import pickle


def _load_score_adjustments() -> dict:
    import gzip

    with (
        importlib.resources.as_file(
            importlib.resources.files("chickenstats.chicken_nhl.score_adjustments").joinpath("score_adjustments.pkl.gz")
        ) as file,
        gzip.open(file, "rb") as fh,
    ):
        return pickle.load(fh)


def _build_adj_weights_lf():
    """Builds a 72-row lookup LazyFrame mapping (strength_state, is_home, score_bucket) → weights.

    Derived from score_adjustments.pkl (chicken_nhl) so both modules share the same calibration.

    State coverage:
    - 5v5, 4v4: 7 score buckets (−3 to +3), home and away
    - 3v3: 1 bucket (pkl values do not vary by score diff)
    - 5v4, 4v5, 5v3, 3v5, 4v3, 3v4: 3 buckets (−1, 0, +1)
      Flipped states (4v5, 3v5, 3v4) are looked up via their mirror state with is_home reversed,
      matching the same logic used in chicken_nhl._game_utils.calculate_score_adjustment.
    - 1v0: 3 buckets, goal weight only (xg/shot/fenwick/corsi zeroed — no model for empty net)
    """
    import polars as pl

    sa = _load_score_adjustments()

    rows = []

    # 5v5 and 4v4: full 7-bucket score sensitivity
    for st in ["5v5", "4v4"]:
        for is_home in [1, 0]:
            h = "home" if is_home else "away"
            for bucket in [-3, -2, -1, 0, 1, 2, 3]:
                r = sa[st][bucket]
                rows.append(
                    (
                        st,
                        is_home,
                        bucket,
                        r[f"{h}_goal_weight"],
                        r[f"{h}_pred_goal_weight"],
                        r[f"{h}_shot_weight"],
                        r[f"{h}_fenwick_weight"],
                        r[f"{h}_corsi_weight"],
                    )
                )

    # 3v3: pkl values are identical across all score diffs — use bucket 0
    for is_home in [1, 0]:
        h = "home" if is_home else "away"
        r = sa["3v3"][0]
        rows.append(
            (
                "3v3",
                is_home,
                0,
                r[f"{h}_goal_weight"],
                r[f"{h}_pred_goal_weight"],
                r[f"{h}_shot_weight"],
                r[f"{h}_fenwick_weight"],
                r[f"{h}_corsi_weight"],
            )
        )

    # Advantage and disadvantage states: 3 buckets.
    # Flipped states use the mirror pkl state with is_home reversed (same logic as _game_utils.py).
    state_map = {
        "5v4": ("5v4", False),
        "4v5": ("5v4", True),
        "5v3": ("5v3", False),
        "3v5": ("5v3", True),
        "4v3": ("4v3", False),
        "3v4": ("4v3", True),
    }
    for st, (pkl_state, flipped) in state_map.items():
        for is_home in [1, 0]:
            pkl_is_home = (1 - is_home) if flipped else is_home
            h = "home" if pkl_is_home else "away"
            for bucket in [-1, 0, 1]:
                r = sa[pkl_state][bucket]
                rows.append(
                    (
                        st,
                        is_home,
                        bucket,
                        r[f"{h}_goal_weight"],
                        r[f"{h}_pred_goal_weight"],
                        r[f"{h}_shot_weight"],
                        r[f"{h}_fenwick_weight"],
                        r[f"{h}_corsi_weight"],
                    )
                )

    # 1v0: goal weight from pkl; xg/shot/fenwick/corsi zeroed (no model applies to empty net)
    for is_home in [1, 0]:
        h = "home" if is_home else "away"
        for bucket in [-1, 0, 1]:
            r = sa["1v0"][bucket]
            rows.append(("1v0", is_home, bucket, r[f"{h}_goal_weight"], 0.0, 0.0, 0.0, 0.0))

    states, homes, buckets, goal_w, xg_w, shot_w, fenwick_w, corsi_w = zip(*rows, strict=False)

    return pl.LazyFrame(
        {
            "strength_state": list(states),
            "is_home": pl.Series(list(homes), dtype=pl.Int8),
            "score_bucket": pl.Series(list(buckets), dtype=pl.Int8),
            "goal_w": list(goal_w),
            "xg_w": list(xg_w),
            "shot_w": list(shot_w),
            "fenwick_w": list(fenwick_w),
            "corsi_w": list(corsi_w),
        }
    )


adj_weights_lf = _build_adj_weights_lf()
