---
name: info-sistema
description: >
  Report system diagnostics: memory usage, CPU load, disk space, uptime,
  pending updates, and running processes. Uses standard Linux commands.
---

When the user asks about system status:

- **Memory**: `free -h` or `cat /proc/meminfo`
- **CPU / load**: `uptime` or `cat /proc/loadavg`
- **Disk**: `df -h /`
- **Uptime**: `uptime -p`
- **Updates** (CachyOS / Arch): `pamac checkupdates 2>/dev/null || checkupdates 2>/dev/null`
- **Top processes**: `ps aux --sort=-%cpu | head -6`

Pick the relevant command(s), execute via `Bash`, and summarise the
result in 1-3 sentences in the same language as the user. Skip
information the user did not ask for.
