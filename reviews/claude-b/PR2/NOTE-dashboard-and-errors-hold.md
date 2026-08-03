# `dashboard.py` and `errors.py` at `main` `5694ab45` — the bind guard is a strict allow-list; no issue filed

> **CORRECTED 2026-08-03.** The `escapes: []` result below is **too strong** and
> is disproved by issue #19. See
> `ADDENDUM-architecture-claims-and-repair-drops-a-field.md`: a `KeyError` from
> `workspace.py:1182` reaches a real `efo task proxy-submit` invocation as an
> uncaught traceback. The census below enumerated `raise` **statements**, so it
> structurally could not see an exception arriving from a dict index, and
> `KeyError` is a `LookupError` — in none of `cli.main`'s four caught families.
> Everything else in this note stands as measured. The lesson is kept rather
> than the claim: an exhaustive census is exhaustive over *the thing it
> enumerates*, and the shape it cannot enumerate is where the counterexample
> lives.

Reproduce with `raw/probe_dashboard_and_errors.py`; raw output in
`raw/raw-dashboard-errors.txt`. **28 checks, 0 unexpected.**

**No socket was bound and no request was served.** The bind guard runs before
the server object exists, so every refusal below is measured from the guard
itself; what the handler *would* serve is measured by calling the same
`Workspace` methods `do_GET` calls.

## The documented bind guard holds, and fails closed on every near miss

`README.md:336-337` — *"Open `http://127.0.0.1:8765`. Remote binding is
rejected unless `--allow-remote` is explicitly supplied."*

`dashboard.py:218` allows exactly `{"127.0.0.1", "::1", "localhost"}`. Fourteen
spellings, all refused with
`Remote dashboard binding requires explicit allow_remote=True`:

```
0.0.0.0      ""            ::            192.168.1.10   example.invalid
"127.0.0.1 " " 127.0.0.1"  LOCALHOST     Localhost      127.1
127.0.0.2    0177.0.0.1    [::1]         localhost.
```

The interesting rows are the last five. `127.1`, `127.0.0.2`, `0177.0.0.1` and
`[::1]` all reach the loopback interface, and `LOCALHOST` is the same name in a
different case — every one is refused anyway, because the guard is a strict
allow-list rather than a pattern match or a `.startswith("127.")`. A test that
only tried `0.0.0.0` would not have shown that.

## What the dashboard would serve

Routes, extracted from the handler: `['/', '/api/status', '/api/ledger']`.
There is no fourth route and no file serving — `DASHBOARD_HTML` is a module
constant and `_handler` contains zero `open(` calls, so no request can name a
path.

`/api/status` returns `workspace.status()` plus `workspace.list_tasks()`, i.e.
**raw task projections**. Measured with markers planted through the API:

```
task description in the payload      SECRETDESC present: True
blocked_reason absolute path         SECRETPATH present: True
authorization checks in the handler  0
```

The SSH collector deliberately strips both of those
(`NOTE-collector-redaction-holds.md` — `task_to_view` and `collect_activity`
whitelist fields, which is why the adapter's absolute paths never reach a
public snapshot). This server does not, and it has no authentication of any
kind.

**Not filed**, because nothing claims otherwise: `README.md:336-337` promises
the bind is local unless explicitly opted out of, and that promise holds
exactly. What is worth an operator knowing, and is written here rather than in
an issue: `--allow-remote` publishes complete task records — descriptions,
blocked reasons, whole `result` evidence bundles — to anyone who can reach the
port, with no token. The local default is the thing protecting it.

## `errors.py`

Eight classes, and every one derives from `EFOError`:
`AuthorizationError`, `ConfigurationError`, `EvidenceError`, `IntegrityError`,
`LeaseError`, `LockTimeout`, `TransitionError`.

## A premise of mine that was wrong

I set out to check whether any failure path reaches a user as a traceback,
assuming `cli.py` catches only `EFOError`. It does not — measured:

```
except (EFOError, OSError, ValueError, json.JSONDecodeError) as exc:
```

Four families. Every exception **call** in the package, enumerated with the run
failing on anything unadjudicated:

| Raised | Disposition | Files |
|---|---|---|
| `ConfigurationError` | EFOError — caught, exit 2 | adapter, dashboard, doctor, independence, model, provenance, util, workspace |
| `AuthorizationError` | EFOError — caught, exit 2 | provenance, workspace |
| `EvidenceError` | EFOError — caught, exit 2 | archive, evidence, provenance, workspace |
| `IntegrityError` | EFOError — caught, exit 2 | ledger, workspace |
| `LeaseError`, `TransitionError`, `LockTimeout` | EFOError — caught, exit 2 | workspace, model, lock |
| `ValueError` | not an `EFOError`, but **in** the catch tuple — exit 2 | cli |
| `SystemExit` | `__main__.py:7`, `raise SystemExit(main())` — the exit itself | `__main__` |

`escapes: []` **among raised statements** — which is the limit of this census,
not a property of the package. Both `ValueError` sites were driven through
`main()` and produce a one-line message with exit 2, no traceback. An
exception raised implicitly by the interpreter is outside what this table can
see; issue #19 is one, and it does escape.

One of them is a dead branch: `cli.py:28`'s
`raise ValueError("Either --description or --description-file is required")` is
never reached, because argparse enforces the required mutually-exclusive group
first and exits with `usage:`. Recorded rather than filed — it is a
belt-and-braces guard behind a parser rule, which is the harmless direction.

## Scope

`dashboard.serve`'s host guard, `_handler`'s routes and what they return,
`errors.py`'s hierarchy, and an exhaustive census of raised exception types
against `cli.main`'s catch tuple. Not examined: the served HTML itself, and the
handler under a real request (no socket was bound).

Pre-registered permissions unchanged: `gpu: false`, `network: false`,
`performance_metrics: false`; gates `allow_skips: false`,
`require_validation: true`, `require_known_answer_check: true`,
`require_independent_verification: true`.

**SUBMITTED, not VERIFIED.**

| Artifact | SHA-256 |
|---|---|
| `raw/probe_dashboard_and_errors.py` | `df47967e0b5b5990a0fc2c4c95e44fb661f47dd1aad4570c0244e712ba6e3ff4` |
| `raw/raw-dashboard-errors.txt` | `9089ab6b37d5a74a91daa52ca56bf6dde5833f972fddfa99fad3017ce04d58b0` |
