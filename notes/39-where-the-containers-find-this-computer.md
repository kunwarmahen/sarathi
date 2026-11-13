# 39 — Where the containers find this computer

Ollama runs on this computer, not in a container. Each container reaches
it at `host.containers.internal`, the name Podman gives the host. Podman
5.7 points that name at 169.254.1.2, which doesn't reach this computer
from the `sarathi` network. Every chat then ended *that went wrong at my
end*, because the model never answered.

The quick fix was to pin this computer's address in
`~/.config/containers/containers.conf`:

```toml
[containers]
host_containers_internal_ip = "192.168.1.44"
```

That address comes from the router. The day it hands out another one,
every container loses Ollama at once, and nothing says why.

Continues [03 — two containers, one clock](03-two-containers-one-clock.md).

## The rules

**WORKED OUT EACH TIME A CONTAINER STARTS.** Every container unit now
`Wants=` and starts `After=` a one-shot service, `sarathi-host-address`.
That service runs `sarathi host-address`, which finds the address
`ip route get` names as the way out (the one Ollama is reached on) and
writes it to a containers.conf module of Sarathi's own:

```
~/.local/share/sarathi/host-address.conf
[containers]
host_containers_internal_ip = "192.168.1.44"
```

Each unit loads it with `ContainersConfModule=`, which Quadlet turns into
`podman --module=… run`. A reboot, a crash, or a restart after a new lease
each works the address out again before the container starts.

**YOUR OWN containers.conf IS NEVER TOUCHED.** The module is Sarathi's
file, and a module wins over a pin left in containers.conf. An old pin can
stay or go.

**NO NETWORK YET IS WAITED OUT, THEN THE LAST ADDRESS KEPT.** At login the
Wi-Fi may not be up. `host-address` waits up to 30 seconds for a route,
then keeps what it wrote last time. A module that isn't there would stop
every container starting, so on a first start with no network at all it
still writes one, with no address in it (Podman's own answer, then).

**WRITTEN WHOLE.** The new file is written beside the old one and moved
into place. A container starting at that moment reads the old address or
the new one, never half of either.

**A MOVE IS SAID, AND `up` MENDS IT.** A new lease while the containers
run moves the computer out from under them. The doctor's `host` line
turns red (*this computer's address moved from 192.168.1.44 to
192.168.1.61*) with **Start everything again**. `up` writes the new
address and, when it moved, starts every container again, since a
running one keeps the address it started with. `up` says it each time:

```
host       the containers reach this computer at 192.168.1.44
```

## Live receipt

`sarathi host-address`, with a scratch state folder, on the house:

```
host       the containers reach this computer at 192.168.1.44
```

A throwaway container on the `sarathi` network, given a module saying
192.168.1.99, against the pin of .44 in containers.conf:

```
$ podman --module probe.conf run --rm --network sarathi --entrypoint getent \
    localhost/sarathi:latest hosts host.containers.internal
192.168.1.99    host.containers.internal host.docker.internal
$ podman run --rm --network sarathi --entrypoint getent \
    localhost/sarathi:latest hosts host.containers.internal
192.168.1.44    host.containers.internal host.docker.internal
```

Quadlet's dry run of the written `sarathi-yantra.container`:
`Wants=sarathi-host-address.service`, `After=sarathi-host-address.service`,
`ExecStart=/usr/bin/podman --module=/home/mahen/.local/share/sarathi/host-address.conf run …`.

## What is deliberately not here

* **The house address in `[house]` is still yours.** A page published on
  your network at `address = "192.168.1.44"` is bound to it. Leave
  `address` empty and the name you gave is looked up at each `up`. To
  keep the address from moving at all, reserve it on your router.
* **No watching for a new lease while running.** The doctor says it, and
  `up` mends it. A program watching the network all day for something
  that happens a few times a year would be more to go wrong.

## Tests

`tests/test_house_day.py` (*TestTheAddress*): the address is the way
out's source, and none is read when there's no route. It's written whole
into Sarathi's module. A new lease is written and said. No network keeps
the last address, and no network ever still leaves a module to load.
Every container wants the address first and loads it, the network unit
doesn't, and the one-shot has no `[Install]`. The doctor says a moved
address in red, with its button.
