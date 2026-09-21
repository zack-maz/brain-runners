# Fonts

Both files are the latin subsets served by Google Fonts, copied from the brand's design-system bundle
(`~/Documents/PROJECTS/BRAND/website/ds-bundle/fonts/`). Both are licensed under the SIL Open Font
License, Version 1.1 (https://openfontlicense.org), which allows bundling and embedding.

| file | family | copyright |
| --- | --- | --- |
| `HankenGrotesk-latin.woff2` | Hanken Grotesk (variable weight) | Copyright 2021 The Hanken Grotesk Project Authors (https://github.com/marcologous/hanken-grotesk) |
| `JetBrainsMono-latin.woff2` | JetBrains Mono (variable weight) | Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono) |

`bakeoff/view.py` embeds them in the page as base64, so the replay stays one file that loads nothing.
