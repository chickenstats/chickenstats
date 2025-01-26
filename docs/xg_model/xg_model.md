---
hide:
  - navigation

glightbox-manual: true

icon: material/google-analytics
description: "Expected Goals model included with chickenstats"
---

# :material-google-analytics: **xG Model**

`chickenstats.chicken_nhl` includes an Expected Goals (xG) model, which is
based off of the [prior work](https://evolving-hockey.com/blog/a-new-expected-goals-model-for-predicting-goals-in-the-nhl/)
of Josh & Luke Younggren of [Evolving-Hockey](http://www.evolving-hockey.com).

The model is an XGBoost classifier, with 38 fields, including distance from net, time since last event, shot angle,
number of players on ice, and whether the shot event comes from a high danger scoring area.

## :material-tools: **Usage**

The xg model is available out-of-the-box with `chickenstats.chicken_nhl.Scraper` and `chickenstats.chicken_nhl.Game`.
xG values are accessed with the pred_goal column in the play-by-play data, or the ixg, xgf, and xga columns
in the individual, on-ice, line, and team stats data.

```python

from chickenstats.chicken_nhl import Scraper

game_id = 2023020001

scraper = Scraper(game_id)
play_by_play = scraper.play_by_play

pbp_xg_values = play_by_play.pred_goal
individual_xg = scraper.stats.ixg

```

## :material-chart-bar: **Model performance**

Information on performance metrics, including AUC-ROC, log-loss, precision, recall, etc

## :material-scatter-plot: **Features and feature performance**

Information on model features (e.g., high-danger, distance from net, angle) and contribution to 
model / model performance

## :material-database-edit: **Data and data preparation**

Information on how the model was constructed, including code snippets





