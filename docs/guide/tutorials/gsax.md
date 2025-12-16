---
icon: material/trending-up
description: "Learn how to analyze goals saved above expected with chickenstats"
---

# **Tutorial for goals saved above expected**

---

## **Intro**

Use the `chickenstats` library to scrape play-by-play data and analyze goalies' goals saved above expected.

Parts of this tutorial are optional and will be clearly marked as such. For help, or any questions,
please don't hesitate to reach out to [chicken@chickenandstats.com](mailto:chicken@chickenandstats.com) or
[@chickenandstats.com](https://bsky.app/profile/chickenandstats.com) on Blue Sky.

---

![png](https://raw.githubusercontent.com/chickenandstats/chickenstats/refs/heads/main/docs/guide/examples/images/saros_gsax_hours_since.png)

---

## **Housekeeping**

### Import dependencies

Import the dependencies we'll need for the guide

```python
import datetime as dt

import matplotlib.patheffects as mpe
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D

import chickenstats.utilities
from chickenstats.chicken_nhl import Scraper, Season
from chickenstats.chicken_nhl.info import NHL_COLORS
from chickenstats.chicken_nhl._helpers import charts_directory
```

### Pandas options

Set different pandas options. This cell is optional


```python
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", 100)
```

### Folder structure


```python
charts_directory()
```

### Chickenstats matplotlib style

chickenstats.utilities includes a custom style package - this activates it. This cell is also optional


```python
plt.style.use("chickenstats")
```

---

## **Scrape data**

### Schedule

Scrape the schedule using the `Season` object


```python
season = Season(2024)
```


```python
schedule = season.schedule(disable_progress_bar=True)
```

### Standings and team names

Scrape the standings and create team name dictionaries to use later


```python
standings = season.standings.copy(deep=True)
```


```python
team_names = standings.sort_values(by="team_name").team_name.str.upper().tolist()
team_codes = standings.sort_values(by="team_name").team.str.upper().tolist()
team_names_dict = dict(zip(team_codes, team_names, strict=False))
```

### Game IDs

Create a list of game IDs to scrape


```python
conds = schedule.game_state == "OFF"

game_ids = schedule.loc[conds].game_id.unique().tolist()
latest_date = schedule.loc[conds].game_date.max()
```

### Play-by-play

Scrape play-by-play data using the `Scraper` object


```python
scraper = Scraper(game_ids, disable_progress_bar=True)
```


```python
pbp = scraper.play_by_play
```

    Python(17693,0x206194800) malloc: Failed to allocate segment from range group - out of space


### Stats

Aggregate statistics to season and game level


```python
scraper.prep_stats(level="season", disable_progress_bar=True)
season_stats = scraper.stats.copy(deep=True)
```


```python
scraper.prep_stats(level="game", disable_progress_bar=True)
game_stats = scraper.stats.copy(deep=True)
```

### Goalie dataframes

Filter the dataframes for goalies and add goals saved above expected stats


```python
def prep_goalie_df(data: pd.DataFrame, strengths: bool) -> pd.DataFrame:
    """Prep goalie dataframes for later analysis.

    Parameters:
        data (pd.DataFrame):
            Pandas dataframe of individual statistics scraped using `chickenstats` library
        strengths (bool):
            If False, aggregates data to all strengths states. If True, data are aggregated
            to strength state level

    """
    df = data.copy(deep=True)

    df = df.loc[df.position == "G"].reset_index(drop=True)

    if not strengths:
        group_cols = [
            "season",
            "session",
            "game_id",
            "game_date",
            "player",
            "eh_id",
            "api_id",
            "position",
            "team",
            "opp_team",
        ]

        group_cols = [x for x in group_cols if x in df.columns]

        agg_stats = {
            x: "sum"
            for x in df.columns
            if x not in group_cols and x != "strength_state" and "percent" not in x and "p60" not in x
        }

        df = df.groupby(group_cols, as_index=False).agg(agg_stats)

    df["gsax"] = df.xga - df.ga
    df["gsax_p60"] = df.gsax / df.toi * 60

    return df
```


```python
goalies_game = prep_goalie_df(data=game_stats, strengths=True)
```


```python
goalies_game_all_sit = prep_goalie_df(data=game_stats, strengths=False)
```


```python
goalies_season = prep_goalie_df(data=season_stats, strengths=True)
```


```python
goalies_season_all_sit = prep_goalie_df(data=season_stats, strengths=False)
```

## **GSaX line charts**

### Prepping data

Calculating cumlative stats


```python
def calc_cumulative_stats(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate cumulative TOI and xG against.

    Parameters:
        data (pd.DataFrame):
            Pandas dataframe of statistics aggregated from the `chickenstats` library and
            prepped for goalie analysis
    """
    df = data.copy(deep=True).sort_values(by="game_date")

    group_list = ["season", "session", "player", "eh_id", "api_id", "team"]

    df["cum_gp"] = df.groupby(group_list)["game_id"].transform("cumcount") + 1

    df["cum_toi"] = df.groupby(group_list)["toi"].transform("cumsum")

    df["cum_gsax"] = df.groupby(group_list)["gsax"].transform("cumsum")

    return df
```


```python
goalies_game_all_sit = calc_cumulative_stats(data=goalies_game_all_sit)
```

### Plot line chart function

Function to plot cumulative GSaX and TOI for a given goalie


```python
def plot_line_chart(
    data: pd.DataFrame,
    goalie: pd.Series,
    ax: plt.axes,
    session: str | None = None,
    ax_title: str | None = None,
    legend_label: str | None = None,
    x_label: bool = False,
    y_label: bool = False,
):
    """Function to plot a seaborn line chart of cumulative time-on-ice and goals scored above expected.

    Parameters:
        data (pd.DataFrame):
            Pandas dataframe of game-level goalie data to plot
        goalie (pd.Series):
            Row of data from season-level goalie data
        ax (plt.axes):
            The matplotlib axes to return after plotting the chart
        session (list):
            Select regular season ("R") or playoffs ("P"), if None, defaults to regular season or "R"
        ax_title (str | None):
            Customize ax title, or, if None, use the goalie's name
        legend_label (str | None):
            Customize the legend label, or, if None, list the cumulative GSaX and TOI
        x_label (bool):
            Whether to print or hide the x-axis label
        y_label (bool):
            Whether to print or hide the y-axis label

    """
    if not session:
        session = "R"

    condition = data.session == session
    plot_df = data.loc[condition].copy()

    color_palette = np.where(
        plot_df.api_id == goalie.api_id, NHL_COLORS[goalie.team]["SHOT"], NHL_COLORS[goalie.team]["MISS"]
    )

    color_palette = dict(zip(plot_df.player, color_palette, strict=False))

    NHL_COLORS[goalie.team]["MISS"]
    line_width = 3

    conds = plot_df.player != goalie.player

    sns.lineplot(
        x="cum_toi", y="cum_gsax", data=plot_df[conds], hue="player", palette=color_palette, ax=ax, lw=line_width
    )

    conds = plot_df.player == goalie.player
    NHL_COLORS[goalie.team]["SHOT"]
    line_width = 6
    path_effect_ec = NHL_COLORS[goalie.team]["GOAL"]

    path_effect = [mpe.Stroke(foreground=path_effect_ec, alpha=1, linewidth=7), mpe.Normal()]

    sns.lineplot(
        x="cum_toi",
        y="cum_gsax",
        data=plot_df[conds],
        hue="player",
        palette=color_palette,
        ax=ax,
        zorder=3,
        lw=3.5,
        path_effects=path_effect,
    )

    if ax_title == "":
        ax_title = ""

    elif not ax_title:
        ax_title = goalie.player

    ax.set_title(ax_title, size=18, weight="heavy", pad=15)

    if y_label:
        ax.set_ylabel("Cumulative GSaX", size=16, labelpad=15, weight="heavy")

    else:
        ax.set_ylabel("")
        ax.yaxis.set_tick_params(which="both", labelbottom=True)

    if x_label:
        ax.set_xlabel("Cumulative time-on-ice (minutes)", size=16, labelpad=15, weight="heavy")

    else:
        ax.set_xlabel("")
        ax.xaxis.set_tick_params(which="both", labelbottom=True)

    legend_elements = list()
    color = NHL_COLORS[goalie.team]["SHOT"]

    xG = round(goalie.gsax, 2)

    toi_max = round(goalie.toi, 2)

    if not legend_label:
        legend_label = f"{xG} GSaX in {toi_max} minutes"

    element = Line2D([0], [0], lw=3, label=legend_label, color=color, path_effects=path_effect)

    legend_elements.append(element)

    ax.legend(
        handles=legend_elements,
        loc="upper left",
        ncol=1,
        fontsize=14,
        title_fontsize=12,
        facecolor="white",
        framealpha=1,
        edgecolor="gray",
    ).set_zorder(-1)

    ax.xaxis.set_tick_params(labelsize=16)
    ax.yaxis.set_tick_params(labelsize=16)

    return ax
```

### Juuse Saros

Plot single goalie's goals saved above expected and time-on-ice


```python
selected_goalie = "JUUSE.SAROS"
conds = goalies_season_all_sit.eh_id == selected_goalie

fig_size = (8, 5)

fig, ax = plt.subplots(figsize=fig_size, dpi=650)

for idx, goalie in goalies_season_all_sit.loc[conds].iterrows():
    plot_df = goalies_game_all_sit.copy()

    plot_line_chart(data=plot_df, goalie=goalie, ax=ax, ax_title="", x_label=True, y_label=True)


title = "Saros is having an NHL-average year"
fig.suptitle(title, ha="center", va="center", y=1.027, size=16, weight="heavy")

subtitle = f"Cumulative GSaX & TOI, all situations | 2024-25 season, as of {latest_date}"
fig.text(s=subtitle, ha="center", va="center", x=0.5, y=0.98, size=12)


# Attribution
attribution = "Data & xG model @chickenandstats.com | Viz @chickenandstats.com"
fig.text(s=attribution, x=0.95, y=-0.095, fontsize=8, horizontalalignment="right", style="italic")

fig.savefig("./charts/saros_gsax.png", dpi=650, bbox_inches="tight", facecolor="white")
```


    
![png](gsax_files/gsax_45_0.png)
    


### Top-6 goalies

Create the top goalies dataframe to iterate through for plotting


```python
top_goalies = goalies_season_all_sit.sort_values(by="gsax", ascending=False).head(6).reset_index(drop=True)
```

### Plot cumulative GSaX and TOI

Cumulative time-on-ice and goals saved above expected for top-6 goalies in NHL


```python
## setting figure size

fig_size = (15, 15)

fig, axes = plt.subplots(3, 2, figsize=fig_size, dpi=650, sharex=True, sharey=True)

fig.tight_layout(pad=5)

axes = axes.reshape(-1)

for idx, top_goalie in top_goalies.iterrows():
    ax = axes[idx]

    x_label = idx >= 4

    y_label = idx in [0, 2, 4]

    plot_df = goalies_game_all_sit.copy()

    plot_line_chart(data=plot_df, goalie=top_goalie, ax=ax, x_label=x_label, y_label=y_label)


title = "Top-6 goaltenders by cumulative goals saved above expected"
fig.suptitle(title, ha="center", va="center", y=1.027, size=24, weight="heavy")

subtitle = f"Cumulative GSaX & cumulative TOI, all situations | 2024-25 season, as of {latest_date}"
fig.text(s=subtitle, ha="center", va="center", x=0.5, y=1.001, size=18)


# Attribution
attribution = "Data & xG model @chickenandstats.com | Viz @chickenandstats.com"
fig.text(s=attribution, x=0.99, y=-0.0125, fontsize=12, horizontalalignment="right", style="italic")

fig.savefig("./charts/top_6_gsax.png", dpi=650, bbox_inches="tight", facecolor="white")
```


    
![png](gsax_files/gsax_49_0.png)
    


## **GSaX and time between games**

### Prepping data

Getting game winners and calculating time between games with the schedule object


```python
def prep_hours_since(data: pd.DataFrame, schedule: pd.DataFrame, strengths: list = None) -> pd.DataFrame:
    """Function to prep dataframe of gsax and hours since for an individual goalie.

    Parameters:
        data (pd.DataFrame):
            Pandas dataframe of goalie stats from `chickenstats` library
        strengths (list):
            List of strength states to filter the dataframe

    """
    if strengths is None:
        strengths = ["5v5"]
    df = data.copy()

    winners = np.where(schedule.home_score > schedule.away_score, schedule.home_team, schedule.away_team)
    winners_map = dict(zip(schedule.game_id.astype(str), winners, strict=False))

    game_date_dt = pd.to_datetime(schedule.game_date_dt, utc=True)
    game_date_map = dict(zip(schedule.game_id.astype(str), game_date_dt, strict=False))

    df["game_date_dt"] = df.game_id.map(game_date_map)
    df["win"] = df.game_id.map(winners_map)
    df.win = np.where(df.team == df.win, 1, 0)

    conds = df.strength_state.isin(strengths)

    df = df.loc[conds].reset_index(drop=True)

    group_list = ["season", "session", "team", "player", "eh_id"]

    df["hours_since"] = df.groupby(group_list).game_date_dt.transform(lambda x: x - x.shift(1)).astype(
        "timedelta64[s]"
    ) / pd.Timedelta(hours=1)

    conds = np.logical_and.reduce([df.hours_since > 0, df.hours_since <= 175, df.toi >= 10])

    df = df.loc[conds].reset_index(drop=True)

    return df
```

### Plotting function

Plot individual goalie GSaX / 60 and time since last game


```python
def plot_hours_since(
    data: pd.DataFrame,
    goalie: pd.Series,
    ax: plt.axes,
    ax_title: str | None = None,
    legend_label: str | None = None,
    x_label: bool = False,
    y_label: bool = False,
):
    """Function to plot a seaborn line chart of cumulative time-on-ice and goals scored above expected.

    Parameters:
        data (pd.DataFrame):
            Pandas dataframe of game-level goalie data to plot
        goalie (pd.Series):
            Row of data from season-level goalie data
        ax (plt.axes):
            The matplotlib axes to return after plotting the chart
        ax_title (str | None):
            Customize ax title, or, if None, use the goalie's name
        x_label (bool):
            Whether to print or hide the x-axis label
        y_label (bool):
            Whether to print or hide the y-axis label

    """
    sns.despine(right=False, top=False, ax=ax)

    df = data.copy()

    min_size = df.fa_p60.min()
    max_size = df.fa_p60.max()
    df.fa_p60.mean()
    size_norm = (min_size, max_size)
    sizes = (10, 500)

    alpha = 0.65
    line_width = 1.3

    colors = NHL_COLORS[goalie.team]

    conds = df.eh_id != goalie.eh_id

    sns.scatterplot(
        x="hours_since",
        y="gsax_p60",
        data=df[conds],
        color=colors["MISS"],
        size="fa_p60",
        size_norm=size_norm,
        sizes=sizes,
        alpha=alpha,
        edgecolor="white",
        linewidth=line_width,
        legend="full",
        ax=ax,
    )

    color_palette = {0: colors["SHOT"], 1: colors["GOAL"]}

    for result, color in color_palette.items():
        conds = df.eh_id == goalie.eh_id

        edge_color = "white" if result == 0 else colors["SHOT"]

        sns.scatterplot(
            x="hours_since",
            y="gsax_p60",
            data=df[conds],
            hue="win",
            palette=color_palette,
            size="fa_p60",
            size_norm=size_norm,
            sizes=sizes,
            alpha=alpha,
            edgecolor=edge_color,
            linewidth=line_width,
            legend=False,
            ax=ax,
        )

    legend_elements = []

    legend_element_labels = ["Win", "Loss", "Other goalies"]

    for label in legend_element_labels:
        if label == "Win":
            color = colors["GOAL"]
            edge_color = colors["SHOT"]

        if label == "Loss":
            color = colors["SHOT"]
            edge_color = "white"

        if label == "Other goalies":
            color = colors["MISS"]
            edge_color = "white"

        element = Line2D(
            [0], [0], lw=0, label=label, markersize=14, marker="o", color=color, mec=edge_color, alpha=alpha
        )

        legend_elements.append(element)

    legend = ax.legend(
        handles=legend_elements,
        loc="upper left",
        ncol=1,
        fontsize=12,
        title_fontsize=16,
        facecolor="white",
        framealpha=1,
        edgecolor="gray",
    )

    ax.add_artist(legend).set_zorder(-1)

    if not ax_title and ax_title != "":
        ax_title = goalie.player

    if ax_title:
        ax.set_title(ax_title, size=18, weight="heavy", pad=15)

    if x_label:
        ax.set_xlabel("Hours since last game", size=18, labelpad=15, weight="heavy")

    else:
        ax.set_xlabel("", size=18, weight="heavy")
        ax.xaxis.set_tick_params(which="both", labelbottom=True)

    if y_label:
        ax.set_ylabel("GSaX / 60", size=18, labelpad=15, weight="heavy")

    else:
        ax.set_ylabel("")
        ax.yaxis.set_tick_params(which="both", labelleft=True)

    ax.xaxis.set_tick_params(labelsize=14)
    ax.yaxis.set_tick_params(labelsize=14)

    ax.yaxis.set_major_locator(ticker.MultipleLocator(2))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))

    return ax
```

### Data

Prepping the data for plotting the next two charts


```python
hours_since_data = prep_hours_since(data=goalies_game, schedule=schedule)
```

### Plotting Juuse Saros

You can also change to plot to whichever goalie you prefer


```python
goalie = "JUUSE.SAROS"
strengths = ["5v5"]

fig_size = (8, 8)

fig, ax = plt.subplots(figsize=fig_size, dpi=650)
fig.tight_layout()
sns.despine(right=False, top=False)

goalie_df = goalies_season.loc[
    np.logical_and(goalies_season.strength_state.isin(strengths), goalies_season.eh_id == goalie)
]

for idx, goalie in goalie_df.iterrows():
    ax = plot_hours_since(data=hours_since_data, goalie=goalie, ax=ax, ax_title="", x_label=True, y_label=True)

title = "Saros's worst games after long breaks"

fig.suptitle(title, ha="center", va="center", y=1.045, size=16, weight="heavy")

subtitle = f"GSaX / 60 & hours since last game (bubbles sized for FA / 60) | 2024-25 season, as of {latest_date}"
fig.text(s=subtitle, ha="center", va="center", x=0.5, y=1.015, size=12)

attribution = "Data & xG model @chickenandstats | Viz @chickenandstats"
fig.text(s=attribution, ha="right", va="center", y=-0.1, x=0.95, size=10, style="italic")

fig.savefig("./charts/saros_gsax_hours_since.png", dpi=650, bbox_inches="tight", facecolor="white")
```


    
![png](gsax_files/gsax_58_0.png)
    


### Elite goalies

Plotting performance and hours since last game for top-6 goalies


```python
## setting figure size

fig_size = (15, 15)

fig, axes = plt.subplots(3, 2, figsize=fig_size, dpi=650)

fig.tight_layout(pad=5)

axes = axes.reshape(-1)

for idx, top_goalie in top_goalies.iterrows():
    ax = axes[idx]

    x_label = idx >= 4

    y_label = idx in [0, 2, 4]

    ax = plot_hours_since(data=hours_since_data, goalie=top_goalie, ax=ax, x_label=x_label, y_label=y_label)


title = "Top-6 goaltenders by cumulative goals saved above expected"
fig.suptitle(title, ha="center", va="center", y=1.027, size=24, weight="heavy")

subtitle = f"GSaX / 60 and hours since last game (bubbles sized for FA / 60), 5v5 | 2024-25 season, as of {latest_date}"
fig.text(s=subtitle, ha="center", va="center", x=0.5, y=1.001, size=18)


# Attribution
attribution = "Data & xG model @chickenandstats.com | Viz @chickenandstats.com"
fig.text(s=attribution, x=0.99, y=-0.0125, fontsize=12, horizontalalignment="right", style="italic")

fig.savefig("./charts/top_6_gsax_hours_since.png", dpi=650, bbox_inches="tight", facecolor="white")
```


    
![png](gsax_files/gsax_60_0.png)
    

