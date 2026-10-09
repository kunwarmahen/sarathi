"""The settings file, and the questions that write it.

The bias these tests encode: A SETTING NOBODY CHOSE NEVER TAKES EFFECT,
AND A KEY NEVER LANDS WHERE IT COULD LEAK. A misspelt table or key stops
everything with its name; a cloud key is typed at a hidden prompt and
saved readable by its owner only, or used from the environment and never
copied; and the local road suggests a model that is actually pulled.
"""

from __future__ import annotations

import argparse
import stat

import pytest

from sarathi import config, first_run
from sarathi.config import Config, ConfigError, parse, render


def init_args(**given) -> argparse.Namespace:
    base = dict(provider=None, model=None, base_url=None, web_port=None, clock_port=None,
                no_clock=False, podman=False, force=False)
    return argparse.Namespace(**{**base, **given})


def test_what_init_writes_reads_back_as_the_same_settings(world):
    for chosen in (Config("ollama", "gemma4:12b", "http://box:11434/v1", 8400, False, 8781,
                          "podman"),
                   Config("ollama", context_window=64000),
                   Config("anthropic")):
        assert parse(render(chosen)) == chosen


@pytest.mark.parametrize("text, says", [
    ('[model]\nprovider = "ollama"\n[clok]\non = false\n', "unknown table [clok]"),
    ('[model]\nprovider = "ollama"\nmodle = "x"\n', "unknown key model.modle"),
    ('[model]\nprovider = "gemini"\n', "model.provider must be one of"),
    ('[model]\nprovider = "ollama"\n[web]\nport = "8321"\n', "web.port must be a port"),
    ('[model]\nprovider = "ollama"\n[clock]\non = "yes"\n', "clock.on must be true or false"),
    ('[model]\nprovider = "ollama"\n[run]\nroad = "docker"\n', "run.road must be one of"),
    ('[model]\nprovider = "ollama"\ncontext_window = "64k"\n', "model.context_window must be"),
    ('[model]\nprovider = "ollama"\ncontext_window = 64\n', "model.context_window must be"),
    ('[model\n', "not valid TOML"),
])
def test_a_setting_it_does_not_know_stops_everything_by_name(text, says):
    with pytest.raises(ConfigError, match=says.replace("[", r"\[")):
        parse(text)


def test_no_settings_yet_says_to_run_init(world):
    with pytest.raises(ConfigError, match="run `sarathi init` first"):
        config.load()


def test_without_a_terminal_init_asks_for_the_provider_as_a_flag(world, capsys):
    assert first_run.run(init_args(), interactive=False) == 2
    assert "--provider ollama|anthropic|openai" in capsys.readouterr().err


def test_the_local_road_suggests_a_pulled_model_that_can_talk(world, monkeypatch):
    monkeypatch.setattr(first_run, "ollama_models", lambda root: [
        "nomic-embed-text:latest", "gemma4:12b", "qwen3.8:latest"])
    assert first_run.run(init_args(provider="ollama"), interactive=False) == 0
    assert config.load().model == "qwen3.8:latest"


def test_the_local_road_offers_a_choice_and_never_an_embedding_model(world, monkeypatch,
                                                                     capsys):
    monkeypatch.setattr(first_run, "ollama_models",
                        lambda root: ["nomic-embed-text:latest", "gemma4:12b", "qwen3.8:latest"])
    answers = iter(["1", "2"])
    assert first_run.run(init_args(), ask=lambda q: next(answers), interactive=True) == 0
    assert config.load() == Config("ollama", "gemma4:12b")
    assert "nomic" not in capsys.readouterr().out


def test_a_model_not_pulled_is_written_with_the_command_that_pulls_it(world, monkeypatch,
                                                                      capsys):
    monkeypatch.setattr(first_run, "ollama_models", lambda root: ["gemma4:12b"])
    first_run.run(init_args(provider="ollama", model="qwen3.8:27b"), interactive=False)
    assert config.load().model == "qwen3.8:27b"
    assert "`ollama pull qwen3.8:27b`" in capsys.readouterr().out


def test_ollama_not_answering_still_leaves_a_working_file(world, monkeypatch, capsys):
    monkeypatch.setattr(first_run, "ollama_models", lambda root: None)
    assert first_run.run(init_args(provider="ollama"), interactive=False) == 0
    assert config.load() == Config("ollama")
    assert "start it (`ollama serve`)" in capsys.readouterr().out


def test_a_typed_key_is_saved_readable_only_by_its_owner(world):
    first_run.run(init_args(provider="anthropic"), ask_secret=lambda q: "sk-typed",
                  interactive=True)
    path = config.secrets_path()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert config.read_secrets() == {"ANTHROPIC_API_KEY": "sk-typed"}
    assert "sk-typed" not in config.settings_path().read_text()


def test_a_key_already_in_the_environment_is_never_copied(world, monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    first_run.run(init_args(provider="openai"), ask_secret=lambda q: pytest.fail("asked"),
                  interactive=True)
    assert not config.secrets_path().exists()
    assert "from your environment (not copied anywhere)" in capsys.readouterr().out


def test_init_will_not_replace_settings_unless_told(world):
    first_run.run(init_args(provider="ollama", model="a"), interactive=False)
    assert first_run.run(init_args(provider="ollama", model="b"), interactive=False) == 1
    assert config.load().model == "a"
    assert first_run.run(init_args(provider="ollama", model="b", force=True),
                         interactive=False) == 0
    assert config.load().model == "b"


def test_the_context_window_reaches_yantra_on_both_roads(world):
    # Yantra's .env is not in the image: without this, a 64k model in a
    # container is shortened at Yantra's 8192 default.
    from sarathi import podman, services
    chosen = parse('[model]\nprovider = "ollama"\ncontext_window = 64000\n')
    assert services.model_env(chosen, {})["OLLAMA_CONTEXT_WINDOW"] == "64000"
    assert podman.container_env(chosen)["OLLAMA_CONTEXT_WINDOW"] == "64000"
    unset = parse('[model]\nprovider = "ollama"\n')
    assert "OLLAMA_CONTEXT_WINDOW" not in services.model_env(unset, {})
    assert "OLLAMA_CONTEXT_WINDOW" not in podman.container_env(unset)
