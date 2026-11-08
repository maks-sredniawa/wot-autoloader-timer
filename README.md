# Autoloader Shell Timer

A World of Tanks mod that shows the load time of **every shell** in an autoreloader magazine (Italian tanks and any other gun with the `autoreload` mechanic), not just the one that's loading now.

```
4.5   16.2   26.7   35.5   1/4   390
```

- **Each number**: seconds until that shell is ready, counted from now. The amber one is loading now.
- **1/4**: shells in the magazine now.
- **390** at the end: potential damage of those shells, as if every one penetrates.
- When the magazine is full it shows each shell's own load time at your current reload speed in grey, fastest first, then **3/3** and the damage in green, for example `10.8   11.7   13.5   3/3   1170`.

The times always use your current reload speed. They're recalculated every 0.1 s from the reload time the server sends for the shell being loaded, so a damaged ammo rack, stun, or a crew member knocked out changes them right away. The rest of the magazine is predicted from the gun's per-shell reload table at that same speed.

## Regular autoloaders

Tanks whose whole magazine reloads at once show the shells left and their potential damage: `4/6   1560`, in green when full (`6/6   2340`). While the magazine reloads it reads `0/6` in amber.

## Ares tanks

The Ares line has no magazine: every shot heats the gun, and too much heat locks it. On these tanks the same line shows how long the gun needs to cool down and how much damage you can still deal before it locks:

- **LOCKED 7.3** in amber: the gun is overheated and can fire again in 7.3 s.
- **8.4   560** while warm: the gun can fire and is fully cold in 8.4 s if you stop shooting, including the delay before cooling starts. The last number is the damage of the shots left before it locks.
- **960** in green: the gun is cold and this is the damage of a full burst.

The damage is shots left × the average damage of the loaded shell, as if every shell penetrates. It's capped by the shells you have left.

The reload quick command stays the game's own on these tanks, and it already reports the overheat time.

## Reload quick command

In an autoreloader, the reload quick command (its own key, or Z → "I'm reloading") sends one team chat line with the whole magazine instead of the game's line, which only knows about the next shell:

```
Ready to fire! Magazine 1/4, full in 35 s
Reloading! First shell 9 s, full in 35 s
Ready to fire! Magazine 4/4
```

Allies don't get the game's reload icon over your tank for that command. If team chat is unavailable (chat turned off, a chat ban, or the chat cooldown), or you're out of shells (magazine and ammo rack both empty), the game's own command goes out as usual. Other tanks are not affected. Turn it off with `reloadChatLine`.

## Install

1. Install [GUIFlash](https://github.com/CH4MPi/GUIFlash) (`gambiter.guiflash_*.wotmod`). Most modpacks include it.
2. Copy `maksforge.autoloader_timer_<version>.wotmod` into `World_of_Tanks/mods/<game version>/`.

## Settings

The first battle writes `mods/configs/autoloader_timer/config.json`:

| Key | Default | Meaning |
| --- | --- | --- |
| `enabled` | `true` | Turns the mod off without uninstalling it |
| `x`, `y` | `0`, `60` | Offset from the crosshair, which the line follows frame by frame across arcade, sniper and arty views |
| `fontSize` | `14` | Text size |
| `hideWhenFull` | `false` | Hide the panel while the magazine is full or an Ares gun is cold |
| `reloadChatLine` | `true` | Replace the reload quick command with the magazine status line in autoreloaders |
| `colors` | | Hex colours for the count, a full magazine, the loading shell, the queued shells and the per-shell times. The Ares line reuses them. |

To move the panel, hold Ctrl to show the cursor and drag it. The new position is saved.

## Build

Needs Python 2.7, the game's script runtime (for example `pyenv install 2.7.18`).

```sh
./build.sh                                   # dist/maksforge.autoloader_timer_<version>.wotmod
python2.7 tests/test_schedule.py
python2.7 tests/test_mod_smoke.py
```

## How it works

`gun.autoreload.reloadTime` holds one base time per magazine slot. The first entry is the shell that fills the magazine, and the last is the shell loaded into an empty one. Every 0.1 s, the mod reads the shell loading now from the game's `AmmoController`. It takes the remaining time from the server, works out your reload factor from that shell's base time, and adds the scaled time of each shell after it.

## Support

Questions and bug reports: open an issue in this repository or write to wotmods.support@maksforge.com.

This is a free fan-made mod by MaksForge. It is not affiliated with or endorsed by Wargaming.
