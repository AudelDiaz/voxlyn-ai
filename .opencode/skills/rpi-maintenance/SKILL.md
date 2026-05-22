---
name: rpi-maintenance
description: >
  Guide Raspberry Pi maintenance: system updates, package cleanup, journal
  log rotation, SD card health (SMART-like checks), and opencode server
  restarts. For Manjaro ARM (Arch-based).
---

When the user asks about maintaining, updating, or cleaning up the server:

- **System update**: `sudo pacman -Syu` (explain what will be updated before running)
- **Package cache cleanup**: `sudo pacman -Sc` and check orphans with `pacman -Qdt`
- **Journal maintenance**: `journalctl --disk-usage` and `sudo journalctl --vacuum-size=500M`
- **SD card health**: `sudo smartctl -a /dev/mmcblk0` (if supported) or check `dmesg | grep -i "mmc\|sdcard\|error"`
- **OpenCode restart**: `sudo systemctl restart opencode-serve.service`
- **Check for large files**: `du -sh /home/* /var/log/* 2>/dev/null | sort -rh | head -10`
- **Zram tuning**: `zramctl` to check current compression stats
- **Uptime check**: `uptime` — recommend reboot if uptime > 90 days

Always confirm before running destructive commands (package removal, journal vacuum). Suggest scheduling updates during low-usage times.
