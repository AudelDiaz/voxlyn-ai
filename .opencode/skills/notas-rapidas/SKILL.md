---
name: notas-rapidas
description: >
  Save quick voice notes to a timestamped Markdown file. Notes are
  appended to ~/Notas/<YYYY-MM-DD>.md for easy lookup.
---

When the user says "toma nota", "apunta", or "guarda esto":

1. Parse the note content from the user's message.
2. Append it to `~/Notas/<YYYY-MM-DD>.md` in this format:

```markdown
## 2026-05-13 12:34

- Comprar leche y huevos
- Llamar al dentista
```

3. Confirm to the user that the note was saved.

If the file or directory does not exist, create it. Use the `Write` tool
to append content (read the file first, append new block, write back).
