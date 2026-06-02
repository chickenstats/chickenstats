# Changelog

## [Unreleased]

### Bug Fixes

- Update new_release
Updating to latest git-cliff action, threw an error last time
- Bug with API ID fallback
Fixing bug with API ID fallback
- Re-ordering based on API ID
reordering player aggregations based on API IDs, to eliminate duplicate rows for different lines
- Updating season dtype
Updating season dtype to int
- Aggregation error with team stats
Fixed a group_by error with the team stats where rows were being dropped
- Updating examples env.example
Updating examples for proper API env variables
- Updating filepaths for data workflows
Updating file paths for data workflows
- Updating dotenv
updating mlflow experiments dotenv
- Updating season column dtype
Updating season column dtype to always be an integer
- Adding proper env variables
- Adding errors and type validation
Improving user ergonomics with warnings and type validation
- Adding parquet to gitignore
Adding parquet files to gitignore
- Adding old schema so they don't have to be recreated
Adding the old schema to the file so they don't have to be recreated from scratch
- Importing from local directory
Importing the function to prep the data from the local xg file vs. the live version in the module.
- De-duplicate change players
Addresses a bug where player is repeated if shift ends at the same time as other shifts. De-duplicates the change on / off players
- Moving xG validation
Moving xG validation to the xg file to keep the code closer to prep_data functions. Should be easier version control as we iterate on the model
- Moving xg.py closer to xg scripts
Moving xg.py where closer to xg scripts for maintenance
- Updating RAPM target metrics and player ID columns
Updating the target metrics to be the env_xg and updating the player ID columns to be API ID
- Updating experiments.py
Updating experiments.py for latest
- Updating rolling stats for env_xg
updating rolling stats to compute off of environment xG
- Updating experiments.py
- Updating naming conventions
- Adding session as categorical column
- Addressing play speed nulls
Adding play speed so they're null and not infinity
- Addressing bugs with monotone constraints
Addressing bugs with monotone constraints where column may not be in the data
- Sorting data before saving
Sorting data before saving to preserver order
- Updating leakage of uv environments
- Removing xG features
Removes ixg from aggregations / stats unless column presenting

### Build

- Update uv.lock
Updating for this dependency
- Updating chickenstats_api dependency
Updating chickenstats_api dependency
- Updting dependencies
updating dependencies
- Update dependencies
Updating dependencies
- Updating dependencies
Upating dependencies
- Updating dependencies
- Updating dependencies
- Adding dependencies and updating ruff sources
Adding dependencies and updating ruff sources

### CI/CD

- Update cliff.toml to add commit bodies
Updating cliff.toml file to add the body message for git commits vs. just the summary messages
- Adding xg_model to clean-dotenv
Adding xg_model as directory to generate a clean dotenv file
- Adding editorconfig
Adding editorconfig to enfroce the new line issues

### Documentation

- Updating evolving_hockey docs
Updating evolving_hockey docs to fix zensical error
- Update readme
Updating readme for polars and for the correct links to the documentation site
- Updating index
Updating documentation homepage for latest updates
- Updating chicken_nhl guide
Updating the chicken_nhl guide for the latest library improvements, include polars

### Features

- Adding team_stats upload
Adding team_stats upload to ChickenStats API class
- Adding experiments.py
Adding file to run xG experiments
- Adding env file for experiments
Adding env file for experiments
- Adding limit functionality
Adding functionality to account for API limits, with wrappers to fetch all data
- Adding API wrapper
Adding wrapper for API access via chickenstats package
- Adding ID generator utilities
Adding ID generator columns to be re-used in development (I.e., loading data)
- Adding module-level track function
Module-level track function for lightweight tracking when iterating through lists
- Custom ChickenTimeRemaining column in progress bar
Adding custom ChickenTimeRemaining column in the progress bar that adds fallback functionality for long-running processes
- Updating scrape_data to write parquet files
Updating the scrape script to write data as parquet (vs. csv) files
- Moving old versions of process and experiments
Moving old versions of processing data and experiments for xG model build
- Building cascade xG model
Initial steps in building a cascade xG model
- Adding process data scripts for env and inf xg
Adding separate process data scripts for environment and informed xG
- Creating a script to finalize inf_xg
Finalizing the informed xG models
- Last commit of xG model before moving behind paywall
Final commit of the xG model before moving behind the paywall
- Adding base_xg and pred_goal capabilities
Initial commit to prep for the cascade xG model
- Adding chickenstats-xg
Adjusting aggregation to account for base_xg, context_xg, and pred_goal, which are part of chickenstats-xg

### Refactor

- Consolidating api_utils
Consolidating the prep stats functions for api upload to single function in api_utils for maintainability
- Updating experiments
Updating the experiments file
- Moving xG model
Moving xG model to a new repo
- Moving xG to other repo
Moving xG experiments to another repo and prep scraper for public release without xG
- Moving xG files to other repo
Moving xG files to another repo
- Removing xG
Removing xG features and functionality from the public scraper

### Testing

- Streamlining tests to account for library changes
Streamlining tests and increasing speed of test suite in CI/CD builds

## [1.7.9.28] - 2026-04-17

### Bug Fixes

- Comprehensive dev dependencies
Ensures all dependencies included in uv dev group
- Updating _validation_utils
Updating _validation_utils to add a build_pandera_schema function and the _get_base_type_type_and_nullable function to pull in the first non-list basetype
- Updating team_stats
Updating team stats levels to pull in strength_state vs. strengths
- Updating dtypes and group columns
Updating dtypes and grouping columns for aggregation functions
- Updating tests suite
Updating test suite to use proper errors and to ignore certain ty results
- Updating polars aggregation
Updating polars aggregation for correct individual corsi for statistics
- Updating adjusted corsi calculations
Updating adjusted corsi calculations to properly calculate block_adj and teammate_block_adj
- Updating change events in pbp
Updating pbp and aggregations to propertly account for zone starts
- Updating testing exceptions
Updating test exceptions to filter warnings that impact polars performance, due to an issue with pandera and checking lazyframes. Will be removed once bug is addressed by pandera
- Adding missing shifts for several games
Add missing OT shifts for several games, there may be others to add later
- Aligning xg prep functions
Aligning xg prep functions and making use of polars validation
- Removing pandera polars performance warning
Removing pandera polars performance warning after latest pandera update
- Removing print debug statement
Accidentally left a print debug statement in there and needed to be removed
- Adding _to_backend utility
Adding _to_backend utility for consistency across modules
- Moving score adjustments calculations
Move score adjustments calculations to properly calculate xg-based adjusted values
- Adding dummy columns
Ensuring the proper dummy columns are constructed

### Build

- Updating dependencies
Updating to latest dependencies
- Update uv.lock
Updating uv.lock and dependencies
- Update dependencies
Updating dependencies to latest versions

### CI/CD

- Update pre-commit-config for git-cliff
Updating pre-commit settings to enforce git-cliff conventions on the commit message
- Adding git-cliff to new releases
Adding git-cliff functionality to the new release workflow to generate release notes automatically
- Updating tests to run monthly
Updating tests workflow to run monthly to ensure consistent build status vs. manual updates
- Updating git checkout in update-docs
Updating the git checkout action in update-docs.yml for an actual supported version (v6 isn't real)
- Updating uv in update-docs-mkdocs
Updating uv to the latest version in update-docs-mkdocs.yml
- Adding json config for renovatebot
Adding json configuration file for renovatebot
- Pre-commit aligned with repo
Ensuring that pre-commit uses the same versions of dependencies as the repository
- Updating pre-commit for ty
Updating pre-commit to run ty only staged files
- Adding codecov configuration
Adding codecove configuration
- Updating docs workflow
Updating docs workflow to reduce duplication by adding workflow dispatch call
- Delete update-docs workflow
Combing docs with update-docs workflows through dispatch call to remove duplication
- Adding lint workflow
Adding lint workflow to catch errors

### Documentation

- Creating _docstrings.py
Create _docstrings.py to house common docstrings to be re-used across modules / classes
- Update _fixes.py
Updating _fixes.py docstrings and comments
- Updating game.py for shared docstring conventions
Update game.py (and underlying Mixin classes) for the shared docstrings recently drafted
- Updating docstrings and code comments
updating docstrings and code comments for non-public functions
- Adding shared docstrings
Adding shared docstring conventions for scraper.py
- Updating docstrings and comments
Updating docstrings and comments for aggregations
- Updating validation docstrings and comments
Updating docstrings and code commenting for validation framework
- Updating utilities docstrings and comments
Updating docstrings and code commenting for utilities module
- Updating scraper docstrings and comments
Updating docstrings and code commenting for scraper classes
- Updating team and player docstrings and comments
Updating team and player docstrings and comments
- Updating progress bar documentation
Improving progress bar documentation to better match rich

### Features

- Dumping failed games to json
Dumping failed games to json, in the event that they exist, for debugging purposes

### Miscellaneous

- Adding git-cliff toml file
Adding toml file for git-cliff configuration
- Adding templates
Adding templates for bug requests, feature requests, and pull requests
- Adding py.typed
Adding py.typed for file type hints

### Refactor

- Creating custom exceptions
Creating custom exception classes for chicken_nhl module
- Updating src/chickenstats/__init__.py
Updating top-level __init__.py to show version number
- Chicken_nhl __init__.py
Updating chicken_nhl module's __init__.py file to show publicly available classes
- Custom exceptions in _validation_utils
Adding custom exception classes to _validation_utils
- Updating evolving_hockey __init__.py
Updating evolving_hockey module to show the publicly available functions
- Update utilities __init__.py
Updating utilities module to show the publicly available functions
- Adding ty type hints and custom exceptions
Adding type hints to comply with ty type checking and adding custom exception functionality
- Adding utility functions to __init__
Adding data_directory and charts_directory functions to chickenstats/utilities/__init__.py
- Converting evolving_hockey pbp functions to polars
Refactoring the evolving_hockey module for polars vs. pandas functionality. Impacts multiple files due to reorgnization
- Adding polars pandera schema
Adding functions to create the polars pandera schemas which are used later
- Significant refactor
Significantly changing the chicken_nhl module to reduce polars / pandas duplication, improve scraper performance, and improve validation framework. Too many changes to list here
- Updating evolving_hockey module
Updating evolving_hockey module to leverage similar polars / narwhal functionality, reduce polars / pandas duplication, and improve validation framework. Shares as much as possible with chicken_nhl module
- Adding enums to aggregation functions
Adds enums to aggregation functions
- Splitting game.py to multiple files
Splitting game.py into multiple files and making use of Mixins to improve simplicity of public API
- Splitting scraper.py
Splitting scraper.py into multiple files to simplify public facing API
- Updating scraper.py
Updating scraper.py to make use of multiple files to simplify public API
- Updating utilities
Updating utilities to be more easily shared across modules, adding enums, and adding type checks
- Adding enums and logging
Updating season and player with enums and logging functionality
- Adding type hints and enums
Adding type hints and enums
- Performance improvements in aggregations
Improving performance with aggregations
- Adding _to_backend and failed_games
Adding _to_backend function for consistency across modules and a failed_games public property
- Adding _to_backend and type hints
Adding _to_backend for consistency across modules and proper dataframe type hints
- Chaining capabilities and performance improvements
Adding ability to chain prep_* methods (I.e., scraper.prep_stats(level="season").stats) for ergonomics and performance improvements for aggregations
- Updating api module
Updating api functions for polars functionality and removing pandas de-duplication.

### Testing

- Updating tests suite
Updating tests suite for refactors and to improve coverage
- Removing polars exception filter
Pandera made the update, no need for polars performance warning exception filter
- Updating testing suite
Updating testing suite for latest changes
- Updating test suite
Updating testing suite for changes
- Updating testing suite for name changes
Updating testing suite for name changes

## [1.7.4] - 2023-12-28
