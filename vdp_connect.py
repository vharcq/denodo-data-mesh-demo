#!/usr/bin/env python3
"""Minimal Denodo VDP connection helper for this demo.

Everything comes from ``demo.env`` at the repository root (copy ``demo.env.example``).
There are no silent defaults: a missing key is an error that names the key, so the demo
never ends up running against a server you did not mean to target.

The JDBC driver is the official Denodo one (``denodo-vdp-jdbcdriver.jar``). It is not
redistributed here: download it from your Denodo installation or the Denodo support site
and point ``VDP_JDBC_JAR`` at it.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(ROOT, "demo.env")
JDBC_DRIVER = "com.denodo.vdp.jdbc.Driver"

REQUIRED = ("VDP_HOST", "VDP_PORT", "VDP_ODBC_PORT", "VDP_USER", "VDP_PASS",
            "VDP_JDBC_JAR", "DEMO_USERS_PASSWORD")


def load_env(path=ENV_FILE):
    """Read KEY=value lines; fail loudly on a missing file or key."""
    if not os.path.isfile(path):
        sys.exit(f"Missing {path}\nCopy demo.env.example to demo.env and fill it in.")
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    missing = [k for k in REQUIRED if not env.get(k)]
    if missing:
        sys.exit(f"{path} is incomplete, missing: {', '.join(missing)}")
    jar = env["VDP_JDBC_JAR"]
    if not os.path.isabs(jar):
        jar = os.path.join(ROOT, jar)
    if not os.path.isfile(jar):
        sys.exit(f"JDBC driver not found: {jar}\n"
                 "Copy denodo-vdp-jdbcdriver.jar from your Denodo installation "
                 "(<DENODO_HOME>/tools/client-drivers/jdbc/) and set VDP_JDBC_JAR.")
    env["VDP_JDBC_JAR"] = jar
    return env


ENV = load_env()


def connect(user, password, database):
    """Open a JDBC connection to one virtual database."""
    import jaydebeapi
    url = f"jdbc:vdb://{ENV['VDP_HOST']}:{ENV['VDP_PORT']}/{database}"
    return jaydebeapi.connect(JDBC_DRIVER, url, [user, password], ENV["VDP_JDBC_JAR"])


def connect_admin(database="admin"):
    return connect(ENV["VDP_USER"], ENV["VDP_PASS"], database)


def statements(path):
    """Yield the statements of a .vql file: strip `--` comments FIRST (they may contain
    ';'), THEN split on ';'. Safe for these files: no '--' appears inside a literal."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    cleaned = []
    for line in raw.splitlines():
        i = line.find("--")
        cleaned.append(line[:i] if i >= 0 else line)
    for chunk in "\n".join(cleaned).split(";"):
        stmt = chunk.strip()
        if stmt:
            yield stmt
