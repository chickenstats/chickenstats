---
icon: material/tune-vertical-variant
description: "Plot single-game lollipop charts to analyze chances created and allowed"
---


# **Lollipop charts tutorial**

---

## **Intro**

Use the `chickenstats` library to scrape play-by-play data and plot shot events as a lollipop chart,
with the length of the stem indicating the predicted goal value. 

Parts of this tutorial are optional and will be clearly marked as such. For help, or any questions,
please don't hesitate to reach out to [chicken@chickenandstats.com](mailto:chicken@chickenandstats.com) or
[@chickenandstats.com](https://bsky.app/profile/chickenandstats.com) on Blue Sky.


---

![png](https://raw.githubusercontent.com/chickenandstats/chickenstats/refs/heads/main/docs/guide/examples/images/nsh_lollipop.png)

## **Housekeeping**

### Import dependencies

Import the dependencies we'll need for the guide


```python
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import chickenstats.utilities  # This imports the chickenstats matplotlib style below
from chickenstats.chicken_nhl import Scraper, Season
from chickenstats.chicken_nhl.info import NHL_COLORS
```

### Pandas options

Sets different pandas options. This cell is optional


```python
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", 100)
```

### Chickenstats matplotlib style

chickenstats.utilities includes a custom style package - this activates it. This cell is also optional


```python
plt.style.use("chickenstats")
```

---

## **Scrape data**

### Schedule, standings, and team names

Scrape the schedule and standings using the `Season` object. Then, create some name dictionaries for convenience later


```python
season = Season(2024)
```


```python
schedule = season.schedule(disable_progress_bar=True)  # Progress bar renders poorly in ipynb to md conversions
```


```python
standings = season.standings  # Standings as a dataframe for the team name dictionaries
```


```python
team_names = standings.sort_values(by="team_name").team_name.str.upper().tolist()
team_codes = standings.sort_values(by="team_name").team.str.upper().tolist()
team_names_dict = dict(zip(team_codes, team_names, strict=False))  # These are helpful for later
```

### Game IDs

Select the team and games to plot. The default is the most recent game for the Nashville Predators :).
Feel free to change for your chosen team code 


```python
team = "NSH"

conds = np.logical_and(
    schedule.game_state == "OFF", np.logical_or(schedule.home_team == team, schedule.away_team == team)
)

game_ids = schedule.loc[conds].game_id.unique().tolist()
game_id = game_ids[-1]
```

### Play-by-play

Scrape the play-by-play data for the chosen game ID. First instantiate the `Scraper` object,
then call the play_by_play attribute


```python
scraper = Scraper(game_id, disable_progress_bar=True)
```


```python
pbp = scraper.play_by_play
```

---

## **Plotting the lollipop chart**

### Helper functions

This helper function formats numbers for the x-axis


```python
def numfmt(x: int, pos) -> str:
    """Function to convert the game-time values as minutes, then format them for the x-axis.

    Used within the matplotlib FuncFormatter.

    Parameters:
        x (int):
            The game time, in seconds, to convert.
        pos:
            Required by the FuncFormatter

    """
    s = str(int(x / 60))
    return s
```

### Plotting function

This function plots the actual lollipop chart. You can select the strength states, while the team parameter
determines which team is in the upper portion of the chart. 

Strength state options include:
* 5v5
* even strength
* special teams (i.e., powerplay and shorthanded)
* empty net
* all strength states


```python
def plot_lollipop(data: pd.DataFrame, ax: plt.axes, team: str | None = None, strengths: str | None = None) -> plt.axes:
    """Function to plot the lollipop chart, with the given in the upper portion.

    Parameters:
        data (pd.DataFrame):
            Play-by-play data for a single game scraped using the chickenstats package.
        ax (plt.axes):
            The axes on which to plot the lollipop chart.
        team (str):
            Three-letter team code to determine which team is in the upper portion of the chart.
            Default is the home team
        strengths (str):
            The strength states to include in the chart. Default is 5v5

    """
    strengths_dict = {
        "5v5": {"name": "5v5", "list": ["5v5"]},
        "even": {"name": "even_strength", "list": ["5v5", "4v4", "3v3"]},
        "special": {"name": "special_teams", "list": ["5v4", "5v3", "4v5", "3v5"]},
        "empty": {"name": "empty_net", "list": ["Ev5", "Ev4", "Ev3", "5vE", "4vE", "3vE"]},
        "all": {"name": "all", "list": ["5v5", "4v4", "3v3", "5v4", "5v3", "4v5", "3v5"]},
    }

    if not strengths:
        strengths = "5v5"

    strengths = strengths_dict[strengths]

    strengths_list = strengths["list"]

    conds = data.strength_state.isin(strengths_list)

    df = data.loc[conds].reset_index(drop=True)

    if not team:
        team = df.home_team.iloc[0]

    ax.set_ylim(-1.05, 1.05)
    # ax.axhline(y = 0, lw=1, alpha=.8)
    ax.axhline(y=0.5, lw=1, zorder=-1, alpha=0.25)
    ax.axhline(y=1, lw=1, zorder=-1, alpha=0.25)
    ax.axhline(y=-0.5, lw=1, zorder=-1, alpha=0.25)
    ax.axhline(y=-1, lw=1, zorder=-1, alpha=0.25)
    ax.set_yticks([1, 0.5, 0, -0.5, -1], labels=[1, 0.5, 0, 0.5, 1])

    max_game_seconds = data.game_seconds.max()

    ax.set_xlim(-5, max_game_seconds + 35)
    ax.spines.bottom.set_position("zero")

    ax.xaxis.set_major_locator(ticker.MultipleLocator(1200))

    xfmt = ticker.FuncFormatter(numfmt)
    ax.xaxis.set_major_formatter(xfmt)
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(60))

    ax.set_ylabel("EXPECTED GOAL VALUE", fontsize=8)

    events = ["GOAL", "SHOT", "MISS"]

    conds = np.logical_and(df.event_team == team, df.event.isin(events))

    plot_data = df.loc[conds]

    team_post = 0

    for _idx, play in plot_data.iterrows():
        colors = NHL_COLORS[play.event_team]

        marker = "o"

        facecolor = colors[play.event]
        edgecolor = colors[play.event]

        if play.event == "GOAL":
            z_order = 3
            alpha = 1
            hatch = ""
            edgecolor = colors["SHOT"]

        else:
            hatch = ""
            alpha = 0.65
            z_order = 2

        if play.event == "MISS":
            if "POST" in play.description:
                team_post += 1
                hatch = "////////"

            edgecolor = colors["SHOT"]

        ax.scatter(
            [play.game_seconds],
            [play.pred_goal],
            marker=marker,
            s=60,
            color=facecolor,
            lw=1.15,
            ec=edgecolor,
            zorder=z_order,
            hatch=hatch,
            alpha=alpha,
        )
        if play.event == "MISS":
            edgecolor = colors["MISS"]

        ax.plot(
            [play.game_seconds, play.game_seconds], [0, play.pred_goal], lw=1.85, color=edgecolor, zorder=0, alpha=0.65
        )

    conds = np.logical_and(df.event_team != team, df.event.isin(events))

    plot_data = df.loc[conds]

    not_team_post = 0

    for _idx, play in plot_data.iterrows():
        colors = NHL_COLORS[play.event_team]

        marker = "o"

        facecolor = colors[play.event]
        edgecolor = colors[play.event]

        if play.event == "GOAL":
            z_order = 3
            alpha = 1
            edgecolor = colors["SHOT"]

        else:
            alpha = 0.65
            z_order = 2

        if play.event == "MISS":
            if "POST" in play.description:
                hatch = "////////"

                not_team_post += 1

            edgecolor = colors["SHOT"]

        ax.scatter(
            [play.game_seconds],
            [play.pred_goal * -1],
            marker=marker,
            s=60,
            color=facecolor,
            lw=1.15,
            ec=edgecolor,
            zorder=z_order,
            alpha=alpha,
        )

        if play.event == "MISS":
            edgecolor = colors["MISS"]
        ax.plot(
            [play.game_seconds, play.game_seconds],
            [0, play.pred_goal * -1],
            lw=1.85,
            color=edgecolor,
            zorder=0,
            alpha=0.65,
        )

    not_team = df.loc[np.logical_and(df.event_team != team, pd.notnull(df.event_team))].event_team.iloc[0]

    # legends

    legend_handles = []

    for event in ["GOAL", "SHOT", "MISS"]:
        colors = NHL_COLORS[team]

        linecolor = colors["SHOT"]
        facecolor = colors[event]

        legend_handle = Line2D(
            [],
            [],
            color=linecolor,
            markeredgecolor=linecolor,
            markerfacecolor=facecolor,
            marker=marker,
            markersize=5,
            label=event,
            alpha=0.65,
        )

        legend_handles.append(legend_handle)

    legend1 = ax.legend(
        handles=legend_handles,
        loc=(0.01, 0.8575),
        ncols=len(legend_handles),
        fontsize="small",
        title=team_names_dict[team],
        title_fontsize="small",
    )
    ax.add_artist(legend1)

    legend_handles = []

    for event in ["GOAL", "SHOT", "MISS"]:
        colors = NHL_COLORS[not_team]

        linecolor = colors["SHOT"]
        facecolor = colors[event]

        legend_handle = Line2D(
            [],
            [],
            color=linecolor,
            markeredgecolor=linecolor,
            markerfacecolor=facecolor,
            marker=marker,
            markersize=5,
            label=event,
            alpha=0.65,
        )

        legend_handles.append(legend_handle)

    legend2 = ax.legend(
        handles=legend_handles,
        loc=(0.01, 0.0575),
        ncols=len(legend_handles),
        fontsize="small",
        title=team_names_dict[not_team],
        title_fontsize="small",
    )
    ax.add_artist(legend2)

    team_g = df.loc[df.event_team == team].goal.sum()
    team_xg = df.loc[df.event_team == team].pred_goal.sum()

    not_team_g = df.loc[df.event_team != team].goal.sum()
    not_team_xg = df.loc[df.event_team != team].pred_goal.sum()

    ax_title = f"{team_names_dict[team]} vs. {team_names_dict[not_team]}"
    ax.set_title(ax_title, ha="left", x=-0.055, y=1.06)

    strengths_name = strengths["name"].replace("_", " ").upper()
    score_subtitle = f"{team_g}G ({round(team_xg, 2)} xG) - {not_team_g}G ({round(not_team_xg, 2)} xG)"
    game_date = df.game_date.iloc[0]

    ax_subtitle = f"{score_subtitle} | {strengths_name} |  {game_date}"
    ax.text(s=ax_subtitle, ha="left", x=-0.055, y=1.035, transform=ax.transAxes)

    attribution = "Viz @chickenandstats.com | xG model @chickenandstats.com"
    ax.text(s=attribution, ha="right", x=0.99, y=-0.05, transform=ax.transAxes, fontsize=8, fontstyle="italic")

    return ax
```

### Plot the lollipop chart

Plot the lollipop for your chosen team and strength state below.
To save the figure, ensure you have a charts folder in your working directory


```python
fig, ax = plt.subplots(dpi=650, figsize=(8, 5))

fig.tight_layout()

ax = plot_lollipop(data=pbp, team=team, strengths="even", ax=ax)

fig.savefig(f"./charts/{game_id}.png", bbox_inches="tight", transparent=False)
```


    
![png](lollipop_files/lollipop_33_0.png)
    

