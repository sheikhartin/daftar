## Daftar

![GitHub repo status](https://img.shields.io/badge/status-active-green?style=flat)
![GitHub license](https://img.shields.io/github/license/sheikhartin/daftar)
![GitHub contributors](https://img.shields.io/github/contributors/sheikhartin/daftar)
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/sheikhartin/daftar)
![GitHub repo size](https://img.shields.io/github/repo-size/sheikhartin/daftar)

The word Daftar comes from Farsi (دفتر), which means notebook. This website is
implemented with the Django framework and allows you to post in Markdown format
and also has a commenting service inside!

### Requirements

- Python 3.10+
- [Poetry](https://python-poetry.org/)
- PostgreSQL for production (SQLite works for local development/tests)

### How to Use

First, install the dependencies:

```bash
poetry install
```

Configure the database and adapt the environment variables to it. Look at the
example [here](daftar/.env.example), then copy it and fill in your values:

```bash
cp daftar/.env.example .env
```

Apply migrations (they are committed, no need to run `makemigrations`):

```bash
poetry run python manage.py migrate
```

Run the test suite (SQLite keeps it fast):

```bash
DB_ENGINE=sqlite poetry run python manage.py test
```

Run it in development:

```bash
poetry run python manage.py runserver --insecure
```

Check the deployment readiness:

```bash
# Start from daftar/.env.example and set DEBUG=0, a real secret key and
# ALLOWED_HOSTS before running:
poetry run python manage.py check --deploy
```

**Note**: Only superusers can update posts and comments through the website...

### Security

The project follows Django's deployment checklist. The defaults are hardened
for production (`DEBUG` and `SECURE_SSL_REDIRECT` derive from the environment),
a Content-Security-Policy is enforced with per-request nonces, comment content
is sanitized with [nh3](https://github.com/messense/nh3), comments are rate
limited per IP with a honeypot trap, and the test suite covers authentication,
authorization, input validation, and XSS scenarios.

Continuous integration runs:

- `ruff` linting and formatting checks
- the Django test suite
- a production `manage.py check --deploy`
- an [OSV-Scanner](https://github.com/google/osv-scanner) audit of
  `poetry.lock` (also watch the GitHub Security tab; [Dependabot]
  (https://docs.github.com/en/code-security/dependabot) keeps the
  dependencies updated weekly)

> **Heads-up for existing deployments:** `db.json` was a dump of the live
> database (users, sessions, admin logs) and has been removed from the
> repository. If you ever committed it, also purge it from Git history
> (`git filter-repo --path db.json --invert-paths` / BFG) and **rotate
> `DJANGO_SECRET_KEY` and the admin password**, because the database dump
> contained session data that can be forged with a leaked secret key.

### License

This project is licensed under the MIT license found in the [LICENSE](LICENSE)
file in the root directory of this repository.
