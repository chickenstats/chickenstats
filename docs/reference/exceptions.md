---
icon: material/alert-circle-outline
description: "Reference materials and information for chickenstats.exceptions"
---

# :material-alert-circle-outline: **exceptions**

Reference materials for `chickenstats.exceptions`. Every error chickenstats raises on purpose
is a subclass of `ChickenstatsError`.

Where one replaces an error from Python or another library, it subclasses that error too, so
older `except` clauses still catch it:

| chickenstats error | Also a |
|--------------------|--------|
| `NetworkError` | `requests.HTTPError` |
| `SchemaValidationError` | `pandera.errors.SchemaError` |
| `InvalidInputError` | `ValueError` |
| `chickenstats.api.APIError` | the `chickenstats_api` error it replaces, such as `UnauthorizedException` |

##::: chickenstats.exceptions
    handler: python
    options:
        members_order: source
        filters:
            - "!^_"
