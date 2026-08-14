---
icon: material/wrench
description: "Guide to chickenstats.utilities"
---

# :material-wrench: **utilities**

Usage information about the `utilities` module - the shared helpers that `chicken_nhl` &
`evolving_hockey` are built on, & that you'll see used directly throughout the
[:material-school: tutorials](../tutorials/shot_maps.md).

## :fontawesome-solid-user-large: **Basic usage**

### **Import module**

Everything below is available directly from `chickenstats.utilities`:

```python
from chickenstats.utilities import charts_directory, data_directory, norm_coords, ChickenSession
```

### **Chart & data directories**

`charts_directory()` & `data_directory()` create (or confirm) a `charts/` or `data/`
subdirectory relative to the current working directory & return its `Path` - safe to call
repeatedly, no error if the directory already exists. Every tutorial calls
`charts_directory()` in its "Housekeeping" section before saving any figures:

```python
charts_dir = charts_directory()  # ./charts/
save_path = charts_dir / "shot_chart.png"
```

### **Matplotlib style**

`chickenstats.utilities` registers two matplotlib styles - `"chickenstats"` (light) &
`"chickenstats_dark"` (dark) - automatically the moment the module is imported, so
`plt.style.use("chickenstats")` works right away:

```python
import matplotlib.pyplot as plt

import chickenstats.utilities  # registers the styles on import

plt.style.use("chickenstats")
```

### **Coordinate normalization**

`norm_coords()` flips shot coordinates so every shot for a reference team travels in the
same direction on the rink, regardless of which end they were actually shooting at. It adds
`norm_coords_x` & `norm_coords_y` columns, leaving `coords_x`/`coords_y` untouched, & works
with Polars, Pandas, or PyArrow input:

```python
plot_data = norm_coords(data=pbp, normalization_column="event_team", normalization_value="NSH")
```

See it in context in the [:material-map-marker: Shot Maps tutorial](../tutorials/shot_maps.md),
where it's used to plot every team's shots attacking the same direction.

### **HTTP session**

`ChickenSession` is a `requests.Session` pre-configured for reliable, high-volume NHL API
scraping - automatic retries with backoff, sane connect/read timeouts, and a larger
connection pool. `Scraper` & `Game` use one internally, but it's available standalone for
any direct requests against NHL endpoints:

```python
from chickenstats.utilities import ChickenSession

with ChickenSession() as session:
    data = session.get("https://api-web.nhle.com/v1/schedule/now").json()
```

### **Progress bars**

`ChickenProgress` (known total) & `ChickenProgressIndeterminate` (unknown total) are the
Rich-based progress bars used throughout `Scraper` & `Game`'s scraping & aggregation
methods. `track()` wraps an iterable in one line for quick standalone use:

```python
from chickenstats.utilities import track

for game_id in track(game_ids, description="Scraping games..."):
    ...  # fetch game data
```

## :material-cog: **Advanced usage**

`utilities` also exposes a handful of enums (`AggLevel`, `Backend`, `Position`, `Zone`,
`FORWARDS`) & a `DataFrameT` type alias used internally for typing `Scraper`/`Game`/`prep_*`
return values across backends - most users won't need these directly, but they're there for
anyone building on top of `chickenstats`' internals. See the docstrings in
[`chickenstats.utilities`](https://github.com/chickenstats/chickenstats/blob/main/src/chickenstats/utilities/__init__.py)
for the full list.