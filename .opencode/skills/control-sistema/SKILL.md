---
name: control-sistema
description: >
  Control the local Linux desktop: adjust volume and brightness, open
  applications, take screenshots, manage windows. Uses Bash commands
  available on a typical Gnome / CachyOS setup.
---

When the user asks to control their computer:

- **Volume**: Use `pactl` (PulseAudio / PipeWire).
  - `pactl set-sink-volume @DEFAULT_SINK@ +5%` (increase)
  - `pactl set-sink-volume @DEFAULT_SINK@ -5%` (decrease)
  - `pactl set-sink-volume @DEFAULT_SINK@ 50%` (absolute)

- **Brightness**: Use `brightnessctl` if available.
  - `brightnessctl set 50%`
  - `brightnessctl set +10%`

- **Open app**: Use `gtk-launch <app.desktop>` or `xdg-open`.
  - `gtk-launch firefox.desktop`
  - `xdg-open https://example.com`

- **Screenshot**: Use `gnome-screenshot` or `grim` (Wayland).
  - `gnome-screenshot -a` (area selection)

- **Suspend / lock**: `systemctl suspend` / `loginctl lock-session`

Always run commands with `subprocess.run` (or equivalent) and confirm
the result to the user in 1-2 sentences.
