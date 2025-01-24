---
icon: octicons/project-roadmap-16
description: "Roadmap for chickenstats development"
---

# :octicons-project-roadmap-16: **Roadmap**

`chickenstats` is an imperfect library with big ambitions and is actively seeking contributions in various ways.
Below are what I think are both the most interesting and would advance the library furthest: 

## :material-numeric-1-circle: **Research and analytics**

"Priority 1A" for the `chickenstats` library is to improve the existing and introduce additional 
statistics and evaluation tools - this was the original goal of the entire project.

The below are just an initial starting point - please feel free to leverage the library for
whatever research you find most interesting. 

- [ ] Regularized Adjusted Plus-Minus (RAPM) / Adjusted Plus-Minus (APM)
- [ ] Goals Above Replacement (GAR) / xG Above Replacement (xGAR)
- [ ] Wins Above Replacement (WAR)

## :material-numeric-2-circle: **Asynchronous scraping**

Re-writing the library to leverage [aiohttp](https://docs.aiohttp.org/en/stable/) is "Priority 1B" for two reasons:

1. asynchronous scraping would speed up the `Scraper` object substantially 
2. The library is fairly extensible (I hope, that was the intention), 
so could be adapted fairly quickly

### Speed improvements

The `chickenstats.chicken_nhl.play_by_play` property scrapes data from seven endpoints before consolidating
into a final play-by-play dataframe, as illustrated by the diagram below. 

Just asynchronous scraping, without any asynchronous (or multithreaded) processing should reduce the time 
to scrape data significantly. My ambitious goal for v2.0 is to reduce the play-by-play scraping time to ~1 second
per game vs. the current 2-4 seconds per game.

``` mermaid
graph LR
  subgraph "raw data"
    html_events_raw(html events endpoint)
    html_rosters_raw(html rosters endpoint)
    html_home_shifts_raw(html home shifts endpoint)
    html_away_shifts_raw(html away shifts endpoint)
    api_rosters_raw(api rosters endpoint)
    api_events_raw(api events endpoint)
    game_info_raw(api game info endpoint)
  end
  subgraph "initial processing"
    html_rosters(html rosters df)
    html_events(html events df)
    api_rosters(api rosters df)
    api_events(api events df)
    shifts(shifts df)
    changes(changes df)
    rosters(rosters df)
  end
  subgraph "final dataframe"
    play_by_play(combined play-by-play df)
  end
    
  html_events_raw(html events endpoint) --> html_events(html events df);
  html_home_shifts_raw --> shifts(shifts df);
  html_away_shifts_raw --> shifts(shifts df);
  shifts --> changes(changes df);
  html_rosters_raw --> html_rosters(html rosters df)
  html_rosters --> rosters(rosters df);
  changes --> play_by_play(combined play-by-play df);
  rosters --> changes(changes df);
  rosters --> play_by_play;
  html_rosters --> html_events;
  html_events --> play_by_play;
  api_events_raw(api events endpoint) --> api_events(api events df);
  game_info_raw(api game info endpoint) --> api_events;
  api_events --> play_by_play(combined play-by-play);
  api_rosters_raw(api rosters endpoint) --> api_rosters(api rosters df);
  api_rosters --> rosters;
  api_rosters --> api_events;
```

### Library extensibility

The good news is that the library was designed with asynchronous scraping and multithreaded processing in-mind - 
each data source (e.g., API events) has a `_scrape` and `_munge` method, before being returned as either a list or
Pandas dataframe. The below code snippet is taken from the `Game` object's `play_by_play` property and demonstrates
this point:

```python
@property
def play_by_play(self) -> list:
    """Docstring omitted for brevity."""
    if self._play_by_play is None: # (1)!
        if self._rosters is None:
            if self._api_rosters is None:
                self._munge_api_rosters() # (2)!

            if self._html_rosters is None:
                self._scrape_html_rosters() # (3)!
                self._munge_html_rosters()

            self._combine_rosters() # (4)!

        if self._changes is None:
            self._scrape_shifts()
            self._munge_shifts()

            self._munge_changes()

        if self._html_events is None: # (5)!
            self._scrape_html_events()
            self._munge_html_events()

        if self._api_events is None:
            self._munge_api_events()

        self._combine_events() # (6)!
        self._munge_play_by_play() # (7)!
        self._prep_xg() # (8)!

    return self._play_by_play # (9)!
```

1. The property first checks if the data have already been scraped - this step is repeated for all underlying
data sources
2. The API events and API rosters are scraped when immediately, which is why there are no `_scrape_api_events()`
or `_scrape_api_rosters()` methods as part of the `Game` object
3. The `_scrape_html_rosters()` and `_munge_html_rosters()` are completely separate methods - the scraped data are 
stored as the `_html_events` attribute, which is then fed into the processing method
4. This method combines the API and HTML rosters into one combined dataset
5. The order of operations matters here - the HTML events dataset requires the rosters and changes to be scraped
and processed
6. All datasets are combined into the play-by-play dataset here
7. The initial combined play-by-play data are then processed
8. xG values are generated, then appended to the play-by-play dataframe
9. The method eventually returns the fully processed play-by-play data as a list

Because all scraping and processing functions are separate, it should be straightforward to leverage either
aiohttp, async, or multiprocessing with minimal changes to the underlying library. However, this chicken has no
experience with any of those tools and is happy to take feedback if the level of effort required is greater
than anticipated :fontawesome-solid-face-smile:

## :material-numeric-3-circle: **Refactoring for speed / reliability**

- [ ] Generally clean up chicken's gross (self-taught) code
- [ ] Reduce the number of loops across all functions
    - [ ] Play-by-play functions are especially egregious here - the method loops through every player
      in the roster once and every event multiple times
