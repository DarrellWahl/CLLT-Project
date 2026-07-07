# Road Traffic Signs Website

This site is built from the extracted Road Traffic Signs dataset.

## Setup

1. Run the website build script from the repository root:

```sh
python3 scripts/build_website.py
```

2. Serve the `website/` folder locally:

```sh
cd website
python3 -m http.server 8000
```

3. Open `http://localhost:8000` in your browser.

## Notes

- The site uses `data/signs.json` for sign metadata.
- Sign images are copied into `website/signs/`.
- If you update `output/sign_mappings_clean.json` or `output/signs/`, rerun the build script.
