"""`sarathi smritikosh`: memories found by meaning, set up once, switched freely.

The biases these tests encode:

* THE BUILT-IN FILE UNLESS YOU SAID OTHERWISE. A new sarathi.toml says
  ``local``; Smritikosh is used only after it is set up, and ``--off``
  goes back with nothing deleted.
* WHAT IS THERE IS USED, NEVER REPLACED. An existing ``.env`` keeps its
  embedding size (the tables were built for it); a key you already have
  is checked and kept, and one that doesn't open your memories is not
  used.
* ONE PERSON'S KEY, ONE PERSON'S MEMORIES. Your key reaches Yantra
  alone; Dvara's people each get an account and key of their own, and
  you are you there too; no key is ever written into a file that can be
  pasted (the MCP configs carry only ``${...}``).

Smritikosh's API is a stand-in that remembers accounts and keys; podman
is a recorder.
"""

from __future__ import annotations

import json
import shlex
import stat
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from sarathi import config as settings_mod
from sarathi import podman, services, smritikosh
from sarathi.config import Config, ConfigError, Door, Pages, Smritikosh, parse, render
from sarathi.home import Home

SET_UP = Smritikosh(checkout="/opt/kosh", volume="pgdata")
ON = Config("ollama", "gemma4:12b", pages=Pages(on=False), memory="smritikosh",
            smritikosh=SET_UP)


# ---- the settings -----------------------------------------------------------------


def test_a_new_settings_file_remembers_in_the_built_in_file():
    fresh = parse(render(Config("ollama")))
    assert fresh.memory == "local" and not fresh.remembers_in_smritikosh
    assert 'via = "local"' in render(Config("ollama"))


def test_smritikosh_set_up_reads_back_as_written():
    assert parse(render(ON)) == ON


def test_switching_to_smritikosh_before_it_is_set_up_says_what_to_run():
    with pytest.raises(ConfigError, match="run `sarathi smritikosh`"):
        parse('[model]\nprovider = "ollama"\n[memory]\nvia = "smritikosh"\n')
    with pytest.raises(ConfigError, match="memory.via is one of local, smritikosh"):
        parse('[model]\nprovider = "ollama"\n[memory]\nvia = "elsewhere"\n')


def test_off_goes_back_to_the_built_in_file_and_keeps_the_set_up(world):
    path = settings_mod.settings_path()
    path.parent.mkdir(parents=True)
    path.write_text(render(ON))
    args = type("A", (), {"off": True, "local": False})()
    assert smritikosh.run_command(args, ON) == 0
    back = settings_mod.load()
    assert back.memory == "local" and back.smritikosh == SET_UP


# ---- its .env ---------------------------------------------------------------------


def test_a_value_replaces_its_commented_example_and_notes_are_not_values(tmp_path):
    text = "# EMBEDDING_DIMENSIONS=1536   # must match\nLLM_PROVIDER=claude\n"
    filled = smritikosh.fill_dotenv(text, {"EMBEDDING_DIMENSIONS": "768", "JWT_SECRET": "s"})
    assert filled.splitlines()[0] == "EMBEDDING_DIMENSIONS=768"
    assert filled.rstrip().endswith("JWT_SECRET=s")
    (tmp_path / ".env").write_text("EMBEDDING_MODEL=nomic-embed-text    # ollama\n"
                                   'POSTGRES_URL="postgresql+asyncpg://u:p@h:5433/d"\n')
    read = smritikosh.read_dotenv(tmp_path / ".env")
    assert read["EMBEDDING_MODEL"] == "nomic-embed-text"
    assert smritikosh.Database.parse(read["POSTGRES_URL"]).port == 5433


def test_an_existing_secret_is_never_replaced_even_a_short_one(world, tmp_path):
    env = tmp_path / ".env"
    env.write_text("JWT_SECRET=short-but-theirs\nPOSTGRES_URL=postgresql+asyncpg://"
                   "smritikosh:pw@localhost:5432/smritikosh\n")
    before = env.read_text()
    smritikosh.settle_dotenv(Config("ollama"), tmp_path, print, pulled=[],
                             cloud_key=lambda: None)
    assert env.read_text() == before


def test_an_existing_env_keeps_its_size_and_gains_only_a_secret(world, tmp_path):
    env = tmp_path / ".env"
    env.write_text("EMBEDDING_PROVIDER=openai\nEMBEDDING_DIMENSIONS=1536\n"
                   "POSTGRES_URL=postgresql+asyncpg://smritikosh:pw@localhost:5432/smritikosh\n")
    said: list[str] = []
    db = smritikosh.settle_dotenv(Config("ollama"), tmp_path, said.append, pulled=[],
                                  cloud_key=lambda: None)
    after = smritikosh.read_dotenv(env)
    assert after["EMBEDDING_DIMENSIONS"] == "1536" and len(after["JWT_SECRET"]) >= 32
    assert db.password == "pw" and "kept" in said[0]


def test_a_new_env_on_the_local_road_is_built_for_768_and_says_so(world, tmp_path):
    said: list[str] = []
    smritikosh.settle_dotenv(Config("ollama"), tmp_path, said.append,
                             pulled=["qwen3.8:latest"], cloud_key=lambda: None)
    env = smritikosh.read_dotenv(tmp_path / ".env")
    assert (env["EMBEDDING_MODEL"], env["EMBEDDING_DIMENSIONS"]) == ("nomic-embed-text", "768")
    assert stat.S_IMODE((tmp_path / ".env").stat().st_mode) == 0o600
    assert any("another embedding model later means an empty database" in s for s in said)
    assert any("`ollama pull nomic-embed-text`" in s for s in said)


def test_the_cloud_road_without_an_openai_key_stops_and_names_the_local_road(world, tmp_path):
    with pytest.raises(smritikosh.SetupError, match="OPENAI_API_KEY"):
        smritikosh.settle_dotenv(Config("anthropic"), tmp_path, print, pulled=None,
                                 cloud_key=lambda: None)
    assert not (tmp_path / ".env").exists()


# ---- accounts and keys ------------------------------------------------------------


class FakeApi:
    """Accounts, logins and keys, as Smritikosh's API answers them."""

    def __init__(self):
        self.accounts: dict[str, str] = {}
        self.keys: dict[str, str] = {}          # key -> account

    def register(self, token, user, password, role="user"):
        assert token == "admin-token"
        if user in self.accounts:
            return 409
        self.accounts[user] = password
        return 201

    def login(self, user, password):
        return f"tok-{user}" if self.accounts.get(user) == password else None

    def mint(self, token, name):
        key = f"sk-{token[4:]}-{len(self.keys)}"
        self.keys[key] = token[4:]
        return key

    def memories(self, key, user, limit=500):
        return 3 if self.keys.get(key) == user else None


class Admin(smritikosh.Accounts):
    def admin(self):
        return "admin-token"


def accounts(api) -> smritikosh.Accounts:
    return Admin(api, print, lambda q: pytest.fail("asked"), False)


def test_a_key_in_yantras_env_is_checked_kept_and_moved_to_secrets(world, monkeypatch):
    api = FakeApi()
    api.keys["sk-old"] = "asha"
    monkeypatch.setattr(smritikosh, "keys_elsewhere",
                        lambda: [("yantra/.env", "sk-wrong"), ("yantra/.env", "sk-old")])
    said: list[str] = []
    assert smritikosh.own_key(api, accounts(api), "asha", said.append) == "sk-old"
    assert settings_mod.read_secrets()[smritikosh.KEY] == "sk-old"
    assert "doesn't open 'asha'" in said[0] and api.accounts == {}


def test_with_no_key_anywhere_you_get_an_account_and_a_key_of_your_own(world, monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(smritikosh, "keys_elsewhere", lambda: [])
    key = smritikosh.own_key(api, accounts(api), "asha", print)
    assert api.keys[key] == "asha" and "asha" in api.accounts


def test_each_person_gets_their_own_account_and_you_are_you(world, tmp_path):
    actors = tmp_path / "actors.toml"
    actors.write_text("[actor.owner]\n[actor.priya]\n[actor.ravi]\n")
    door = Door(actors=str(actors), state=str(tmp_path / "state"))
    config = replace(ON, door=door)
    api = FakeApi()
    api.accounts["dvara-ravi"] = "x"
    api.keys["sk-ravi"] = "dvara-ravi"
    smritikosh.write_people(config, {"ravi": {"user": "dvara-ravi", "key": "sk-ravi"}})
    smritikosh.people_keys(config, api, accounts(api), "asha", "sk-mine", print)
    people = smritikosh.read_people(config)
    assert people["owner"] == {"user": "asha", "key": "sk-mine"}
    assert people["ravi"]["key"] == "sk-ravi"                       # kept: it still opens
    assert api.keys[people["priya"]["key"]] == "dvara-priya"       # theirs, not yours
    path = smritikosh.people_path(config)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_an_account_already_there_without_its_password_is_not_guessed_at(world):
    api = FakeApi()
    api.accounts["asha"] = "theirs"
    with pytest.raises(smritikosh.SetupError, match="doesn't know its password"):
        accounts(api).make("asha", "k", "secrets.env")


# ---- what `up` hands each piece ---------------------------------------------------


@pytest.fixture
def kosh(world, tmp_path):
    checkout = tmp_path / "kosh"
    for name in ("uvicorn", "smritikosh-mcp", "alembic"):
        (checkout / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
        (checkout / ".venv" / "bin" / name).write_text("")
    (checkout / ".env").write_text(
        "POSTGRES_URL=postgresql+asyncpg://smritikosh:pw@localhost:5432/smritikosh\n"
        "EMBEDDING_BASE_URL=http://localhost:11434\n")
    settings_mod.save_secret(smritikosh.KEY, "sk-mine")
    settings_mod.save_secret("OPENAI_API_KEY", "sk-openai")
    return replace(ON, smritikosh=replace(SET_UP, checkout=str(checkout)))


def found(world):
    from conftest import program
    from sarathi.siblings import Found, SIBLINGS

    bin_dir = world / "bin"
    return {s.name: Found(s, str(program(bin_dir, s.name)) if s.name in
                          ("yantra", "setu", "samay", "dvara") else None)
            for s in SIBLINGS}


def test_on_the_process_road_smritikosh_starts_first_and_yantra_is_pointed_at_it(world,
                                                                                kosh):
    planned, _ = services.plan(kosh, found(world))
    assert planned[0].name == "smritikosh"
    assert planned[0].cwd == Path(kosh.smritikosh.checkout)      # its .env is there
    page = next(s for s in planned if s.name == "yantra")
    config_file = Path(page.argv[page.argv.index("--mcp-config") + 1])
    assert page.env["YANTRA_MEMORY"] == "smritikosh"
    assert page.env[smritikosh.KEY] == "sk-mine"
    server = json.loads(config_file.read_text())["servers"]["smritikosh"]
    assert server["env"]["SMRITIKOSH_API_KEY"] == "${SMRITIKOSH_API_KEY}"
    assert "sk-mine" not in config_file.read_text()


def test_on_the_process_road_its_tables_are_brought_up_before_it_serves(world, kosh,
                                                                      monkeypatch):
    # A pulled checkout can name a column the database has not got yet;
    # every query would fail on it, so the upgrade runs first, every time.
    order: list[str] = []
    monkeypatch.setattr(smritikosh, "start_database",
                        lambda kosh, db, say: order.append("database"))
    monkeypatch.setattr(smritikosh, "start_extras", lambda kosh: [])

    def migrate(checkout, say):
        order.append("tables")
        say("tables     1 step(s) run")
    monkeypatch.setattr(smritikosh, "migrate", migrate)
    planned, _ = services.plan(kosh, found(world))

    said = planned[0].prepare()

    assert order == ["database", "tables"]
    assert said == "tables     1 step(s) run"


def test_up_to_date_tables_say_nothing_on_every_up(world, kosh, monkeypatch):
    monkeypatch.setattr(smritikosh, "start_database", lambda kosh, db, say: None)
    monkeypatch.setattr(smritikosh, "start_extras", lambda kosh: [])
    monkeypatch.setattr(smritikosh, "migrate",
                        lambda checkout, say: say("tables     up to date"))
    planned, _ = services.plan(kosh, found(world))

    assert planned[0].prepare() is None


def test_your_key_reaches_what_runs_as_you_and_no_other_piece(world, kosh):
    planned, _ = services.plan(kosh, found(world))
    for service in planned:
        if service.name not in ("yantra", "samay"):
            assert smritikosh.KEY not in service.env, service.name
    assert "OPENAI_API_KEY" in services.model_env(kosh)     # an ordinary key still goes


def test_a_run_samay_starts_remembers_where_yantras_page_does(world, kosh):
    planned, _ = services.plan(kosh, found(world))
    by = {s.name: s for s in planned}
    page = by["yantra"].argv
    server = page[page.index("--mcp-config") + 1]
    run = shlex.split(by["samay"].env["SAMAY_YANTRA"])
    assert run[1:] == ["--mcp-config", server]
    assert by["samay"].env["YANTRA_MEMORY"] == "smritikosh"
    assert by["samay"].env["YANTRA_USER"] == by["yantra"].env["YANTRA_USER"]
    assert by["samay"].env[smritikosh.KEY] == "sk-mine"
    local, _ = services.plan(replace(kosh, memory="local"), found(world))
    samay = next(s for s in local if s.name == "samay")
    assert "--mcp-config" not in samay.env["SAMAY_YANTRA"]
    assert "YANTRA_MEMORY" not in samay.env and smritikosh.KEY not in samay.env


def test_dvara_reads_each_persons_key_from_its_own_file(world, kosh, tmp_path):
    from conftest import program
    door = Door(actors=str(program(tmp_path, "actors.toml")), root=str(tmp_path),
                state=str(tmp_path / "state"))
    settings_mod.save_secret("DVARA_TOKEN", "t")
    planned, notes = services.plan(replace(kosh, door=door), found(world))
    dvara = next(s for s in planned if s.name == "dvara")
    file = Path(dvara.argv[dvara.argv.index("--memory") + 1])
    env = json.loads(file.read_text())["servers"]["smritikosh"]["env"]
    assert env == {"SMRITIKOSH_API_KEY": "${DVARA_MEMORY_KEY}",
                   "SMRITIKOSH_USER_ID": "${DVARA_MEMORY_USER}",
                   "SMRITIKOSH_BASE_URL": "http://127.0.0.1:8080"}
    assert smritikosh.KEY not in dvara.env


def test_with_memory_local_nothing_of_smritikosh_is_started_or_handed(world, kosh):
    planned, _ = services.plan(replace(kosh, memory="local"), found(world))
    assert "smritikosh" not in [s.name for s in planned]
    page = next(s for s in planned if s.name == "yantra")
    assert "--mcp-config" not in page.argv and "YANTRA_MEMORY" not in page.env


# ---- the podman road --------------------------------------------------------------


@pytest.fixture
def host(world, monkeypatch):
    monkeypatch.setenv("HOME", str(world / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(world / "home" / ".config"))
    monkeypatch.setattr(podman, "run", lambda argv, **kw: subprocess.CompletedProcess(
        argv, 0, "", ""))


def test_on_podman_the_database_and_server_are_units_and_mount_nothing_else(host, kosh):
    road = replace(kosh, road="podman")
    units = podman.units(road)
    db, api = units["sarathi-smritikosh-db.container"], units["sarathi-smritikosh.container"]
    assert "Volume=pgdata:/var/lib/postgresql/data:Z" in db
    assert "PublishPort=127.0.0.1:5432:5432" in db
    assert "Volume=" not in api and "UserNS" not in api
    assert "After=sarathi-smritikosh.service" in units["sarathi-yantra.container"]
    assert "--mcp-config" in units["sarathi-yantra.container"]
    assert "sk-mine" not in "".join(units.values())


def test_on_podman_its_settings_name_the_database_container_and_the_host(host, kosh):
    held = podman.unit_secrets(replace(kosh, road="podman"))
    server = held["sarathi-smritikosh"]
    assert server["POSTGRES_URL"].endswith("@sarathi-smritikosh-db:5432/smritikosh")
    assert server["EMBEDDING_BASE_URL"] == "http://host.containers.internal:11434"
    assert held["sarathi-yantra"][smritikosh.KEY] == "sk-mine"
    # Samay's runs are yours too; Dvara's are each person's own (memory.json)
    assert held["sarathi-samay"][smritikosh.KEY] == "sk-mine"
    assert smritikosh.KEY not in held.get("sarathi-dvara", {})


def test_on_podman_samays_runs_start_with_your_memory(host, kosh):
    units = podman.units(replace(kosh, road="podman"))
    samay = units["sarathi-samay.container"]
    assert "After=sarathi-smritikosh.service" in samay
    assert "Environment=YANTRA_MEMORY=smritikosh" in samay
    assert "--mcp-config" in samay and "smritikosh-yantra-podman.json" in samay
    assert "sk-mine" not in samay


def test_off_on_podman_writes_no_smritikosh_unit(host, kosh):
    assert not any("smritikosh" in name
                   for name in podman.units(replace(kosh, road="podman", memory="local")))


# ---- the home page's switch -------------------------------------------------------


def test_the_switch_writes_the_setting_and_starts_again(world):
    path = settings_mod.settings_path()
    path.parent.mkdir(parents=True)
    path.write_text(render(replace(ON, memory="local")))
    restarted = []
    home = Home(settings_mod.load(), dict, memory=lambda c: {"via": c.memory},
                restart=lambda: restarted.append(1))
    code, said = home.switch("smritikosh")
    assert code == 200 and "Nothing is deleted" in said and restarted == [1]
    assert settings_mod.load().memory == "smritikosh"
    assert home.memory() == {"via": "smritikosh"}


def test_the_switch_wont_turn_on_what_was_never_set_up(world):
    path = settings_mod.settings_path()
    path.parent.mkdir(parents=True)
    path.write_text(render(Config("ollama")))
    home = Home(settings_mod.load(), dict, memory=lambda c: {},
                restart=lambda: pytest.fail("restarted"))
    code, said = home.switch("smritikosh")
    assert code == 409 and "`sarathi smritikosh`" in said
    assert home.switch("nowhere")[0] == 400


def test_a_run_stopped_after_making_an_account_logs_in_to_it_next_time(world):
    api = FakeApi()
    real_mint = api.mint
    api.mint = lambda token, name: (_ for _ in ()).throw(smritikosh.SetupError("stopped"))
    with pytest.raises(smritikosh.SetupError):
        accounts(api).make("dvara-priya", "k", "memory.json")
    assert "dvara-priya" in api.accounts           # made, and its key never minted
    api.mint = real_mint
    key = accounts(api).make("dvara-priya", "k", "memory.json")
    assert api.keys[key] == "dvara-priya"
    path = settings_mod.state_dir() / smritikosh.ACCOUNTS_FILE
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


# ---- a database already here --------------------------------------------------------

DB = {"Config": {"Env": ["POSTGRES_USER=smritikosh", "POSTGRES_PASSWORD=the-old-one"]},
      "Mounts": [{"Destination": "/var/lib/postgresql/data", "Name": "pgdata"}],
      "State": {"Running": True}}


def a_checkout(where: Path, password: str | None) -> Path:
    where.mkdir(parents=True)
    (where / "pyproject.toml").write_text("")
    if password is not None:
        (where / ".env").write_text(f"POSTGRES_URL=postgresql+asyncpg://smritikosh:"
                                    f"{password}@localhost:5432/smritikosh\n")
    return where


@pytest.fixture
def your_machine(world, monkeypatch):
    """A database made months ago by a checkout kept in the folder above
    the others; the one beside them is a stray clone with a new .env."""
    monkeypatch.setenv("HOME", str(world / "home"))
    monkeypatch.setattr(smritikosh, "container", lambda name: DB)
    real_which = smritikosh.shutil.which
    monkeypatch.setattr(smritikosh.shutil, "which", lambda name, **kw: (
        "/usr/bin/podman" if name == "podman" else real_which(name, **kw)))
    above = a_checkout(world / "smritikosh", "the-old-one")
    stray = a_checkout(world / "checkouts" / "smritikosh", "a-new-random-one")
    seen = {}

    def stop(checkout, say):        # the step after the checkout is chosen
        seen["checkout"] = checkout
        raise smritikosh.SetupError("stop here")
    monkeypatch.setattr(smritikosh, "sync", stop)
    return above, stray, seen


def test_the_checkout_whose_env_opens_the_database_is_used_not_a_clone(your_machine):
    above, stray, seen = your_machine
    with pytest.raises(smritikosh.SetupError, match="stop here"):
        smritikosh.setup(Config("ollama"), say=print, interactive=False)
    assert seen["checkout"] == above


def test_with_no_checkout_that_opens_it_nothing_is_cloned_or_written(your_machine,
                                                                      monkeypatch):
    above, stray, seen = your_machine
    (above / ".env").unlink()
    monkeypatch.setattr(smritikosh, "clone", lambda say: pytest.fail("cloned"))
    with pytest.raises(smritikosh.SetupError, match="SARATHI_SMRITIKOSH"):
        smritikosh.setup(Config("ollama"), say=print, interactive=False)
    assert "checkout" not in seen


def test_a_checkout_you_named_that_doesnt_open_it_is_refused_not_overridden(
        your_machine, monkeypatch):
    above, stray, seen = your_machine
    named = replace(ON, smritikosh=replace(SET_UP, checkout=str(stray)))
    with pytest.raises(smritikosh.SetupError, match="another password, another JWT_SECRET"):
        smritikosh.setup(named, say=print, interactive=False)
    assert "checkout" not in seen


# ---- Neo4j, MongoDB and Redis (--full) ----------------------------------------------

YOURS = {
    "neo4j_container": {
        "Name": "neo4j_container", "Image": "sha256:n30",
        "ImageName": "docker.io/library/neo4j:latest",
        "Config": {"Env": ["NEO4J_AUTH=neo4j/kept-secret", "PATH=/usr/bin",
                           "NEO4J_HOME=/var/lib/neo4j"]},
        "Mounts": [{"Type": "bind", "Source": "/home/you/neo4j/data", "Destination": "/data"}],
        "HostConfig": {"PortBindings": {"7687/tcp": [{"HostIp": "", "HostPort": "7687"}],
                                        "7474/tcp": [{"HostIp": "", "HostPort": "7474"}]}},
        "State": {"Running": False}},
    "mongodb": {
        "Name": "mongodb", "Image": "sha256:m0", "ImageName": "docker.io/library/mongo:latest",
        "Config": {"Env": []},
        "Mounts": [{"Type": "volume", "Name": "mongodb", "Destination": "/data/db"}],
        "HostConfig": {"PortBindings": {"27017/tcp": [{"HostIp": "", "HostPort": "27017"}]}},
        "State": {"Running": True}},
}


@pytest.fixture
def stores(world, monkeypatch, tmp_path):
    """Your Neo4j and MongoDB containers; no Redis yet."""
    ran: list[list[str]] = []
    up = {7687, 27017}                      # Redis listens once it is made

    def run(argv, **kw):
        ran.append(argv)
        if argv[:3] == ["podman", "run", "-d"]:
            up.add(6379)
        out = "\n".join(YOURS) if argv[:3] == ["podman", "ps", "-a"] else ""
        if argv[:3] == ["podman", "image", "inspect"]:
            out = "PATH=/usr/bin\nNEO4J_HOME=/var/lib/neo4j\n"
        return subprocess.CompletedProcess(argv, 0, out, "")
    monkeypatch.setattr(smritikosh, "run", run)
    monkeypatch.setattr(podman, "run", run)
    monkeypatch.setattr(smritikosh, "container", lambda name: YOURS.get(name))
    monkeypatch.setattr(smritikosh, "listening", lambda port, host="127.0.0.1": port in up)
    checkout = tmp_path / "kosh"
    checkout.mkdir()
    (checkout / ".env").write_text("NEO4J_URI=bolt://localhost:7687\nNEO4J_USER=neo4j\n"
                                   "NEO4J_PASSWORD=kept-secret\n"
                                   "MONGODB_URL=mongodb://localhost:27017\n")
    return checkout, ran


def test_full_uses_your_containers_by_their_address_and_adds_only_what_is_missing(stores):
    checkout, ran = stores
    said: list[str] = []
    kosh = smritikosh.settle_extras(Smritikosh(checkout=str(checkout)), checkout,
                                    said.append, wait=0)
    assert (kosh.full, kosh.neo4j, kosh.mongodb) == (True, "neo4j_container", "mongodb")
    env = smritikosh.read_dotenv(checkout / ".env")
    assert env["NEO4J_PASSWORD"] == "kept-secret"                 # yours, untouched
    assert env["REDIS_URL"] == "redis://localhost:6379/0"         # the one it lacked
    assert ["podman", "start", "neo4j_container"] in ran
    made = next(a for a in ran if a[:3] == ["podman", "run", "-d"])
    assert "127.0.0.1:6379:6379" in made and made[-1].endswith("redis:7-alpine")
    assert not any(a[:3] == ["podman", "run", "-d"] and "mongo" in a[-1] for a in ran)


def test_a_unit_copies_its_container_by_image_id_never_a_tag(host, stores):
    checkout, _ = stores
    config = replace(ON, road="podman", smritikosh=replace(
        SET_UP, checkout=str(checkout), full=True, neo4j="neo4j_container",
        mongodb="mongodb", redis="nowhere"))
    units = podman.units(config)
    neo = units["sarathi-smritikosh-neo4j.container"]
    assert "Image=sha256:n30" in neo and "latest" not in neo
    assert "Volume=/home/you/neo4j/data:/data" in neo
    assert "PublishPort=127.0.0.1:7687:7687" in neo
    assert "Volume=mongodb:/data/db" in units["sarathi-smritikosh-mongodb.container"]
    assert "sarathi-smritikosh-redis.container" not in units      # no container to copy
    kept = podman.env_file("sarathi-smritikosh-neo4j").read_text()
    assert "NEO4J_AUTH=neo4j/kept-secret" in kept and "PATH=" not in kept
    api = units["sarathi-smritikosh.container"]
    assert "After=sarathi-smritikosh-neo4j.service" in api


def test_inside_containers_each_store_is_reached_by_its_unit_or_left_out(tmp_path):
    (tmp_path / ".env").write_text("NEO4J_URI=bolt://localhost:7687\n"
                                   "MONGODB_URL=mongodb://localhost:27017\n")
    full = smritikosh.container_dotenv(tmp_path, db_host="db",
                                       extras={"neo4j": "sarathi-smritikosh-neo4j"})
    assert full["NEO4J_URI"] == "bolt://sarathi-smritikosh-neo4j:7687"
    assert "MONGODB_URL" not in full          # not run here: nothing waits on it


def test_full_reads_back_and_no_full_turns_it_off(world):
    config = replace(ON, smritikosh=replace(SET_UP, full=True, neo4j="neo4j_container"))
    assert parse(render(config)) == config
    assert parse(render(ON)).smritikosh.extras() == {}
    from sarathi.cli import build_parser
    with pytest.raises(SystemExit):
        build_parser().parse_args(["smritikosh", "--full", "--no-full"])


# ---- Smritikosh's own dashboard ----------------------------------------------------


def a_ui(checkout: Path, built: bool) -> Path:
    ui = checkout / "ui"
    (ui / ".next").mkdir(parents=True)
    (ui / "package.json").write_text("{}")
    if built:
        (ui / ".next" / "BUILD_ID").write_text("b1")
    return ui


def test_the_dashboard_is_linked_only_when_it_answers_as_smritikosh(world, tmp_path):
    a_ui(tmp_path, built=False)
    config = replace(ON, smritikosh=replace(SET_UP, checkout=str(tmp_path),
                                            dashboard_port=9))     # nothing listens
    dash = smritikosh.dashboard(config)
    assert dash["up"] is False and dash["url"] == "http://localhost:9/dashboard/memories"
    assert "`sarathi smritikosh` builds it" in dash["start"]
    assert smritikosh.dashboard(replace(ON, smritikosh=replace(
        SET_UP, checkout=str(tmp_path / "no-ui")))) is None
    assert parse(render(config)).smritikosh.dashboard_port == 9


def test_up_starts_the_built_dashboard_after_smritikosh_on_this_computer_only(world, kosh):
    checkout = Path(kosh.smritikosh.checkout)
    a_ui(checkout, built=True)
    planned, _ = services.plan(kosh, found(world))
    names = [s.name for s in planned]
    assert names.index("smritikosh-ui") == names.index("smritikosh") + 1
    ui = planned[names.index("smritikosh-ui")]
    assert ui.argv[1:] == ["start", "--hostname", "127.0.0.1", "--port", "3000"]
    assert ui.env["SMRITIKOSH_API_URL"] == "http://127.0.0.1:8080"
    assert "AUTH_SECRET" not in ui.env          # stays in its own .env.local
    off = replace(kosh, smritikosh=replace(kosh.smritikosh, dashboard=False))
    assert "smritikosh-ui" not in [s.name for s in services.plan(off, found(world))[0]]


def test_an_unbuilt_dashboard_is_said_not_started(world, kosh):
    a_ui(Path(kosh.smritikosh.checkout), built=False)
    planned, notes = services.plan(kosh, found(world))
    assert "smritikosh-ui" not in [s.name for s in planned]
    assert any("`sarathi smritikosh` builds it" in n for n in notes)


def test_on_podman_the_dashboard_is_a_user_service_with_no_node_in_the_image(host, kosh):
    a_ui(Path(kosh.smritikosh.checkout), built=True)
    unit = podman.dashboard_unit(replace(kosh, road="podman"))
    assert "ExecStart=" in unit and "next start --hostname 127.0.0.1 --port 3000" in unit
    assert "After=sarathi-smritikosh.service" in unit
    assert podman.dashboard_unit(replace(kosh, road="podman", memory="local")) is None


def test_a_build_older_than_the_ui_s_last_commit_is_built_again(world, tmp_path,
                                                                 monkeypatch):
    import shutil as sh
    monkeypatch.setenv("PATH", str(Path(sh.which("git", path="/usr/bin:/bin")).parent))
    ui = a_ui(tmp_path, built=True)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (ui / "page.tsx").write_text("x")
    import os
    os.utime(ui / ".next" / "BUILD_ID", (1, 1))          # built long ago
    subprocess.run(["git", "-C", str(tmp_path), "add", "ui/page.tsx"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c",
                    "user.email=t@t", "commit", "-qm", "ui"], check=True)
    assert smritikosh.built(tmp_path) is False
    os.utime(ui / ".next" / "BUILD_ID")                  # built now
    assert smritikosh.built(tmp_path) is True


def test_a_dashboard_not_started_says_whether_it_was_never_built_or_is_stale(
        world, tmp_path, monkeypatch):
    import shutil as sh
    monkeypatch.setenv("PATH", str(Path(sh.which("git", path="/usr/bin:/bin")).parent))
    ui = a_ui(tmp_path, built=False)
    assert smritikosh.unbuilt(tmp_path) == "not built yet"
    (ui / ".next" / "BUILD_ID").write_text("b1")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (ui / "page.tsx").write_text("x")
    import os
    os.utime(ui / ".next" / "BUILD_ID", (1, 1))
    subprocess.run(["git", "-C", str(tmp_path), "add", "ui/page.tsx"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c",
                    "user.email=t@t", "commit", "-qm", "ui"], check=True)
    assert smritikosh.unbuilt(tmp_path) == "its build is older than the last commit to ui/"
