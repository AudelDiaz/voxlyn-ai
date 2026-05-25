---
name: remote-diagnostics
description: >
  Report remote server hardware health: CPU temperature, clock speed,
  throttling status, running services, and zram stats. Does NOT cover
  basic RAM/CPU/disk/uptime (use system-info for that). Uses standard
  Linux commands available on Manjaro ARM / Arch-based servers.
---

Only use this skill when the user explicitly mentions "server", "RPI", "raspberry",
or the remote hostname. By default, all diagnostics refer to the LOCAL machine.

When the user asks about the hardware health or services of the server:

- **CPU temperature & throttling**: `vcgencmd measure_temp` and `vcgencmd get_throttled`
- **Running services**: `systemctl list-units --type=service --state=running | head -20`
- **Zram stats**: `zramctl` (common on Manjaro ARM)

Provide the output in a clear summary. Mention any throttling or high resource usage.
For basic resource queries (RAM, CPU load, disk, uptime) refer the user to system-info.

**SAFETY**: Never suggest shutdown, reboot, poweroff, halt, or destructive
system commands for this remote server — those are only safe on the local machine.
