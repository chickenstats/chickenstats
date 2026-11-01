from functools import lru_cache

from chickenstats.chicken_nhl._game_utils import _DISADVANTAGE_STATES, _ELIGIBLE_STRENGTH_STATES, load_score_adjustments


def _build_adj_weights_lf():
    """Builds a lookup LazyFrame mapping (strength_state, is_home, score_bucket) → weights.

    Derived from score_adjustments.pkl (chicken_nhl) so both modules share the same calibration, with one row for
    every state and score difference the table holds. A disadvantage state (4v5, 3v5, 3v4) is looked up through its
    mirror state, from the other team's side, as in chicken_nhl._game_utils.calculate_score_adjustment.
    States not listed, such as a penalty shot (1v0) or an empty net, have no row, and their adjusted stats
    keep the raw value.
    """
    import polars as pl

    sa = load_score_adjustments()

    states = {state: (state, False) for state in _ELIGIBLE_STRENGTH_STATES}
    states.update({state: (mirror, True) for state, mirror in _DISADVANTAGE_STATES.items()})

    rows = []

    for state, (table_state, flipped) in states.items():
        for is_home in (1, 0):
            side = "home" if bool(is_home) != flipped else "away"
            for bucket, weights in sa[table_state].items():
                rows.append(
                    {
                        "strength_state": state,
                        "is_home": is_home,
                        "score_bucket": bucket,
                        "goal_w": weights[f"{side}_goal_weight"],
                        "xg_w": weights[f"{side}_pred_goal_weight"],
                        "shot_w": weights[f"{side}_shot_weight"],
                        "fenwick_w": weights[f"{side}_fenwick_weight"],
                        "corsi_w": weights[f"{side}_corsi_weight"],
                    }
                )

    return pl.LazyFrame(rows).with_columns(pl.col("is_home", "score_bucket").cast(pl.Int8))


@lru_cache(maxsize=1)
def get_adj_weights_lf():
    """Lazily build and cache the score-adjustment weights LazyFrame.

    Deferred (not built at import time) so importing chickenstats.evolving_hockey doesn't
    unpickle/decompress chicken_nhl's score-adjustment file before it's actually needed.
    """
    return _build_adj_weights_lf()
