# 28 — The doctor

Something stops working, and the question isn't "what is each piece
doing?" (`sarathi status`) but **what's broken, and what do I type?**
A phone that can't open a page, because ufw drops the port. An image
built before yesterday's fix. A Gmail sign-in that Google ended. A
schedule that failed at 08:00. A model that holds 8,192 tokens while
Yantra plans for 65,536, so Ollama silently drops the tools. Each of
those is already known to some program here, and until now each was
found only by the thing it broke.

```
$ sarathi doctor
0 to fix, 5 worth a look, 8 fine

! worth a look  phone: iphone isn't connected: not answering -- start WebDriverAgent on it
      fix: plug it in, unlock it, then `sparsh iphone`
! worth a look  phone: the iPhone's WebDriverAgent signature runs out Sat 24 Oct 14:49: rebuild it ...
      fix: on the Mac: ./build-wda-on-mac.sh, then `sparsh iphone WDA.ipa`
! worth a look  image: the image is older than the code: dvara 4db57fa, prahari 1199c1d, ...
      fix: sarathi image && sarathi up
! worth a look  firewall: ufw is on, and its rules need root to read; if a phone can't open ...
      fix: sudo ufw allow from 192.168.1.0/24 to any port 3000,8321,... proto tcp
✓ fine  model: qwen3.8-64k:latest is pulled and answering; it holds 65536 tokens
✓ fine  setu: 13 accounts, none marked stopped (Setu tries each sign-in once a day)
✓ fine  samay: Samay is running; 0 runs in the last day, none failed
✓ fine  running: 11 of 11 pieces `sarathi up` started are running
✓ fine  memory: Smritikosh is answering
✓ fine  disk: 80.0 GB free where /home/mahen is
```

Settings → **Check** on the home page asks the same thing
(`GET /api/doctor`, the owner's only) and draws the same lines.

## It reads, it doesn't guess

Every line comes from the program that knows:

| line | told by |
|---|---|
| a sign-in stopped | Setu's own mark, set by its daily try (`setu status --json`) |
| a schedule failed | Samay's new `recent`: the last day's runs, failed ones named by their schedule's words (Samay's status) |
| a phone not connected, the iPhone's signature | Sparsh's status (`named`, `wda.days_left`) |
| the model: served, pulled, how much it holds | Yantra's status, which now asks Ollama for the loaded model's context length, else the `num_ctx` it was made with |
| Dvara's problems | Dvara's status |
| a piece stopped | what `up` started (systemd or a pid), and the end of its log |
| the image older than the code | Podman's image date against each checkout's last commit; containers still on an older one |
| ports shut to phones | `sudo -n ufw status` (or `firewall-cmd --list-ports`) |
| disk | free space where home and Podman's storage are |

Two of those were new knowledge in a sibling, not in Sarathi. Samay's
status didn't say what failed, and Yantra's didn't say how much the
model holds. Both now do, in their own `status --json`, where any other
program can read it too.

## Red, amber, green, and nothing changed

**Red** is broken now: something you rely on doesn't work until it's
fixed (a stopped piece, an expired sign-in, a shut port, a model
holding less than the plan, no image). **Amber** works, or can't be
seen from here, and may not work tomorrow (an image older than the code,
a phone unplugged, a signature running out, a failed run). **Green** is
fine. Each red and amber line carries its fix. The doctor runs none of
them: opening a port needs root, a rebuild takes minutes, and a sign-in
needs the person. It exits 1 when anything is red, so a script can ask
it too.

**What it can't see, it says.** ufw's rules are root's to read. The
doctor tries `sudo -n`, which never prompts. When that isn't allowed,
the line is amber, says why, and gives the line to run "if a phone can't
open a page". It's never marked "open" on a guess. The same goes for
Google: a sign-in's end is known only by using it, which Setu does once
a day, so the doctor repeats Setu's mark and doesn't make a new try.

**What doesn't cry wolf.** A cloud model isn't tried, because that costs
a call. A piece turned off in `sarathi.toml` isn't reported missing, and
an optional program that isn't installed isn't mentioned at all.
Smritikosh's own databases (Postgres, Neo4j, MongoDB, Redis) run their
own images, so they're never "on an older image". The first live run
said they were, and that was fixed before this landed. A plan of 64,000
on a 65,536 model is the docs' own advice: only a model holding a
quarter more than the plan gets a line.

## Live receipt

On this house, Podman road, everything up. The doctor's own first run
found two of its own mistakes. The memory store's databases were listed
as "on an older image", and 64,000 against 65,536 came up as wasted room.
After the fixes, the result was 0 red, 5 amber, 8 green:

* both phones unplugged;
* the iPhone's signature running out tomorrow;
* the image four commits behind;
* ufw unreadable without root, with the full `sudo ufw allow` line.

All five are true. The Check tab, on a scratch home page (port 8797),
answered in 2.3 seconds, drew the same 13 lines wide in light mode and
at phone width in dark mode, and refused anyone without the token (401).

## What is not here

* **No fix button.** A fix that needs root or the person stays a line
  to type. The places the home page can already fix something (Apply,
  Bring it back, My accounts) are where those fixes live.
* **No near-expiry for Google sign-ins.** Only using the token tells,
  and Setu already does that daily. The iPhone's signature has a date,
  so it gets one.
* **No exact tool-token count.** The window check compares what the
  model holds with what Yantra plans for, plus a floor (16k) under which
  a big connection won't fit. Selection on many tools (Yantra's note 106)
  handles the rest.
* **Not on a schedule.** A nightly doctor that messages you is one
  Samay schedule away. It wasn't added until someone wants it.

Tests: `tests/test_doctor.py` (25). The bias is a known problem not
said, and its opposite, a doctor that cries wolf.
