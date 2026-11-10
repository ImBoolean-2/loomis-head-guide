# Release

`loomis-head-guide-0.7.2.zip` is the installable package. Its root contains
`loomis_head/` and `loomis_head.desktop`, so Krita's **Tools → Scripts → Import Python
Plugins** accepts it directly.

The ZIP is built from the `loomis_head/` folder in this repository:

```bash
cd ..
zip -r release/loomis-head-guide-0.7.2.zip loomis_head loomis_head.desktop \
  -x '*/__pycache__/*' '*.pyc' '*.bak*'
```

## Other files

- `loomis-head-guide-0.7.2.patch` — cumulative diff from the 0.5.0 base (`b8a762d`) to
  0.7.2, so it includes the Asaro bust commit `7051243`. See `UPSTREAM-DIFF-0.7.2.md`
  for how to apply it and what it excludes.
- `UPSTREAM-DIFF-0.7.2.md` — per-area summary of the diff and its base.
- `README-UPSTREAM.md` — handoff for the upstream author: features, compatibility, how to
  test and known limits (PyQt6 untested, undo without a macro, faceted Asaro bust).
- `loomis-head-guide-0.7.1.*`, `loomis-head-guide-0.7.0.*`, `UPSTREAM-DIFF-0.7.0.md` and
  `UPSTREAM-DIFF-0.7.1.md` — kept as history.

## Checks before publishing

```bash
cd loomis_head && python3 -m unittest test_generator test_asaro   # 73 tests
cd .. && unzip -l release/loomis-head-guide-0.7.2.zip | grep -E 'models|asaro|qt_compat'
```
