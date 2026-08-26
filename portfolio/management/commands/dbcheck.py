"""Database configuration and permission diagnostics.

Prints the exact database settings Django is using (without secrets),
connects as the project role and, on PostgreSQL, reports the owner of the
``public`` schema and whether the role may create objects there. This is the
first thing to run when ``python manage.py migrate`` fails with
``permission denied for schema public``.
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Show the configured database and check its permissions."

    def handle(self, *args: object, **options: object) -> None:
        database = settings.DATABASES["default"]
        self.stdout.write("Configured database (no secrets shown):")
        self.stdout.write(f"  engine: {database['ENGINE']}")
        self.stdout.write(f"  name:   {database['NAME']}")
        self.stdout.write(f"  user:   {database.get('USER') or '(none)'}")
        self.stdout.write(f"  host:   {database.get('HOST') or '(local socket)'}")
        self.stdout.write(f"  port:   {database.get('PORT') or '(default)'}")

        try:
            with connection.cursor() as cursor:
                if connection.vendor == "sqlite":
                    self.stdout.write(
                        "Connection OK (SQLite; schema permissions do not apply)."
                    )
                    return

                cursor.execute("SELECT current_user, current_database()")
                user, database_name = cursor.fetchone()
                self.stdout.write(f"Connected as: {user} @ {database_name}")

                if connection.vendor == "postgresql":
                    cursor.execute(
                        "SELECT pg_get_userbyid(nspowner) "
                        "FROM pg_namespace WHERE nspname = 'public'"
                    )
                    schema_owner = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT has_schema_privilege(current_user, 'public', 'CREATE')"
                    )
                    can_create = cursor.fetchone()[0]
                    self.stdout.write(f"public schema owner: {schema_owner}")
                    self.stdout.write(
                        "CREATE on public schema: " + ("YES" if can_create else "NO")
                    )
                    if schema_owner != user:
                        self.stderr.write(
                            "The connected role does NOT own the public schema; "
                            "run as a superuser:"
                        )
                    if not can_create:
                        self.stderr.write(
                            "The connected role cannot create objects. "
                            "Run as the postgres superuser:"
                        )
                        self.stderr.write("  sudo -u postgres psql -d " + database_name)
                        self.stderr.write(
                            "  ALTER SCHEMA public OWNER TO " + user + ";"
                        )
                        self.stderr.write(
                            "  GRANT USAGE, CREATE ON SCHEMA public TO " + user + ";"
                        )
        except Exception as exc:
            raise CommandError(f"Database connection failed: {exc}") from exc
