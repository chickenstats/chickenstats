---
icon: fontawesome/solid-flag-usa
description: "Dive into the 4 Nations Face-OFF"
---

# **Tutorial for 4 Nations Face-Off**

---

## **Intro**

Use the `chickenstats` library to scrape play-by-play data and international team performance in the 4 Nations Face-Off.

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
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

import chickenstats.utilities
from chickenstats.utilities import ChickenSession
from chickenstats.chicken_nhl import Scraper, Season
from chickenstats.chicken_nhl.info import NHL_COLORS, INTERNATIONAL_COLORS

from pathlib import Path
import requests

from PIL import Image
from io import BytesIO, StringIO

from bokeh.plotting import figure, output_file, output_notebook, show, save
from bokeh.models import (
    HoverTool,
    ColumnDataSource,
    Title,
    Div,
    NumeralTickFormatter,
    Label,
    Line,
    Span,
    CDSView,
    BooleanFilter,
)
from bokeh.embed import server_document
from bokeh.layouts import gridplot, column
from bokeh.models import Range1d
```

### Pandas options

Set different pandas options. This cell is optional


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

### Schedule

Scrape the schedule using the `Season` object


```python
season = Season(2024)
```


```python
schedule = season.schedule(disable_progress_bar=True, sessions="FO")
```

### Game IDs

Create a list of game IDs to scrape


```python
conds = schedule.game_state.isin(["OFF", "FINAL"])

game_ids = schedule.loc[conds].game_id.unique().tolist()
```

### Play-by-play

Scrape play-by-play data using the `Scraper` object


```python
scraper = Scraper(game_ids)
```


```python
pbp = scraper.play_by_play
```


    Output()



<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"></pre>



### Stats

Aggregate statistics to season and game level


```python
scraper.prep_stats(level="season")
season_stats = scraper.stats.copy(deep=True)
```


    Output()



<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"></pre>




```python
scraper.prep_stats(level="game")
game_stats = scraper.stats.copy(deep=True)
```


    Output()



<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"></pre>




```python
scraper.prep_lines(level="season")
lines = scraper.lines
```


    Output()



<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"></pre>




```python
scraper.prep_team_stats(level="season")
team_stats = scraper.team_stats
```


    Output()



<pre style="white-space:pre;overflow-x:auto;line-height:normal;font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace"></pre>



## Matplotlib


```python
strength_state = "5v5"
toi_min = 5

# Setting filter conditions and filtering data
conds = np.logical_and(lines.strength_state == strength_state, lines.toi >= toi_min)
plot_lines = lines.loc[conds].sort_values(by="xgf_percent", ascending=False).reset_index(drop=True)

# Setting overall figures
fig, axes = plt.subplots(nrows=2, ncols=2, dpi=650, figsize=(8, 6))

fig.tight_layout(pad=2.5)

axes = axes.reshape(-1)

# Getting the averages and drawing the average lines
xga_mean = plot_lines.xga_p60.mean()
xgf_mean = plot_lines.xgf_p60.mean()

# Setting the size norm so bubbles are consistent across figures
size_norm = (plot_lines.toi.min(), plot_lines.toi.max())

# Getting the teams and standings data to iterate through
teams = ["CAN", "FIN", "SWE", "USA"]
team_names = ["CANADA", "FINLAND", "SWEDEN", "UNITED STATES"]
team_names = dict(zip(teams, team_names, strict=False))

# Iterating through the standings data
for _idx, team in enumerate(teams):
    # Setting the team    # Setting the axis
    ax = axes[_idx]

    team_name = team_names[team]
    team_stats_plot = team_stats.loc[
        np.logical_and(team_stats.strength_state == strength_state, team_stats.team == team)
    ]

    # Average lines
    ax.axvline(x=xga_mean, zorder=-1, alpha=0.5)
    ax.axhline(y=xgf_mean, zorder=-1, alpha=0.5)

    # Getting plot colors based on team
    colors = INTERNATIONAL_COLORS[team]

    # Filtering data and plotting the non-selected teams first
    conds = plot_lines.team != team
    plot_data = plot_lines.loc[conds]

    # They all get gray colors
    facecolor = colors["MISS"]
    edgecolor = "white"  # colors["MISS"]

    # Plotting the non-selected teams' data
    sns.scatterplot(
        data=plot_data,
        x="xga_p60",
        y="xgf_p60",
        size="toi",
        sizes=(20, 150),
        size_norm=size_norm,
        lw=1.5,
        facecolor=facecolor,
        edgecolor=edgecolor,
        alpha=0.5,
        legend=False,
        ax=ax,
    )

    # Filtering and plotting the selected team's data
    conds = plot_lines.team == team
    plot_data = plot_lines.loc[conds]

    # Setting the colors
    facecolor = colors["GOAL"]
    edgecolor = colors["SHOT"]

    # Plotting the selected team's data
    sns.scatterplot(
        data=plot_data,
        x="xga_p60",
        y="xgf_p60",
        size="toi",
        sizes=(20, 150),
        size_norm=size_norm,
        lw=1.5,
        facecolor=facecolor,
        edgecolor=edgecolor,
        alpha=0.8,
        legend=False,
        ax=ax,
    )

    # Setting x and y axes labels
    x_labels = [2, 3]

    if _idx in x_labels:
        ax.axes.set_xlabel("xGA per 60 minutes", fontsize=7)
    else:
        ax.axes.set_xlabel("")

    y_labels = [0, 2]

    if _idx in y_labels:
        ax.axes.set_ylabel("xGF per 60 minutes", fontsize=7)
    else:
        ax.axes.set_ylabel("")

    # Setting tick params font size
    ax.tick_params(axis="both", which="major", labelsize=7)

    gf = team_stats_plot.gf.iloc[0]
    xgf = round(team_stats_plot.xgf.iloc[0], 2)
    ga = team_stats_plot.ga.iloc[0]
    xga = round(team_stats_plot.xga.iloc[0], 2)
    toi = round(team_stats_plot.toi.iloc[0], 2)

    # Setting the ax title
    ax_title = f"{team_name} | {gf} GF ({xgf} xGF) - {ga} GA ({xga} xGA) | {toi} TOI"
    ax.set_title(ax_title, fontsize=7, x=-0.085, y=1.03, horizontalalignment="left")

    condition = schedule.home_team == team

    logo_url = f"https://raw.githubusercontent.com/chickenandstats/chickenstats/refs/heads/main/logos/international/{team.lower()}.png"

    with ChickenSession() as session:
        logo = BytesIO(session.get(logo_url).content)

        logo = Image.open(logo)

        imagebox = OffsetImage(logo, zoom=0.15, alpha=0.15, zorder=-10)
        imagebox.image.axes = ax

        ab = AnnotationBbox(imagebox, (0.5, 0.5), xycoords="axes fraction", bboxprops={"lw": 0}, alpha=0, zorder=-10)

        ax.add_artist(ab)

        # for idx, line in plot_data.iterrows():

        #     _x = line.xga_p60
        #     _y = line.xgf_p60

        #     if _y >= 5:
        #         texty = _y - 0.25

        #     elif _y >= 2.5:
        #         texty = _y + 0.25

        #     elif _y >= 1.5:
        #         texty = _y - 0.25

        #     else:
        #         texty = _y + 0.25

        #     if _x >= 6:
        #         textx = _x - 2

        #     elif _x >= 5:
        #         textx = _x - 0.25

        #     else:
        #         textx = _x + 0.25

        #     bbox_dict = {"facecolor": "white", "alpha": 0.25, "edgecolor": "none", "pad": 1}

        #     ax.annotate(line.forwards, xy=(_x, _y), xytext=(textx, texty), fontsize=4, bbox=bbox_dict)

# Figure suptitle and subtitle
fig_suptitle = "Forward line combinations' chances created vs. chances allowed"
fig.suptitle(fig_suptitle, x=0.01, y=1.085, fontsize=11, fontweight="bold", horizontalalignment="left")

todays_date = dt.datetime.now().strftime("%Y-%m-%d")
subtitle = f"4 Nations Face-Off | >{toi_min} min. TOI at 5v5 (size indicates TOI) | {todays_date}"
fig.text(s=subtitle, x=0.01, y=1.0315, fontsize=10, horizontalalignment="left")

# Attribution
attribution = "Data & xG model @chickenandstats.com | Viz @chickenandstats.com"
fig.text(s=attribution, x=0.99, y=-0.03, fontsize=8, horizontalalignment="right", style="italic")

savepath = Path("./5v5_4n_fo_forwards.png")
# fig.savefig(savepath, transparent=False, bbox_inches="tight")
```


    
![png](four_nations_files/four_nations_30_0.png)
    


## Bokeh


```python
team = "USA"
team_name = "UNITED STATES"
strength_state = "5v5"
device_type = "desktop"
data = lines.copy()
toi_min = 5
display_plot = True

output_file_str = f"{team.lower()}_5v5_{device_type}.html"

plot_attributes = {
    "desktop": {
        "size_multiplier": 15,
        "major_label_font_size": "9pt",
        "axis_label_font_size": "10pt",
        "title_font_size": "22pt",
        "subtitle_font_size": "16pt",
        "stats_font_size": "11pt",
        "stats_y_value": 0.95,
        "player_name_font_size": "12pt",
        "ncols": 4,
        "height": 240,  # 240,
    },
    "mobile": {
        "size_multiplier": 8,
        "major_label_font_size": "7pt",
        "axis_label_font_size": "8pt",
        "title_font_size": "14pt",
        "subtitle_font_size": "11pt",
        "stats_font_size": "8pt",
        "stats_y_value": 0.95,
        "player_name_font_size": "10pt",
        "ncols": 1,
        "height": 240,  # 240,
    },
}

plot_attributes = plot_attributes[device_type]
plot_colors = {"dark_gray": "#36454F", "light_gray": "#D3D3D3", "medium_gray": "#808080"}

# Setting filter conditions and filtering data
conditions = np.logical_and(lines.strength_state == strength_state, lines.toi >= toi_min)
plot_lines = lines.loc[conditions].sort_values(by="xgf_percent", ascending=False).reset_index(drop=True)

x_range = Range1d(plot_lines.xga_p60.min() - 1, plot_lines.xga_p60.max() + 1)
y_range = Range1d(plot_lines.xgf_p60.min() - 1, plot_lines.xgf_p60.max() + 1)

# Getting the averages and drawing the average lines
xga_mean = plot_lines.xga_p60.mean()
xgf_mean = plot_lines.xgf_p60.mean()

# Setting the size norm so bubbles are consistent across figures
size_norm = (plot_lines.toi.min(), plot_lines.toi.max())

# Getting the teams and standings data to iterate through
teams = ["CAN", "FIN", "SWE", "USA"]
team_names = ["CANADA", "FINLAND", "SWEDEN", "UNITED STATES"]
team_names = dict(zip(teams, team_names, strict=False))

plot_list = []

if display_plot:
    output_notebook()

else:
    output_file(output_file_str)

# Iterating through the standings data
for _idx, team in enumerate(teams):
    team_name = team_names[team]
    team_stats_plot = team_stats.loc[
        np.logical_and(team_stats.strength_state == strength_state, team_stats.team == team)
    ]

    colors = INTERNATIONAL_COLORS[team]

    condition = plot_lines.team == team

    plot_data = plot_lines.loc[condition].copy()

    # plot = prep_stats(data = plot, strengths = strengths)

    plot_data["edgecolors"] = colors["SHOT"]
    plot_data["colors"] = colors["GOAL"]
    plot_data["toi_size"] = plot_data.toi

    source = plot_data.copy()

    source = ColumnDataSource(source)

    TOOLS = "hover,crosshair,pan,wheel_zoom,zoom_in,zoom_out,box_zoom,undo,redo,reset,tap,box_select,poly_select,lasso_select"

    p = figure(tools=TOOLS, x_range=x_range, y_range=y_range)

    vline = Span(
        location=xga_mean, dimension="height", line_color=plot_colors["light_gray"], line_width=2, level="underlay"
    )
    hline = Span(
        location=xgf_mean, dimension="width", line_color=plot_colors["light_gray"], line_width=2, level="underlay"
    )

    p.add_layout(vline)
    p.add_layout(hline)

    p.scatter(
        x="xga_p60",
        y="xgf_p60",
        size="toi",
        source=source,
        color="colors",
        alpha=0.65,
        line_color="edgecolors",
        line_width=2.5,
    )

    gf = team_stats_plot.gf.iloc[0]
    xgf = round(team_stats_plot.xgf.iloc[0], 2)
    ga = team_stats_plot.ga.iloc[0]
    xga = round(team_stats_plot.xga.iloc[0], 2)
    toi = round(team_stats_plot.toi.iloc[0], 2)

    # Setting the ax title
    subtitle = f"{team_name} | {gf} GF ({xgf} xGF) - {ga} GA ({xga} xGA) | {toi} TOI"

    p.add_layout(
        Title(
            text=subtitle,
            text_font_size=plot_attributes["player_name_font_size"],
            text_font_style="bold",
            text_color=plot_colors["dark_gray"],
            vertical_align="middle",
            align="left",
            text_line_height=1,
        ),
        "above",
    )

    p.outline_line_width = 0
    p.grid.grid_line_color = None
    p.axis.minor_tick_line_color = None
    p.axis.major_tick_line_color = plot_colors["dark_gray"]
    p.axis.major_tick_out = 3
    p.axis.major_tick_line_width = 2.5
    #p.axis.ticker = [0, 0.25, 0.5, 0.75, 1]
    #p.axis.major_label_overrides = {x: f"{round(x * 100)}" for x in [0, 0.25, 0.5, 0.75, 1]}

    p.axis.major_label_text_font_size = plot_attributes["major_label_font_size"]
    p.axis.axis_label_text_font_size = plot_attributes["axis_label_font_size"]
    p.axis.axis_line_color = plot_colors["dark_gray"]
    p.axis.axis_line_width = 2

    p.yaxis.axis_label = "xGF per 60 minutes"

    p.xaxis.axis_label = "xGA per 60 minutes"

    hover = p.select(dict(type=HoverTool))

    hover.tooltips = [
        ("LINE", "@forwards"),
        ("TOI", "@toi{0.0}"),
        ("GOALS", "@gf"),
        ("xGF%", "@xgf_percent{0.0%}"),
        ("xGF", "@xgf{0.0}"),
        ("xGA", "@xga{0.0}"),
        ("xGF/60", "@xgf_p60{0.0}"),
        ("xGA/60", "@xga_p60{0.0}"),
    ]
    hover.mode = "mouse"
    hover.name = "tooltips"

    plot_list.append(p)

grid = gridplot(
    plot_list,
    ncols=2,
    toolbar_location="right",
    height=300, #plot_attributes["height"],
    sizing_mode = 'stretch_width',
)

title_str = "Forward line combinations' chances created vs. chances allowed"

title = Div(
    text=title_str,
    styles={"font-size": plot_attributes["title_font_size"],
            "color": plot_colors["dark_gray"],
            "font-weight": "bold",
           },
    margin=(0, 0, 0, 10),
)

todays_date = dt.datetime.now().strftime("%Y-%m-%d")
subtitle_str = f"4 Nations Face-Off | >{toi_min} min. TOI at 5v5 (size indicates TOI) | {todays_date}"

subtitle = Div(
    text=subtitle_str,
    styles={
        "font-size": plot_attributes["subtitle_font_size"],
        "color": plot_colors["medium_gray"],
        "font-weight": "light",
    },
    margin=(-5, 0, 10, 13),
    background="white",
)

attribution = "Data & xG model @chickenandstats.com | Viz @chickenandstats.com"

footer = Div(text=attribution, styles={"font-size": "10pt",
                                       "color": plot_colors["medium_gray"],
                                       "font-weight": "light",
                                      })
# margin=(0, 0, 0, 0))


chart = column(title, subtitle, grid, footer, sizing_mode="scale_width", background="white")

if display_plot == True:
    show(chart, background_fill_color="white")

else:
    save(chart)
```


<style>
    .bk-notebook-logo {
        display: block;
        width: 20px;
        height: 20px;
        background-image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEgAACxIB0t1+/AAAABx0RVh0U29mdHdhcmUAQWRvYmUgRmlyZXdvcmtzIENTNui8sowAAAOkSURBVDiNjZRtaJVlGMd/1/08zzln5zjP1LWcU9N0NkN8m2CYjpgQYQXqSs0I84OLIC0hkEKoPtiH3gmKoiJDU7QpLgoLjLIQCpEsNJ1vqUOdO7ppbuec5+V+rj4ctwzd8IIbbi6u+8f1539dt3A78eXC7QizUF7gyV1fD1Yqg4JWz84yffhm0qkFqBogB9rM8tZdtwVsPUhWhGcFJngGeWrPzHm5oaMmkfEg1usvLFyc8jLRqDOMru7AyC8saQr7GG7f5fvDeH7Ej8CM66nIF+8yngt6HWaKh7k49Soy9nXurCi1o3qUbS3zWfrYeQDTB/Qj6kX6Ybhw4B+bOYoLKCC9H3Nu/leUTZ1JdRWkkn2ldcCamzrcf47KKXdAJllSlxAOkRgyHsGC/zRday5Qld9DyoM4/q/rUoy/CXh3jzOu3bHUVZeU+DEn8FInkPBFlu3+nW3Nw0mk6vCDiWg8CeJaxEwuHS3+z5RgY+YBR6V1Z1nxSOfoaPa4LASWxxdNp+VWTk7+4vzaou8v8PN+xo+KY2xsw6une2frhw05CTYOmQvsEhjhWjn0bmXPjpE1+kplmmkP3suftwTubK9Vq22qKmrBhpY4jvd5afdRA3wGjFAgcnTK2s4hY0/GPNIb0nErGMCRxWOOX64Z8RAC4oCXdklmEvcL8o0BfkNK4lUg9HTl+oPlQxdNo3Mg4Nv175e/1LDGzZen30MEjRUtmXSfiTVu1kK8W4txyV6BMKlbgk3lMwYCiusNy9fVfvvwMxv8Ynl6vxoByANLTWplvuj/nF9m2+PDtt1eiHPBr1oIfhCChQMBw6Aw0UulqTKZdfVvfG7VcfIqLG9bcldL/+pdWTLxLUy8Qq38heUIjh4XlzZxzQm19lLFlr8vdQ97rjZVOLf8nclzckbcD4wxXMidpX30sFd37Fv/GtwwhzhxGVAprjbg0gCAEeIgwCZyTV2Z1REEW8O4py0wsjeloKoMr6iCY6dP92H6Vw/oTyICIthibxjm/DfN9lVz8IqtqKYLUXfoKVMVQVVJOElGjrnnUt9T9wbgp8AyYKaGlqingHZU/uG2NTZSVqwHQTWkx9hxjkpWDaCg6Ckj5qebgBVbT3V3NNXMSiWSDdGV3hrtzla7J+duwPOToIg42ChPQOQjspnSlp1V+Gjdged7+8UN5CRAV7a5EdFNwCjEaBR27b3W890TE7g24NAP/mMDXRWrGoFPQI9ls/MWO2dWFAar/xcOIImbbpA3zgAAAABJRU5ErkJggg==);
    }
</style>
<div>
    <a href="https://bokeh.org" target="_blank" class="bk-notebook-logo"></a>
    <span id="ef6e30b9-7a5c-4d8a-bd14-7357774d8d20">Loading BokehJS ...</span>
</div>







<div id="e150cb8a-ac97-4b13-9468-16c86485446a" data-root-id="p1287" style="display: contents;"></div>






```python

```
