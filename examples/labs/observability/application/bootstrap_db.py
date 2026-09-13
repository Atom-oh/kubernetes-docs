"""One-time schema/user setup for a dedicated PostgreSQL lab database."""

import argparse
import json
import os
import secrets
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy import create_engine

from db_config import load_database_url
from storage import metadata


def prepare_runtime_user(admin_url, password):
    """Create a fixed lab runtime role; never alter an existing role/password."""
    engine = create_engine(admin_url)
    try:
        metadata.create_all(engine)
    finally:
        engine.dispose()
    kwargs = {
        "host": admin_url.host, "port": admin_url.port or 5432,
        "dbname": admin_url.database, "user": admin_url.username,
        "password": admin_url.password, **dict(admin_url.query),
    }
    with psycopg.connect(**kwargs) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", ("lab_runtime",))
            if cursor.fetchone():
                raise ValueError("lab_runtime already exists; use an explicit rotation procedure")
            cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier("lab_runtime"), sql.Literal(password),
            ))
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO lab_runtime").format(
                sql.Identifier(admin_url.database),
            ))
            cursor.execute("GRANT USAGE ON SCHEMA public TO lab_runtime")
            cursor.execute(
                "GRANT SELECT, INSERT, UPDATE ON "
                "lab_orders, lab_payments, lab_outbox, lab_inbox TO lab_runtime"
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-connection-file", required=True)
    parser.add_argument("--runtime-connection-file", required=True)
    args = parser.parse_args()
    admin_url = load_database_url(args.admin_connection_file)
    if isinstance(admin_url, str):
        parser.error("This bootstrap requires PostgreSQL")
    output = Path(args.runtime_connection_file)
    # Reserve a private destination before changing the database. Existing
    # credentials are never overwritten or silently rotated.
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    password = secrets.token_urlsafe(32)
    try:
        config = {
            "drivername": "postgresql+psycopg", "host": admin_url.host,
            "port": admin_url.port or 5432, "database": admin_url.database,
            "username": "lab_runtime", "password": password,
            "query": dict(admin_url.query),
        }
        with os.fdopen(descriptor, "w") as stream:
            descriptor = None
            json.dump(config, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Persist the candidate privately before the role transaction commits,
        # so a process interruption does not lose its generated password.
        prepare_runtime_user(admin_url, password)
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        # On failure this is only a candidate credential. Do not deploy it until
        # the DB transaction is verified. Preserve it; never drop/rotate a role.
        raise
    print("Runtime connection file created; keep it private and mount it as a Secret.")


if __name__ == "__main__":
    main()
