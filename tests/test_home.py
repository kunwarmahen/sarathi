"""`sarathi home`: one page of links, each carrying its page's key.

The bias is A KEY RING LEFT ON THE TABLE. The page reads Samay's, Setu's
and Dvara's page tokens so its links open them signed in, which makes
its own answer the most valuable thing on the machine. So the tests ask
it without its token and with the wrong one, and check the keys appear
only behind the right one, and never in the page's static files.

The other bias is A HOME PAGE THAT GROWS LOGIC. It links and reports;
it starts nothing, and a POST is refused -- except the chat's, which
passes your words to Dvara and decides nothing (tests at the end). A page that isn't running is
shown down with the command that starts it, never started for you.
"""

from __future__ import annotations

import stat
from pathlib import Path

import json
import urllib.error
import urllib.request

import pytest

from sarathi.config import Config, Door, Pages
from conftest import program
from sarathi.home import ENV_TOKEN, TOKEN_FILE, Home, HomeServer, home_token, pages

GOOD = "the-home-token-long-enough"


@pytest.fixture
def keys(world, tmp_path, monkeypatch):
    """Each program's page token, where that program keeps it."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SETU_HOME", str(tmp_path / "setu"))
    monkeypatch.setenv("SAMAY_STATE", str(tmp_path / "samay"))
    for var in ("SAMAY_TOKEN", "SETU_PAGE_TOKEN", "DVARA_PAGE_TOKEN", ENV_TOKEN):
        monkeypatch.delenv(var, raising=False)
    for folder, token in (("samay/serve.token", "samay-key-1234567890"),
                          ("setu/page.token", "setu-key-1234567890"),
                          ("door/state/page.token", "dvara-key-1234567890")):
        path = tmp_path / folder
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(token + "\n")
    return tmp_path


def config(tmp_path: Path, *, door: bool = True, by_up: bool = False) -> Config:
    return Config(provider="ollama", web_port=8321, clock_port=8780,
                  door=Door(state=str(tmp_path / "door" / "state")) if door else None,
                  pages=Pages(on=by_up))


@pytest.fixture
def served(keys):
    home = Home(config(keys), lambda: {"setu": "9 connections"},
                up=lambda port: port != 8785)
    server = HomeServer(home, GOOD, port=0)
    server.start()
    yield server
    server.stop()


class Answer:
    def __init__(self, status_code, text, headers):
        self.status_code, self.text, self.headers = status_code, text, headers

    def json(self):
        return json.loads(self.text)


def ask(server, path, token=GOOD, method="GET"):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(server.url.rstrip("/") + path, headers=headers,
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return Answer(res.status, res.read().decode(),
                          {k.lower(): v for k, v in res.headers.items()})
    except urllib.error.HTTPError as err:
        return Answer(err.code, err.read().decode(),
                      {k.lower(): v for k, v in err.headers.items()})


def get(server, path, token=GOOD):
    return ask(server, path, token)


def test_the_keys_are_only_behind_the_home_token(served):
    assert get(served, "/api/pieces", token=None).status_code == 401
    assert get(served, "/api/pieces", token="wrong-token-of-some-length").status_code == 401
    for path in ("/", "/page.js", "/md.js", "/page.css", "/favicon.svg"):
        assert "key-1234567890" not in get(served, path, token=None).text


def test_each_link_opens_its_page_signed_in(served):
    by = {p["name"]: p for p in get(served, "/api/pieces").json()["pieces"]}
    assert by["samay"]["open"] == "http://127.0.0.1:8780/#token=samay-key-1234567890"
    assert by["setu"]["open"] == "http://127.0.0.1:8775/#token=setu-key-1234567890"
    assert by["dvara"]["open"] == "http://127.0.0.1:8785/#token=dvara-key-1234567890"
    assert by["yantra"]["open"] == "http://127.0.0.1:8321/" and by["yantra"]["keyed"]


def test_yantras_link_carries_the_token_sarathi_made_for_its_page(keys):
    from sarathi.config import YANTRA_TOKEN, save_secret

    save_secret(YANTRA_TOKEN, "yantra-key-1234567890")
    by = {p["name"]: p for p in Home(config(keys), lambda: {}).pieces()}
    assert by["yantra"]["open"] == "http://127.0.0.1:8321/?token=yantra-key-1234567890"


def test_with_a_house_each_card_links_by_the_name_the_page_was_opened_at(keys):
    from dataclasses import replace

    from sarathi.config import House

    home = Home(replace(config(keys), house=House("beast.local", "192.168.1.44")),
                lambda: {})
    by = {p["name"]: p for p in home.pieces("beast.local")}
    assert by["samay"]["open"] == "http://beast.local:8780/#token=samay-key-1234567890"
    assert by["yantra"]["url"] == "http://beast.local:8321/"
    # here, at the computer, the same page links to 127.0.0.1
    assert home.pieces("127.0.0.1")[0]["url"] == "http://127.0.0.1:8321/"
    # with no house the other pages are this computer's alone, so 127.0.0.1
    plain = Home(config(keys), lambda: {})
    assert plain.pieces("beast.local")[0]["url"] == "http://127.0.0.1:8321/"


def test_a_host_header_no_link_could_hold_is_not_put_in_one(keys):
    from dataclasses import replace

    from sarathi.config import House

    home = Home(replace(config(keys), house=House("beast.local", "192.168.1.44")),
                lambda: {})
    server = HomeServer(home, GOOD, port=0)
    server.start()
    try:
        url = server.url + "api/pieces"
        for host, wanted in (("beast.local:8760", "http://beast.local:8321/"),
                             ("evil\"><script>", "http://127.0.0.1:8321/")):
            request = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {GOOD}", "Host": host})
            with urllib.request.urlopen(request) as answer:
                assert json.loads(answer.read())["pieces"][0]["url"] == wanted
    finally:
        server.stop()


def test_a_page_that_is_down_says_how_to_start_it_and_nothing_starts_it(served):
    dvara = next(p for p in get(served, "/api/pieces").json()["pieces"]
                 if p["name"] == "dvara")
    assert dvara["up"] is False and "page --as owner" in dvara["start"]
    assert ask(served, "/api/pieces", method="POST").status_code == 405


def test_pages_up_starts_say_so_and_their_ports_follow_the_settings(keys):
    on = Config(provider="ollama", door=Door(state=str(keys / "door" / "state")),
                pages=Pages(on=True, setu_port=9775, door_port=9785))
    by = {p.name: p for p in pages(on)}
    assert by["setu"].port == 9775 and by["dvara"].port == 9785
    assert by["setu"].start == by["dvara"].start == "sarathi up"


def test_the_line_under_a_page_is_its_programs_own_status(served):
    setu = next(p for p in get(served, "/api/pieces").json()["pieces"]
                if p["name"] == "setu")
    assert setu["said"] == "9 connections"


def test_a_page_whose_key_is_missing_gets_a_plain_link_and_says_so(keys):
    (keys / "setu" / "page.token").unlink()
    setu = next(p for p in Home(config(keys), dict, up=lambda _p: True).pieces()
                if p["name"] == "setu")
    assert setu["open"] == "http://127.0.0.1:8775/" and setu["keyed"] is False


def test_no_door_no_dvara_card_and_no_clock_no_samay_card(keys):
    names = [p.name for p in pages(config(keys, door=False))]
    assert names == ["yantra", "samay", "setu"]
    off = Config(provider="ollama", clock_on=False)
    assert "samay" not in [p.name for p in pages(off)]


def test_the_programs_are_asked_at_most_every_thirty_seconds(keys):
    asked = []
    home = Home(config(keys), lambda: asked.append(1) or {}, up=lambda _p: True)
    home.pieces()
    home.pieces()
    assert len(asked) == 1


def test_nothing_may_frame_it_and_its_links_send_no_referrer(served):
    headers = get(served, "/", token=None).headers
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert headers["referrer-policy"] == "no-referrer"


def test_a_picture_an_answer_carries_may_be_shown(served):
    # /phone's screen is fetched with the token and shown as a blob: URL
    policy = get(served, "/", token=None).headers["content-security-policy"]
    assert "img-src 'self' data: blob:;" in policy
    # and an answer read aloud is played from one (spoken.py through Dvara)
    assert "media-src blob:;" in policy


def test_the_home_token_is_made_once_and_kept_for_you_alone(world, monkeypatch, tmp_path):
    monkeypatch.delenv(ENV_TOKEN, raising=False)
    first = home_token()
    assert home_token() == first and len(first) >= 16
    path = tmp_path / "state" / TOKEN_FILE
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_the_pages_script_parses():
    # The Python tests never run page.js; dvara's page once broke on a name
    # declared twice while every Python test passed.
    import shutil
    import subprocess
    from importlib.resources import files
    node = shutil.which("node", path="/usr/bin:/usr/local/bin:/bin")
    if node is None:
        pytest.skip("node is not installed")
    script = files("sarathi").joinpath("static", "page.js")
    done = subprocess.run([node, "--check", str(script)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_the_chat_is_the_page_and_pages_and_settings_are_one_icon_away():
    # Each view has an icon at its own address (so a reload stays put), and
    # the stylesheet hides every section but the view's own: a section left
    # out of a rule would pile up under the chat again.
    from importlib.resources import files
    static = files("sarathi").joinpath("static")
    page = static.joinpath("index.html").read_text()
    css = static.joinpath("page.css").read_text()
    for view in ("chat", "pages", "settings"):
        assert f'href="#{view}"' in page and f'data-view="{view}"' in page
        assert f'body[data-view="{view}"]' in css
    assert 'id="chat-full"' not in page   # the chat already has the window


def test_an_answer_is_drawn_as_markdown_and_never_as_its_own_markup():
    # The chat draws an agent's answer as markdown with md.js; anything the
    # model wrote as HTML must arrive as text.
    import shutil
    import subprocess
    from importlib.resources import files
    node = shutil.which("node", path="/usr/bin:/usr/local/bin:/bin")
    if node is None:
        pytest.skip("node is not installed")
    script = files("sarathi").joinpath("static", "md.js")
    probe = (f"const {{renderMarkdown}} = require({str(script)!r});"
             "process.stdout.write(renderMarkdown('**Done**\\n\\n<script>x</script>'))")
    done = subprocess.run([node, "-e", probe], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert "<strong>Done</strong>" in done.stdout and "<script>" not in done.stdout


def test_a_phone_card_opens_yantras_page_when_sparsh_is_here(world, keys):
    names = lambda c: [p.name for p in pages(c)]  # noqa: E731
    assert "sparsh" not in names(config(keys))
    program(world / "bin", "sparsh")
    card = next(p for p in pages(config(keys)) if p.name == "sparsh")
    assert card.title == "Your phone" and card.port == 8321 and card.token() is None
    assert "phone panel on Yantra's page" in card.purpose


def test_no_phone_card_on_the_podman_road(world, keys):
    # a container can't reach a phone on a USB cable yet
    program(world / "bin", "sparsh")
    podman = Config(provider="ollama", web_port=8321, road="podman", pages=Pages(on=False))
    assert "sparsh" not in [p.name for p in pages(podman)]


# ---- the chat: Dvara's web channel, passed through ---------------------------
#
# The bias here is A PASS-THROUGH THAT SPEAKS FOR SOMEBODY ELSE. The chat
# names who is talking itself (the owner in sarathi.toml); a browser that
# sends an actor must not be able to change it, and Dvara's token must
# never reach the browser.

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
import threading  # noqa: E402

from sarathi.home import Chat  # noqa: E402

DOOR_KEY = "the-door-token-long-enough"


@pytest.fixture
def door():
    """A stand-in Dvara: records what it was asked, answers as the web
    channel does."""
    heard: list[tuple[str, str, dict]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def _answer(self, code, data):
            raw = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            heard.append(("GET", self.path, {"auth": self.headers.get("Authorization")}))
            if "/export" in self.path:
                raw = "# the boiler\n\n**You**\n\nboiler?\n".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Disposition",
                                 "attachment; filename*=UTF-8''2026-10-18-the-boiler.md")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            if self.path.startswith("/web/spoken"):
                raw = b"RIFF a voice"
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            if self.path.startswith("/web/push"):
                actor = self.path.split("actor=")[1].split("&")[0]
                return self._answer(200, {"topic": f"dvara-{actor}-0123456789abcdef"})
            self._answer(200, {"lines": [{"id": 1, "who": "notice", "text": "2 new mails"}],
                               "agents": ["greeter"], "busy": [], "asks": [], "holds": []})

        def do_DELETE(self):
            heard.append(("DELETE", self.path, {}))
            if "/open-now" in self.path:
                return self._answer(409, {"detail": "that conversation is open in a chat now"})
            self._answer(200, {"deleted": self.path.split("/")[-1].split("?")[0]})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            heard.append(("POST", self.path, body))
            if self.path.startswith("/web/asks/gone"):
                return self._answer(404, {"detail": "that question is not waiting any more"})
            self._answer(200, {"line": {"id": 2, "who": "you", "text": body.get("text")}})

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    httpd.heard = heard
    yield httpd
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def chatting(keys, door):
    home = Home(config(keys), lambda: {})
    chat = Chat(f"http://127.0.0.1:{door.server_address[1]}", DOOR_KEY, "mahen")
    server = HomeServer(home, GOOD, port=0, chat=chat)
    server.start()
    yield server
    server.stop()


def send(server, path, body, token=GOOD):
    req = urllib.request.Request(
        server.url.rstrip("/") + path, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_a_message_goes_to_dvara_as_the_owner_whoever_the_browser_says(chatting, door):
    status, said = send(chatting, "/api/chat",
                        {"agent": "greeter", "text": "hi", "actor": "guest"})
    assert status == 200 and said["line"]["text"] == "hi"
    method, path, body = door.heard[-1]
    assert (method, path.split("?")[0]) == ("POST", "/web/message")
    assert body == {"agent": "greeter", "text": "hi", "actor": "mahen"}


def test_files_go_to_dvara_with_the_message_and_dvara_checks_them(chatting, door):
    files = [{"name": "receipt.png", "data": "aGVsbG8="}]
    status, _ = send(chatting, "/api/chat", {"agent": "greeter", "text": "", "files": files})
    assert status == 200
    assert door.heard[-1][2] == {"agent": "greeter", "text": "", "files": files,
                                 "actor": "mahen"}


def test_the_chat_reads_the_owners_lines_with_the_doors_token(chatting, door):
    seen = ask(chatting, "/api/chat?after=0").json()
    assert seen["lines"][0]["text"] == "2 new mails"
    method, path, headers = door.heard[-1]
    assert path.startswith("/web?") and "actor=mahen" in path
    assert headers["auth"] == f"Bearer {DOOR_KEY}"
    assert DOOR_KEY not in ask(chatting, "/api/pieces").text


def test_an_answer_passes_on_and_dvaras_refusal_comes_back_in_its_words(chatting, door):
    status, _ = send(chatting, "/api/chat/asks/a1", {"approve": True})
    assert status == 200 and door.heard[-1][2] == {"approve": True, "actor": "mahen"}
    status, said = send(chatting, "/api/chat/asks/gone", {"approve": False})
    assert status == 404 and "not waiting" in said["detail"]
    status, _ = send(chatting, "/api/chat/holds/h1", {"answers": {"c": True}})
    assert status == 200 and door.heard[-1][2] == {"answers": {"c": True}, "actor": "mahen"}


def test_the_chat_needs_the_home_token_and_takes_no_other_post(chatting, door):
    assert send(chatting, "/api/chat", {"agent": "greeter", "text": "hi"},
                token="wrong")[0] == 401
    assert ask(chatting, "/api/chat", token="wrong").status_code == 401
    assert send(chatting, "/api/chat/other/x", {})[0] == 405
    assert door.heard == []


def test_history_lists_searches_and_reads_only_the_owners_own(chatting, door):
    ask(chatting, "/api/chat/chats?q=boiler+pressure&actor=guest")
    method, path, _ = door.heard[-1]
    assert (method, path.split("?")[0]) == ("GET", "/web/chats")
    assert "actor=mahen" in path and "guest" not in path
    assert "q=boiler+pressure" in path
    ask(chatting, "/api/chat/chats/abc123")
    assert door.heard[-1][1].split("?")[0] == "/web/chats/abc123"
    # an id is one segment on Dvara's side whatever it holds: never a step up
    ask(chatting, "/api/chat/chats/..%2Fweb")
    assert door.heard[-1][1].split("?")[0] == "/web/chats/..%252Fweb"


def test_history_passes_a_conversation_on_as_a_file_to_share(chatting, door):
    got = ask(chatting, "/api/chat/chats/abc123/export?actor=guest")
    assert got.status_code == 200 and got.text.startswith("# the boiler")
    assert got.headers["content-type"].startswith("text/markdown")
    assert "the-boiler.md" in got.headers["content-disposition"]
    method, path, headers = door.heard[-1]
    assert path.split("?")[0] == "/web/chats/abc123/export" and "actor=mahen" in path
    assert DOOR_KEY not in got.text
    assert ask(chatting, "/api/chat/chats/abc123/export", token="wrong").status_code == 401


def test_an_answer_read_aloud_comes_through_as_audio_for_you_alone(chatting, door):
    got = ask(chatting, "/api/chat/spoken?line=7&actor=guest")
    assert got.status_code == 200 and got.text == "RIFF a voice"
    assert got.headers["content-type"] == "audio/wav"
    _, path, headers = door.heard[-1]
    assert path.split("?")[0] == "/web/spoken" and "line=7" in path and "actor=mahen" in path
    assert ask(chatting, "/api/chat/spoken?line=7", token="wrong").status_code == 401


def test_an_answers_steps_come_through_for_you_alone_and_as_a_file(chatting, door):
    got = ask(chatting, "/api/chat/steps?line=7&actor=guest")
    assert got.status_code == 200
    _, path, _ = door.heard[-1]
    assert path.split("?")[0] == "/web/steps" and "line=7" in path and "actor=mahen" in path
    made = ask(chatting, "/api/chat/steps/export?line=7")
    assert made.status_code == 200 and made.headers["content-type"].startswith("text/markdown")
    _, path, _ = door.heard[-1]
    assert path.split("?")[0] == "/web/steps/export" and "actor=mahen" in path
    assert DOOR_KEY not in made.text
    assert ask(chatting, "/api/chat/steps?line=7", token="wrong").status_code == 401


def test_history_deletes_through_dvara_and_its_refusal_comes_back(chatting, door):
    status, said = send(chatting, "/api/chat/chats/abc123/delete", {"actor": "guest"})
    assert status == 200 and said == {"deleted": "abc123"}
    method, path, _ = door.heard[-1]
    assert method == "DELETE" and "actor=mahen" in path
    status, said = send(chatting, "/api/chat/chats/open-now/delete", {})
    assert status == 409 and "open in a chat" in said["detail"]
    assert send(chatting, "/api/chat/chats/abc123/delete", {}, token="wrong")[0] == 401


def test_dvara_down_is_said_not_hung(keys):
    home = Home(config(keys), lambda: {})
    server = HomeServer(home, GOOD, port=0, chat=Chat("http://127.0.0.1:9", DOOR_KEY, "mahen"))
    server.start()
    try:
        answer = ask(server, "/api/chat")
        assert answer.status_code == 502 and "isn't answering" in answer.json()["detail"]
    finally:
        server.stop()


def test_no_door_means_no_chat(served):
    assert ask(served, "/api/chat").status_code == 404
    assert ask(served, "/api/pieces").json()["chat"] is False


def test_the_chat_finds_the_doors_token_in_secrets_and_the_owner_in_settings(
        world, keys, monkeypatch):
    from sarathi.config import save_secret
    monkeypatch.delenv("DVARA_TOKEN", raising=False)
    cfg = Config(provider="ollama", door=Door(owner="mahen", port=8799))
    assert Chat.for_config(cfg) is None
    save_secret("DVARA_TOKEN", DOOR_KEY)
    chat = Chat.for_config(cfg)
    assert (chat.url, chat.token, chat.actor) == ("http://127.0.0.1:8799", DOOR_KEY, "mahen")
    assert Chat.for_config(Config(provider="ollama")) is None


def test_sarathi_home_with_the_page_already_running_prints_its_links(keys, monkeypatch,
                                                                    capsys):
    """`sarathi up` starts the home page, and `sarathi home` is what people
    type to get its link: it said "Address already in use" and nothing else."""
    from dataclasses import replace

    from sarathi import cli
    from sarathi.config import House, render, settings_path

    monkeypatch.setenv(ENV_TOKEN, GOOD)
    settings_path().parent.mkdir(parents=True, exist_ok=True)
    settings_path().write_text(render(replace(config(keys),
                                              house=House("beast.local", "192.168.1.44"))))
    running = HomeServer(Home(config(keys), lambda: {}), GOOD, port=0)
    running.start()
    try:
        port = running.httpd.server_address[1]
        assert cli.main(["home", "--port", str(port)]) == 0
    finally:
        running.stop()
    said = capsys.readouterr().out
    assert f"http://127.0.0.1:{port}/#token={GOOD}" in said
    assert f"http://beast.local:{port}/#token={GOOD}" in said


def test_sarathi_home_on_a_port_something_else_holds_is_still_an_error(keys, monkeypatch,
                                                                      capsys):
    import socket

    from sarathi import cli
    from sarathi.config import render, settings_path

    monkeypatch.setenv(ENV_TOKEN, GOOD)
    settings_path().parent.mkdir(parents=True, exist_ok=True)
    settings_path().write_text(render(config(keys)))
    other = socket.socket()
    other.bind(("127.0.0.1", 0))
    other.listen()
    try:
        assert cli.main(["home", "--port", str(other.getsockname()[1])]) == 2
    finally:
        other.close()
    assert "Address already in use" in capsys.readouterr().err
