---
name: reminders
description: >
  Set, list, and manage reminders and timers. Reminders are persisted to
  ~/.voice-assistant/reminders.json and use systemd-run for timed alerts.
---

When the user asks about reminders or timers:

**Data file**: `~/.voice-assistant/reminders.json` (JSON array of objects).

**Reminder object format**:
```json
{
  "id": "unique-string",
  "text": "Call the dentist",
  "created_at": "2026-05-13T12:00:00",
  "due_at": "2026-05-13T12:30:00",
  "done": false
}
```

**Operations**:

1. **Set a reminder**: Add to the JSON file. For time-based reminders,
   schedule a systemd timer:
   ```
   systemd-run --user --on-active=30min --unit=va-reminder-<id> \
     notify-send "Reminder" "<text>"
   ```

2. **List reminders**: Read the file and present active (non-done) items
   sorted by `due_at`.

3. **Mark done**: Set `"done": true` for the matching id.

4. **Clear all done**: Remove all items with `"done": true`.

Always confirm what you did in one sentence.
