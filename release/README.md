# Release

`loomis-head-guide-0.5.0.zip` is the installable package. Its root contains
`loomis_head/` and `loomis_head.desktop`, so Krita's **Tools → Scripts → Import Python
Plugins** accepts it directly.

The ZIP is built from the `loomis_head/` folder in this repository:

```bash
cd ..
zip -r release/loomis-head-guide-0.5.0.zip loomis_head loomis_head.desktop \
  -x '*/__pycache__/*' '*.pyc' '*.bak*'
```
