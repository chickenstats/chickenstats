from unidecode import unidecode

correct_names_dict = {
    "AJ GREER": "A.J. GREER",
    "ALEXEY TOROPCHENKO": "ALEXEI TOROPCHENKO",
    "ANDR BENOT": "ANDRE BENOIT",
    "ANTHONY DEANGELO": "TONY DEANGELO",
    "BJ CROMBEEN": "B.J. CROMBEEN",
    "BO GROULX": "BENOIT-OLIVIER GROULX",
    "BRADLEY MILLS": "BRAD MILLS",
    "CAL PETERSEN": "CALVIN PETERSEN",
    "CALLAN FOOTE": "CAL FOOTE",
    "CAM HILLIS": "CAMERON HILLIS",
    "CHASE DELEO": "CHASE DE LEO",
    "CHRIS VANDE VELDE": "CHRIS VANDEVELDE",
    "CRISTOVAL NIEVES": "BOO NIEVES",
    "DAN CLEARY": "DANIEL CLEARY",
    "DANNY CLEARY": "DANIEL CLEARY",
    "DANIEL CARCILLO": "DAN CARCILLO",
    "DANNY BRIERE": "DANIEL BRIERE",
    "DANNY O'REGAN": "DANIEL O'REGAN",
    "DAVID JOHNNY ODUYA": "JOHNNY ODUYA",
    "EVGENII DADONOV": "EVGENY DADONOV",
    "EGOR SHARANGOVICH": "YEGOR SHARANGOVICH",
    "FREDDY MODIN": "FREDRIK MODIN",
    "FREDERICK MEYER IV": "FREDDY MEYER",
    "GERRY MAYHEW": "GERALD MAYHEW",
    "HARRISON ZOLNIERCZYK": "HARRY ZOLNIERCZYK",
    "JAMES WYMAN": "J.T. WYMAN",
    "JT WYMAN": "J.T. WYMAN",
    "JEAN-FRANCOIS BERUBE": "J-F BERUBE",
    "J.F. BERUBE": "J-F BERUBE",
    "J.J. MOSER": "JANIS MOSER",
    "JAKE MIDDLETON": "JACOB MIDDLETON",
    "JEAN-FRANCOIS JACQUES": "J-F JACQUES",
    "JONATHAN AUDY-MARCHESSAULT": "JONATHAN MARCHESSAULT",
    "JOSH DUNNE": "JOSHUA DUNNE",
    "JOSHUA MORRISSEY": "JOSH MORRISSEY",
    "JT BROWN": "J.T. BROWN",
    "JT COMPHER": "J.T. COMPHER",
    "KENNETH APPLEBY": "KEN APPLEBY",
    "KRYSTOFER BARCH": "KRYS BARCH",
    "MARTIN ST LOUIS": "MARTIN ST. LOUIS",
    "MARTIN ST PIERRE": "MARTIN ST. PIERRE",
    "MARTY HAVLAT": "MARTIN HAVLAT",
    "MATHEW DUMBA": "MATT DUMBA",
    "MATTHEW DUMBA": "MATT DUMBA",
    "MATTHEW BENNING": "MATT BENNING",
    "MATTHEW CARLE": "MATT CARLE",
    "MATTHEW IRWIN": "MATT IRWIN",
    "MATTHEW MURRAY": "MATT MURRAY",
    "MATTHEW NIETO": "MATT NIETO",
    "MATTIAS JANMARK-NYLEN": "MATTIAS JANMARK",
    "MAXIME TALBOT": "MAX TALBOT",
    "MAX LAJOIE": "MAXIME LAJOIE",
    "MAXWELL REINHART": "MAX REINHART",
    "MICHAEL CAMMALLERI": "MIKE CAMMALLERI",
    "MICHAEL GRIER": "MIKE GRIER",
    "MICHAEL FERLAND": "MICHEAL FERLAND",
    "MICHAEL MATHESON": "MIKE MATHESON",
    "MICHAEL RUPP": "MIKE RUPP",
    "MICHAEL SANTORELLI": "MIKE SANTORELLI",
    "MICHAEL YORK": "MIKE YORK",
    "MIKE ZIGOMANIS": "MICHAEL ZIGOMANIS",
    "MIKE VERNACE": "MICHAEL VERNACE",
    "MITCHELL MARNER": "MITCH MARNER",
    "NICOLAS PETAN": "NIC PETAN",
    "NICHOLAS BAPTISTE": "NICK BAPTISTE",
    "NICHOLAS BOYNTON": "NICK BOYNTON",
    "NICHOLAS CAAMANO": "NICK CAAMANO",
    "NICHOLAS DRAZENOVIC": "NICK DRAZENOVIC",
    "NICHOLAS PAUL": "NICK PAUL",
    "NICHOLAS SHORE": "NICK SHORE",
    "NICK ABRUZZESE": "NICHOLAS ABRUZZESE",
    "NICK MERKLEY": "NICHOLAS MERKLEY",
    "NICKLAS GROSSMAN": "NICKLAS GROSSMANN",
    "NIKLAS KRONVALL": "NIKLAS KRONWALL",
    "NIKOLAI KULEMIN": "NIKOLAY KULEMIN",
    "OLIVIER MAGNAN-GRENIER": "OLIVIER MAGNAN",
    "PA PARENTEAU": "P.A. PARENTEAU",
    "PIERRE-ALEX PARENTEAU": "P.A. PARENTEAU",
    "PAT MAROON": "PATRICK MAROON",
    "PHILIP VARONE": "PHIL VARONE",
    "QUINTIN HUGHES": "QUINN HUGHES",
    "RJ UMBERGER": "R.J. UMBERGER",
    "SAMMY WALKER": "SAMUEL WALKER",
    "SASHA CHMELEVSKI": "ALEX CHMELEVSKI",
    "STEVEN REINPRECHT": "STEVE REINPRECHT",
    "THOMAS MCCOLLUM": "TOM MCCOLLUM",
    "TIM GETTINGER": "TIMOTHY GETTINGER",
    "TJ GALIARDI": "T.J. GALIARDI",
    "TJ HENSICK": "T.J. HENSICK",
    "TJ OSHIE": "T.J. OSHIE",
    "TJ TYNAN": "T.J. TYNAN",
    "TOBY ENSTROM": "TOBIAS ENSTROM",
    "TOMMY NOVAK": "THOMAS NOVAK",  # API ID: 8478438
    "VINCENT HINOSTROZA": "VINNIE HINOSTROZA",
    "WILL BORGEN": "WILLIAM BORGEN",
    "WILLIAM THOMAS": "BILL THOMAS",
    "ZACHARY ASTON-REESE": "ZACH ASTON-REESE",
    "ZACHARY HAYES": "ZACK HAYES",
    "ZACHARY SANFORD": "ZACH SANFORD",
}

correct_api_names_dict = {
    8480222: "SEBASTIAN.AHO2",
    8476979: "ERIK.GUSTAFSSON2",
    8478400: "COLIN.WHITE2",
    8474744: "SEAN.COLLINS2",
    8471221: "ALEX.PICARD2",
    8482247: "MIKKO.LEHTONEN2",
    8480979: "NATHAN.SMITH2",
    8480193: "DANIIL.TARASOV2",
    8483678: "ELIAS.PETTERSSON2",
}


def correct_player_name(
    player_name: str, season: str | int, player_position: str | None = None, player_jersey: str | int | None = None
) -> tuple[str, str]:
    """Normalizes a player name and derives their Evolving Hockey ID.

    Applies prefix substitutions (ALEXANDRE → ALEX, etc.), looks up known
    misspellings in correct_names_dict, builds the EH ID from the cleaned
    name, then appends a "2" suffix for players with duplicate IDs based on
    season, position, or jersey number.

    Parameters:
        player_name: Raw player name in ALL CAPS.
        season: Eight-digit season integer, e.g. 20232024.
        player_position: Position code, e.g. "D", "C", "G".
        player_jersey: Jersey number as int or team-prefixed string, e.g. 25 or "VAN25".

    Returns:
        Tuple of (corrected_name, eh_id).
    """
    player_name = player_name.replace("ALEXANDRE", "ALEX").replace("ALEXANDER", "ALEX").replace("CHRISTOPHER", "CHRIS")

    player_name = correct_names_dict.get(player_name, player_name)

    player_eh_id = unidecode(player_name)
    name_split = player_eh_id.split(" ", maxsplit=1)

    player_eh_id = f"{name_split[0]}.{name_split[1]}".replace("..", ".")

    # Correcting Evolving Hockey IDs for duplicates

    season_int = int(season)

    duplicates = {
        "SEBASTIAN.AHO": player_position == "D",
        "COLIN.WHITE": season_int >= 20162017,
        "SEAN.COLLINS": player_position is not None and player_position != "D",
        "ALEX.PICARD": player_position is not None and player_position != "D",
        "ERIK.GUSTAFSSON": season_int >= 20152016,
        "MIKKO.LEHTONEN": season_int >= 20202021,
        "NATHAN.SMITH": season_int >= 20212022,
        "DANIIL.TARASOV": player_position == "G",
        "ELIAS.PETTERSSON": player_position == "D" or player_jersey == "VAN25" or player_jersey == 25,
    }

    for duplicate_name, condition in duplicates.items():
        if player_eh_id == duplicate_name and condition:
            player_eh_id = f"{duplicate_name}2"

    # Something weird with Colin White

    if player_eh_id == "COLIN.":  # Not covered by tests
        player_eh_id = "COLIN.WHITE2"

    return player_name, player_eh_id
