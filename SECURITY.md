# Security Policy

## What's supported

I fix the latest release. That's it. If you're on an older version
and something breaks, upgrade first.

The NHL changes its feeds without warning. When that breaks
chickenstats, I'll respond within 3 days and aim to ship a fix within
14. Fixes go out as a patch release, like 1.9.1.

There's at least one patch a year before the season starts, so team
and schedule tables are ready for it.

## What can change

Versions follow major.minor.patch. Patches fix bugs and don't change
columns. A name leaving the public API raises a FutureWarning for at
least one minor release before it goes, and the warning tells you what
to use instead. Anything that changes your numbers or columns is on
the upgrade page for that release.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, email [chicken@chickenandstats.com](mailto:chicken@chickenandstats.com) with the subject line:
`chickenstats security vulnerability`

Include a description of the issue, steps to reproduce, and any relevant version information.

**Response timeline:**
- Acknowledgement within 3 days
- Assessment and patch within 14 days for confirmed vulnerabilities
