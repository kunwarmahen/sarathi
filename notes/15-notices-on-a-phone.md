# 15 — notices on a phone

*[Note 14](14-everyone-in-the-house.md) let each person in the house
sign in to a chat of their own. Two things stayed in the chat or on
Telegram: notices reached their phone only through Telegram, and their
own Setu page only through `/accounts page`. This note brings both to
the home page.*

## The problem, as you would meet it

Priya signs in to the home page and doesn't use Telegram. Her 7 am
schedule's answer waited on the page until she opened it after
breakfast. To see her own accounts she had to type `/accounts page`
into a chat with an agent, which is an odd place for it.

## ntfy, started by Sarathi

```bash
sarathi dvara --ntfy          # [dvara] ntfy = true, ntfy_port = 8793
sarathi up
```

`up` starts ntfy, a small push server, before Dvara. Dvara then posts
every notice for every person to their own topic there (Dvara's note 40).
The pieces:

* **WHERE IT LISTENS.** On `[dvara] window_host` when that is one
  address, the same address people's phones already use for the home
  page and Setu's, so a phone at home reaches it. Otherwise on
  `127.0.0.1`, where nothing but this computer hears it, and the page
  says so. Never on every address.
* **WHERE A TAP GOES.** Dvara gets `DVARA_NTFY_CLICK`, the home page on
  that address, so tapping a notice opens the chat it came from.
* **PLAIN PROGRAMS.** On plain programs it is ntfy's own program, found
  on PATH or as `SARATHI_NTFY`. If it isn't installed, `up` says so, and
  Dvara is not pointed at a server that isn't there.
* **CONTAINERS.** On Podman it is ntfy's own image, pinned
  (`docker.io/binwiederhier/ntfy:v2.11.0`), in a unit of its own
  (`sarathi-ntfy`) on the shared network. Its cache is in a volume, and
  Dvara reaches it as `http://sarathi-ntfy:80`. Since it isn't
  Sarathi's image, `sarathi image` never restarts it. Its port joins the
  firewall line `up` prints.
* **AN IPHONE, WOKEN THROUGH NTFY.SH, NEVER WITH THE WORDS.** iOS lets an
  app wake only through Apple's push, and only ntfy.sh can ask Apple for
  it. A server in the house can be posted to all day, but an iPhone shows
  nothing until someone opens the app. So `[dvara] ntfy_upstream =
  "https://ntfy.sh"` starts ntfy with `--upstream-base-url` set to it.
  For each message, ntfy tells ntfy.sh only that one came: its id and a
  hash of the topic. ntfy.sh wakes the iPhone, and the iPhone fetches the
  words from the house. The price is that ntfy.sh learns *when* a
  notice came, never *what* it said. That is why this is off unless it
  is set (and a checkbox on the settings page).
* **THE ADDRESS THE PHONE TYPED.** The hash is of the server address
  together with the topic, so ntfy is told, as its `--base-url`, the
  exact address the phone subscribed with. That is the house's name by
  default. `[dvara] ntfy_url` overrides it for a phone that was set up
  with `http://192.168.1.44:8793`, and the home page's **Notices on this
  phone** then shows that address too. If the two addresses differ,
  ntfy.sh wakes nothing, without any error.

## On the page, for each person

**Notices on this phone** (in the chat, for you and for each person
signed in) asks Dvara for their topic and shows the house's server,
their topic, and a link that opens the ntfy app subscribed
(`ntfy://host:port/topic?secure=false`). The page keeps nothing: the
topic is Dvara's, made from a key only Dvara holds, and it is shown only
to the person it belongs to.

**My accounts** (on a person's side) asks Dvara for the one-time link
`/accounts page` makes, by the same code, and shows it as a link to tap.
A phone blocks a window opened after a wait, so the link isn't opened
for them. When there is no link to make (the owner turned people's
pages off, their accounts are in a shared folder), Dvara's words say
why.

**A BUTTON PRESSED ON THE PHONE.** A skill offered comes with **Keep**
and **Not now**. The ntfy app presses them at `POST /api/push/answer`
on the home page, with no sign-in, since it holds none of ours. The page
passes the press to Dvara as it came, and Dvara takes it only with the
mark it made for that one offer (Dvara's notes/40).

## Receipt

ntfy's pinned image started with the unit's own command and answered
`200`. A scratch Dvara pointed at it posted a quiet look back's notice
and a refused sign-in's notice, each to its own person's topic, read
back from the server (Dvara's note 40). The Sarathi pieces (the plan,
the units, the page's two routes) are covered by tests. They have not
been run on either road, and no real phone has received a notice yet.

An iPhone, on the Podman road. The owner's topic had 5 notices posted
to it over a night (a look back, a skill offered, the morning brief),
and ntfy's stats said `subscribers=0`. The app showed the notices only
when opened, and the phone never buzzed. With `ntfy_url =
"http://192.168.1.44:8793"` and `ntfy_upstream = "https://ntfy.sh"`, the
unit's line became `Exec=serve ... --cache-duration 24h --base-url
http://192.168.1.44:8793 --upstream-base-url https://ntfy.sh`, and from
inside the container `https://ntfy.sh/v1/health` answered
`{"healthy":true}`.

The house side was then proved on its own terms. A listener on
`https://ntfy.sh/<sha256 of base-url/topic>/json` saw a `poll_request`
about three seconds after each local post. Even so, the iPhone stayed
silent through three tests, after it re-subscribed by the house's name
and after its Default Server was set to that name. Each time the message
was there on refresh. What fixed it was deleting and reinstalling the
app, setting the Default Server before adding the topic. The next test
reached the locked phone. So `base-url` must equal the app's *Default
Server*, not only the server typed for one subscription, and an app that
subscribed before upstream was on may need a fresh install.

## What the tests hold

`tests/test_ntfy.py`: the setting reads, writes and refuses a word;
ntfy listens on the house address or this computer alone; Dvara is
pointed at it before `serve` and told where a tap opens; with no ntfy
installed, `up` says so and Dvara gets no `--ntfy`; the Podman road
brings ntfy's image, published on 127.0.0.1 and the house address, with
Dvara after it; an iPhone is woken through ntfy.sh only when
`ntfy_upstream` is set, with the phone's address as the base-url, on both roads; `ntfy_url` wins over the house name, and both
settings read, write, and refuse an address with no `http`. `tests/test_people.py`: **My accounts** asks Dvara for
the signed-in person's own link and nobody else's; **Notices on this
phone** names their own topic on the house's server, and is off without
ntfy.

## What is not here yet

* ~~**A real phone.** On an iPhone, a server in the house can't wake the
  app.~~ It can, through ntfy.sh, with the words kept home (above).
* **Away from home.** A phone hears notices while it can reach the
  house. Tailscale would carry them further, and is not set up here.
