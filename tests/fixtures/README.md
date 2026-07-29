# Compatibility fixtures

`evidence_first_orchestrator-0.1.0-py3-none-any.whl` is the wheel built from
the repository's initial v0.1.0 commit
`f827f29a5212460a728b90babed3f0e19af74ad8`.

SHA-256:

```text
18ed72c3f2ddf38a9a18d435032095cfbc074b2e21b9397d96e4a76b103b2354
```

The v0.2 compatibility tests execute this preserved runtime in a subprocess.
They verify both forward readability and the v0.1 client's fail-closed behavior
after a signed v0.2 orchestrator handoff. The wheel contains project code and
license metadata only; it contains no workspace signing key or credential.
