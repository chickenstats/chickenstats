"""One rule for player names and eh_ids, used by the rosters, the play-by-play and the GAR and xGAR frames."""

import polars as pl

from chickenstats.chicken_nhl._player_names import correct_names_dict

# Duplicate names to replace with f"{name}2"
duplicate_names = {
    "SEBASTIAN.AHO": pl.col("position") == "D",
    "COLIN.WHITE": pl.col("season") >= 20162017,
    "SEAN.COLLINS": (pl.col("position").is_not_null() & (pl.col("position") != "D")),
    "ALEX.PICARD": (pl.col("position").is_not_null() & (pl.col("position") != "D")),
    "ERIK.GUSTAFSSON": pl.col("season") >= 20152016,
    "MIKKO.LEHTONEN": pl.col("season") >= 20202021,
    "NATHAN.SMITH": pl.col("season") >= 20212022,
    "DANIIL.TARASOV": pl.col("position") == "G",
    "ELIAS.PETTERSSON": ((pl.col("position") == "D") | (pl.col("team_jersey") == "VAN25")),
}

# Names to shorten
shortened_names = {"ALEXANDER": "ALEX", "ALEXANDRE": "ALEX", "CHRISTOPHER": "CHRIS"}


def player_name_expr(expr: pl.Expr) -> pl.Expr:
    """Turns an export name such as 'NIKITA.KUCHEROV' into the player name chicken_nhl uses, 'NIKITA KUCHEROV'.

    The accents go, long first names are shortened, known misspellings are corrected and a trailing '2' is dropped.
    A first name that ends in a dot is written with two, as in 'A.J..GREER', which becomes 'A.J. GREER'.
    """
    cleaned = (
        expr.str.normalize("NFKD")
        .str.replace_all(r"\p{Mn}", "")
        .str.replace_many(list(shortened_names.keys()), list(shortened_names.values()))
        .str.replace(r"2$", "")
    )
    spaced = (
        pl.when(cleaned.str.contains("..", literal=True))
        .then(cleaned.str.replace("..", ". ", literal=True))
        .otherwise(cleaned.str.replace(".", " ", literal=True))
    )
    return spaced.replace(correct_names_dict)


def name_key_expr(expr: pl.Expr) -> pl.Expr:
    """An export name reduced to the eh_id it starts from, before the suffix that separates two players."""
    return player_name_expr(expr).str.replace(" ", ".", literal=True).str.replace("..", ".", literal=True)


def eh_id_expr(expr: pl.Expr) -> pl.Expr:
    """The eh_id of an export name, with the '2' of the second player of a shared name.

    The frame needs ``position``, an integer ``season`` and ``team_jersey``.
    """
    key = name_key_expr(expr)
    is_second_player = pl.any_horizontal(
        expr.str.ends_with("2"), *[(key == name) & condition for name, condition in duplicate_names.items()]
    ).fill_null(False)

    return pl.when(is_second_player).then(key + "2").otherwise(key)
