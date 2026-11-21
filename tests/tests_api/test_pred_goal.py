import narwhals as nw
import polars as pl
import pytest

from chickenstats.api import join_pred_goal
from chickenstats.exceptions import InvalidInputError


@pytest.fixture
def pbp():
    return pl.DataFrame(
        {
            "game_id": [2023020001] * 4,
            "event_idx": [1, 2, 3, 4],
            "event": ["FAC", "SHOT", "GOAL", "MISS"],
            "player_1_api_id": [8471214, 8478402, 8477934, None],
            "base_xg": [None, 0.01, 0.02, 0.03],
        }
    )


@pytest.fixture
def pred():
    return pl.DataFrame(
        {
            "game_id": [2023020001] * 3 + [2023020002],
            "event_idx": [2, 3, 4, 2],
            "season": [20232024] * 4,
            "session": ["R"] * 4,
            "event": ["SHOT", "GOAL", "MISS", "SHOT"],
            "period": [1] * 4,
            "period_seconds": [10, 20, 30, 40],
            "player_1_api_id": [8478402, 8477934, None, 8478402],
            "base_xg": [0.1, 0.2, 0.3, 0.4],
            "context_xg": [0.11, 0.21, 0.31, 0.41],
            "pred_goal": [0.12, 0.22, 0.32, 0.42],
        }
    )


def test_predictions_are_added_to_their_events(pbp, pred):
    result = join_pred_goal(pbp, pred)

    assert result.columns == ["game_id", "event_idx", "event", "player_1_api_id", "base_xg", "context_xg", "pred_goal"]
    assert result["event_idx"].to_list() == [1, 2, 3, 4]
    assert result["base_xg"].to_list() == [None, 0.1, 0.2, 0.3]
    assert result["pred_goal"].to_list() == [None, 0.12, 0.22, 0.32]


def test_a_null_shooter_on_both_sides_matches(pbp, pred):
    result = join_pred_goal(pbp, pred)

    assert result.filter(pl.col("event_idx") == 4)["context_xg"].item() == 0.31


def test_an_all_null_shooter_column_still_matches(pbp, pred):
    pbp = pbp.filter(pl.col("event_idx") == 4)
    pred = pred.filter(pl.col("event_idx") == 4).with_columns(pl.lit(None).alias("player_1_api_id"))

    assert join_pred_goal(pbp, pred)["pred_goal"].to_list() == [0.32]


def test_a_different_event_raises(pbp, pred):
    pred = pred.with_columns(event=pl.when(pl.col("event_idx") == 3).then(pl.lit("SHOT")).otherwise("event"))

    with pytest.raises(
        InvalidInputError, match=r"(?s)1 prediction\(s\).*event 3: pbp GOAL by 8477934, pred SHOT by 8477934"
    ):
        join_pred_goal(pbp, pred)


def test_a_different_shooter_raises(pbp, pred):
    pred = pred.with_columns(
        player_1_api_id=pl.when(pl.col("event_idx") == 4).then(8478402).otherwise("player_1_api_id")
    )

    with pytest.raises(InvalidInputError, match=r"event 4: pbp MISS by None, pred MISS by 8478402"):
        join_pred_goal(pbp, pred)


@pytest.mark.parametrize("column", ["event_idx", "player_1_api_id"])
def test_a_missing_pbp_column_raises(pbp, pred, column):
    with pytest.raises(InvalidInputError, match=f"pbp is missing the column\\(s\\) {column}"):
        join_pred_goal(pbp.drop(column), pred)


@pytest.mark.parametrize("column", ["game_id", "event", "pred_goal"])
def test_a_missing_pred_column_raises(pbp, pred, column):
    with pytest.raises(InvalidInputError, match=f"pred is missing the column\\(s\\) {column}"):
        join_pred_goal(pbp, pred.drop(column))


def test_a_repeated_prediction_raises(pbp, pred):
    with pytest.raises(InvalidInputError, match="more than one row"):
        join_pred_goal(pbp, pl.concat([pred, pred.head(1)]))


def test_old_adjusted_xg_is_dropped(pbp, pred):
    result = join_pred_goal(pbp.with_columns(base_xg_adj=pl.col("base_xg")), pred)

    assert "base_xg_adj" not in result.columns


@pytest.mark.parametrize(
    ("backend", "module", "frame_type"), [("pandas", "pandas", "DataFrame"), ("pyarrow", "pyarrow", "Table")]
)
def test_each_backend_returns_its_type(pbp, pred, backend, module, frame_type):
    native = pytest.importorskip(module)
    expected = getattr(native, frame_type)

    assert isinstance(join_pred_goal(pbp, pred, backend=backend), expected)


def test_narwhals_returns_narwhals(pbp, pred):
    assert isinstance(join_pred_goal(pbp, pred, backend="narwhals"), nw.DataFrame)


def test_the_output_follows_the_pbp_backend(pbp, pred):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")

    result = join_pred_goal(pbp.to_pandas(), pred.to_arrow())

    assert isinstance(result, pd.DataFrame)
    assert result["pred_goal"].tolist()[1:] == [0.12, 0.22, 0.32]
