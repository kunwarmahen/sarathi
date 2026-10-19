# 23 — every server, by one name

*[Note 11](11-the-firewall-says-nothing.md) put the pages a phone needs on
the house address: the home page, Setu's page, the sign-in windows and
ntfy. Everything else stayed on `127.0.0.1`. Yantra's page, Samay, Dvara's
page and Smritikosh opened only at this computer, and every link they
handed out said `127.0.0.1` or an IP address nobody remembers. `[house]`
puts every server on the home network, and has every link say the name
the house knows this computer by.*

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

On the Podman road, every unit keeps its `127.0.0.1` port and gets a
second `PublishPort` on the house address: Yantra's page, Samay, Dvara,
Dvara's page, Setu's page and its window, the home page, ntfy, and
Smritikosh's server, database, dashboard and its Neo4j, MongoDB and
Redis. On the plain-programs road a flag takes one address, so the
pieces listen on every address (`0.0.0.0`). This computer and the
pieces themselves keep reaching each other on `127.0.0.1`.

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
firewall: ufw is on; if a phone can't open 192.168.1.44 on 3000, 5432, 6379, 7474, 7687, 8080, 8321, 8760, 8770, 8775, 8780, 8785, 8790, 8791, 8793, 27017, open them to your network (once is enough):
  sudo ufw allow from 192.168.1.0/24 to any port 3000,5432,6379,7474,7687,8080,8321,8760,8770,8775,8780,8785,8790,8791,8793,27017 proto tcp
```

It never runs it: that needs root, and it is your call, as in note 11.

## Receipt

The units for this computer's own settings, rendered with `[house]` and
not written (an extract):

```
published on: 192.168.1.44 | links: linux-al-ml-beast.local
== sarathi-dvara.container
   PublishPort=127.0.0.1:8770:8765
   PublishPort=192.168.1.44:8770:8765
   Environment=SETU_WINDOW_URL=http://linux-al-ml-beast.local:8790
   Environment=SETU_PAGE_URL=http://linux-al-ml-beast.local:8775/
== sarathi-samay.container
   PublishPort=192.168.1.44:8780:8780
   Environment=SAMAY_PUBLIC_URL=http://linux-al-ml-beast.local:8780/
== sarathi-setu.container
   Exec=/usr/local/bin/setu serve --host 0.0.0.0 --port 8775 --public-url http://linux-al-ml-beast.local:8775/ …
== sarathi-smritikosh-db.container
   PublishPort=192.168.1.44:5432:5432
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
* **Passwords for the databases' ports.** PostgreSQL has its own
  password from Smritikosh's `.env`. Neo4j, MongoDB and Redis keep
  whatever their containers were made with. Publishing them was asked
  for. The firewall line is what keeps them to the house.
* **A name made up for you.** Sarathi doesn't set up Avahi or a DNS
  entry. `name` is whatever your network already answers to.
