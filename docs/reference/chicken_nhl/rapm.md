---
icon: material/matrix
description: "Reference materials and information for chickenstats.chicken_nhl.rapm"
---

# :material-matrix: **chicken_nhl.rapm**

Reference materials for `chickenstats.chicken_nhl.rapm`, the sparse design matrix for a RAPM
regression. Requires the `rapm` extra (`pip install chickenstats[rapm]`).

##::: chickenstats.chicken_nhl.rapm
    handler: python
    options:
        members:
            - build_rapm_matrix
            - build_position_map
            - RAPM_METRICS
            - RAPM_SITUATIONS
        filters:
            - "!^_"

###::: chickenstats.chicken_nhl.rapm.RapmMatrix
    handler: python
    options:
        show_bases: false
        # Inspection shows each field's value as a private _tuplegetter call.
        show_attribute_values: false
        filters:
            - "!^_"
