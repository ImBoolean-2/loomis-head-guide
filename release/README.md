# Release

`loomis-head-guide-0.7.1.zip` is the installable package. Its root contains
`loomis_head/` and `loomis_head.desktop`, so Krita's **Tools → Scripts → Import Python
Plugins** accepts it directly.

The ZIP is built from the `loomis_head/` folder in this repository:

```bash
cd ..
zip -r release/loomis-head-guide-0.7.1.zip loomis_head loomis_head.desktop \
  -x '*/__pycache__/*' '*.pyc' '*.bak*'
```

## Other files

- `loomis-head-guide-0.7.1.patch` — cumulative diff from the 0.5.0 base (`b8a762d`) to
  0.7.1, so it includes the Asaro profile commit `d9eeeb5`. See `UPSTREAM-DIFF-0.7.1.md`
  for how to apply it and what it excludes.
- `UPSTREAM-DIFF-0.7.1.md` — per-area summary of the diff and its base.
- `README-UPSTREAM.md` — handoff for the upstream author: features, compatibility, how to
  test and known limits (PyQt6 untested, undo without a macro, faceted Asaro profile).
- `loomis-head-guide-0.7.0.*` and `UPSTREAM-DIFF-0.7.0.md` — kept as history.

## Checks before publishing

```bash
cd loomis_head && python3 -m unittest test_generator test_asaro   # 63 tests
cd .. && unzip -l release/loomis-head-guide-0.7.1.zip | grep -E 'models|asaro|qt_compat'
```
