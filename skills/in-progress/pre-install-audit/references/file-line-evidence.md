# Checklist: file and line evidence

Every finding the report relies on points at a line in the pinned commit, or at the inventory when the finding is that a path is absent.

## Citation shape

Use one line per quote:

```text
path/from/clone/root:17: the line text
```

Take that line from `scripts/show_lines.py`. Keep the path relative to the clone root. When a line is longer than the script prints, keep the script's truncation marker so the quote matches the tool output.

## Absence

An absence claim names the inventory command and the pinned SHA, then states that the path was not in the inventory. Do not treat a skipped directory as proof the path is missing.

## Mark each line

- Each finding in the report has a `path:line` quote or an absence note tied to the inventory.
- The quotes come from the pinned SHA, the same SHA as the report header.
- The report does not rely on a paraphrase that has no citation.

Done when a reader can check every finding against the clone without taking your word for the wording.
