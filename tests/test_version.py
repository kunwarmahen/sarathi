"""`sarathi version`: which commit of each project is running.

The bias is A VERSION THAT SAYS WHAT WAS CHECKED OUT, NOT WHAT RUNS. On
the podman road the containers run the image, and the checkouts move on
after it is built; so the commits come from the image's own label, and
the checkout's commit is shown against it, never in its place. An image
from before the label is said to be one, not shown with today's commits.

git is real; podman is answered by hand.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from sarathi import podman, version
from sarathi.config import Config, Pages

from test_home import GOOD, ask, config as home_config, keys  # noqa: F401  (fixture)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c",
                           "user.email=t@t", *args], check=True, capture_output=True,
                          text=True).stdout.strip()


def commit(repo: Path, words: str) -> str:
    (repo / "kept.txt").write_text(words + "\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", words)
    return git(repo, "rev-parse", "--short", "HEAD")


@pytest.fixture
def checkouts(world, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    made = {}
    for name in podman.CHECKOUTS:
        repo = world / "checkouts" / name
        repo.mkdir(parents=True)
        git(repo, "init", "-q")
        made[name] = commit(repo, f"{name}: the first")
    return world / "checkouts"


def label_of(into: Path) -> dict:
    return json.loads((into / podman.BUILD_FILE).read_text())


def test_a_version_is_the_day_of_the_commit_and_its_place_in_that_day(world, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    repo = world / "one"
    repo.mkdir()
    git(repo, "init", "-q")
    for words, when in (("a", "2026-10-24T22:00:00+05:30"), ("b", "2026-10-25T09:00:00+05:30"),
                        ("c", "2026-10-25T23:30:00+05:30")):
        (repo / "kept.txt").write_text(words)
        git(repo, "add", ".")
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-qm", words], check=True, capture_output=True,
                       env={**os.environ, "GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when})
    assert version.dated(repo) == "2026.10.25.2"
    assert version.dated(repo, "HEAD~2") == "2026.10.24.1"


def test_the_image_gets_a_version_file_for_each_program_to_read(checkouts, tmp_path):
    into = tmp_path / "context"
    podman.stage(into)
    number, at = (into / "yantra" / "VERSION").read_text().split()
    assert number == version.dated(checkouts / "yantra")
    assert at == git(checkouts / "yantra", "rev-parse", "--short", "HEAD")
    assert label_of(into)["projects"]["yantra"]["version"] == number
    assert not (checkouts / "yantra" / "VERSION").exists()     # never in the checkout


def test_an_image_stamped_without_versions_has_them_worked_out(checkouts, tmp_path,
                                                               monkeypatch):
    into = tmp_path / "context"
    podman.stage(into)
    stamp = label_of(into)
    for p in stamp["projects"].values():
        del p["version"]
    answer_podman(monkeypatch, {version.LABEL: json.dumps(stamp)})
    got = version.report(Config("ollama", road="podman", pages=Pages(on=False)))
    samay = next(p for p in got["projects"] if p["name"] == "samay")
    assert samay["running"]["version"] == version.dated(checkouts / "samay")


def test_the_build_writes_down_each_commit_and_what_it_left_out(checkouts, tmp_path):
    (checkouts / "samay" / "kept.txt").write_text("edited, not committed\n")
    into = tmp_path / "context"
    podman.stage(into)
    stamp = label_of(into)
    assert stamp["format"] == version.BUILD_FORMAT
    samay = stamp["projects"]["samay"]
    assert samay["subject"] == "samay: the first" and samay["left_out"] == 1
    assert samay["commit"] == git(checkouts / "samay", "rev-parse", "--short", "HEAD")
    assert stamp["projects"]["yantra"]["left_out"] == 0


def test_the_label_goes_on_the_image(monkeypatch):
    built = []

    def stage(into, env=None, config=None):
        (into / podman.BUILD_FILE).write_text('{"format": "sarathi.build.v1"}')
        return []
    monkeypatch.setattr(podman, "stage", stage)
    monkeypatch.setattr(podman.shutil, "which", lambda name: None)
    monkeypatch.setattr(podman, "run", lambda argv, **kw: subprocess.CompletedProcess(argv, 0, ""))
    monkeypatch.setattr(podman.subprocess, "run",
                        lambda argv, **kw: built.append(argv) or
                        subprocess.CompletedProcess(argv, 0))
    assert podman.build() == 0
    argv = built[0]
    assert argv[argv.index("--label") + 1] == 'sarathi.build={"format": "sarathi.build.v1"}'


def answer_podman(monkeypatch, labels: dict | None, made: int = 1_760_000_000):
    real = podman.run

    def run(argv, **kw):
        if argv[:3] == ["podman", "image", "inspect"]:
            return subprocess.CompletedProcess(argv, 0, f"{made} {json.dumps(labels)}\n", "")
        if argv[0] in ("podman", "systemctl"):
            return subprocess.CompletedProcess(argv, 1, "", "")   # nothing running
        return real(argv, **kw)
    monkeypatch.setattr(podman, "run", run)


def test_on_containers_the_image_says_and_newer_commits_are_counted(checkouts, tmp_path,
                                                                    monkeypatch):
    into = tmp_path / "context"
    podman.stage(into)
    stamp = label_of(into)
    built_at = stamp["projects"]["yantra"]["commit"]
    commit(checkouts / "yantra", "yantra: after the build")
    commit(checkouts / "yantra", "yantra: and another")
    answer_podman(monkeypatch, {version.LABEL: json.dumps(stamp)})
    got = version.report(Config("ollama", road="podman", pages=Pages(on=False)))
    yantra = next(p for p in got["projects"] if p["name"] == "yantra")
    assert yantra["running"]["commit"] == built_at
    assert yantra["running"]["subject"] == "yantra: the first"
    assert yantra["now"]["subject"] == "yantra: and another" and yantra["newer"] == 2
    assert next(p for p in got["projects"] if p["name"] == "setu")["newer"] == 0
    assert got["image"]["stamped"] is True
    said = version.text(got)
    assert "2 newer in the checkout" in said and "sarathi image && sarathi up" in said


def test_an_image_from_before_the_label_is_said_to_be_one(checkouts, monkeypatch):
    answer_podman(monkeypatch, None)
    got = version.report(Config("ollama", road="podman", pages=Pages(on=False)))
    assert got["image"] == {"exists": True, "made": 1_760_000_000, "stamped": False,
                            "behind": []}
    # today's checkouts are never shown as what runs
    assert all(p["running"] is None for p in got["projects"] if not p.get("here"))
    assert "built before images said their commits" in version.text(got)


def test_no_image_yet(checkouts, monkeypatch):
    monkeypatch.setattr(podman, "run",
                        lambda argv, **kw: subprocess.CompletedProcess(argv, 1, "", "no"))
    got = version.report(Config("ollama", road="podman", pages=Pages(on=False)))
    assert got["image"] == {"exists": False}
    assert "no image built yet" in version.headline(got)


def test_on_plain_programs_the_checkouts_say_uncommitted_and_all(checkouts):
    (checkouts / "setu" / "kept.txt").write_text("edited\n")
    got = version.report(Config("ollama", pages=Pages(on=False)))
    assert got["image"] is None
    setu = next(p for p in got["projects"] if p["name"] == "setu")
    assert setu["running"] == setu["now"] and setu["running"]["left_out"] == 1
    assert "plain programs" in version.headline(got)
    assert "+1 uncommitted change(s)" in version.text(got)


def test_the_home_page_says_it_to_the_owner_alone(keys):  # noqa: F811
    from sarathi.home import Home, HomeServer

    asked = []
    home = Home(home_config(keys), lambda: {},
                version=lambda c: asked.append(1) or {
                    "format": version.FORMAT, "sarathi": "0.1.0", "road": "process",
                    "image": None, "projects": []})
    server = HomeServer(home, GOOD, port=0)
    server.start()
    try:
        got = ask(server, "/api/version")
        assert got.status_code == 200
        assert got.json()["said"] == "Sarathi 0.1.0, plain programs from their checkouts"
        # (the report's own number; a real one is the day of Sarathi's last commit)
        assert ask(server, "/api/version", token=None).status_code == 401
        assert ask(server, "/api/version", token="wrong-token-of-a-good-length"
                   ).status_code == 401
        ask(server, "/api/version")
        assert len(asked) == 1           # asked again within 30s: the same answer
    finally:
        server.stop()
