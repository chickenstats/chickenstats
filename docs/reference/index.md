---
hide:
  - navigation
description: "Reference materials and information for chickenstats"
---

# :material-bookshelf: **Reference**

Home of in-depth explanations and debugging assistance. Navigate using the links below.
For more detailed walk-throughs or examples, please consult the **[:material-school: User Guide](../guide/index.md)**.

You can also find reference materials for **[non-public class methods](../contribute/backend/chicken_nhl.md)**
available from objects in `chickenstats.chicken_nhl.scrape`.
**[Nested functions for munging raw data](../contribute/backend/evolving_hockey.md)** from
**[evolving-hockey.com](https://www.evolving-hockey.com)** can be found within `chickenstats.evolving_hockey.base`
and `chickenstats.evolving_hockey.stats`.


## **Modules**

<div class="grid cards" markdown>

-   :material-hockey-sticks: `chicken_nhl`

    ---

    Scrape data from official NHL endpoints

    [:simple-readthedocs: Read more](chicken_nhl/scrape.md)

-   :material-sigma: `chicken_nhl.aggregate`

    ---

    Turn play-by-play into individual, line and team stats

    [:simple-readthedocs: Read more](chicken_nhl/aggregate.md)

-   :material-key: `chicken_nhl.identity`

    ---

    The columns that identify a row of aggregated stats

    [:simple-readthedocs: Read more](chicken_nhl/identity.md)

-   :material-matrix: `chicken_nhl.rapm`

    ---

    Build the design matrix for a RAPM regression

    [:simple-readthedocs: Read more](chicken_nhl/rapm.md)

-   :material-chart-scatter-plot: `chicken_nhl.viz`

    ---

    Chart play-by-play and stats

    [:simple-readthedocs: Read more](chicken_nhl/viz.md)

-   :material-file-sign: `chicken_nhl.contract`

    ---

    The order, strength states and schema tools of play-by-play

    [:simple-readthedocs: Read more](chicken_nhl/contract.md)

-   :material-hockey-puck: `evolving_hockey`

    ---

    Munge data from [Evolving Hockey](https://evolving-hockey.com)

    [:simple-readthedocs: Read more](evolving_hockey/stats.md)

-   :material-web: `utilities.ChickenSession`

    ---

    The HTTP session every request goes through

    [:simple-readthedocs: Read more](utilities/session.md)

-   :material-alert-circle-outline: `exceptions`

    ---

    The errors chickenstats raises

    [:simple-readthedocs: Read more](exceptions.md)


</div>

## **Fancy stats**

<div class="grid cards" markdown>

-   :material-adjust: Score and venue adjustments

    ---

    Adjusting corsi and fenwick events

    [:simple-readthedocs: Read more](fancy_stats/score_adjustments.md)


</div>