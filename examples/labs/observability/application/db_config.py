"""Load a mounted database configuration without interpolating passwords."""

import json
from pathlib import Path

from sqlalchemy.engine import URL


def load_database_url(path):
    text = Path(path).read_text().strip()
    if text.startswith("sqlite:///"):
        return text  # Explicit disposable local-test profile.
    try:
        config = json.loads(text)
    except ValueError:
        raise ValueError("Use a PostgreSQL JSON connection file, not an interpolated DSN") from None
    required = {"drivername", "host", "port", "database", "username", "password", "query"}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError("Unexpected database connection fields")
    if config["drivername"] != "postgresql+psycopg":
        raise ValueError("Only the reviewed PostgreSQL driver is supported")
    for key in ("host", "database", "username", "password"):
        if not isinstance(config[key], str) or not config[key] or "\0" in config[key]:
            raise ValueError(f"Invalid database {key}")
    if type(config["port"]) is not int or not 1 <= config["port"] <= 65535:
        raise ValueError("Invalid database port")
    query = config["query"]
    if not isinstance(query, dict) or set(query) != {"sslmode", "sslrootcert"}:
        raise ValueError("Configure explicit PostgreSQL TLS verification")
    if query["sslmode"] != "verify-full" or not isinstance(query["sslrootcert"], str) or not query["sslrootcert"]:
        raise ValueError("PostgreSQL requires verify-full and a CA file")
    # URL.create accepts the raw password separately. Do not URL-encode it
    # beforehand or concatenate it into a DSN string.
    return URL.create(**config)
