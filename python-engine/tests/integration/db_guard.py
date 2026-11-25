"""Fail-closed guard for the integration tests that write to a database (D0, DR-6).

These tests insert and delete rows. They must never run against the development database, so this module
decides *before any connection is made* whether `SCHEMA_DIFF_DATABASE_URL` names an approved test database,
and re-checks the identity of the live connection before the first write. Nothing here prints the URL or a
password: messages carry only the database and role names.

Approved: a database named `priceaction_test`, optionally followed by `_` and lowercase letters or digits
(for example `priceaction_test_ci1`), reached as a role that is not one of the live application roles.
Everything else is refused, including the development database `priceaction`.
"""

from __future__ import annotations

import os
import re

from sqlalchemy import Connection, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

ENV_URL = "SCHEMA_DIFF_DATABASE_URL"
ENV_REQUIRE = "REQUIRE_SCHEMA_DIFF"

APPROVED_DATABASE = re.compile(r"priceaction_test(_[a-z0-9]+)*")
# Roles that run the live application or administer the cluster: tests must use their own role.
FORBIDDEN_ROLES = frozenset({"postgres", "app_engine", "app_backend"})
# libpq query parameters that can silently change the database a URL points at.
FORBIDDEN_QUERY_KEYS = frozenset({"dbname", "service", "options"})


class DatabaseGuardError(RuntimeError):
    """The target database is not an approved test database. The tests must not run."""


def check_database_url(url: str) -> str:
    """Return `url` unchanged if it names an approved test database and role, else raise (never connects)."""
    try:
        parsed = make_url(url)
    except ArgumentError as exc:
        raise DatabaseGuardError("not a valid database URL") from exc
    if not parsed.drivername.startswith("postgresql"):
        raise DatabaseGuardError("only PostgreSQL test databases are approved")
    if not parsed.database or APPROVED_DATABASE.fullmatch(parsed.database) is None:
        raise DatabaseGuardError(f"database {parsed.database!r} is not an approved test database")
    hidden = sorted(FORBIDDEN_QUERY_KEYS & set(parsed.query))
    if hidden:
        raise DatabaseGuardError(f"URL parameters {hidden} could change the target database")
    if not parsed.username:
        raise DatabaseGuardError("the URL must name the dedicated test role explicitly")
    if parsed.username in FORBIDDEN_ROLES:
        raise DatabaseGuardError(f"role {parsed.username!r} is a live application or administrative role")
    return url


def approved_database_url() -> str | None:
    """The approved test database URL, or `None` when none is configured (the tests then skip).

    With `REQUIRE_SCHEMA_DIFF=1` (CI) a missing URL is an error. A URL that is set but not approved is always
    an error: the module fails to import, so no test in it runs and no connection is attempted.
    """
    url = os.environ.get(ENV_URL)
    if not url:
        if os.environ.get(ENV_REQUIRE) == "1":
            raise DatabaseGuardError(f"{ENV_REQUIRE}=1 but {ENV_URL} is not set")
        return None
    return check_database_url(url)


def assert_approved_connection(conn: Connection) -> None:
    """Re-check the live connection's database and role before the first write (defence in depth)."""
    database, role = conn.execute(text("select current_database(), current_user")).one()
    conn.rollback()
    if APPROVED_DATABASE.fullmatch(database) is None:
        raise DatabaseGuardError(f"connected to {database!r}, which is not an approved test database")
    if role in FORBIDDEN_ROLES:
        raise DatabaseGuardError(f"connected as {role!r}, a live application or administrative role")
