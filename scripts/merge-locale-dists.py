#!/usr/bin/env python3
"""Merge per-locale VitePress dists (built with VP_LOCALES=<locale>) into one site.

Usage: python3 scripts/merge-locale-dists.py <out-dir> <dist-ko> <dist-en> [...]

The first dist is the base (root index.html/404/robots come from it). For the
rest, locale page trees and content-hashed assets are copied in, and the two
per-build manifests that only cover their own pages — hashmap.json (SPA
navigation chunk map) and sitemap.xml — are unioned. Same-name assets are
content-hashed by Vite, so collisions are identical files and safe to skip.
"""
import json
import re
import shutil
import sys
from pathlib import Path

LOCALES = ('ko', 'en', 'cn', 'jp', 'es')


def copy_missing(src: Path, dst: Path) -> None:
    for p in src.rglob('*'):
        if not p.is_file():
            continue
        out = dst / p.relative_to(src)
        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out)


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out, dists = Path(sys.argv[1]), [Path(d) for d in sys.argv[2:]]

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(dists[0], out)
    for d in dists[1:]:
        for loc in LOCALES:
            if (d / loc).is_dir():
                copy_missing(d / loc, out / loc)
        copy_missing(d / 'assets', out / 'assets')

    hashmap: dict[str, str] = {}
    urls: list[str] = []
    for d in dists:
        hashmap.update(json.loads((d / 'hashmap.json').read_text()))
        urls += re.findall(r'<url>.*?</url>', (d / 'sitemap.xml').read_text())
    (out / 'hashmap.json').write_text(json.dumps(hashmap, separators=(',', ':')))
    uniq = list(dict.fromkeys(urls))
    (out / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + ''.join(uniq) + '</urlset>'
    )
    print(f'merged {len(dists)} dists -> {out}: hashmap {len(hashmap)} pages, sitemap {len(uniq)} urls')


if __name__ == '__main__':
    main()
