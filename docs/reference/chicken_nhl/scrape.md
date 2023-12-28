---

icon: material/download

---

# :material-download: **chicken_nhl.scrape**

Reference materials for the `chickenstats.chicken_nhl.scrape` module. Testing

For more detailed walk-throughs or examples, please consult the **[:material-school: User Guide](../../guide/guide.md)**

## **main**

The below functions are the main scraping functions in `chickenstats.chicken_nhl`.
The vast majority of users should find them sufficient for their NHL data-gathering needs. 

Game IDs, which are the basis for most functionality, can be found using `scrape_schedule()`,
divisions and conferences can be found using `scrape_standings()`, while play-by-play data is scraped
using `scrape_pbp()`.

## **inputs**

The below functions are mainly used as inputs for the `scrape_pbp()` function. 
The vast majority of users should have no need for these functions as the main data points are included elsewhere.

However, if you feel that the primary functions don't suit your needs, these are available for custom analyses. 
