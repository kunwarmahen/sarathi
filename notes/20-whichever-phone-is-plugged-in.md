# Whichever phone is plugged in

Sarathi held one phone: an Android (its cable, or `[phone] address`)
or an iPhone (`[phone] wda`), and a settings file with both was refused
([note 19](19-an-iphone-too.md)). The reason was Sparsh's: it took an
iPhone it was told about ahead of any Android. Then the iPhone went in a
drawer and the Android went back on the cable. Yantra's page, Telegram
and the home page all still said *"iPhone, not answering"*. Getting the
Android back meant `sarathi phone tcpip`, which wrote over the iPhone,
and the same again in the other direction next time.

Sparsh now uses the phone that answers, not the one written down
(Sparsh's notes/15). That makes the one-phone rule unnecessary, and
Sarathi drops it.

## Both written, the plugged-in one used

`[phone]` may hold `address` and `wda` together. `sarathi phone iphone`
saves the iPhone beside the Android; `sarathi phone ADDRESS` and
`tcpip` keep the iPhone. The Settings page does the same: **Use the
iPhone** is under *An iPhone*, no longer *An iPhone instead*. Two
phones that answer at once are Sparsh's to say, with both names.

## `up` doesn't wait for an iPhone that isn't there

`up` starts a saved iPhone's WebDriverAgent when it isn't answering
(`sparsh iphone --background`), and waits up to five minutes for it.
With the Android on the cable and the iPhone in the drawer, every `up`
would have waited out those five minutes. So `up` asks Sparsh first, with
no iPhone named, whether an Android answers. If one does, the iPhone's
unit (`sarathi-iphone`) is started and not waited for. `sparsh iphone`
waits for the phone by itself, so plugging the iPhone back in is all it
takes, and `up` says which phone it is now.

## The cable, lent to the containers

The containers couldn't see the cable, so an Android reached them only
over Wi-Fi ([note 08](08-the-phone-over-wifi.md)). With `[phone] on`,
`up` now starts **`sarathi-adb`**, a user service running Sparsh's
`adb-share`. It lends this computer's adb through `~/.sparsh/adb.sock`,
mode 0600, in the folder those containers already mount. Each container
that works the phone (Yantra's page, Dvara, Samay) gets
`ADB_SERVER_SOCKET=localfilesystem:…/adb.sock`. It is a file, not a
port, because whoever reaches adb can work the phone, and a port the
containers can reach is on the house address too. `down` leaves the
share running, as it does the iPhone's unit. `down --remove` takes it
away.

## LIVE RECEIPT

The real `sarathi.toml` still had `wda = "http://127.0.0.1:8100"` from
the iPhone, and the Nexus 6P was on the cable. Before, inside the
Yantra container:

```
$ podman exec sarathi-yantra sparsh status --json   # phones
{'serial': 'http://host.containers.internal:8100', 'state': 'offline', 'model': 'iPhone',
 'note': 'not answering -- start WebDriverAgent on it'}
```

`sarathi image` (with Sparsh `7f7e9dc`), then `sarathi up`:

```
adb        the phone on this computer's cable, lent to the containers  (unit sarathi-adb)
...
dvara      restarting with the new settings  (unit sarathi-dvara)
yantra     restarting with the new settings  (unit sarathi-yantra)
...
iphone     waiting behind; the Android on the cable (Nexus_6P) is the phone now
```

After, in both containers:

```
== sarathi-yantra
{'serial': '84B7N16128001616', 'state': 'device', 'model': 'Nexus_6P', 'note': ''}
{'serial': 'http://host.containers.internal:8100', 'state': 'offline', 'model': 'iPhone', ...}
== sarathi-dvara
{'serial': '84B7N16128001616', 'state': 'device', 'model': 'Nexus_6P', 'note': ''}
{'serial': 'http://host.containers.internal:8100', 'state': 'offline', 'model': 'iPhone', ...}

$ podman exec sarathi-yantra sparsh look --peek
App: com.android.systemui
(The phone is locked: this is its lock screen, not the app asked for. ...)
```

`adb devices` on this computer still listed the phone, and
`~/.sparsh/adb.sock` was `srw-------`. `up` came straight back rather
than waiting on the iPhone.

## What the tests hold

`tests/test_phone.py`: an iPhone reads back as written beside an
Android; `sarathi phone iphone` keeps the Android's address and an
Android address afterwards keeps the iPhone; a cable on the podman road
is said to be lent through `sarathi-adb`; Yantra's, Dvara's and Samay's
units get `ADB_SERVER_SOCKET` naming the file, the share's unit runs
`adb-share --socket` and publishes no port, and with no `[phone]`
nothing is lent; `up` starts the iPhone's unit without waiting while an
Android answers, and waits as before when none does.
`tests/test_settings_page.py`: **Use the iPhone** saves it beside the
Android, and the Android's address again keeps it.

## What is not here yet

* ~~The iPhone back on the cable after this, end to end.~~ Run: the
  Nexus swapped for the iPhone, and the next task went to the iPhone,
  with nothing changed in Sarathi.
* Both phones on at once, each owned by a person (the several-phones plan).
