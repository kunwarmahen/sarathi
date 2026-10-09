"""The podman road: the image, the units, and what reaches the containers.

The bias these tests encode: A CONTAINER SEES THE SAME THINGS AT THE SAME
PATHS, AND NOTHING SECRET IS WRITTEN INTO A UNIT. The image holds only
committed code, and says what it left out; the data folders are mounted
where they are on the host; the page starts after the clock and shares
nothing else with it, so either comes back alone; a key reaches a
container only through secrets.env, never as a line in a file that can
be pasted; and a unit is rewritten -- and systemd reloaded -- only when sarathi.toml changed it.

podman and systemctl are replaced by a recorder; git is real.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from sarathi import podman, services
from sarathi.config import Config, ConfigError, Door, Pages

# the pages are their own tests (at the end); here, the three pieces
LOCAL = Config("ollama", "gemma4:12b", web_port=8410, clock_port=8790, road="podman",
               pages=Pages(on=False))
NO_CLOCK = Config("ollama", clock_on=False, road="podman", pages=Pages(on=False))


class Recorder:
    def __init__(self):
        self.calls: list[list[str]] = []
        self.answers: dict[tuple, subprocess.CompletedProcess] = {}

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        for prefix, done in self.answers.items():
            if tuple(argv[:len(prefix)]) == prefix:
                return done
        return subprocess.CompletedProcess(argv, 0, "", "")

    def said(self, *prefix) -> int:
        return sum(1 for c in self.calls if tuple(c[:len(prefix)]) == prefix)


@pytest.fixture
def host(world, monkeypatch):
    monkeypatch.setenv("HOME", str(world / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(world / "home" / ".config"))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.delenv("SAMAY_STATE", raising=False)
    recorder = Recorder()
    monkeypatch.setattr(podman, "run", recorder)
    recorder.taken = set()            # host ports something else listens on
    monkeypatch.setattr(podman, "answers", lambda port: port in recorder.taken)
    return recorder


def page(config=LOCAL) -> str:
    return podman.units(config)["sarathi-yantra.container"]


def test_the_page_starts_after_the_clock_and_shares_nothing_else_with_it(host):
    text = page()
    assert "Wants=sarathi-samay.service\nAfter=sarathi-samay.service" in text
    assert "BindsTo" not in text and "--pid" not in text
    assert "--samay /usr/local/bin/samay" in text and "PublishPort=127.0.0.1:8410:8321" in text
    assert "Upholds" not in podman.units(LOCAL)["sarathi-samay.container"]


def test_with_the_clock_off_there_is_no_clock_and_nothing_bound_to_one(host):
    made = podman.units(NO_CLOCK)
    assert list(made) == ["sarathi-yantra.container", "sarathi.network"]
    text = made["sarathi-yantra.container"]
    assert "--no-samay" in text and "sarathi-samay" not in text


def test_every_data_folder_is_mounted_where_it_is_on_the_host(host, world):
    home = world / "home"
    text = page()
    for folder in (home / ".samay", home / ".local/state/setu", home / ".local/state/yantra",
                   home / ".yantra", services.work_dir()):
        assert f"Volume={folder}:{folder}:z" in text
    assert f"Environment=HOME={home}" in text and "UserNS=keep-id" in text


def test_a_local_model_is_reached_on_the_host_and_a_remote_one_where_it_is(host):
    assert "OLLAMA_BASE_URL=http://host.containers.internal:11434/v1" in page()
    remote = Config("ollama", base_url="http://gpu-box:11434/v1", road="podman")
    assert "OLLAMA_BASE_URL=http://gpu-box:11434/v1" in page(remote)


def test_a_key_reaches_the_containers_only_through_their_own_env_file(host, world):
    cloud = Config("anthropic", road="podman")
    assert "EnvironmentFile" not in page(cloud)
    secrets = world / "config" / "secrets.env"
    secrets.parent.mkdir(parents=True)
    secrets.write_text("ANTHROPIC_API_KEY=sk-secret\n")
    text = page(cloud)
    own = podman.env_file("sarathi-yantra")
    assert f"EnvironmentFile={own}" in text and "sk-secret" not in text
    podman.write_env_files(cloud)
    assert "ANTHROPIC_API_KEY=sk-secret" in own.read_text()
    assert oct(own.stat().st_mode & 0o777) == "0o600"


def test_a_key_in_the_shell_does_not_count_on_the_podman_road(host, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-shell")
    with pytest.raises(ConfigError, match="keys come only from there"):
        podman.preflight(Config("anthropic", road="podman"))


def test_no_image_yet_says_how_to_build_one(host):
    host.answers[("podman", "image", "exists")] = subprocess.CompletedProcess([], 1, "", "")
    with pytest.raises(ConfigError, match="run `sarathi image` first"):
        podman.preflight(LOCAL)


def test_processes_from_the_other_road_must_be_stopped_first(host):
    services.state_dir().joinpath("run").mkdir(parents=True)
    services.state_dir().joinpath("run", "page.json").write_text(json.dumps({"pid": 1}))
    with pytest.raises(ConfigError, match="`sarathi down` on the process road first"):
        podman.preflight(LOCAL)


def test_units_are_rewritten_and_systemd_reloaded_only_on_a_change(host):
    assert podman.install(podman.units(LOCAL))
    assert not podman.install(podman.units(LOCAL))
    assert host.said("systemctl", "--user", "daemon-reload") == 1
    assert podman.install(podman.units(NO_CLOCK))
    assert sorted(p.name for p in podman.unit_dir().iterdir()) == [
        "sarathi-yantra.container", "sarathi.network"]
    assert host.said("systemctl", "--user", "daemon-reload") == 2


def test_the_clocks_address_is_its_own_line_said_from_this_machine(host):
    host.answers[("podman", "logs")] = subprocess.CompletedProcess(
        [], 0, "samay 0.1.0: ...\npage: http://0.0.0.0:8780/#token=abc\n", "")
    assert podman.clock_address(LOCAL) == "http://127.0.0.1:8790/#token=abc"


def test_the_clock_is_told_the_address_a_browser_here_uses():
    unit = podman.units(LOCAL)["sarathi-samay.container"]
    assert "Environment=SAMAY_PUBLIC_URL=http://127.0.0.1:8790/" in unit


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_the_image_holds_only_what_is_committed_and_says_what_it_left_out(world, tmp_path,
                                                                         monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    checkouts = world / "checkouts"
    for name in podman.CHECKOUTS:
        repo = checkouts / name
        repo.mkdir(parents=True)
        git(repo, "init", "-q")
        (repo / "kept.txt").write_text("committed\n")
        git(repo, "add", ".")
        git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "one")
    (checkouts / "samay" / "kept.txt").write_text("edited, not committed\n")
    (checkouts / "samay" / "new.txt").write_text("never added\n")
    into = tmp_path / "context"
    lines = podman.stage(into)
    assert (into / "samay" / "kept.txt").read_text() == "committed\n"
    assert not (into / "samay" / "new.txt").exists()
    assert (into / "Containerfile").exists()
    samay = next(line for line in lines if line.startswith("samay"))
    assert "2 uncommitted change(s) left out" in samay
    assert "uncommitted" not in next(line for line in lines if line.startswith("yantra"))


def test_a_missing_checkout_is_named(world, tmp_path):
    with pytest.raises(ConfigError, match="yantra, setu, samay"):
        podman.stage(tmp_path / "context")


def test_down_says_the_units_come_back_at_login_unless_removed(host):
    podman.install(podman.units(LOCAL))
    said = podman.down()
    assert said[-1].startswith("they start again at your next login")
    assert (podman.unit_dir() / "sarathi-yantra.container").exists()
    said = podman.down(remove=True)
    assert said[-1].startswith("units removed")
    assert list(podman.unit_dir().iterdir()) == []
    assert podman.down() == ["no Sarathi units are installed"]


# ---- the door, on the podman road ---------------------------------------------------

DOOR = Config("ollama", "gemma4:12b", web_port=8410, clock_port=8790, road="podman",
              door=Door(port=8766, telegram="greeter"))


def with_door_secrets(world):
    secrets = world / "config" / "secrets.env"
    secrets.parent.mkdir(parents=True, exist_ok=True)
    secrets.write_text("DVARA_TOKEN=dvara-token\nTELEGRAM_TOKEN=123:bot\n")


def test_the_door_is_a_third_container_wired_to_the_clock_by_name(host, world):
    with_door_secrets(world)
    made = podman.units(DOOR)
    door = made["sarathi-dvara.container"]
    home = world / "home"
    assert "--ask --provider ollama --model gemma4:12b --samay /usr/local/bin/samay" in door
    assert "serve --host 0.0.0.0 --port 8765 --telegram greeter" in door
    assert "PublishPort=127.0.0.1:8766:8765" in door
    assert "After=sarathi-samay.service" in door
    for folder in (home / "dvara/agents", home / "dvara", home / "dvara/state"):
        assert f"Volume={folder}:{folder}:z" in door
    assert "Environment=SAMAY_DVARA_URL=http://sarathi-dvara:8765" in made[
        "sarathi-samay.container"]
    assert "After=sarathi-dvara.service" in made["sarathi-yantra.container"]
    assert all("Network=sarathi.network" in made[f"sarathi-{n}.container"]
               for n in ("samay", "dvara", "yantra"))
    assert "123:bot" not in "".join(made.values())


def test_the_bots_token_reaches_the_door_and_no_other_container(host, world):
    with_door_secrets(world)
    podman.write_env_files(DOOR)
    door = podman.env_file("sarathi-dvara").read_text()
    clock = podman.env_file("sarathi-samay").read_text()
    page_env = podman.env_file("sarathi-yantra").read_text()
    assert "TELEGRAM_TOKEN=123:bot" in door and "DVARA_TOKEN=dvara-token" in door
    assert "SAMAY_DVARA_TOKEN=dvara-token" in clock and "TELEGRAM" not in clock
    assert "TOKEN" not in page_env
    assert oct(podman.env_file("x").parent.stat().st_mode & 0o777) == "0o700"


def test_an_image_without_dvara_says_how_to_put_it_in(host, world):
    with_door_secrets(world)
    (world / "home" / "dvara" / "agents").mkdir(parents=True)
    (world / "home" / "dvara" / "actors.toml").write_text("[actor.owner]\n")
    host.answers[("podman", "run", "--rm", "--entrypoint", "test")] = \
        subprocess.CompletedProcess([], 1, "", "")
    with pytest.raises(ConfigError, match="the image has no dvara"):
        podman.preflight(DOOR)


def test_a_door_with_no_actors_file_does_not_start(host, world):
    with_door_secrets(world)
    with pytest.raises(ConfigError, match="no actors file"):
        podman.preflight(DOOR)


# ---- a browser in the image, and the door's window -------------------------------


def test_the_image_carries_a_browser_bubblewrap_and_a_screen():
    text = Path(podman.__file__).with_name("Containerfile").read_text()
    for wanted in ("bubblewrap", "xvfb", "google-chrome-stable", "--extra browse",
                   "YANTRA_BROWSER_EXECUTABLE"):
        assert wanted in text


def test_a_newer_chrome_here_rebuilds_the_image_s_browser(host, monkeypatch):
    """The Chrome step was cached: `sarathi image` kept 154 while this
    machine had 155, and the note said to run `sarathi image` again."""
    text = Path(podman.__file__).with_name("Containerfile").read_text()
    arg, step = text.index("ARG HOST_BROWSER"), text.index("google-chrome-stable")
    assert arg < step and "${HOST_BROWSER" in text[arg:step]
    built = []
    monkeypatch.setattr(podman, "stage", lambda into, env=None: [])
    monkeypatch.setattr(podman.shutil, "which", lambda name: name)
    monkeypatch.setattr(podman, "browser_version", lambda argv: (155, 0, 8059, 39))
    monkeypatch.setattr(podman.subprocess, "run",
                        lambda argv, **kw: built.append(argv) or
                        subprocess.CompletedProcess(argv, 0))
    assert podman.build() == 0
    assert "HOST_BROWSER=155.0.8059.39" in built[0]


def test_the_image_is_built_for_this_machine_whatever_the_base_tags_hold(host, monkeypatch):
    """An arm64 build left arm64 debian and python under their usual names;
    the next plain `sarathi image` built arm64 and the door took three
    minutes to start under qemu."""
    built = []
    monkeypatch.setattr(podman, "stage", lambda into, env=None: [])
    monkeypatch.setattr(podman.shutil, "which", lambda name: None)
    monkeypatch.setattr(podman.os, "uname", lambda: os.uname_result(
        ("Linux", "box", "7.0", "#1", "x86_64")))
    monkeypatch.setattr(podman.subprocess, "run",
                        lambda argv, **kw: built.append(argv) or
                        subprocess.CompletedProcess(argv, 0))
    assert podman.build() == 0
    assert built[0][built[0].index("--platform") + 1] == "linux/amd64"


def test_every_container_gets_room_for_a_browser_and_a_wall_for_a_connector(host, world):
    """bubblewrap mounts a fresh /proc; masked, the kernel refuses it."""
    with_door_secrets(world)
    containers = [t for n, t in podman.units(DOOR).items() if n.endswith(".container")]
    assert all("ShmSize=1g" in t and "Unmask=/proc/*" in t for t in containers)


def test_every_container_stops_when_asked(host, world):
    """A program as PID 1 never sees SIGTERM unless it catches it: `setu
    serve` and `dvara page` sat out the 10 seconds, were killed, and their
    units read 'failed' after every `sarathi down`."""
    with_door_secrets(world)
    containers = [t for n, t in podman.units(DOOR).items() if n.endswith(".container")]
    assert containers and all("RunInit=true" in t for t in containers)
    # and a program the init's SIGTERM ends (143) was stopped, not failed
    assert all("SuccessExitStatus=143" in t for t in containers)


def test_home_is_writable_in_every_container(host, world):
    """Root-owned, Chrome dies at start: 'did not answer Target.createTarget'."""
    with_door_secrets(world)
    home = world / "home"
    containers = [t for n, t in podman.units(DOOR).items() if n.endswith(".container")]
    assert all(f"Tmpfs={home}:rw,mode=0700,U" in t for t in containers)
    assert all(f"Volume={home}/.samay:{home}/.samay:z" in t for t in containers)


def test_no_window_asked_for_publishes_nothing_more(host, world):
    with_door_secrets(world)
    door = podman.units(DOOR)["sarathi-dvara.container"]
    assert "SETU_WINDOW" not in door
    assert door.count("PublishPort=") == 1


def test_the_window_is_published_where_asked_and_linked_from_there(host, world):
    """Listening everywhere INSIDE, published on window_host alone, and a
    link a phone can open -- never the container's own address."""
    with_door_secrets(world)
    config = Config("ollama", road="podman",
                    door=Door(window_host="100.101.102.103"))
    door = podman.units(config)["sarathi-dvara.container"]
    assert "PublishPort=100.101.102.103:8790:8790" in door
    assert "Environment=SETU_WINDOW_HOST=0.0.0.0" in door
    assert "Environment=SETU_WINDOW_PORT=8790" in door
    assert "Environment=SETU_WINDOW_URL=http://100.101.102.103:8790" in door


def test_a_window_behind_your_own_https_keeps_its_address(host, world):
    with_door_secrets(world)
    config = Config("ollama", road="podman", door=Door(
        window_host="127.0.0.1", window_port=8767, window_url="https://door.example.net"))
    door = podman.units(config)["sarathi-dvara.container"]
    assert "PublishPort=127.0.0.1:8767:8767" in door
    assert "Environment=SETU_WINDOW_URL=https://door.example.net" in door


def test_a_window_listening_everywhere_must_say_its_address(host, world):
    with_door_secrets(world)
    (world / "home" / "dvara" / "agents").mkdir(parents=True)
    (world / "home" / "dvara" / "actors.toml").write_text("[actor.owner]\n")
    config = Config("ollama", road="podman", door=Door(window_host="0.0.0.0"))
    with pytest.raises(ConfigError, match="window_url must say the address"):
        podman.preflight(config)


@pytest.mark.parametrize("here, inside, warned", [
    ("Google Chrome 155.0.1.2", "Google Chrome 154.0.8037.97", True),
    ("Google Chrome 154.0.8037.97", "Google Chrome 154.0.8037.97", False),
    ("Google Chrome 153.0.1.1", "Google Chrome 154.0.8037.97", False),
    ("Google Chrome 155.0.1.2", "", False),
])
def test_a_newer_chrome_here_than_in_the_image_is_said(host, monkeypatch, here, inside,
                                                       warned):
    """Chrome refuses a profile a newer Chrome wrote."""
    monkeypatch.setattr(podman.shutil, "which", lambda name, **kw: name)
    host.answers[(podman.BROWSER, "--version")] = subprocess.CompletedProcess([], 0, here, "")
    host.answers[("podman", "run")] = subprocess.CompletedProcess([], 0, inside, "")
    note = podman.browser_note()
    assert (note is not None) is warned
    if warned:
        assert "Chrome 155.0.1.2, the image 154.0.8037.97" in note
        assert "`sarathi image`" in note


def test_a_network_gone_missing_is_made_again_before_anything_joins_it(host, world):
    """Its one-shot service stays 'active' after the network is removed,
    so systemd alone would never make it again."""
    host.answers[("podman", "network", "exists")] = subprocess.CompletedProcess([], 1, "", "")
    host.answers[("systemctl", "--user", "is-active")] = subprocess.CompletedProcess(
        [], 0, "", "")
    podman.up(LOCAL)
    assert host.said("systemctl", "--user", "restart", "sarathi-network.service") == 1


def test_removing_stops_the_networks_service_before_the_network_goes(host):
    podman.install(podman.units(LOCAL))
    podman.down(remove=True)
    stop = host.calls.index(["systemctl", "--user", "stop", "sarathi-network.service"])
    gone = host.calls.index(["podman", "network", "rm", "sarathi"])
    assert stop < gone


def test_a_port_something_else_holds_is_said_and_the_unit_not_left_looping(host, world):
    """Published, it fails inside systemd every few seconds with the reason
    deep in a journal -- as it did behind another program on 8765."""
    with_door_secrets(world)
    (world / "home" / "dvara" / "agents").mkdir(parents=True)
    (world / "home" / "dvara" / "actors.toml").write_text("[actor.owner]\n")
    host.answers[("systemctl", "--user", "is-active")] = subprocess.CompletedProcess(
        [], 3, "", "")
    host.taken = {8766}
    lines, ok = podman.up(DOOR)
    assert not ok
    assert ("dvara      not started: something else is listening on port 8766 "
            "(change dvara.port in sarathi.toml)") in lines
    assert host.said("systemctl", "--user", "start", "sarathi-dvara.service") == 0
    assert host.said("systemctl", "--user", "stop", "sarathi-dvara.service") == 1


def test_the_windows_port_is_checked_too(host, world):
    with_door_secrets(world)
    (world / "home" / "dvara" / "agents").mkdir(parents=True)
    (world / "home" / "dvara" / "actors.toml").write_text("[actor.owner]\n")
    host.answers[("systemctl", "--user", "is-active")] = subprocess.CompletedProcess(
        [], 3, "", "")
    host.taken = {8790}
    config = Config("ollama", road="podman", clock_port=8781,
                    door=Door(window_host="127.0.0.1"))
    lines, _ = podman.up(config)
    assert any("port 8790 (change dvara.window_port" in line for line in lines)


# ---- switching roads ---------------------------------------------------------------


def _settings(world, road):
    (world / "config").mkdir(exist_ok=True)
    (world / "config" / "sarathi.toml").write_text(
        f'[model]\nprovider = "ollama"\n[run]\nroad = "{road}"\n')


def test_the_road_is_said_with_how_to_take_the_other(host, world, capsys):
    from sarathi.cli import main
    _settings(world, "process")
    assert main(["road"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("road: process -- plain programs")
    assert "`sarathi road podman`" in out


def test_leaving_the_podman_road_removes_its_units_so_login_cannot_bring_them_back(
        host, world, capsys):
    """Both roads use the same ports."""
    from sarathi.cli import main
    from sarathi.config import load
    _settings(world, "podman")
    podman.install(podman.units(LOCAL))
    assert main(["road", "process"]) == 0
    assert load().road == "process"
    assert not any(podman.unit_dir().glob("sarathi-*.container"))
    assert "next: `sarathi up`" in capsys.readouterr().out


def test_taking_the_podman_road_without_an_image_says_to_build_one(host, world, capsys):
    from sarathi.cli import main
    from sarathi.config import load
    _settings(world, "process")
    host.answers[("podman", "image", "exists")] = subprocess.CompletedProcess([], 1, "", "")
    assert main(["road", "podman"]) == 0
    assert load().road == "podman"
    assert "next: `sarathi image` (once), then `sarathi up`" in capsys.readouterr().out


# ---- a file Setu names outside its folder ------------------------------------------


def _client(world, where="Desktop"):
    path = world / "home" / where / "client_secret_x.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}")
    return path


def test_the_google_client_file_setu_names_is_mounted_alone_and_read_only(host, world):
    """Setu keeps only its path; the file sits wherever Google's download
    put it, which no container sees -- and the rest of that folder stays out."""
    client = _client(world)
    setu = podman.data_dirs()[1]
    setu.mkdir(parents=True)
    (setu / "config.json").write_text(json.dumps({"google_client_file": str(client)}))
    with_door_secrets(world)
    for name, text in podman.units(DOOR).items():
        if name.endswith(".container"):
            assert f"Volume={client}:{client}:ro,z" in text
            assert f"Volume={client.parent}:" not in text


def test_the_environment_names_it_first_and_a_missing_file_mounts_nothing(host, world,
                                                                         monkeypatch):
    client = _client(world, "Downloads")
    monkeypatch.setenv("SETU_GOOGLE_CLIENT_FILE", str(client))
    assert podman.setu_files() == [client]
    monkeypatch.setenv("SETU_GOOGLE_CLIENT_FILE", str(world / "gone.json"))
    assert podman.setu_files() == []


def test_a_running_unit_whose_file_changed_is_restarted_not_left_on_old_settings(
        host, world):
    """'units rewritten' meant nothing to a container already running."""
    host.answers[("systemctl", "--user", "is-active")] = subprocess.CompletedProcess(
        [], 0, "", "")
    podman.install(podman.units(LOCAL))
    lines, _ = podman.up(Config("ollama", "gemma4:12b", web_port=8411, clock_port=8790,
                                road="podman"))
    assert "yantra     restarting with the new settings  (unit sarathi-yantra)" in lines
    assert host.said("systemctl", "--user", "stop", "sarathi-yantra.service") == 1
    assert host.said("systemctl", "--user", "stop", "sarathi-samay.service") == 0


def test_a_unit_running_an_older_image_is_restarted_after_a_build(host, world):
    """`sarathi image` changed nothing in a container already running."""
    host.answers[("systemctl", "--user", "is-active")] = subprocess.CompletedProcess(
        [], 0, "", "")
    podman.install(podman.units(LOCAL))
    host.answers[("podman", "image", "inspect")] = subprocess.CompletedProcess(
        [], 0, "sha-new\n", "")
    host.answers[("podman", "container", "inspect", "--format", "{{.Image}}",
                  "sarathi-yantra")] = subprocess.CompletedProcess([], 0, "sha-old\n", "")
    host.answers[("podman", "container", "inspect")] = subprocess.CompletedProcess(
        [], 0, "sha-new\n", "")
    lines, _ = podman.up(LOCAL)
    assert "yantra     restarting with the new image  (unit sarathi-yantra)" in lines
    assert host.said("systemctl", "--user", "stop", "sarathi-yantra.service") == 1
    assert host.said("systemctl", "--user", "stop", "sarathi-samay.service") == 0


# ---- the pages, on the podman road ----------------------------------------------------

PAGES = Config("ollama", "gemma4:12b", web_port=8410, clock_port=8790, road="podman",
               door=Door(port=8766, owner="mahen"),
               pages=Pages(on=True, setu_port=8875, door_port=8885, home_port=8860))


def test_setus_page_is_a_container_published_here_only(host, world):
    setu = podman.units(PAGES)["sarathi-setu.container"]
    assert "setu serve --host 0.0.0.0 --port 8775 --public-url http://127.0.0.1:8875/" in setu
    assert "PublishPort=127.0.0.1:8875:8775" in setu


def test_setus_page_on_the_window_address_opens_peoples_links_on_their_phones(host, world):
    """One address (Tailscale, the home network): Setu's page is published
    there as well as here, sees people's folders (that folder alone), and
    the door builds their links with that address."""
    with_door_secrets(world)
    config = Config("ollama", road="podman", door=Door(window_host="100.101.102.103"),
                    pages=Pages(on=True, setu_port=8875))
    made = podman.units(config)
    setu = made["sarathi-setu.container"]
    folders = world / "home/dvara/state/setu"
    assert f"--people {folders}" in setu
    assert "PublishPort=127.0.0.1:8875:8775" in setu
    assert "PublishPort=100.101.102.103:8875:8775" in setu
    assert f"Volume={folders}:{folders}:z" in setu
    assert "Volume=" + str(world / "home/dvara/state") + ":" not in setu  # not the whole state
    door = made["sarathi-dvara.container"]
    assert "Environment=SETU_PAGE_URL=http://100.101.102.103:8875/" in door


def test_every_address_or_none_keeps_setus_page_here(host, world):
    with_door_secrets(world)
    for where in (None, "0.0.0.0", "127.0.0.1"):
        config = Config("ollama", road="podman",
                        door=Door(window_host=where, window_url="https://door.example.net"),
                        pages=Pages(on=True, setu_port=8875))
        made = podman.units(config)
        assert made["sarathi-setu.container"].count("PublishPort=") == 1
        assert "SETU_PAGE_URL" not in made["sarathi-dvara.container"]
        assert config.people_env() == {}


def test_setus_page_has_its_own_window_beside_the_doors(host, world):
    """In its container everyone is on another device, the owner too: an
    Amazon sign-in from Setu's page is always the streamed window, and it
    had no address to give one -- the link said 127.0.0.1 inside."""
    with_door_secrets(world)
    config = Config("ollama", road="podman", door=Door(window_host="100.101.102.103"),
                    pages=Pages(on=True, setu_port=8875))
    setu = podman.units(config)["sarathi-setu.container"]
    assert "PublishPort=100.101.102.103:8791:8791" in setu
    assert "Environment=SETU_WINDOW_HOST=0.0.0.0" in setu
    assert "Environment=SETU_WINDOW_URL=http://100.101.102.103:8791" in setu
    door = podman.units(config)["sarathi-dvara.container"]
    assert "PublishPort=100.101.102.103:8790:8790" in door        # the door keeps its own


def test_with_no_window_address_setus_window_is_for_this_computer(host, world):
    with_door_secrets(world)
    for config in (Config("ollama", road="podman", door=Door(window_port=8800),
                          pages=Pages(on=True)),
                   Config("ollama", road="podman", pages=Pages(on=True))):
        setu = podman.units(config)["sarathi-setu.container"]
        port = 8801 if config.door else 8791
        assert f"PublishPort=127.0.0.1:{port}:{port}" in setu
        assert f"Environment=SETU_WINDOW_URL=http://127.0.0.1:{port}" in setu


def test_behind_a_window_url_setus_page_gets_no_window_of_its_own(host, world):
    with_door_secrets(world)
    config = Config("ollama", road="podman",
                    door=Door(window_host="100.101.102.103", window_url="https://door.example.net"),
                    pages=Pages(on=True))
    assert "SETU_WINDOW" not in podman.units(config)["sarathi-setu.container"]


def test_a_taken_window_port_for_setus_page_is_said_before_it_starts(host, world,
                                                                     monkeypatch):
    with_door_secrets(world)
    monkeypatch.setattr(podman, "preflight", lambda config: None)
    config = Config("ollama", road="podman", door=Door(window_host="100.101.102.103"),
                    pages=Pages(on=True))
    host.answers[("systemctl", "--user", "is-active")] = subprocess.CompletedProcess(
        [], 3, "", "")
    host.taken = {8791}
    lines, ok = podman.up(config)
    assert not ok
    assert ("setu       not started: something else is listening on port 8791 "
            "(change dvara.window_port in sarathi.toml)") in lines
    assert host.said("systemctl", "--user", "start", "sarathi-setu.service") == 0


def test_the_owner_page_reaches_the_door_by_name_with_its_token_from_its_own_file(
        host, world):
    with_door_secrets(world)
    made = podman.units(PAGES)
    owner = made["sarathi-dvara-page.container"]
    assert "page --as mahen --host 0.0.0.0 --port 8785" in owner
    assert "PublishPort=127.0.0.1:8885:8785" in owner
    assert "Environment=DVARA_URL=http://sarathi-dvara:8765" in owner
    assert "After=sarathi-dvara.service" in owner
    assert "dvara-token" not in owner                       # never in the unit itself
    podman.write_env_files(PAGES)
    assert podman.env_file("sarathi-dvara-page").read_text().splitlines()[1:] == [
        "DVARA_TOKEN=dvara-token"]
    for other in ("sarathi-yantra", "sarathi-setu"):
        path = podman.env_file(other)
        assert not path.exists() or "DVARA_TOKEN" not in path.read_text()


def test_the_home_page_is_a_user_service_started_at_login_and_gone_when_off(host, world):
    text = podman.home_unit(PAGES)
    assert " home --port 8860" in text and "WantedBy=default.target" in text
    assert podman.install_home(text) is True
    assert podman.unit_file("sarathi") == world / "home/.config/systemd/user/sarathi-home.service"
    assert host.said("systemctl", "--user", "enable", "sarathi-home.service") == 1
    assert podman.install_home(text) is False               # unchanged: nothing reloaded
    assert podman.home_unit(LOCAL) is None
    assert podman.install_home(None) is True
    assert not podman.unit_file("sarathi").exists()
    assert host.said("systemctl", "--user", "disable", "sarathi-home.service") == 1


def test_up_shows_each_pages_address_with_its_key(host, world, monkeypatch):
    with_door_secrets(world)
    host.answers[("systemctl", "--user", "is-active")] = subprocess.CompletedProcess(
        [], 0, "", "")
    monkeypatch.setattr(podman, "preflight", lambda config: None)
    setu_home = world / "home/.local/state/setu"
    setu_home.mkdir(parents=True)
    (setu_home / "page.token").write_text("setu-key\n")
    lines, _ = podman.up(PAGES)
    assert any(line.startswith("setu       ") and "http://127.0.0.1:8875/#token=setu-key" in line
               for line in lines), lines
    assert any(line.startswith("sarathi    ") for line in lines)


def test_a_unit_under_its_old_name_is_stopped_before_it_is_removed(host, world):
    # removed while running, its container would keep holding the port
    # the new unit needs
    old = podman.unit_dir() / "sarathi-clock.container"
    old.parent.mkdir(parents=True)
    old.write_text("[Container]\n")
    lines, _ = podman.up(LOCAL)
    assert "sarathi-clock stopped and removed: it is sarathi-samay now" in lines
    stop = host.calls.index(["systemctl", "--user", "stop", "sarathi-clock.service"])
    assert not old.exists() and stop >= 0
    assert (podman.unit_dir() / "sarathi-samay.container").exists()


def test_every_container_keeps_this_computers_time(host, world, monkeypatch):
    """In UTC a browser told every page so, while the address said New
    York: X refused the streamed window's password on the mismatch."""
    monkeypatch.setattr(podman, "host_timezone", lambda: "America/New_York")
    with_door_secrets(world)
    containers = [t for n, t in podman.units(DOOR).items() if n.endswith(".container")]
    assert containers and all("Environment=TZ=America/New_York" in t for t in containers)


def test_a_timezone_is_read_by_name_never_as_a_path(monkeypatch):
    monkeypatch.setenv("TZ", ":Asia/Kolkata")
    assert podman.host_timezone() == "Asia/Kolkata"
    monkeypatch.setenv("TZ", "/etc/localtime")      # a path names no zone
    monkeypatch.setattr(podman.os.path, "realpath",
                        lambda _p: "/usr/share/zoneinfo/Europe/Berlin")
    monkeypatch.setattr(podman.Path, "read_text", lambda self: "")
    assert podman.host_timezone() == "Europe/Berlin"
