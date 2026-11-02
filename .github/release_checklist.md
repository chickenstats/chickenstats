# Release checklist

The version comes from the branch name, so `v1.9.0` releases 1.9.0. Publishing a GitHub release is what ships.

## Before the release

- [ ] Run the `regression` workflow on the release branch and keep the `regression-results` artifact.
- [ ] If a saved frame's columns or types changed since the last release, confirm `SAVE_FORMAT` in
      `_scraper_persist.py` went up in the same commit. A change to values alone needs no bump.
- [ ] Each Breaking commit is on the upgrade page: `python scripts/upgrade_notes.py --check docs/guide/upgrade_1_9.md`.
- [ ] Each summer: `_TEAMS_BY_YEAR` and `regular_season_end_dates` in `_season_constants.py` cover the coming season.
- [ ] Run the `new-release` workflow by hand from the release branch. Turn on `test_index` to upload to TestPyPI.
- [ ] Read the `release-notes` artifact from that run. Every Breaking subject has its paragraph under it.

## The release

- [ ] Merge the release branch into `main`. The tag has to sit on `main`, or `git-cliff --latest` picks the wrong range.
- [ ] Publish a GitHub release from `main`, tagged `v<version>`. The notes can be left blank; the workflow fills them in.
- [ ] Watch `new-release`. If it fails before `publish`, nothing has reached PyPI: fix it and run the failed jobs again.

## After the release

- [ ] Install from PyPI into a clean environment and check `chickenstats.__version__`.
- [ ] Check the attestations on the PyPI release page.
- [ ] Merge the changelog pull request.
- [ ] Merge `main` into the next development branch.

## A patch release

- [ ] Branch `v1.9.1` from `main` (not from the development branch) and push it, which sets the version.
- [ ] Fix, and follow the steps above. A patch has no column changes, so `SAVE_FORMAT` stays the same.
- [ ] Merge `main` into the development branch afterward, so the fix is in the next minor release.
