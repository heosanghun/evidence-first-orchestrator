# Contributing

## Development setup

```bash
python -m pip install -e .
python -m unittest discover -s tests -t . -v
```

Only Python 3.10 or newer and the standard library are required at runtime.

## Change expectations

- Add focused tests for every state transition or evidence-gate change.
- Preserve deny-by-default permissions.
- Do not weaken an acceptance gate to make a test pass.
- Treat a skipped test as a separate outcome.
- Keep external command execution free of `shell=True`.
- Never add a silent fallback for a missing task, report, artifact, or key.
- Update the architecture and migration docs when behavior changes.

## Pull requests

Describe:

- the behavior changed;
- the failure mode it addresses;
- the exact checks run;
- pass, fail, and skip counts;
- known-answer cases used;
- unmeasured items as `[FILL]`.
