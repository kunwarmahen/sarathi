"""`sarathi smritikosh`: a memory that finds things by meaning, set up once.

Yantra remembers things about you in a small file of its own that
matches words: "find me flights" never finds "lives near RDU". Smritikosh
is a memory server that searches by meaning, and Yantra's own guide to
it (Yantra's SMRITIKOSH.md) is ten steps by hand. This command is those
steps, run in order, each one skipped when it is already done:

    1. its checkout       SARATHI_SMRITIKOSH, or beside the others, or a
                          git clone there; ``uv sync --extra mcp``
    2. its settings       Smritikosh's own ``.env``: the local road
                          (Ollama, nomic-embed-text, 768) or the cloud
                          road (OpenAI embeddings, 1536), by ``[model]``
    3. its database       PostgreSQL with pgvector, in a container
    4. its tables         ``alembic upgrade head``
    5. an admin           only when someone needs an account made
    6. your account       named as Yantra knows you, and its key
    7. Dvara's people     one account and one key each
    8. the switch         ``[memory] via = "smritikosh"`` in sarathi.toml

and then ``sarathi up`` starts the server and hands Yantra (and Dvara's
turns) the way to reach it.

THE BUILT-IN FILE IS THE DEFAULT, AND ONE COMMAND AWAY. ``--off`` sets
``[memory] via = "local"`` again. Nothing is deleted on either switch:
the file keeps what it had, Smritikosh keeps what it had, and Yantra's
``/memory copy local`` brings the file's memories across once.

WHAT IS ALREADY THERE IS USED, NEVER REPLACED. A Smritikosh you set up by
hand has a ``.env``, a database and a key: the ``.env`` is read and only
a missing ``JWT_SECRET`` is added, the database container is started as
it is (its volume becomes Sarathi's to start on both roads), and a key
already in secrets.env or in Yantra's ``.env`` is checked and kept. The
embedding size in an existing ``.env`` is never touched: the tables were
built for it, and another size means an empty database.

THROUGH ITS DOCUMENTED API ONLY. Accounts and keys are made the way the
guide makes them -- ``/auth/register``, ``/auth/token``, ``/keys`` --
and the first admin with ``BOOTSTRAP_ADMIN=1`` on a server started for
that one call, as an environment variable, never edited into its file.
Sarathi's admin is called ``sarathi``, so it never collides with an
``admin`` you made yourself, and is made only when an account has to be:
a Smritikosh that already holds your account and key needs no admin.

A KEY PER PERSON, NEVER THE ADMIN'S. A Smritikosh key reaches only its
own account's memories. Yantra gets yours (``SMRITIKOSH_API_KEY`` in
secrets.env, handed to Yantra and Dvara alone); each person in Dvara's
actors file gets an account of their own (``dvara-<id>``) and a key of
their own, in Dvara's ``memory.json``, readable by you alone. The owner
in that file is you, with your own account, so what you told Yantra's
page is what Dvara's agents know about you on Telegram. A person added
to the actors file later gets theirs the next time this runs.

NEO4J, MONGODB AND REDIS ARE LEFT OUT. Smritikosh runs without them and
says "degraded", which is fine for everything Yantra asks of it.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from sarathi.config import (
    Config,
    ConfigError,
    Smritikosh,
    read_secrets,
    render,
    save_secret,
    settings_path,
    state_dir,
    write_private,
)
from sarathi.siblings import SIBLINGS, beside_dir, locate

REPO = "https://github.com/kunwarmahen/smritikosh"
DB_IMAGE = "docker.io/pgvector/pgvector:pg17"
#: The two roads' embedding models and the sizes the tables are built for.
LOCAL_EMBED, LOCAL_DIMS = "nomic-embed-text", 768
CLOUD_EMBED, CLOUD_DIMS = "text-embedding-3-small", 1536
#: Smritikosh's own chat model on the local road, for its extra features
#: (Yantra doesn't use them): a small one, when it is pulled.
SMALL_CHAT = "gemma4:e4b"
CLOUD_CHAT = {"anthropic": ("claude", "claude-haiku-4-5-20251001"),
              "openai": ("openai", "gpt-4o-mini")}
#: The admin Sarathi makes, and the secrets it keeps.
ADMIN = "sarathi"
KEY, ADMIN_PASSWORD = "SMRITIKOSH_API_KEY", "SMRITIKOSH_ADMIN_PASSWORD"
#: Every secret that is Smritikosh's: handed to Yantra and Dvara alone.
SECRETS = (KEY, ADMIN_PASSWORD)
#: Dvara's file of each person's name and key (dvara's memory.py).
PEOPLE_FILE = "memory.json"
#: The passwords of the accounts Sarathi made, in its state folder.
ACCOUNTS_FILE = "smritikosh-accounts.json"
#: A person's account, when they are not you.
PERSON_PREFIX = "dvara-"
#: The most memories the home page counts before it says "500 or more".
COUNT_LIMIT = 500
READY = 60.0


class SetupError(Exception):
    """A step that can't go on, in words, with what to do about it."""


# ---- where it is ------------------------------------------------------------------


def sibling():
    return next(s for s in SIBLINGS if s.name == "smritikosh")


def find_checkout(config: Config) -> tuple[Path | None, str]:
    """(checkout, which rule found it): sarathi.toml's, then the checkout
    SARATHI_SMRITIKOSH's program sits in, then beside the others."""
    named = config.smritikosh.path()
    if named is not None:
        return named, "sarathi.toml"
    hit = locate(sibling())
    if hit is not None:
        program = Path(hit[0]).resolve()
        repo = program.parents[2] if program.parent.name == "bin" else None
        if repo is not None and (repo / "pyproject.toml").is_file():
            return repo, hit[1]
    root = beside_dir()
    if root is not None and (root / "smritikosh" / "pyproject.toml").is_file():
        return root / "smritikosh", "beside"
    return None, ""


def program(checkout: Path, name: str = "smritikosh-mcp") -> Path:
    return checkout / ".venv" / "bin" / name


def run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False, **kw)


def clone(say: Callable[[str], None]) -> Path:
    root = beside_dir()
    if root is None:
        raise SetupError("no folder to clone Smritikosh into: set SARATHI_SIBLINGS, or "
                         "SARATHI_SMRITIKOSH to a smritikosh-mcp you have")
    where = root / "smritikosh"
    if where.exists():
        raise SetupError(f"{where} is there but is not a Smritikosh checkout")
    say(f"checkout   cloning {REPO} into {where}")
    done = run(["git", "clone", REPO, str(where)])
    if done.returncode != 0:
        raise SetupError(f"git clone failed: {done.stderr.strip()}")
    return where


def sync(checkout: Path, say: Callable[[str], None]) -> None:
    """``uv sync --extra mcp``, when its programs are not there yet."""
    if all(program(checkout, n).is_file() for n in ("smritikosh-mcp", "uvicorn", "alembic")):
        return
    uv = shutil.which("uv")
    if uv is None:
        raise SetupError("uv is not installed: https://docs.astral.sh/uv/")
    say("checkout   installing its programs (uv sync --extra mcp)")
    done = run([uv, "sync", "--extra", "mcp"], cwd=checkout)
    if done.returncode != 0 or not program(checkout).is_file():
        raise SetupError(f"uv sync --extra mcp failed in {checkout}: "
                         f"{(done.stderr or done.stdout).strip()[-400:]}")


# ---- its .env ---------------------------------------------------------------------


_LINE = re.compile(r"^\s*(?:#\s*)?([A-Z][A-Z0-9_]*)\s*=")


def read_dotenv(path: Path) -> dict[str, str]:
    """KEY=VALUE lines; '#' lines skipped, an unquoted value's ``  # note``
    dropped, as Smritikosh's own reader does."""
    out = {}
    try:
        lines = path.read_text().splitlines()
    except FileNotFoundError:
        return {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if value[:1] in ("'", '"'):
            value = value[1:value.find(value[0], 1)] if value.find(value[0], 1) > 0 \
                else value[1:]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        out[key.strip()] = value
    return out


def fill_dotenv(text: str, values: dict[str, str]) -> str:
    """``text`` with each key set: its line (or its commented-out example)
    replaced where it first appears, the rest added at the end."""
    left = dict(values)
    out = []
    for line in text.splitlines():
        hit = _LINE.match(line)
        key = hit.group(1) if hit else None
        if key in left:
            out.append(f"{key}={left.pop(key)}")
        elif key in values and not line.lstrip().startswith("#"):
            continue                       # a second live line for a key set above
        else:
            out.append(line)
    if left:
        out += ["", "# Set by `sarathi smritikosh`."] + [f"{k}={v}" for k, v in left.items()]
    return "\n".join(out) + "\n"


@dataclass(frozen=True)
class Database:
    """POSTGRES_URL, in its parts."""

    user: str
    password: str
    host: str
    port: int
    name: str

    @classmethod
    def parse(cls, url: str) -> Database:
        parts = urllib.parse.urlsplit(url.replace("postgresql+asyncpg", "postgresql", 1))
        if not parts.hostname or not parts.username:
            raise SetupError(f"POSTGRES_URL in Smritikosh's .env is not one Sarathi can "
                             f"read: {url!r}")
        return cls(urllib.parse.unquote(parts.username),
                   urllib.parse.unquote(parts.password or ""), parts.hostname,
                   parts.port or 5432, parts.path.lstrip("/") or "smritikosh")

    def url(self, host: str | None = None, port: int | None = None) -> str:
        auth = f"{urllib.parse.quote(self.user)}:{urllib.parse.quote(self.password)}"
        return (f"postgresql+asyncpg://{auth}@{host or self.host}:{port or self.port}/"
                f"{self.name}")


def road_settings(config: Config, *, pulled: list[str] | None,
                  cloud_key: Callable[[], str | None]) -> tuple[dict[str, str], list[str]]:
    """Smritikosh's model settings for this machine's road, and lines to say."""
    notes = []
    if config.provider == "ollama":
        base = (config.base_url or "http://localhost:11434").removesuffix("/v1")
        talk = [n for n in (pulled or []) if "embed" not in n]
        chat = SMALL_CHAT if SMALL_CHAT in talk else (config.model or (talk[0] if talk
                                                                        else SMALL_CHAT))
        if pulled is not None and not any(n.split(":")[0] == LOCAL_EMBED for n in pulled):
            notes.append(f"Ollama has no {LOCAL_EMBED} yet: `ollama pull {LOCAL_EMBED}` "
                         "before anything is remembered")
        return {"LLM_PROVIDER": "ollama", "LLM_MODEL": chat, "LLM_BASE_URL": base,
                "EMBEDDING_PROVIDER": "ollama", "EMBEDDING_MODEL": LOCAL_EMBED,
                "EMBEDDING_BASE_URL": base,
                "EMBEDDING_DIMENSIONS": str(LOCAL_DIMS)}, notes
    held = read_secrets()
    chat_key = held.get(f"{config.provider.upper()}_API_KEY") or os.environ.get(
        f"{config.provider.upper()}_API_KEY", "")
    embed_key = held.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") or cloud_key()
    if not embed_key:
        raise SetupError("the cloud road turns memories into numbers with OpenAI, and "
                         "there is no OPENAI_API_KEY: put one in secrets.env, or use "
                         "the local road (`ollama pull nomic-embed-text`, then `sarathi "
                         "smritikosh --local`)")
    provider, model = CLOUD_CHAT[config.provider]
    return {"LLM_PROVIDER": provider, "LLM_MODEL": model, "LLM_API_KEY": chat_key,
            "EMBEDDING_PROVIDER": "openai", "EMBEDDING_MODEL": CLOUD_EMBED,
            "EMBEDDING_API_KEY": embed_key,
            "EMBEDDING_DIMENSIONS": str(CLOUD_DIMS)}, notes


def settle_dotenv(config: Config, checkout: Path, say: Callable[[str], None], *,
                  pulled: list[str] | None, cloud_key: Callable[[], str | None]) -> Database:
    """Write Smritikosh's .env, or add what an existing one is missing."""
    path = checkout / ".env"
    if path.exists():
        held = read_dotenv(path)
        added = {}
        # only when MISSING: Smritikosh may encrypt stored sign-ins with
        # it, and a new one would leave them unreadable
        if not held.get("JWT_SECRET"):
            added["JWT_SECRET"] = secrets.token_hex(32)
        if added:
            write_private(path, fill_dotenv(path.read_text(), added))
        dims = held.get("EMBEDDING_DIMENSIONS", "1536")
        say(f"settings   {path} kept ({held.get('EMBEDDING_PROVIDER', '?')}, "
            f"{held.get('EMBEDDING_MODEL', '?')}, {dims})"
            + (f"; added {', '.join(added)}" if added else ""))
        return Database.parse(held.get("POSTGRES_URL", "postgresql+asyncpg://smritikosh:"
                                       "smritikosh@localhost:5432/smritikosh"))
    values, notes = road_settings(config, pulled=pulled, cloud_key=cloud_key)
    db = Database("smritikosh", secrets.token_hex(16), "localhost",
                  config.smritikosh.db_port, "smritikosh")
    values.update({"POSTGRES_URL": db.url(), "JWT_SECRET": secrets.token_hex(32),
                   "APP_ENV": "development", "BOOTSTRAP_ADMIN": "0"})
    example = checkout / ".env.example"
    text = example.read_text() if example.is_file() else ""
    write_private(path, fill_dotenv(text, values))
    say(f"settings   wrote {path}: {values['EMBEDDING_PROVIDER']}, "
        f"{values['EMBEDDING_MODEL']}, {values['EMBEDDING_DIMENSIONS']} dimensions")
    say(f"           (the tables are built for {values['EMBEDDING_DIMENSIONS']} now; another "
        "embedding model later means an empty database)")
    for note in notes:
        say(f"           {note}")
    return db


# ---- its database -----------------------------------------------------------------


def container(name: str) -> dict[str, Any] | None:
    """``podman inspect`` of a container, or None when there is none."""
    done = run(["podman", "container", "inspect", name])
    if done.returncode != 0:
        return None
    try:
        return json.loads(done.stdout)[0]
    except (ValueError, IndexError):
        return None


def volume_of(found: dict[str, Any]) -> str | None:
    for mount in found.get("Mounts") or []:
        if mount.get("Destination") == "/var/lib/postgresql/data" and mount.get("Name"):
            return mount["Name"]
    return None


def listening(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def db_ready(name: str, db: Database, wait: float = READY) -> bool:
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if run(["podman", "exec", name, "pg_isready", "-U", db.user, "-d", db.name]
               ).returncode == 0:
            return True
        time.sleep(1)
    return False


def start_database(kosh: Smritikosh, db: Database, say: Callable[[str], None] | None = None,
                   ) -> Smritikosh:
    """The plain container, started (made first when there is none).
    Returns the settings with the volume it really uses."""
    say = say or (lambda _line: None)
    found = container(kosh.database)
    if found is None:
        if listening(kosh.db_port):
            raise SetupError(f"something else is listening on port {kosh.db_port}: "
                             "change smritikosh.db_port in sarathi.toml")
        done = run(["podman", "run", "-d", "--name", kosh.database,
                    "-e", f"POSTGRES_USER={db.user}", "-e", f"POSTGRES_PASSWORD={db.password}",
                    "-e", f"POSTGRES_DB={db.name}",
                    "-p", f"127.0.0.1:{kosh.db_port}:5432",
                    "-v", f"{kosh.volume}:/var/lib/postgresql/data:Z", DB_IMAGE])
        if done.returncode != 0:
            raise SetupError(f"could not start the database: {done.stderr.strip()}")
        say(f"database   started {kosh.database} ({DB_IMAGE}, volume {kosh.volume})")
    else:
        kosh = replace(kosh, volume=volume_of(found) or kosh.volume)
        if not (found.get("State") or {}).get("Running"):
            done = run(["podman", "start", kosh.database])
            if done.returncode != 0:
                raise SetupError(f"could not start {kosh.database}: {done.stderr.strip()} "
                                 f"(is something else on port {kosh.db_port}?)")
            say(f"database   started {kosh.database} (yours, volume {kosh.volume})")
        else:
            say(f"database   {kosh.database} already running (volume {kosh.volume})")
    if not db_ready(kosh.database, db):
        raise SetupError(f"{kosh.database} did not become ready: `podman logs "
                         f"{kosh.database}`")
    return kosh


def stop_database(kosh: Smritikosh) -> bool:
    """The plain container stopped, so the podman road's unit can use its
    volume (two servers on one data folder would ruin it). True if it ran."""
    found = container(kosh.database)
    if found is None or not (found.get("State") or {}).get("Running"):
        return False
    run(["podman", "stop", kosh.database])
    return True


def opens(checkout: Path, found: dict[str, Any]) -> bool:
    """Whether this checkout's .env holds the database container's own
    user and password: then it is the setup that made it."""
    url = read_dotenv(checkout / ".env").get("POSTGRES_URL")
    if not url:
        return False
    env = dict(item.split("=", 1) for item in (found.get("Config") or {}).get("Env") or []
               if "=" in item)
    try:
        db = Database.parse(url)
    except SetupError:
        return False
    return (db.user, db.password) == (env.get("POSTGRES_USER", "postgres"),
                                      env.get("POSTGRES_PASSWORD"))


def checkout_for_database(found: dict[str, Any]) -> Path | None:
    """The checkout that made a database already here, looked for where a
    person keeps one: beside the others, the folder above them, ~/src,
    home. FOUND BY ITS PASSWORD, never by its name alone."""
    root = beside_dir()
    places = [root, root.parent] if root is not None else []
    places += [Path.home() / "src", Path.home() / "Documents", Path.home()]
    for place in places:
        candidate = place / "smritikosh"
        if (candidate / "pyproject.toml").is_file() and opens(candidate, found):
            return candidate
    return None


def stranger_database(kosh: Smritikosh, found: dict[str, Any],
                      checkout: Path | None) -> str:
    """Why a database that is already here can't be set up afresh, and
    the ways on."""
    where = f"{checkout}/.env" if checkout else "no checkout of Smritikosh found"
    return (f"a Smritikosh database is already here ({kosh.database}, volume "
            f"{volume_of(found) or '?'}), made with another setup's .env, and {where}. "
            "A new .env would not open it (another password, another JWT_SECRET). "
            "Point Sarathi at the checkout that made it: SARATHI_SMRITIKOSH="
            "/path/to/smritikosh/.venv/bin/smritikosh-mcp sarathi smritikosh -- or copy "
            "that checkout's .env here, or set smritikosh.database (and db_port) in "
            "sarathi.toml to start a separate one")


def migrate(checkout: Path, say: Callable[[str], None]) -> None:
    done = run([str(program(checkout, "alembic")), "upgrade", "head"], cwd=checkout)
    if done.returncode != 0:
        said = (done.stderr or done.stdout).strip()
        hint = (" -- the database has no pgvector: it must come from the pgvector "
                "image" if "vector" in said else
                f" -- the password in {checkout / '.env'} (POSTGRES_URL) is not the "
                "database's: that .env came from another setup than the database "
                "did. Point Sarathi at the checkout that made the database "
                "(SARATHI_SMRITIKOSH=/path/.venv/bin/smritikosh-mcp), or put its "
                "POSTGRES_URL and JWT_SECRET here" if "password authentication" in said
                else "")
        raise SetupError(f"building its tables failed{hint}:\n{said[-600:]}")
    ran = [line for line in (done.stderr + done.stdout).splitlines()
           if "Running upgrade" in line]
    say(f"tables     {len(ran)} step(s) run" if ran else "tables     up to date")


# ---- its API ----------------------------------------------------------------------


class Api:
    """Smritikosh's documented API: health, logins, accounts and keys."""

    def __init__(self, url: str, timeout: float = 15.0) -> None:
        self.url = url.rstrip("/")
        self.timeout = timeout

    def call(self, method: str, path: str, body: dict | None = None,
             token: str | None = None, query: dict | None = None) -> tuple[int, Any]:
        q = ("?" + urllib.parse.urlencode(query, doseq=True)) if query else ""
        request = urllib.request.Request(
            f"{self.url}{path}{q}", method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json",
                     **({"Authorization": f"Bearer {token}"} if token else {})})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as answer:
                return answer.status, json.loads(answer.read() or b"null")
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read() or b"null")
            except ValueError:
                return exc.code, None
        except (OSError, ValueError) as exc:
            return 0, {"detail": str(getattr(exc, "reason", exc))}

    def alive(self) -> bool:
        """Whether Smritikosh answers here -- its own name, from a page that
        asks nothing else. /health can take half a minute: it waits on every
        store its .env names, MongoDB included, running or not."""
        code, said = self.call("GET", "/openapi.json")
        return code == 200 and isinstance(said, dict) and \
            (said.get("info") or {}).get("title") == "Smritikosh"

    def health(self) -> dict | None:
        """Its /health, when the thing answering is Smritikosh and says in time."""
        code, said = self.call("GET", "/health")
        return said if code == 200 and isinstance(said, dict) and "postgres" in said \
            else None

    def login(self, user: str, password: str) -> str | None:
        code, said = self.call("POST", "/auth/token",
                               {"username": user, "password": password})
        return said.get("access_token") if code == 200 and isinstance(said, dict) else None

    def register(self, token: str | None, user: str, password: str, role: str = "user",
                 ) -> int:
        code, _ = self.call("POST", "/auth/register",
                            {"username": user, "password": password, "role": role,
                             "app_ids": ["default"]}, token=token)
        return code

    def mint(self, token: str, name: str) -> str:
        code, said = self.call("POST", "/keys", {"name": name, "app_ids": ["default"]},
                               token=token)
        if code != 201 or not isinstance(said, dict) or not said.get("key"):
            raise SetupError(f"Smritikosh would not make a key ({code}): {said}")
        return said["key"]

    def memories(self, key: str, user: str, limit: int = COUNT_LIMIT) -> int | None:
        """How many memories ``user`` has, read with their key; None when
        the key doesn't open them."""
        code, said = self.call("GET", f"/memory/{urllib.parse.quote(user)}", token=key,
                               query={"app_ids": ["default"], "limit": limit})
        if code != 200 or not isinstance(said, dict):
            return None
        return len(said.get("events") or [])


@contextmanager
def serving(checkout: Path, kosh: Smritikosh, *, bootstrap: bool,
            say: Callable[[str], None]):
    """An Api to call: the one already answering on its port, or one
    started here for these steps and stopped after them. ``bootstrap``
    starts it able to make its first admin without a login -- which only
    a server started here can be."""
    api = Api(kosh.url)
    if api.alive():
        if bootstrap:
            raise SetupError(f"Smritikosh is already running at {kosh.url}, and making "
                             "its first admin needs it started fresh: stop it "
                             "(`sarathi down`, or wherever you started it), then run "
                             "this again")
        yield api
        return
    if listening(kosh.port):
        raise SetupError(f"something that isn't Smritikosh is on port {kosh.port}: "
                         "change smritikosh.port in sarathi.toml")
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    env["BOOTSTRAP_ADMIN"] = "1" if bootstrap else "0"
    log = state_dir() / "logs" / "smritikosh-setup.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as out:
        proc = subprocess.Popen([str(program(checkout, "uvicorn")), "smritikosh.api.main:app",
                                 "--host", "127.0.0.1", "--port", str(kosh.port)],
                                cwd=checkout, env=env, stdin=subprocess.DEVNULL,
                                stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True)
    try:
        deadline = time.monotonic() + READY
        while not api.alive():
            if proc.poll() is not None or time.monotonic() > deadline:
                raise SetupError(f"Smritikosh's server didn't start; its log: {log}")
            time.sleep(0.5)
        say(f"server     started for these steps at {kosh.url}"
            + (" (able to make its first admin)" if bootstrap else ""))
        yield api
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---- accounts ---------------------------------------------------------------------


def owner_name() -> str:
    """Your name as Yantra files your memories: $YANTRA_USER, else the login."""
    return os.environ.get("YANTRA_USER", "").strip() or getpass.getuser()


def keys_elsewhere() -> list[tuple[str, str]]:
    """(where, key) for a SMRITIKOSH_API_KEY in Yantra's .env: the
    checkout's, and the folder `up` starts Yantra in."""
    out = []
    hit = locate(next(s for s in SIBLINGS if s.name == "yantra"))
    places = [state_dir() / "work" / ".env"]
    if hit is not None:
        found = Path(hit[0]).resolve()
        if found.parent.name == "bin":
            places.insert(0, found.parents[2] / ".env")
    for path in places:
        key = read_dotenv(path).get(KEY)
        if key:
            out.append((str(path), key))
    return out


def actors(config: Config) -> list[str]:
    """The ids in Dvara's actors file, or none with Dvara off."""
    door = config.door
    if door is None:
        return []
    try:
        data = tomllib.loads(door.path("actors").read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return []
    table = data.get("actor")
    return sorted(table) if isinstance(table, dict) else []


def people_path(config: Config) -> Path | None:
    return config.door.path("state") / PEOPLE_FILE if config.door is not None else None


def read_people(config: Config) -> dict[str, dict[str, str]]:
    path = people_path(config)
    try:
        raw = json.loads(path.read_text()) if path is not None else {}
    except (OSError, ValueError):
        return {}
    table = raw.get("people") if isinstance(raw, dict) else None
    return {k: v for k, v in table.items() if isinstance(v, dict)} \
        if isinstance(table, dict) else {}


def write_people(config: Config, table: dict[str, dict[str, str]]) -> Path:
    path = people_path(config)
    assert path is not None
    write_private(path, json.dumps({"people": dict(sorted(table.items()))}, indent=2) + "\n")
    return path


class Accounts:
    """The admin, made or logged in to only when an account must be made."""

    def __init__(self, api: Api, say: Callable[[str], None],
                 ask_secret: Callable[[str], str], interactive: bool) -> None:
        self.api = api
        self.say = say
        self.ask_secret = ask_secret
        self.interactive = interactive
        self._token: str | None = None

    def admin(self) -> str:
        if self._token is not None:
            return self._token
        password = read_secrets().get(ADMIN_PASSWORD)
        if password is None:
            raise NeedsBootstrap
        token = self.api.login(ADMIN, password)
        if token is None:
            raise SetupError(f"the admin {ADMIN!r} would not log in with the password in "
                             "secrets.env")
        self._token = token
        return token

    def make(self, user: str, key_name: str, put_key: str) -> str:
        """A new account and its key. Its password is KEPT BEFORE THE
        ACCOUNT IS MADE (``passwords``), so a run stopped between the two
        can log in next time; an account Sarathi didn't make can only be
        logged in to with its password: asked for, once. ``put_key`` says
        where a key could go instead."""
        kept = passwords()
        password = kept.get(user) or secrets.token_urlsafe(24)
        if user not in kept:
            keep_password(user, password)
        code = self.api.register(self.admin(), user, password)
        if code == 409 and self.api.login(user, password) is None:
            if not self.interactive:
                raise SetupError(f"Smritikosh already has an account {user!r} and Sarathi "
                                 "doesn't know its password: run this in a terminal to "
                                 f"type it, or put its key in {put_key}")
            password = self.ask_secret(f"Smritikosh password for {user!r} (hidden): ")
        elif code not in (201, 409):
            raise SetupError(f"Smritikosh would not make the account {user!r} ({code})")
        # a new account can answer 201 a moment before it is saved: the
        # first login is tried for a few seconds, never the password guessed
        deadline = time.monotonic() + 5.0
        while (token := self.api.login(user, password)) is None \
                and code == 201 and time.monotonic() < deadline:
            time.sleep(0.25)
        if token is None:
            raise SetupError(f"could not log in to Smritikosh as {user!r}")
        return self.api.mint(token, key_name)


def passwords() -> dict[str, str]:
    """The passwords of the accounts Sarathi made, readable by you alone."""
    try:
        raw = json.loads((state_dir() / ACCOUNTS_FILE).read_text())
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in raw.items() if isinstance(v, str)} if isinstance(raw, dict) \
        else {}


def keep_password(user: str, password: str) -> None:
    write_private(state_dir() / ACCOUNTS_FILE,
                  json.dumps({**passwords(), user: password}, indent=2) + "\n")


class NeedsBootstrap(Exception):
    """No admin yet that Sarathi can log in as."""


def make_admin(api: Api, say: Callable[[str], None]) -> None:
    password = secrets.token_urlsafe(24)
    code = api.register(None, ADMIN, password, role="admin")
    if code == 409:
        raise SetupError(f"Smritikosh has an admin called {ADMIN!r} that Sarathi has no "
                         f"password for: put it in secrets.env as {ADMIN_PASSWORD}")
    if code != 201:
        raise SetupError(f"Smritikosh would not make its first admin ({code})")
    save_secret(ADMIN_PASSWORD, password)
    say(f"admin      made {ADMIN!r}; its password is in secrets.env")


def own_key(api: Api, accounts: Accounts, me: str, say: Callable[[str], None]) -> str:
    """Your key: secrets.env's, else Yantra's .env's -- each checked --
    else a new account and key."""
    held = read_secrets().get(KEY)
    tried = [("secrets.env", held)] if held else []
    tried += keys_elsewhere()
    for where, key in tried:
        if api.memories(key, me, 1) is not None:
            if where != "secrets.env":
                save_secret(KEY, key)
            say(f"you        {me!r}, with the key from {where}")
            return key
        say(f"you        the key in {where} doesn't open {me!r}'s memories: not used")
    key = accounts.make(me, "sarathi-yantra", f"secrets.env as {KEY}")
    save_secret(KEY, key)
    say(f"you        account {me!r} and its key (in secrets.env)")
    return key


def people_keys(config: Config, api: Api, accounts: Accounts, me: str, mine: str,
                say: Callable[[str], None]) -> None:
    """One account and key per person in Dvara's actors file; you as you."""
    ids = actors(config)
    if not ids:
        return
    assert config.door is not None
    table = read_people(config)
    made = []
    for actor in ids:
        entry = table.get(actor, {})
        if actor == config.door.owner:
            table[actor] = {"user": me, "key": mine}
            continue
        user = entry.get("user") or f"{PERSON_PREFIX}{actor}"
        if entry.get("key") and api.memories(entry["key"], user, 1) is not None:
            continue
        table[actor] = {"user": user, "key": accounts.make(
            user, f"dvara-{actor}", f"{people_path(config)} as people.{actor}.key")}
        made.append(actor)
    path = write_people(config, table)
    others = len(ids) - (config.door.owner in ids)
    say(f"dvara      {len(ids)} in the actors file: you as {me!r}"
        + (f", {others} with {'an account' if others == 1 else 'accounts'} of their own"
           if others else "")
        + (f" ({', '.join(made)} new)" if made else "") + f"; keys in {path}")


# ---- the command ------------------------------------------------------------------


def setup(config: Config, *, local: bool = False, say: Callable[[str], None] = print,
          ask_secret: Callable[[str], str] = getpass.getpass,
          interactive: bool | None = None) -> Config:
    """Every step, in order; the settings to write when they all worked."""
    from sarathi.first_run import ollama_models, ollama_root

    interactive = sys.stdin.isatty() if interactive is None else interactive
    if shutil.which("podman") is None:
        raise SetupError("Smritikosh's database runs in a container, and podman is not "
                         "installed")
    checkout, how = find_checkout(config)
    # A database already here was made by some setup's .env. A new .env
    # would hold another password and another JWT_SECRET (which may
    # encrypt its stored sign-ins), so that setup's checkout is found
    # first, never cloned around.
    existing = container(config.smritikosh.database)
    if existing is not None and (checkout is None or not opens(checkout, existing)):
        made = checkout_for_database(existing)
        if made is not None and how in ("", "beside"):
            checkout, how = made, f"its .env opens {config.smritikosh.database}"
        else:
            raise SetupError(stranger_database(config.smritikosh, existing, checkout))
    if checkout is None:
        checkout = clone(say)
        how = "cloned"
    say(f"checkout   {checkout}  ({how})")
    sync(checkout, say)

    road = replace(config, provider="ollama", model=None) if local else config
    pulled = ollama_models(ollama_root(road.base_url)) if road.provider == "ollama" else None

    def cloud_key() -> str | None:
        if not interactive:
            return None
        value = ask_secret("OPENAI_API_KEY, to turn memories into numbers "
                           "(hidden; Enter to stop): ").strip()
        if value:
            save_secret("OPENAI_API_KEY", value)
        return value or None

    db = settle_dotenv(road, checkout, say, pulled=pulled, cloud_key=cloud_key)
    kosh = replace(config.smritikosh, checkout=str(checkout), db_port=db.port)
    kosh = start_database(kosh, db, say)
    migrate(checkout, say)

    me = owner_name()
    said: set[str] = set()

    def once(line: str) -> None:       # the steps run again after an admin is made
        if line not in said:
            said.add(line)
            say(line)

    def steps(api: Api) -> None:
        accounts = Accounts(api, once, ask_secret, interactive)
        mine = own_key(api, accounts, me, once)
        people_keys(replace(config, smritikosh=kosh), api, accounts, me, mine, once)

    try:
        with serving(checkout, kosh, bootstrap=False, say=say) as api:
            steps(api)
    except NeedsBootstrap:
        with serving(checkout, kosh, bootstrap=True, say=say) as api:
            make_admin(api, say)
        with serving(checkout, kosh, bootstrap=False, say=say) as api:
            steps(api)
    if config.road == "podman":
        # the unit uses this volume from now on; never two servers on it
        stop_database(kosh)
    return replace(config, memory="smritikosh", smritikosh=kosh)


def run_command(args, config: Config) -> int:
    path = settings_path()
    if args.off:
        if config.memory == "local":
            print("memory: already the built-in file (local)")
            return 0
        path.write_text(render(replace(config, memory="local")))
        print("memory: back to the built-in file (local). Smritikosh keeps what it has;\n"
              "  `sarathi smritikosh` switches again. next: `sarathi up`")
        return 0
    try:
        done = setup(config, local=args.local)
    except SetupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    path.write_text(render(done))
    print(f"memory: smritikosh (in {path})")
    if config.memory != "smritikosh":
        print("  what the built-in file holds stays there: type `/memory copy local` on "
              "Yantra's page once to bring it across")
    print("next: `sarathi up`" + (" (rebuild first with `sarathi image`: the image needs "
                                  "Smritikosh in it)" if config.road == "podman" else ""))
    return 0


# ---- how it's doing ---------------------------------------------------------------


def health(config: Config) -> dict[str, Any]:
    """For ``sarathi status`` and the home page: up or down, what its
    /health says, and how many memories are yours."""
    kosh = config.smritikosh
    api = Api(kosh.url, timeout=3.0)
    up = api.alive()
    said = api.health() if up else None
    out: dict[str, Any] = {"on": config.remembers_in_smritikosh,
                           "set_up": kosh.checkout is not None, "url": kosh.url,
                           "up": up, "health": said, "memories": None}
    key = read_secrets().get(KEY)
    if up and key:
        out["memories"] = api.memories(key, owner_name())
    return out


def health_line(config: Config, seen: dict[str, Any] | None = None) -> str:
    """One line: where memories are kept, and how that is going."""
    if not config.remembers_in_smritikosh:
        tail = ("; `sarathi smritikosh` switches to Smritikosh"
                if config.smritikosh.checkout is None
                else "; Smritikosh is set up: `sarathi smritikosh` switches to it")
        return "memory: the built-in file (local)" + tail
    seen = seen or health(config)
    if not seen["up"]:
        return f"memory: smritikosh, NOT ANSWERING at {seen['url']} (`sarathi up`)"
    said = seen["health"]
    count = seen["memories"]
    many = ("?" if count is None else f"{count}+" if count >= COUNT_LIMIT else str(count))
    how = (f"postgres {said.get('postgres')}, {said.get('status')}" if said else
           "its /health is slow to say (MongoDB or Neo4j named in its .env, not running)")
    return (f"memory: smritikosh at {seen['url']} -- {how}; {many} remembered for "
            f"{owner_name()}")


# ---- what `up` hands each piece ---------------------------------------------------


def mcp_dir() -> Path:
    return state_dir() / "mcp"


def mcp_files(config: Config, *, command: str, url: str, suffix: str) -> tuple[Path, Path]:
    """Yantra's --mcp-config and Dvara's --memory, for one road. NO KEY
    IN EITHER: Yantra fills ``${SMRITIKOSH_API_KEY}`` from its own
    environment, and Dvara fills each person's from memory.json."""
    folder = mcp_dir()
    folder.mkdir(parents=True, exist_ok=True)
    yantra = folder / f"smritikosh-yantra{suffix}.json"
    door = folder / f"smritikosh-dvara{suffix}.json"
    for path, user, key in ((yantra, "${YANTRA_USER}", "${SMRITIKOSH_API_KEY}"),
                            (door, "${DVARA_MEMORY_USER}", "${DVARA_MEMORY_KEY}")):
        path.write_text(json.dumps({"servers": {"smritikosh": {
            "command": command,
            "env": {"SMRITIKOSH_API_KEY": key, "SMRITIKOSH_USER_ID": user,
                    "SMRITIKOSH_BASE_URL": url}}}}, indent=2) + "\n")
    return yantra, door


def yantra_env() -> dict[str, str]:
    """What tells Yantra to keep memories there, and whose."""
    env = {"YANTRA_MEMORY": "smritikosh", "YANTRA_USER": owner_name()}
    key = read_secrets().get(KEY)
    if key:
        env[KEY] = key
    return env


def container_dotenv(checkout: Path, *, db_host: str) -> dict[str, str]:
    """Smritikosh's .env as its container must read it: the database by
    its name on Sarathi's network, and Ollama on the host."""
    from sarathi.podman import from_container

    values = read_dotenv(checkout / ".env")
    values.pop("BOOTSTRAP_ADMIN", None)
    if values.get("POSTGRES_URL"):
        values["POSTGRES_URL"] = Database.parse(values["POSTGRES_URL"]).url(db_host, 5432)
    for key in ("LLM_BASE_URL", "EMBEDDING_BASE_URL", "LLM_FALLBACK_BASE_URL"):
        if values.get(key):
            values[key] = from_container(values[key])
    return values
