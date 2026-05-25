---
name: remote-diagnostics
description: >
  Report remote server health: CPU temperature, clock speed, throttling
  status, memory usage, disk usage, uptime, and running services. Uses standard
  Linux commands available on Manjaro ARM / Arch-based servers.
---

Only use this skill when the user explicitly mentions "server", "RPI", "raspberry",
or the remote hostname. By default, all diagnostics refer to the LOCAL machine.

When the user asks about the health, status, or diagnostics of the server:

- **CPU temperature & throttling**: `vcgencmd measure_temp` and `vcgencmd get_throttled`
- **System load**: `uptime` and `cat /proc/loadavg`
- **Memory**: `free -h`
- **Disk**: `df -h`
- **Running services**: `systemctl list-units --type=service --state=running | head -20`
- **Zram stats**: `zramctl` (common on Manjaro ARM)
- **Uptime**: `uptime -p`

Provide the output in a clear summary. Mention any throttling or high resource usage. Ask the user if they want to investigate further if anything looks abnormal.

**SAFETY**: Never suggest shutdown, reboot, poweroff, halt, or destructive
system commands for this remote server — those are only safe on the local machine.
