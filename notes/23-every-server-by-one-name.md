# 23 — every page, by one name

*[Note 11](11-the-firewall-says-nothing.md) put the pages a phone needs on
the house address: the home page, Setu's page, the sign-in windows and
ntfy. Everything else stayed on `127.0.0.1`. Yantra's page, Samay, Dvara's
page and Smritikosh opened only at this computer, and every link they
handed out said `127.0.0.1` or an IP address nobody remembers. `[house]`
puts every page you open in a browser on the home network, and has every
link say the name the house knows this computer by. What only the
pieces talk to stays on this computer.*

## One table, two words

```toml
[house]
name = "linux-al-ml-beast.local"
address = "192.168.1.44"
```

`name` is what the house's other devices call this computer. Avahi
answers `<hostname>.local` on most home networks, and a router may have
its own name for it. Every link says it. `address` is the one address
everything is published on. Unset, it is what the name finds here, the
first IPv4 address. A name is no use to `PublishPort`, which needs an
address, and an address is no use to a person, who won't remember it.

## Published on both, linked by name

**THE PAGES, AND NOTHING BEHIND THEM.** On the Podman road each page
keeps its `127.0.0.1` port and gets a second `PublishPort` on the house
address: Yantra's page, Samay's, Dvara's page, Setu's page, the home
page, and Smritikosh's dashboard. So do the two things a page sends a
phone to: the sign-in windows (8790, 8791, and 8792 for a sign-in
started on Yantra's page) and ntfy, which were on the house address
already (note 11). What only the pieces talk to stays on
`127.0.0.1`: Dvara's own port (8770, which answers Samay and its page,
not a browser), Smritikosh's server and its PostgreSQL, Neo4j, MongoDB
and Redis. Nothing on another device has a reason to reach those, and a
port nobody needs open is one less thing to guard. On the plain-programs
road a flag takes one address, so the pages listen on every address
(`0.0.0.0`). Dvara and Smritikosh stay on `127.0.0.1` there too.

Then the words that leave each piece say the name:

| What | Says |
|---|---|
| Samay's printed address (`SAMAY_PUBLIC_URL`) | `http://linux-al-ml-beast.local:8780/` |
| Setu's page (`--public-url`), a person's `/accounts page` link (`SETU_PAGE_URL`) | `http://linux-al-ml-beast.local:8775/` |
| a sign-in window's link (`SETU_WINDOW_URL`, and `SETU_WINDOW_NAME` on the plain road) | `http://linux-al-ml-beast.local:8790/w/…` |
| an invite to the home page, ntfy's subscribe link | the name, on their ports |
| Smritikosh's dashboard (`AUTH_URL`; it listens everywhere) | the name, since its sign-in sends you to that one name |

**The home page links by the name you opened it at.** Its cards are
built from the request's own `Host`. Opened as
`http://linux-al-ml-beast.local:8760/` on a phone, every card says
`linux-al-ml-beast.local`. Opened as `127.0.0.1` at this computer, they
say `127.0.0.1`. Both work, because every page is on both. A `Host`
that isn't a plain name or address is not put in a link. Without
`[house]` the cards stay on `127.0.0.1`, since nothing else is published
there.

## Yantra's page gets a token

Yantra's page runs a shell. On the house network it would be a shell
for every device on the Wi-Fi, so it now wants a token whenever it
listens beyond this computer (Yantra's notes/132). Sarathi makes one
token, keeps it in `secrets.env` as `YANTRA_WEB_TOKEN`, and passes it to
Yantra alone: in Yantra's own env file on the Podman road, and in its
environment on the plain road. No other piece gets it. The home page's
Yantra card links to `/?token=…`. Opening it once on a device sets a
cookie, and that device stays in. Sarathi passes the token on both
roads, with or without `[house]`, so the same card works either way.

## Gmail, from the phone

With `[house]`, Dvara's sign-in window is on whether or not
`window_host` was set. Dvara's `/connect gmail` then streams Google's own
page to the phone, so its return to `127.0.0.1` lands on this computer
(Dvara's notes/52). Google won't send that return anywhere else. No name
on the house network would have helped Gmail on its own.

## The firewall

`sarathi up` names every published port, and the one command that opens
them to the house's network alone:

```
firewall: ufw is on; if a phone can't open 192.168.1.44 on 3000, 8321, 8760, 8775, 8780, 8785, 8790, 8791, 8793, open them to your network (once is enough):
  sudo ufw allow from 192.168.1.0/24 to any port 3000,8321,8760,8775,8780,8785,8790,8791,8793 proto tcp
```

It never runs it: that needs root, and it is your call, as in note 11.

## Receipt

The units for this computer's own settings, rendered with `[house]` and
not written (an extract):

```
published on: 192.168.1.44 | links: linux-al-ml-beast.local
== sarathi-dvara.container
   PublishPort=127.0.0.1:8770:8765
   PublishPort=192.168.1.44:8790:8790
   Environment=SETU_WINDOW_URL=http://linux-al-ml-beast.local:8790
   Environment=SETU_PAGE_URL=http://linux-al-ml-beast.local:8775/
== sarathi-samay.container
   PublishPort=192.168.1.44:8780:8780
   Environment=SAMAY_PUBLIC_URL=http://linux-al-ml-beast.local:8780/
== sarathi-setu.container
   Exec=/usr/local/bin/setu serve --host 0.0.0.0 --port 8775 --public-url http://linux-al-ml-beast.local:8775/ …
== sarathi-dvara-page.container
   PublishPort=192.168.1.44:8785:8785
== sarathi-smritikosh.container, -db, -neo4j, -mongodb, -redis
   (127.0.0.1 only)
== sarathi-yantra.container
   PublishPort=192.168.1.44:8321:8321
dashboard: next start --hostname 0.0.0.0 --port 3000, AUTH_URL=http://linux-al-ml-beast.local:3000
```

Yantra's page with its token, asked over the house name, answered 401
without the token and 200 once the link had been opened (Yantra's
notes/132). Running all of it on the Podman road needs `sarathi image`
first, since the token and Gmail's window are in the newer Yantra, Setu
and Dvara.

## What was deliberately not built

* **Publishing on every address on the Podman road.** One address
  keeps the pieces off other networks this computer is on (a VPN, a
  container bridge). The plain road has no such choice, and its
  firewall line is what narrows it.
* **What isn't a page, on the house address.** Dvara's own port,
  Smritikosh's server, and its PostgreSQL, Neo4j, MongoDB and Redis are
  reached by the pieces alone, on this computer. Your memories are seen
  from another device through Smritikosh's dashboard, which is a page.
* **A name made up for you.** Sarathi doesn't set up Avahi or a DNS
  entry. `name` is whatever your network already answers to.
