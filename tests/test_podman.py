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
import subprocess
from pathlib import Path

import pytest

from sarathi import podman, services
from sarathi.config import Config, ConfigError, Door

LOCAL = Config("ollama", "gemma4:12b", web_port=8410, clock_port=8790, road="podman")


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
    return podman.units(config)["sarathi-page.container"]


def test_the_page_starts_after_the_clock_and_shares_nothing_else_with_it(host):
    text = page()
    assert "Wants=sarathi-clock.service\nAfter=sarathi-clock.service" in text
    assert "BindsTo" not in text and "--pid" not in text
    assert "--samay /usr/local/bin/samay" in text and "PublishPort=127.0.0.1:8410:8321" in text
    assert "Upholds" not in podman.units(LOCAL)["sarathi-clock.container"]


def test_with_the_clock_off_there_is_no_clock_and_nothing_bound_to_one(host):
    made = podman.units(Config("ollama", clock_on=False, road="podman"))
    assert list(made) == ["sarathi-page.container", "sarathi.network"]
    text = made["sarathi-page.container"]
    assert "--no-samay" in text and "sarathi-clock" not in text


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
    own = podman.env_file("sarathi-page")
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
    assert podman.install(podman.units(Config("ollama", clock_on=False, road="podman")))
    assert sorted(p.name for p in podman.unit_dir().iterdir()) == [
        "sarathi-page.container", "sarathi.network"]
    assert host.said("systemctl", "--user", "daemon-reload") == 2


def test_the_clocks_address_is_its_own_line_said_from_this_machine(host):
    host.answers[("podman", "logs")] = subprocess.CompletedProcess(
        [], 0, "samay 0.1.0: ...\npage: http://0.0.0.0:8780/#token=abc\n", "")
    assert podman.clock_address(LOCAL) == "http://127.0.0.1:8790/#token=abc"


def test_the_clock_is_told_the_address_a_browser_here_uses():
    unit = podman.units(LOCAL)["sarathi-clock.container"]
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
    assert (podman.unit_dir() / "sarathi-page.container").exists()
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
    door = made["sarathi-door.container"]
    home = world / "home"
    assert "--ask --provider ollama --model gemma4:12b --samay /usr/local/bin/samay" in door
    assert "serve --host 0.0.0.0 --port 8765 --telegram greeter" in door
    assert "PublishPort=127.0.0.1:8766:8765" in door
    assert "After=sarathi-clock.service" in door
    for folder in (home / "dvara/agents", home / "dvara", home / "dvara/state"):
        assert f"Volume={folder}:{folder}:z" in door
    assert "Environment=SAMAY_DVARA_URL=http://sarathi-door:8765" in made[
        "sarathi-clock.container"]
    assert "After=sarathi-door.service" in made["sarathi-page.container"]
    assert all("Network=sarathi.network" in made[f"sarathi-{n}.container"]
               for n in ("clock", "door", "page"))
    assert "123:bot" not in "".join(made.values())


def test_the_bots_token_reaches_the_door_and_no_other_container(host, world):
    with_door_secrets(world)
    podman.write_env_files(DOOR)
    door = podman.env_file("sarathi-door").read_text()
    clock = podman.env_file("sarathi-clock").read_text()
    page_env = podman.env_file("sarathi-page").read_text()
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


def test_every_container_gets_room_for_a_browser_and_a_wall_for_a_connector(host, world):
    """bubblewrap mounts a fresh /proc; masked, the kernel refuses it."""
    with_door_secrets(world)
    containers = [t for n, t in podman.units(DOOR).items() if n.endswith(".container")]
    assert all("ShmSize=1g" in t and "Unmask=/proc/*" in t for t in containers)


def test_home_is_writable_in_every_container(host, world):
    """Root-owned, Chrome dies at start: 'did not answer Target.createTarget'."""
    with_door_secrets(world)
    home = world / "home"
    containers = [t for n, t in podman.units(DOOR).items() if n.endswith(".container")]
    assert all(f"Tmpfs={home}:rw,mode=0700,U" in t for t in containers)
    assert all(f"Volume={home}/.samay:{home}/.samay:z" in t for t in containers)


def test_no_window_asked_for_publishes_nothing_more(host, world):
    with_door_secrets(world)
    door = podman.units(DOOR)["sarathi-door.container"]
    assert "SETU_WINDOW" not in door
    assert door.count("PublishPort=") == 1


def test_the_window_is_published_where_asked_and_linked_from_there(host, world):
    """Listening everywhere INSIDE, published on window_host alone, and a
    link a phone can open -- never the container's own address."""
    with_door_secrets(world)
    config = Config("ollama", road="podman",
                    door=Door(window_host="100.101.102.103"))
    door = podman.units(config)["sarathi-door.container"]
    assert "PublishPort=100.101.102.103:8790:8790" in door
    assert "Environment=SETU_WINDOW_HOST=0.0.0.0" in door
    assert "Environment=SETU_WINDOW_PORT=8790" in door
    assert "Environment=SETU_WINDOW_URL=http://100.101.102.103:8790" in door


def test_a_window_behind_your_own_https_keeps_its_address(host, world):
    with_door_secrets(world)
    config = Config("ollama", road="podman", door=Door(
        window_host="127.0.0.1", window_port=8767, window_url="https://door.example.net"))
    door = podman.units(config)["sarathi-door.container"]
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
    assert ("door   not started: something else is listening on port 8766 "
            "(change door.port in sarathi.toml)") in lines
    assert host.said("systemctl", "--user", "start", "sarathi-door.service") == 0
    assert host.said("systemctl", "--user", "stop", "sarathi-door.service") == 1


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
    assert any("port 8790 (change door.window_port" in line for line in lines)


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
    assert "page   restarting with the new settings  (unit sarathi-page)" in lines
    assert host.said("systemctl", "--user", "stop", "sarathi-page.service") == 1
    assert host.said("systemctl", "--user", "stop", "sarathi-clock.service") == 0
