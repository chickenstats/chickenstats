from datetime import datetime

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    SpinnerColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

import io

from chickenstats.chicken_nhl.helpers import s_session


def munge_cf(df: pd.DataFrame, scrape_year: int):
    """Function to clean raw data from capfriendly.com"""
    new_cols = {
        x: x.lower().replace(" ", "_").replace("._", "_").replace(".", "_")
        for x in df.columns
    }

    df.rename(columns=new_cols, inplace=True)

    df.player = df.player.replace(r"(\d+\.)", "", regex=True).str.strip()

    df.player = (
        df.player.str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
    )

    df.country = (
        df.country.str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
        .str.upper()
    )

    df.handed = df.handed.str.upper()

    df.drafted = df.drafted.astype(str).str.upper()

    split = df.drafted.astype(str).str.split("-", n=2, expand=True)
    df["pick"] = split[0].str.strip()
    df.pick = np.where(df.pick == "nan", np.nan, df.pick)
    df["round"] = split[1].str.strip()
    df["draft_year (Team)"] = split[2].str.strip()

    split = df["draft_year (Team)"].str.split(" ", n=2, expand=True)
    df["draft_year"] = split[0].str.strip()
    df["draft_team"] = split[1].str.strip()
    df["draft_team"] = (
        df["draft_team"]
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
    )

    split = df["date_of_birth"].str.split(",", n=1, expand=True)
    df["birth_year"] = split[1].str.strip().astype(int)
    df["birth_date_dt"] = pd.to_datetime(df["date_of_birth"], format="mixed")
    df["birth_date"] = df.birth_date_dt.dt.strftime("%Y-%m-%d")

    today = pd.to_datetime(datetime.today())

    df["age_precise"] = (today - df.birth_date_dt).dt.days / 365.2425

    cols = [
        "cap_hit",
        "cap_hit_%",
        "aav",
        "salary",
        "base_salary",
        "s_bonus",
        "p_bonus",
        "minors",
    ]

    for col in cols:
        df[col] = (
            df[col]
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace("%", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col])  # .convert_dtypes()

    player_split = df.player.str.split(" ", n=1, expand=True)

    alexs = ["ALEXANDER", "ALEXANDRE"]

    for alex in alexs:
        player_split[0] = player_split[0].str.upper().replace(alex, "ALEX", regex=True)

    player_split[0] = player_split[0].str.upper().replace("JOSHUA", "JOSH", regex=True)
    player_split[0] = player_split[0].str.upper().replace("SAMUEL", "SAM", regex=True)
    player_split[0] = player_split[0].str.upper().replace("JOSEPH", "JOE", regex=True)

    df.player = player_split[0].str.upper() + "." + player_split[1].str.upper()

    names_dict = {
        "MITCHELL.MARNER": "MITCH.MARNER",
        "JOSHUA.MORRISSEY": "JOSH.MORRISSEY",
        "MATTHEW.BOLDY": "MATT.BOLDY",
        "DANIEL.VLADAR": "DAN.VLADAR",
        "ANTHONY.DEANGELO": "TONY.DEANGELO",
        "MICHAEL.MATHESON": "MIKE.MATHESON",
        "NICHOLAS.PAUL": "NICK.PAUL",
        "CHRISTOPHER.TANEV": "CHRIS.TANEV",
        "J.J..MOSER": "JANIS.MOSER",
        "MATTHEW.BENNING": "MATT.BENNING",
        "EVGENI.DADONOV": "EVGENY.DADONOV",
        "MAXIME.COMTOIS": "MAX.COMTOIS",
        "JOHN-JASON.PETERKA": "J.J.PETERKA",
        "JOSHUA.NORRIS": "JOSH.NORRIS",
        "MATTHEW.BENIERS": "MATTY.BENIERS",
        "ZACHARY.WERENSKI": "ZACH.WERENSKI",
        "JOSHUA.BROWN": "JOSH.BROWN",
        "SAMUEL.MONTEMBEAULT": "SAM.MONTEMBEAULT",
        "JOSHUA.MAHURA": "JOSHUA.MAHURA",
        "ALEXANDER.KERFOOT": "ALEX.KERFOOT",
        "ALEXANDER.WENNBERG": "ALEX.WENNBERG",
        "AJ.GREER": "A.J.GREER",
        "SAM.GIRARD": "SAMUEL.GIRARD",
        "MICHAEL.ANDERSON": "MIKEY.ANDERSON",
        "CAL.PETERSEN": "CALVIN.PETERSEN",
        "SAM.ERSSON": "SAMUEL.ERSSON",
        "ZACHARY.JONES": "ZAC.JONES",
        "JACOB.CHRISTIANSEN": "JAKE.CHRISTIANSEN",
        "ALEXEY.TOROPCHENKO": "ALEXEI.TOROPCHENKO",
        "YEGOR.ZAMULA": "EGOR.ZAMULA",
        "ZACHARY.SANFORD": "ZACH.SANFORD",
        "SAM.BLAIS": "SAMMY.BLAIS",
        "NICOLAS.PETAN": "NIC.PETAN",
        "SAM.WALKER": "SAMUEL.WALKER",
        "JOE.CRAMAROSSA": "JOSEPH.CRAMAROSSA",
        "DANIEL.RENOUF": "DAN.RENOUF",
        "C.J..SUESS": "CJ.SUESS",
        "SAM.FAGEMO": "SAMUEL.FAGEMO",
        "WILL.BITTEN": "WILLIAM.BITTEN",
    }

    for old_name, new_name in names_dict.items():
        df.player = df.player.str.replace(old_name, new_name, regex=False)

    DUOS = {
        "SEBASTIAN.AHO": df.pos.str.contains("D"),
        "COLIN.WHITE": df.season >= 20162017,
        "SEAN.COLLINS": df.season >= 20162017,
        "ALEX.PICARD": ~df.pos.str.contains("D"),
        "ERIK.GUSTAFSSON": df.season >= 20152016,
        "MIKKO.LEHTONEN": df.season >= 20202021,
        "NATHAN.SMITH": df.season >= 20212022,
        "DANIIL.TARASOV": df.pos == "G",
    }

    DUOS = [
        np.logical_and(df.player == player, condition)
        for player, condition in DUOS.items()
    ]

    df["player_id"] = np.where(np.logical_or.reduce(DUOS), df.player + "2", df.player)

    df["weight_lbs"] = (
        df.weight.str.split("-", expand=True)[0].str.replace(" lbs", "").astype(int)
    )

    df["weight_kg"] = (
        df.weight.str.split("-", expand=True)[1].str.replace(" kg", "").astype(int)
    )

    df["height_imperial"] = df.height.str.split("-", n=1, expand=True)[0]

    height_split = df.height_imperial.str.replace('"', "").str.split("'", expand=True)

    df["height_ft"] = height_split[0].astype(int) + (height_split[1].astype(int) / 12)

    df["height_cm"] = (
        df.height.str.split("-", expand=True)[1].str.replace(" cm", "").astype(int)
    )

    df["years_remaining"] = df.exp_year - scrape_year

    df["years_remaining_pct"] = df.years_remaining / df.length

    df["signing_date_dt"] = pd.to_datetime(df.signing_date, format="mixed")

    df.signing_date = df.signing_date_dt.dt.strftime("%Y-%m-%d")

    df["signing_age_precise"] = (
        df.signing_date_dt - df.birth_date_dt
    ).dt.days / 365.2425

    df["contract_type"] = df["type"].str.upper()

    cols = [
        "extension",
        "slide_cand_",
        "arb_req",
        "arb_elig_1",
        "waivers_exempt",
    ]

    cols = [x for x in cols if x in df.columns]

    for col in cols:
        df[col] = np.where(pd.notnull(df[col]), 1, 0)

    df = df.fillna(np.nan)

    cols = [
        "season",
        "player",
        "player_id",
        "team",
        "pos",
        "country",
        "birth_date",
        "birth_year",
        "age",
        "age_precise",
        "handed",
        "height_ft",
        "height_cm",
        "weight_lbs",
        "weight_kg",
        "drafted",
        "draft_year",
        "draft_team",
        "pick",
        "round",
        "signing_date",
        "signing_age",
        "signing_age_precise",
        "signing",
        "expiry",
        "exp_year",
        "years_remaining",
        "pct_remaining",
        "length",
        "extension",
        "contract_type",
        "aav",
        "salary",
        "base_salary",
        "cap_hit",
        "cap_hit_%",
        "s_bonus",
        "p_bonus",
        "clause",
        "arb_req",
        "arb_elig_1",
        "waivers_exempt",
        "minors",
        "slide_cand_",
    ]

    cols = [x for x in cols if x in df.columns]

    rename_cols = {
        "pick": "draft_pick",
        "round": "draft_round",
        "exp_year": "expiration_year",
        "cap_hit_%": "cap_hit_pct",
        "p_bonus": "performance_bonus",
        "s_bonus": "signing_bonus",
        "arb_req": "arbitration_required",
        "arb_elig_1": "arbitration_eligible",
        "pos": "position",
        "length": "contract_length",
        "slide_cand_": "slide_candidate",
        "extension": "contract_extension",
    }

    df = df[cols].rename(columns=rename_cols).drop_duplicates()

    return df


def scrape_capfriendly(year: int | list[int | str] = 2023):
    """
    Scrape salary data from Capfriendly for a given year or years. Returns a Pandas DataFrame.
    By default, returns data from the 2023-2024 season. Historical data supported.
    Typically takes 8-12 seconds per season.

    For a glossary of terms, please visit www.capfriendly.com

    Parameters:
        year (str | int):
            Four-digit year, or list-like object consisting of four-digit years

    Returns:
        season (int):
            8-digit season code, e.g., 20222023
        player_name (str):
            Player's latin-encoded name, e.g., FILIP.FORSBERG
        player_id (str):
            Identifier that can be used to match with Evolving Hockey data, e.g., FILIP.FORSBERG
        team (str):
            3-letter team code, e.g., NSH
        country (str):
            Country with which player is affiliated, e.g., SWEDEN
        position (str):
            Player's position, e.g., LW
        birth_date (str):
            Player's birth date, e.g., 1994-08-13
        birth_year (int):
            Player's birth year, e.g., 1994
        age (int):
            Player's age as of start of the season, e.g., 28
        age_precise (float):
            Player's age as of the time the data is scraped, e.g., 28.62208
        handed (str):
            Hand with which the player shoots (skater) or catches (goalie), e.g., RIGHT
        height_ft (float):
            Player's height in feet, e.g., 6.083333
        height_cm (int):
            Player's height in centimeters, e.g., 185
        weight_lbs (int):
            Player's weight in pounds, e.g., 205
        weight_kg (int):
            Player's weight in kilograms, e.g., 93
        drafted (str):
            Player's draft information, e.g., 11 - ROUND 1 - 2012 (WSH)
        draft_year (int):
            Year player was drafted, e.g., 2012
        draft_team (str):
            Team that drafted player, e.g., WSH
        draft_pick (str):
            Pick with which player was drafted, e.g., 11
        draft_round (str):
            Round in which player was drafted, e.g., ROUND 1
        signing_date (str):
            Date on which current contract was signed, e.g., 2022-07-09
        signing_age (int):
            Age in years at time of signing, e.g., 27
        signing_age_precise (float):
            Age in years at time of singing, e.g., 27.904748
        signing (str):
            Contract type at time of signing, e.g., UFA
        expiry (str):
            Contract type at time of expiry, e.g., UFA
        expiration_year (int):
            Year the current contract expires, e.g., 2030
        years_remaining (int):
            Years remaining on the contract from current year, e.g., 7
        contract_length (int):
            Length of the contract, e.g., 8
        contract_extension (int):
            Dummy variable for if the contract was an extension, e.g., 1
        contract_type (str):
            Type of contract, e.g., STANDARD (1-WAY)
        aav (int):
            Average annual value of contract, e.g., 8500000
        salary (int):
            Salary value of contract, e.g., 10000000
        base_salary (int):
            Base salary value of contract, e.g., 10000000
        cap_hit (int):
            Dollar value hit to salary cap, e.g., 8500000
        cap_hit_pct (float):
            Percentage of salary cap allocated to player, e.g, 10.3%
        signing_bonus (int):
            Dollar value of signing bonus, e.g., 0
        performance_bonus (int):
            Dollar value of performance bonus, e.g., 0
        clause (str):
            Type of trade protections player has, e.g., NMC
        arbitration_required (int):
            Whether salary arbitration is required, e.g., 0
        arbitration_eligible (int):
            Whether the contract is eligible for arbitration, e.g., 0
        minors (float):
            Salary if player were in the minors, e.g., 10000000
        slide_candidate (int):
            Whether player is a slide candidate, e.g., 0

    Examples:
        Scrape all contract information for active players in the current season
        >>> cf = scrape_capfriendly()

        Returns data for multiple seasons
        >>> years = list(range(2019, 2023))
        >>> cf = scrape_capfriendly(years)

    """

    s = s_session()

    concat_list = []

    with s as s:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            SpinnerColumn(),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
        ) as progress:
            scrape_year = year + 1

            season = int(f"{year}{year + 1}")

            pages = range(1, 51)

            concat_list = list()

            pbar_message = "Downloading CapFriendly data..."

            cf_task = progress.add_task(pbar_message, total=len(pages))

            for page in pages:
                url = f"https://www.capfriendly.com/browse/active/{scrape_year}"

                display_param = (
                    "birthday,country,weight,height,weightkg,heightcm,draft,slide-candidate,"
                    "waivers-exempt,signing-status,expiry-year,performance-bonus,signing-bonus,caphit-percent,aav,"
                    "length,minors-salary,base-salary,arbitration-eligible,type,signing-age,signing-date,"
                    "arbitration,extension"
                )

                hide_param = "skater-stats,goalie-stats"

                payload = {
                    "age-calculation-date": "october1",
                    "display": display_param,
                    "hide": hide_param,
                    "pg": str(page),
                }

                response = s.get(url, params=payload)

                if response.status_code != 200:
                    pbar_message = (
                        f"SCRAPING CAPFRIENDLY DATA FOR THE {year}-{scrape_year} SEASON"
                    )

                    progress.update(
                        cf_task, description=pbar_message, advance=1, refresh=True
                    )

                    continue

                soup = BeautifulSoup(response.text, "lxml")

                response_df = pd.read_html(
                    io.StringIO(str(soup.find_all("table"))), na_values="-"
                )[0]

                if response_df.empty:
                    pbar_message = (
                        f"SCRAPING CAPFRIENDLY DATA FOR THE {year}-{scrape_year} SEASON"
                    )

                    progress.update(
                        cf_task, description=pbar_message, advance=1, refresh=True
                    )

                    continue

                response_df["season"] = season

                concat_list.append(response_df)

                year_df = pd.concat(concat_list, ignore_index=True)

                year_df = munge_cf(year_df, scrape_year=scrape_year)

                pbar_message = (
                    f"SCRAPING CAPFRIENDLY DATA FOR THE {year}-{scrape_year} SEASON"
                )

                progress.update(
                    cf_task, description=pbar_message, advance=1, refresh=True
                )

    return year_df
