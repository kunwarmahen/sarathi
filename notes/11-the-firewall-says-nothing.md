# 11 — the firewall says nothing

*[Note 05](05-a-browser-in-the-image.md) published the door's streamed
window on the house address, and Setu's page joined it there so a
person's `/accounts page` link opens on their phone. Every check of that
was made from this computer. This note is the first one made from a
phone on the Wi-Fi.*

## A page that keeps loading

The link was made the way Dvara makes it, in a person's folder inside
the door's container, and opened in the browser of a Nexus 6P on the
same Wi-Fi:

```
$ podman exec -e SETU_HOME=…/dvara/state/setu/owner sarathi-dvara setu page-link --json
{"url": "http://192.168.1.44:8775/#link=owner.…", "person": "owner", …}
```

The phone's browser showed the address and a white page, its progress
bar stuck near the start. From this computer the same address answered
200 at once. From the phone, port by port:

```
8790 rc=0          the door's window
8775 nc: Timeout   Setu's page
8791 nc: Timeout   Setu's page's window
```

ufw was on. Port 8790 had been opened by hand for the door's window
weeks before, because the tutorial's firewall step named that port alone.
The two that came later were never opened, and nothing anywhere said so:
not Setu's log (the request never reached it), not `sarathi up` (which
checks its pages from 127.0.0.1, where no firewall stands), not the
phone (a dropped packet just looks slow).

## Named, not opened

**A FIREWALL IS NAMED, NOT OPENED.** When `window_host` is one address
and ufw (its `ENABLED=yes`, readable without root) or firewalld is on,
`sarathi up` ends with the ports published there and the command that
opens exactly those, to that address's own network:

```
$ sarathi up
…
sarathi    already running at http://127.0.0.1:8760/#token=…  (unit sarathi-home)
firewall: ufw is on; if a phone can't open 192.168.1.44 on 8775, 8790, 8791, open them to your network (once is enough):
  sudo ufw allow from 192.168.1.0/24 to any port 8775,8790,8791 proto tcp
```

It runs none of it. Opening a port needs root and is the owner's call,
and a program that edits the firewall on the way up is one nobody can
safely run twice. The price is the word "if": reading ufw's rules also
needs root, so Sarathi can't tell an open port from a closed one and
says the line every time. Two lines on every `up` seemed better than a
setup step that fails without a sound.

The network comes from the address's own interface (`ip -o addr`, so
`192.168.1.44/24` gives `192.168.1.0/24`), falling back to the /24
around it. A Tailscale address gets its own interface's network the same
way.

Only the Podman road says it. On the process road the windows take any
free port, so there is no fixed list to name.

## Not here yet

* **A check from outside.** Sarathi could ask the phone (it has adb) to
  open each port and report which time out. That would answer the "if",
  but only for a house with a phone on the cable or the Wi-Fi.
