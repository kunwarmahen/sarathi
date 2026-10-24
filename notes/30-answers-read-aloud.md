# 30 — Answers read aloud

Dvara reads an answer aloud with Piper and sends it after the words
(Dvara's [notes/64](https://github.com/kunwarmahen/dvara/blob/main/notes/64-an-answer-read-aloud.md)).
Sarathi's part is three things: a voice in the image, a choice per
person in Settings, and a play button in the home page's chat.

## A voice in the image

The image gets Piper (`piper-tts`, pinned, in its own environment under
`/opt/piper`, linked as `piper`) and one voice file,
`en_US-lessac-medium`, in `/usr/share/piper/voices`, where Dvara looks
for one. That's about 290 MB: onnxruntime is most of it, the voice 61 MB.
ffmpeg was already there for hearing voice notes; it now also turns
Piper's WAV into the OGG Opus Telegram shows as a voice note.

Another voice is a name from
[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices):

```
SARATHI_PIPER_VOICE=de_DE-thorsten-medium sarathi image
SARATHI_PIPER_VOICE= sarathi image            # none: answers stay words
```

`sarathi image` passes it as the build's `PIPER_VOICE` and says, after
the browser line, which voice the image ended up with:

```
browser in the image: Google Chrome 155.0.8059.39
voice in the image:   en_US-lessac-medium
```

On the process road Dvara uses your own Piper (`pipx install piper-tts`)
and a voice in `~/.local/share/piper/voices`.

## A choice per person

Settings → People → **Change** has **Answers read aloud**: *When they
sent a voice note* (blank in the file, Dvara's default), *Every answer*
or *Never*. It is Dvara's `speak =` for them, written and checked by
Dvara like every other box there. The card under their name says
"every answer read aloud" or "answers not read aloud" when it isn't the
default. Each person can still change their own with `/voice` in the
chat, and theirs wins.

## A play button

Every answer in the home page's chat gets **▶ Listen** when Dvara can
speak (its look says `voice: true`). Pressed, the page asks
`GET /api/chat/spoken?line=N`, which Sarathi passes to Dvara's
`/web/spoken` as you, the way a file is fetched. The WAV comes back with
the sign-in header, so it plays from a `blob:` address; the page's
security policy had no `media-src` (so `default-src 'none'` refused
audio), and gained `media-src blob:`, nothing wider. ■ Stop stops it,
and pressing another answer's ▶ stops the first.

An answer you asked to hear (a voice note sent, or *Every answer*) plays
by itself when it arrives. Only one that arrives while the page is open:
reopening the page doesn't read the morning's answers at you.

## Receipt

In a throwaway container from the current image, the new step as
written: Piper installed, the voice fetched (63 MB), *"The bins go out
on Tuesday."* made into a 74 KB WAV, and ffmpeg turned that into a 6.7 KB
OGG that starts `OggS`, which is what Telegram wants.

Then a scratch home page (`SARATHI_CONFIG`, `SARATHI_STATE` and
`SARATHI_HOME_TOKEN` set, on 8799) in front of a scratch Dvara with
`--web` (`qwen3.8-64k:latest`), driven in Chrome with its microphone fed
a recorded question. 🎤, talk, 🎤, **Send**:

```
answered after 47.2s
{"heard": "I heard: \"When do the bins go out?\"",
 "listen": "■ Stop",
 "played": ["blob:", "playing"]}
typed answer played by itself: False
{"afterPress": ["blob:", "playing"], "button": "▶ Listen"}
errors: []
```

The spoken question was answered and the answer played by itself, under
the page's real policy (no bypass). A typed question after it didn't
play by itself; pressing its ▶ did, and the button went back to
▶ Listen when it ended.

## What the tests hold

`tests/test_podman.py`: the Containerfile installs Piper and a voice
where Dvara looks, a build without `SARATHI_PIPER_VOICE` passes no voice,
and one with it passes `PIPER_VOICE`. `tests/test_home.py`: an answer
read aloud comes through as `audio/wav`, asked of Dvara as you, and not
without your key; the page's policy allows audio from `blob:`.

## What is not here yet

* **The image built with it.** The step was run in a container from the
  current image, not as part of a full `sarathi image`; that's the next
  rebuild.
* **A voice per person.** One voice for the house; Settings has no box
  for it.
* **The doctor asking about it.** `sarathi doctor` doesn't yet say
  whether Dvara can speak; `/voice` in the chat does.
