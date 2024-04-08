---

icon: material/notebook

---

# :material-notebook: **Introduction**

Welcome to the technical documentation & reference materials for
**[chickenstats](https://github.com/chickenandstats/chickenstats)**,
a Python package for scraping & analyzing sports data. With just a few lines of code:

* **Scrape & manipulate** data from various NHL endpoints, leveraging
[:material-hockey-sticks: chicken_nhl](reference/chicken_nhl/scrape.md), which includes
a **proprietary xG model** for shot quality metrics
* **Augment play-by-play data** & **generate custom aggregations** from raw csv files downloaded from
[Evolving-Hockey](https://evolving-hockey.com) *(subscription required)* with
[:material-hockey-puck: evolving_hockey](reference/evolving_hockey/stats.md)

Here you can find detailed guides & explanations for most features. The package is under active development - download
the latest version (1.8.0) for the most up-to-date features & be sure to consult the correct documentation
:fontawesome-solid-face-smile-beam:.

## :material-navigation: **Navigation**

??? tip 
    Navigate the site using the header, side-bar, or search tool.
    Mobile users can tap **:material-menu:** (upper-left) to bring up the menu, then
    **:material-table-of-contents:** to see a linked table of contents for the current page,
    or **:material-arrow-left:** to navigate the menu back towards the home page. 

<div class="grid cards" markdown>

-   :material-download-box:{ .lg .middle } __Usage & installation__

    ---

    Download & install `chickenstats` with `pip` to get up
    & running in just a few minutes.

    [:octicons-arrow-right-24: Getting Started](home/getting_started.md)

-   :material-school:{ .lg .middle } __Tutorials & examples__

    ---

    Discover the package using hands-on tutorials
    & examples from the User Guide.

    [:octicons-arrow-right-24: User Guide](guide/guide.md)

-   :material-bookshelf:{ .lg .middle } __Reference materials__

    ---

    Consult the Reference section for in-depth explanations 
    & debugging assistance.

    [:octicons-arrow-right-24: Reference](reference/reference.md)

-   :material-google-analytics:{ .lg .middle } __xG model__

    ---

    Learn about the open-source expected goals (xG) model included with `chickenstats`.

    [:octicons-arrow-right-24: xG model](xg_model/xg_model.md)

-   :material-typewriter:{ .lg .middle } __Blog__

    ---

    Read the latest analyses leveraging the library, as well as about the newest features & releases

    [:octicons-arrow-right-24: Blog](blog/index.md)

-   :fontawesome-solid-user-group:{ .lg .middle } __Contribute__

    ---

    Read about known issues, future development roadmap, and/or how to contribute. 

    [:octicons-arrow-right-24: Contribute](contribute/contribute.md)

</div>

## :material-information: **Overview**

`chickenstats` is open-source because open-source is cool.

The library is composed of two modules, each for a different data source.

=== ":material-hockey-sticks: `chicken_nhl`"
    
    `chickenstats.chicken_nhl` provides tools to scrape data from official NHL sources(1)
    & construct a play-by-play dataframe with 70+ potential fields(2) for each event.(3)
    Each game is scraped in approximately 3-4 seconds, with minimal performance degradation
    after scraping hundreds or thousands of games.(4) All underlying data is stored after retrieval
    and processing.(5)
    { .annotate } 

    1.  Sources include (non-exhaustive): :material-numeric-1-circle: HTML shifts,
    :material-numeric-2-circle: events, &
    :material-numeric-3-circle: rosters, as well as :material-numeric-4-circle: events,
    :material-numeric-5-circle: rosters, & :material-numeric-6-circle: game information
    from the NHL's API endpoints.
    2.  Fields include (non-exhaustive) primary player idenfitication & information
    (e.g., position), various game state characteristics (e.g., strength-state, score-state,
    score differential), Cartesian event coordinates, shot type (e.g., wrist, slap, deflection),
    distance & angle from net,  & on-ice teammate & opponent identification & information.
    3.  Supported events include: :material-numeric-1-circle: goals (including assists),
    :material-numeric-2-circle: shots on net, :material-numeric-3-circle: missed shots,
    :material-numeric-4-circle: blocked shots, :material-numeric-5-circle: faceoffs,
    :material-numeric-6-circle: penalties & delayed penalties, :material-numeric-7-circle:
    giveaways, & :material-numeric-8-circle: takeaways.
    4.  This can be improved (and will be as the library is refactored).
    However, the library was designed with known negative impacts (e.g., Pydantic-based data validation).
    5.  For example, HTML & API events data, key inputs for the play-by-play DataFrame,
    are retained after scraping play-by-play data. This reduces the burden on public endpoints & improves debugging.

    ??? info "Data are supported from 2010-11 to present"
        With some exceptions for individual games, the `Game` & `Scraper` objects 
        will return data for games occurring since the start of
        the 2010-2011 season. However, the `Season` object (including the `schedule()`
        & `standings()` methods) will return data extending to the NHL's founding in 1917.

    The module includes three classes for accessing data. First, import the relevant classes
        
    ```python
    from chickenstats.chicken_nhl import Scraper, Season, Game
    ```

    === "`Scraper`"

        Scrapes individual & multiple games. It takes a single game ID or a
        list-like object of game IDs & scrapes publicly-accessible,
        official NHL endpoints and returns a Pandas DataFrame.

        Data include (non-exhaustive): :material-numeric-1-circle: HTML shifts,
        :material-numeric-2-circle: events, &
        :material-numeric-3-circle: rosters, as well as :material-numeric-4-circle: events,
        :material-numeric-5-circle: rosters, & :material-numeric-6-circle: game information
        from the NHL's API endpoints.

        ???+ Example

            Scrape play-by-play data for the first ten games of the current (2023-24) regular season
    
            ```python
            game_ids = list(range(2023020001, 2023020011))
            scraper = Scraper(game_ids)
            pbp = scraper.play_by_play
            ```
    
            Scrape roster data for the first ten games of the current (2023-24) regular season
    
            ```python
            game_ids = list(range(2023020001, 2023020011))
            scraper = Scraper(game_ids)
            rosters = scraper.rosters
            ```

    === "`Game`"
        
        Scrapes data for a single game. A series of `Game` objects functions as the backbone of any `Scraper` object.

        ???+ Example

            The `Game` object functions similarly to the `Scraper` object, with the major exception that
            data are returned as a list by default.
    
            To return a list of play-by-play events
    
            ```python
            game_id = 2023020001
            game = Game(game_id)
            pbp = game.play_by_play
            ```
    
            To return the equivalent Pandas DataFrame, simply append "_df" to the property
    
            ```python
            game_id = 2023020001
            game = Game(game_id)
            pbp = game.play_by_play_df
            ```

        A `Scraper` can access data for both individual and multiple games, so I would recommend
        sticking around there. 
        
        ??? Info "Contribute"
            That said, if you'd like to contribute, the `Game`
            object provides non-public methods to access
            data at intermediate processing stages. The below returns a list of raw HTML events, prior to any processing.
            
            ```python
            from chickenstats.chicken_nhl import Game
        
            game_id = 2023020001
            game = Game(game_id)
            html_events = game._scrape_html_events()
            ```
            For more information & direction, see [:fontawesome-solid-user-group: Contribute](contribute/contribute.md)
        
    === "`Season`"

        Scrapes schedule and standings information for a given season.

        ???+ Example

            Scrape schedule data for every team for the current (2023-24) season
    
            ```python
            season = Season(2023)
            schedule = season.schedule()
            ```
    
            For a specific team, just provide the three-letter abbreviation
    
            ```python
            season = Season(2023)
            schedule = season.schedule('NSH')
            ```

            To get the latest standings for that season

            ```python
            season = Season(2023)
            standings = season.standings
            ```

=== ":material-hockey-puck: `evolving_hockey`"

    `chickenstats.evolving_hockey` provides tools to munge data from official evolving-hockey.com.(1) The module's
    functions combine raw play-by-play and shift csv files available from the queries section of the site, then 
    aggregate the data.(2) The resulting aggregations have additional fields(3) that are not currently available.
    { .annotate } 

    1.  Subscription (and I cannot emphasize this enough) required.
    2.  Aggregations include line and team level, as well as groupings by score state, teammates, and opposition.
    3.  Additional fields include: :material-numeric-1-circle: high-danger events,
    :material-numeric-2-circle: score- and venue-adjusted events, using evolving-hockey's methodology and figures
    :material-numeric-3-circle: forwards and defensemen on-ice.

    The module includes four functions for accessing data. First, import the relevant functions
        
    ```python
    from chickenstats.evolving_hockey import prep_pbp, prep_stats, prep_lines, prep_team
    ```

    === "`prep_pbp()`"

        Combines the raw play-by-play and shifts CSV files into a Pandas DataFrame with additional fields for
        analysis and aggregation.

        ???+ Example

            Combine CSV files into Pandas DataFrame
    
            ```python
            shifts_raw = pd.read_csv('shifts_raw.csv')
            pbp_raw = pd.read_csv('pbp_raw.csv')

            pbp = prep_pbp(pbp_raw, shifts_raw)
            ```

    === "`prep_stats()`"
        
        Aggregates an individual player's stats and on-ice stats. Can be grouped by teammates and opposition.

        ???+ Example

            First, have a cleaned play-by-play DataFrame handy

            ```python
            shifts_raw = pd.read_csv('shifts_raw.csv')
            pbp_raw = pd.read_csv('pbp_raw.csv')

            pbp = prep_pbp(pbp_raw, shifts_raw)
            ```

            Basic game-level stats, with no teammates or opposition
            
            ```python
            stats = prep_stats(pbp)
            ```

            Period-level stats, grouped by teammates

            ```python
            stats = prep_stats(pbp, level = 'period', teammates=True)
            ```

            Session-level (e.g., regular seasion) stats, grouped by teammates and opposition
            
            ```python
            stats = prep_stats(pbp, level='session', teammates=True, opposition=True)
            ```
        
    === "`prep_lines()`"

        Aggregates forward or defensive line statistics, with options to group by teammates, opposition, score state,
        and strength state

        ???+ Example

            First, have a cleaned play-by-play DataFrame handy

            ```python
            shifts_raw = pd.read_csv('shifts_raw.csv')
            pbp_raw = pd.read_csv('pbp_raw.csv')

            pbp = prep_pbp(pbp_raw, shifts_raw)
            ```

            Basic game-level stats for forwards, with no teammates or opposition
            
            ```python
            lines = prep_lines(pbp, position='f')
            ```

            Period-level stats for defense, grouped by teammates

            ```python
            lines = prep_lines(pbp, position='d', level='period', teammates=True)
            ```

            Session-level (e.g., regular seasion) stats, grouped by teammates and opposition
            
            ```python
            lines = prep_lines(pbp, position='f', level='session', teammates=True, opposition=True)
            ```

    === "`prep_team()`"

        Aggregates team statistics, can be grouped by score state.

        ???+ Example

            First, have a cleaned play-by-play DataFrame handy

            ```python
            shifts_raw = pd.read_csv('shifts_raw.csv')
            pbp_raw = pd.read_csv('pbp_raw.csv')

            pbp = prep_pbp(pbp_raw, shifts_raw)
            ```

            Basic game-level stats for teams
    
            ```python
            team = prep_team(pbp)
            ```
    
            Period-level team stats, grouped by score state
    
            ```python
            team = prep_team(pbp, level='period', score=True)
            ```

For more detailed tutorials & examples or in-depth reference materials,
consult [:material-school: User Guide](guide/guide.md) or
[:material-bookshelf: Reference](reference/reference.md)

## :material-help: **Help**

How to get help [:octicons-arrow-right-24: Help](home/help.md)

## :material-heart: **Acknowledgements**

`chickenstats` would not be possible without the efforts of countless other individuals.
