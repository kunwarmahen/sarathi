# 14 — everyone in the house

*[Note 12](12-a-chat-on-the-home-page.md) put a chat on the home page,
passed through to Dvara's web channel. It spoke as one person: you, the
owner, because the page's key is yours. This note lets the other people
in the house sign in to the same page and talk to their own agents,
as themselves.*

## The problem, as you would meet it

Priya is in Dvara's actors file. She has her own allowance, her own
agents, her own folder and her own Gmail sign-in, and she can use all of
them from Telegram. She doesn't use Telegram. The home page has a chat,
but it is yours: its key opens every program's page and every key on
the ring, so you can't hand it to her. Her only way in was `curl` with
Dvara's token, which is worse.

## A sign-in in front of the chat

```bash
sarathi invite priya
```
```
priya's link, for one device, within 48 hours:
  http://192.168.1.44:8760/#invite=priya.4Ljrd…
They open it and choose a password; after that they sign in with 'priya' and that password, and see their own chat only.
```

She opens it on her phone, chooses a password, and the page is her
chat. Next time she signs in with her name and that password. The
home page has **People in the house** for you as well: everyone in the
actors file, whether they have signed in and on how many devices, an
**Invite** button that shows the link to send, and **Sign out
everywhere**.

**ONE PERSON, ONE DVARA ACTOR.** A sign-in is an id from Dvara's actors
file and nothing else. Her allowance, rules, folder, memories and Setu
sign-ins are the ones that id has on Telegram. None of that is kept
here, so none of it can drift from Dvara. Only the conversation belongs
to the page (Dvara's `web:chat` thread). A name that isn't in the actors
file can't be invited, and you can't invite yourself: your way in is
still the page's key.

**THE OWNER ADDS THEM.** There is no sign-up form. Nobody can make
themselves a person in this house by finding the address.

**THE LINK WORKS ONCE.** The first device to open it chooses the
password and uses the link up. The same link later, or forwarded, opens
nothing. A newer invite replaces one not yet used. A second invite for
someone who already signed up is how a forgotten password is reset, and
using it signs out every device they had.

**THEIR CHAT AND NOTHING ELSE.** Signed in, a person gets `/api/me` and
the chat. Every owner's door answers 403 for them: the cards and their
keys, the memory switch, the list of people, inviting. The page in
their browser draws only the chat, but the server enforces the line, not
the script. Who they are comes from their session on every call. A
body that says `"actor": "owner"` is ignored, as it was in note 12.

**YOU SEE WHAT DVARA'S PAGE ALREADY SHOWS YOU.** Their turns are on
Dvara's page with who, which agent, the cost and the tools, labelled
*web*, and their words stay theirs. That rule was already Dvara's; this
note adds no second one.

## Why here, and not in Dvara

Sarathi holds the wiring and no logic of its own, and a sign-in looks
like logic. But Dvara's web channel was built to trust a caller that
names the person (note 34 there), and the home page was already that
caller, holding the only key that can open it. So who may open the home
page is the home page's question, the same as its own key was. What a
person may DO once they're in (agents, allowance, rules, memories) is
never asked here; Dvara answers it as it does on Telegram.

## Where the phone reaches it

The home page listened on this computer only. With `[dvara]
window_host` set to one address (your home network, or Tailscale), the
same address Setu's page already uses for people's links, `sarathi up`
now starts the home page there too (`--also-host`), and the invite link
uses it. Without it, the link opens on this computer only, and both
`sarathi invite` and the page say so. If the address can't be listened
on (Tailscale down, say), the home page still starts for you on
127.0.0.1 and prints why. On the Podman road the home page is a user
service on the host, so the same flag goes in its unit. The firewall
line `up` prints now has the home page's port too:

```
firewall: ufw is on; if a phone can't open 192.168.1.44 on 8760, 8775, 8790, 8791, open them to your network (once is enough):
  sudo ufw allow from 192.168.1.0/24 to any port 8760,8775,8790,8791 proto tcp
```

## What is kept, and how

`~/.local/share/sarathi/people.json`, yours alone, beside the home
page's own token:

* the password as scrypt with its own salt;
* an invite and each device's session only as a SHA-256 of it.

A copy of the file gives nobody a way in. A device stays signed in until
it signs out, you sign that person out (`sarathi people --sign-out
priya`, or the button), or it goes 90 days unused. Five wrong passwords
for one name in fifteen minutes and that name waits out the rest of
them. A wrong name and a wrong password get the same words, and take the
same time.

Over plain HTTP on your home network, a password crosses Wi-Fi the way
every other page here does. Tailscale encrypts it. A home network you
don't trust is a reason to use Tailscale, for this page and the rest.

## Receipt

A scratch Dvara on 8798 (`serve --web`, the example agents plus `priya`
with `agents = ["greeter"]`, `qwen3.8:latest` through Ollama) and the
home page in front of it on 8797 with `--also-host 192.168.1.44`:

```
$ sarathi invite stranger
error: stranger isn't in Dvara's actors file. Add [actor.stranger] there first (who they are, which agents, their allowance), then invite them
$ sarathi invite owner
error: owner is you: your way in is the home page's own address, the one `sarathi home` prints

POST http://192.168.1.44:8797/api/claim {link, password}  -> {"name": "priya", "session": "s.…"}
POST the same link again  -> "that link has been used, has run out, or was replaced by a newer one: ask for a new one"
GET  /api/me as priya     -> {"owner": false, "name": "priya", "chat": true}
GET  /api/pieces as priya -> 403
POST /api/chat as priya {"agent": "greeter", "text": "Hello! My name is Priya. …", "actor": "owner"}
greeter : Hi Priya, I'm the doorkeeper's greeter, just here at the front desk.
agents: ['greeter']
```

The owner's own chat on the same page stayed empty (0 lines), with all
four agents. Dvara's record of the turn:

```
2026-10-11 20:15  web       priya/greeter  end_turn  $0.0000  'Hello! My name is Priya. …'
```

In Chrome at 390 pixels wide, the guest's invite link opened *Choose your
password* with the name filled in. Their message got *"I greet you at the
door and answer quick, simple questions."*, and the top said *Signed in
as guest · Sign out*, with no cards. After signing out, a wrong password
said *that name and password don't match*, and the right one brought the
two lines back. The owner's page at 1100 pixels listed guest, priya and
ravi, and **Invite** for ravi showed the link to send. The browser run
found one bug: the chat's Send button was looked up as the page's first
`.send`, which is now the sign-in button. Fixed.

## What is not here yet

* **Push to a phone.** As in note 12: lines wait until the page asks.
  A page installed on a phone that is woken by a notice may come later.
* **A person's Setu page from here.** They still ask for it in the chat
  (`/accounts page`, Dvara's note 31). A link on their side of this page
  would be one more door through the same sign-in.
* **The Podman road, tried.** The unit gets `--also-host`. It was run as
  plain programs.
