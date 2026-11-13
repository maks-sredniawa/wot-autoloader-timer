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

- **8.4   560** while warm: the gun can fire and is fully cold in 8.4 s if you stop shooting, including the delay before cooling starts. The last number is the damage of the shots left before it locks.
- **960** in green: the gun is cold and this is the damage of a full burst.
- While the gun is locked the line is hidden, because the game shows its own lockout timer.

The damage is shots left × the average damage of the loaded shell, as if every shell penetrates. It's capped by the shells you have left.

The reload quick command stays the game's own on these tanks, and it already reports the overheat time.

## Aim timer

A small bar to the right of the crosshair shows how far your gun has aimed, on every tank:

- **The seconds above it** count down until the circle is fully aimed. The **percentage below it** shows how far it has shrunk. Both are amber while aiming.
- **Fully aimed**: the seconds disappear and the bar and `100%` turn green.
- **While you drive**, it measures against the circle you'd reach standing still, so the seconds show how long you'd still need to aim after stopping.

### Type 71 line (dual accuracy)

On guns with dual accuracy, the circle gets much smaller once the gun has cooled after a shot. The game shows a second circle for it but no timer. The bar shows both stages:

- **100%** is the hot gun fully aimed, as on any tank. A tick on the bar marks it.
- **The part above the tick** is the extra the cooled gun gives. It is solid grey while the gun cools after a shot, with the seconds until it has cooled next to it, and empty once the gun has cooled.
- **Aiming past 100%** fills that part in cyan. The percentage keeps counting up to the gun's real gain: the hot circle divided by the cooled one, 167% on the Type 71 (0.40 against 0.24).
- **A full bar with no seconds left** is the best shot the gun can make.

The game doesn't tell the client how long the cooldown is after crew skills, so the first countdown of a battle uses the gun's base delay. After one full cycle the mod counts with the delay it measured. The countdown starts when the server switches the accurate mode off, so ping shifts it slightly.

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
| `aimTimer` | | `enabled` (`true`) shows the aim timer. `x`, `y` (`150`, `0`) are its offset from the crosshair in arcade view; `sniper` (`120`, `60`) and `strategic` (`180`, `70`) hold the offsets for the zoomed and artillery views. |
| `colors` | | Hex colours for the count, a full magazine, the loading shell, the queued shells, and the per-shell times. The Ares line and the aim timer's text reuse them. The bar's own colours are built in. |

To move the panel or the aim timer, hold Ctrl to show the cursor and drag it (the aim timer by its bar, seconds or percentage). The new position is saved. The aim timer keeps a separate position for arcade, sniper and artillery view, so drag it once in each.

## Build

Needs Python 2.7, the game's script runtime (for example `pyenv install 2.7.18`).

```sh
./build.sh                                   # dist/maksforge.autoloader_timer_<version>.wotmod
python2.7 tests/test_schedule.py
python2.7 tests/test_aim.py
python2.7 tests/test_mod_smoke.py
```

## How it works

`gun.autoreload.reloadTime` holds one base time per magazine slot. The first entry is the shell that fills the magazine, and the last is the shell loaded into an empty one. Every 0.1 s, the mod reads the shell loading now from the game's `AmmoController`. It takes the remaining time from the server, works out your reload factor from that shell's base time, and adds the scaled time of each shell after it.

## Support

Questions and bug reports: open an issue in this repository or write to wotmods.support@maksforge.com.

This is a free fan-made mod by MaksForge. It is not affiliated with or endorsed by Wargaming.
