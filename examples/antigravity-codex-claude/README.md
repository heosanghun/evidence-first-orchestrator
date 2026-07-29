# Antigravity, Codex, and Claude Code

Initialize the preset:

```bash
efo init ./team-workspace \
  --name "Antigravity research team" \
  --preset antigravity-codex-claude
```

Antigravity creates non-overlapping tasks:

```bash
efo task add ./team-workspace \
  --actor antigravity \
  --id CODEX-1 \
  --owner codex \
  --title "Statistical utility" \
  --description-file ./examples/antigravity-codex-claude/task.md \
  --allow-write /project/cts/eval

efo task add ./team-workspace \
  --actor antigravity \
  --id CLAUDE-1 \
  --owner claude \
  --title "Backbone verifier" \
  --description-file ./examples/antigravity-codex-claude/task.md \
  --allow-write /project/cts/backbone_audit
```

Both agents can work concurrently because their task ownership and write roots
do not overlap. If one output is needed by the other, create a second task with
`--requires CODEX-1` instead of allowing concurrent edits to the same file.

Keep agents in manual mode until their installed CLIs and non-interactive flags
have been tested. Then register a command-mode worker with an explicit argument
array and run `efo worker loop`.
