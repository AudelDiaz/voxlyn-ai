---
name: remote-diagnostics
description: >
  Report the server's hardware health: CPU temperature, clock speed,
  throttling status, running services, and zram stats. This server is
  the machine running this OpenCode assistant. Uses standard Linux
  commands available on Manjaro ARM / Arch-based servers.
---

When the user asks about the server's hardware health or services:

- **CPU temperature & throttling**: `vcgencmd measure_temp` and `vcgencmd get_throttled`
- **Running services**: `systemctl list-units --type=service --state=running | head -20`
- **Zram stats**: `zramctl` (common on Manjaro ARM)

Provide the output in a clear summary. Mention any throttling or high resource usage.

**NOTE**: This server is where the assistant runs. Basic resource queries
(CPU load, RAM, disk, uptime) refer to this same machine — they are not separate skills.

**SAFETY**: Never suggest shutdown, reboot, poweroff, halt, or destructive
system commands.
