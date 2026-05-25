---
name: rpi-security
description: >
  Analyze Raspberry Pi security: fail2ban status and banned IPs, firewall rules
  (iptables/nftables), listening network ports, SSH auth logs for failed login
  attempts, and system audit logs. For Manjaro ARM (Arch-based).
---

Only use this skill when the user explicitly mentions "server", "RPI", "raspberry",
or the remote hostname. By default, all security queries refer to the LOCAL machine.

When the user asks about security, intrusion attempts, or firewall status on the server:

- **fail2ban status**: `fail2ban-client status` and `fail2ban-client status <jail>` for each active jail
- **Listening ports**: `ss -tlnp` and `ss -ulnp`
- **Firewall rules**: `sudo iptables -L -n` or `sudo nft list ruleset`
- **SSH auth failures**: `journalctl -u sshd --since "24 hours ago" | grep "Failed password" | wc -l`
- **Recent auth logs**: `journalctl -u sshd --since "1 hour ago" --no-pager | grep -E "Failed|Accepted|Invalid" | tail -20`
- **Suspicious IPs**: `journalctl -u sshd --since "48 hours ago" | grep "Failed password" | awk '{print $(NF-3)}' | sort | uniq -c | sort -nr | head -10`

Summarize findings: number of failed attempts, top attacking IPs, banned IPs by fail2ban, and any exposed services. Do not alarm unnecessarily — many SSH attempts are background noise.

**SAFETY**: Never suggest shutdown, reboot, poweroff, halt, or destructive
system commands for this remote server — those are only safe on the local machine.
