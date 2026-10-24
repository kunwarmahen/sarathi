# 31 — A voice for each language

Dvara reads an answer in the person's own voice, or in one for the
answer's language when theirs doesn't speak it, and under "always"
reads what's sent unasked too (Dvara's
[notes/65](https://github.com/kunwarmahen/dvara/blob/main/notes/65-whose-voice-and-which-language.md)).
That only helps if the voices are there. Sarathi's part is saying which
voices the house has, putting them where Dvara looks on both roads, and
a box to give each person one.

## One list, both roads

```toml
[dvara]
voices = ["en_US-lessac-medium", "hi_IN-pratham-medium"]
```

Piper's names from
[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices),
checked as names when sarathi.toml is read (`language_REGION-who-quality`),
so a typo is said at once rather than as a failed download in the middle
of a build. English alone when the key is missing; `[]` for none.

* **Podman road:** `sarathi image` passes the list as `PIPER_VOICES`,
  and the image's step fetches each into `/usr/share/piper/voices`.
* **Plain programs:** `sarathi dvara --voices en_US-lessac-medium,hi_IN-pratham-medium`
  writes the list and fetches each voice that isn't already in
  `~/.local/share/piper/voices` (the card first, it's small; a name
  that isn't there is said, and the rest still come). On the Podman road
  the same command writes the list and says to run `sarathi image`.

Both fetch from the same pinned place (`resolve/v1.0.0`), so a voice
that works on one road works on the other. That set has Hindi
(`hi_IN-pratham-medium`, `hi_IN-priyamvada-medium`), Malayalam, Nepali,
English, German and many more; voices added since (Telugu, Marathi and
Urdu among them, in Piper's current list) would need the pin moved.

## In Settings

**Settings → Sarathi → Dvara** has *Voices for answers read aloud*, the
same list with commas, refused by name the same way. After a change the
image needs `sarathi image` on the Podman road (the box's hint says so).

**Settings → People → Change → Their voice** offers every voice Dvara
finds on this computer, and on the Podman road the image's list too
(the computer and the image can hold different ones), with *The house's*
first. It is Dvara's `voice =` for them; their own `/voice use N` in the
chat still wins. The card under their name says *read in …* when one is
set. *Answers read aloud* now says that *Every answer* includes what's
sent unasked, like a morning brief.

## Receipt

`fetch_voices` for real, into a scratch folder:

```
['fetched the voice hi_IN-priyamvada-medium to /tmp/vtest',
 "the voice xx_XX-nobody-medium couldn't be fetched (HTTP Error 404: Not Found);
  is the name right? https://huggingface.co/rhasspy/piper-voices lists them"]
1.8s
```

The image's new step with two voices, run in a throwaway container from
the current image: both voices in `/usr/share/piper/voices`, a Hindi
sentence read by `hi_IN-pratham-medium` and made into an `OggS` voice
note by the image's ffmpeg.

## What the tests hold

`tests/test_door.py`: voices read back as written, English when unset,
a wrong name refused; a voice fetched from where the image fetches it;
voices fetched once and a missing one said; `sarathi dvara --voices`
writing the list and fetching on plain programs, refusing "hindi".
`tests/test_podman.py`: the image takes the list, English when unset,
both names when two. `tests/test_settings_page.py`: voices typed with
commas, a wrong name refused.

## What is not here yet

* **The doctor comparing the list with the image.** A list changed
  since the last `sarathi image` isn't flagged; `/voice` in the chat
  lists what Dvara actually has.
* **Voices newer than the pin.** Telugu, Marathi, Urdu and the other
  voices added after `v1.0.0` need the pin moved in the Containerfile and in
  `door.py` together.
