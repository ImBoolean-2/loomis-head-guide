# Contributing

Thanks for helping. This plugin is GPL-3.0-only; by contributing you agree to license
your changes under the same terms.

## Ways to contribute

- **Languages**: improve an existing translation or add a new one.
- **Heads**: share a Loomis head preset in `heads/`.
- **Hair and features**: add parameters, curves or UI.
- **Fixes**: crashes, Krita compatibility, performance.
- **Docs and screenshots**: tutorials or real panel screenshots.

Open an issue first for large changes. For small fixes, a pull request is fine.

## Development setup

1. Fork the repository and clone your fork.
2. Copy `loomis_head/` and `loomis_head.desktop` into Krita's `pykrita` directory.
   - Linux Flatpak: `~/.var/app/org.kde.krita/data/krita/pykrita/`
3. Restart Krita; enable the plugin in
   **Settings → Configure Krita → Python Plugin Manager** and open
   **Settings → Dockers → Loomis Head Guide**.
4. After editing Python files, restart Krita (Python plugins are loaded at startup).

Run the tests (no Krita, Qt or PyQt5 needed):

```bash
cd loomis_head
python3 -m unittest test_generator.py -v
```

Before a pull request:

- Keep the default generator output stable unless the change is intentional.
- Add a test for new generator parameters or serialization.
- Update the translations (`en`, `es`, `pt`, `fr`) for new UI strings.
- Keep the plugin offline: no network, telemetry or new runtime dependencies.
- Update `CREDITS.md` if you add third-party code.

## Add a language

1. Copy `loomis_head/translations/en.json` to `<code>.json` (for example `de.json`) and
   translate the values. Keep the keys identical.
2. Add the code to `SUPPORTED` in `loomis_head/i18n.py`.
3. Add the language to the selector in `loomis_head/loomis_head_plugin.py`
   (`_build_language_panel`).
4. Check that the key set matches English:

   ```bash
   python3 - <<'PY'
   import json, pathlib
   base = json.loads(pathlib.Path('loomis_head/translations/en.json').read_text())
   new = json.loads(pathlib.Path('loomis_head/translations/de.json').read_text())
   assert set(base) == set(new)
   print('OK')
   PY
   ```

## Add a head preset

Follow [`heads/README.md`](heads/README.md). Put the JSON and a 400×400 PNG preview in
`heads/<your-alias>/`. Fill `author` and `license`; do not include personal data. Prefer
an alias. Heads are data, not code, so they can use a different license.

## Add hair or a facial feature

1. Add the parameter in `loomis_head/loomis_head_generator.py`: default, setter,
   `to_dict`/`from_dict` and the geometry in `build_svg`.
2. Add a control in `loomis_head/features_dialog.py` (`FeaturePanel`) and include it in
   `sync_from_model`.
3. Add translations for the label in all JSON files.
4. Add a test in `loomis_head/test_generator.py` (roundtrip, extremes, no NaN).
5. If it affects the preview, check that `loomis_head/preview.py` still renders.

## Future head models

The share format has a `model` field. A new engine should implement the same
`build_svg(width, height, samples)` interface and be selected by `model`; the loader must
reject unknown models with a clear message. Do not change the Loomis defaults.

## Pull request checklist

- [ ] Tests pass (`python3 -m unittest test_generator.py -v`).
- [ ] Translations updated for new strings.
- [ ] Screenshots/GIF updated if the UI changed.
- [ ] `CREDITS.md` updated for third-party code.
- [ ] No user data, `.kra` files or generated state in the diff.
- [ ] The PR description explains what and why.

Be respectful; see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
