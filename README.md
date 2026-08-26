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

### PostgreSQL setup (Arch Linux)

First, create a dedicated role and database for the project (run this once,
as the `postgres` superuser; `psql -l` should not yet contain `portfolio_db`):

```bash
sudo -u postgres psql
```

```sql
CREATE ROLE daftar WITH LOGIN PASSWORD 'a-strong-password';
CREATE DATABASE portfolio_db OWNER daftar;
\q
```

Then point `daftar/.env` at them (and never commit the real `.env`):

```dotenv
DB_ENGINE=postgresql
DB_NAME=portfolio_db
DB_USER=daftar
DB_PASSWORD=a-strong-password
DB_HOST=127.0.0.1
DB_PORT=5432
```

Verify the connection and apply the migrations:

```bash
PGPASSWORD='a-strong-password' psql -h 127.0.0.1 -U daftar -d portfolio_db -c 'select 1;'
poetry run python manage.py migrate
```

Notes:

- On Arch, PostgreSQL does not start automatically; `sudo systemctl start postgresql`
  (and `enable` it if you want it on boot). Check with `pg_isready`.
- If you prefer the existing `root` role, it must also work for `localhost`/`127.0.0.1`
  connections: `ALTER ROLE root WITH LOGIN PASSWORD '...';` then
  `CREATE DATABASE portfolio_db OWNER root;` and use those credentials in `.env`.
- `localhost` can resolve to `::1` first (as in the error you saw); `127.0.0.1`
  is unambiguous. The database must exist — Postgres reports
  `FATAL: database "..." does not exist` before Django can create anything.

Run the test suite (SQLite keeps it fast):

```bash
DB_ENGINE=sqlite poetry run python manage.py test
```

Run it in development:

```bash
poetry run python manage.py runserver --insecure
```

### Troubleshooting: `Unable to find a suitable destination for "daftar.pth"`

This happens when Poetry is configured to install into your global/system
Python (`virtualenvs.create = false`) and that environment's `site-packages`
is not writable (for example, a system-wide Python installed with `sudo`
under `/usr/local`, as is common with `make altinstall`). Poetry wants to use
its own virtual environment, which also keeps dependencies isolated from
your system packages.

Diagnose it:

```bash
poetry config virtualenvs.create      # should print true
poetry config --list | grep virtualenvs
poetry env info                       # "Path" should point into ~/.cache/pypoetry/...
```

Fix it by letting Poetry manage the virtualenv again:

```bash
poetry config virtualenvs.create true
poetry env remove --all               # clear the broken environment first
poetry install
poetry run python manage.py check
```

If you deliberately keep `virtualenvs.create = false`, create and activate a
project virtualenv first so Poetry has a writable destination:

```bash
python3 -m venv .venv
source .venv/bin/activate
poetry install
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
