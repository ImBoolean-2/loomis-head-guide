# Media

| File | What it is |
| --- | --- |
| `hero.gif` | Real 36-frame render of the head rotating, with zone colours and hair |
| `head-front.png`, `head-three-quarter.png`, `head-back.png` | Real renders at 800×800 |
| `zone-colors.png` | Front render showing the per-zone colours |
| `hair-patterns.png` | Real renders of straight/zigzag/spiky/curly hair |
| `promo.png` | 1800×1200 promotional image: real head renders + panel mockup |
| `panel.png` | Screenshot of the HTML panel mockup (not a real Krita screenshot) |
| `panel-preview.html` | Browser mockup of the panel layout |

Images are generated with the plugin's generator and ImageMagick:

```bash
magick -background '#1b1b1b' frame.svg -flatten frame.png
magick -delay 6 -loop 0 frames/*.png hero.gif
```

If you capture the real Krita docker, add it as `panel.png` and reference it from the
README; it is more useful than the mockup.
