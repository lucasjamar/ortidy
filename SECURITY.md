# Security Policy

## Supported versions

`ortidy` is pre-1.0; only the latest released version on PyPI receives fixes.

## Reporting a vulnerability

Please report security issues **privately** — do not open a public issue.

Use GitHub's private vulnerability reporting:
**[Report a vulnerability](https://github.com/lucasjamar/ortidy/security/advisories/new)**
(repo → *Security* → *Report a vulnerability*).

We aim to acknowledge reports within a few days. Once a fix is ready we'll
release it to PyPI and credit the reporter unless anonymity is requested.

## Scope

`ortidy` is a thin dataframe façade over [Google OR-Tools](https://developers.google.com/optimization).
The heavy lifting (and most of the attack surface) lives in OR-Tools and the
dataframe backends — please report issues in those to their respective projects.
