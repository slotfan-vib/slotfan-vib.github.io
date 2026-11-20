#!/usr/bin/env python3
"""
check_site.py — consistency check for saeedlotfan.com. Run before every push:

    python build_seo.py      # regenerate + recount (must end "none (already in step)" on a 2nd run)
    python check_site.py     # report anything that breaks the site's conventions

Exits with status 1 if any ERROR is found; WARN lines are worth a look.
The rules it checks are written out in README.md ("Checklist for every update").
"""

import glob
import html
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MAIN = ["index.html", "research.html", "publications.html", "teaching.html",
        "people.html", "contact.html"] + sorted(glob.glob("projects/*.html"))
PAPERS = sorted(glob.glob("papers/*.html"))
NEWS_TAGS = {"Journal paper", "Conference paper", "Talk", "Poster", "M.Sc. thesis",
             "Funded project", "Student project", "Open positions"}
PUB_TYPES = {"Journal", "Conference", "Presentation", "Poster"}

errors, warns = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warns.append(msg)


def read(p):
    return io.open(p, encoding="utf-8").read()


def visible_text(doc):
    doc = re.sub(r"<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>", " ", doc, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", doc))


pages = {p.replace("\\", "/"): read(p) for p in MAIN + PAPERS}
build = read("build_seo.py")
asset_v = re.search(r'ASSET_V\s*=\s*"([^"]+)"', build).group(1)
project_keys = set(re.findall(r'^\s{4}"([\w-]+)":\s*\{', build.split("PROJECTS = {", 1)[1].split("\n}", 1)[0], re.M))

# ---------------------------------------------------------------- every page
ids = {p: set(re.findall(r'\bid="([^"]+)"', s)) for p, s in pages.items()}
for p, s in pages.items():
    for v in set(re.findall(r'\.(?:css|js)\?v=([\w.-]+)', s)):
        if v != asset_v:
            err(f"{p}: asset version ?v={v} (ASSET_V is {asset_v}) - run build_seo.py")
    base = os.path.dirname(p)
    for attr, url in re.findall(r'\b(href|src)="([^"]+)"', s):
        if "${" in url or url.startswith(("http", "mailto:", "tel:", "data:", "javascript:")):
            continue
        url = html.unescape(url)
        path, _, frag = url.partition("#")
        path = path.split("?")[0]
        target = os.path.normpath(os.path.join(base, path)).replace("\\", "/") if path else p
        if path and not os.path.exists(target):
            err(f"{p}: broken {attr} {url}")
        elif frag and target in ids and frag not in ids[target]:
            err(f"{p}: missing anchor {url}")
    for tag in re.findall(r"<a\b[^>]*>", s):
        h = re.search(r'href="([^"]+)"', tag)
        if not h or "${" in h.group(1):
            continue
        external = h.group(1).startswith("http") and "saeedlotfan.com" not in h.group(1)
        if external and 'target="_blank"' not in tag:
            err(f"{p}: external link opens in the same tab: {h.group(1)[:70]}")
        if 'target="_blank"' in tag and "noopener" not in tag:
            err(f"{p}: target=_blank without rel=noopener: {h.group(1)[:70]}")
    for tag in re.findall(r"<img\b[^>]*>", s):
        if "${" in tag:
            continue
        missing = [a for a in ("alt=", "width=", "height=") if a not in tag]
        if missing:
            err(f"{p}: <img> without {', '.join(m[:-1] for m in missing)}: {tag[:90]}")
    for j in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try:
            json.loads(j)
        except ValueError as e:
            err(f"{p}: invalid JSON-LD ({e})")

    # wording conventions (main pages: hand-written text)
    if p in MAIN:
        t = visible_text(s)
        rules = [
            (r"\b(?:BSc|MSc|PhD|Msc|Bsc|Phd|B\.S\.|M\.S\.)\b", "degree spelling (use B.Sc., M.Sc., Ph.D.)"),
            (r"\b(?:19|20)\d\d\s+[-–—]\s*(?:(?:19|20)\d\d|Present)\b", "year range with spaces (use 2022–Present)"),
            (r"\b(?:19|20)\d\d-(?:(?:19|20)\d\d|Present)\b", "year range with a hyphen (use an en dash)"),
            (r"\b(?:Assoc\.|Asst\.|Assist\.) Prof", "use Dr. for assistant/associate professors"),
            (r"\bTurkey\b", "use Türkiye"),
            (r"\b(?:Sabanci|Atilim|Turkiye|Cigeroglu|Tubitak|TUBITAK|Bogazici|Kocaeli Universitesi)\b", "Turkish spelling (Sabancı, Atılım, Ciğeroğlu, TÜBİTAK, ...)"),
            (r"\bPresentations?\b", 'type label is "Talk" (data key stays Presentation)'),
        ]
        if p == "publications.html":   # its plain list repeats the citations (checked in the data below)
            t = visible_text(s.split("<!-- static-index:start -->")[0])
        for pat, why in rules:
            for m in sorted(set(re.findall(pat, t))):
                err(f"{p}: '{m}' - {why}")

# ---------------------------------------------------------------- news cards
idx = pages["index.html"]
months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
prev = None
for i, art in enumerate(re.findall(r'<article class="news-item.*?</article>', idx, re.S), 1):
    tag = re.search(r'<span class="pub-tag[^"]*">([^<]+)</span>', art)
    date = re.search(r'<time class="news-date" datetime="([^"]+)">([^<]+)</time>', art)
    title = re.search(r'<h3 class="news-title">(.*?)</h3>', art, re.S)
    label = visible_text(title.group(1)).strip()[:50] if title else f"card {i}"
    if not tag or tag.group(1) not in NEWS_TAGS:
        err(f"news '{label}': type label {tag.group(1) if tag else 'missing'!r} not one of {sorted(NEWS_TAGS)}")
    if not date:
        err(f"news '{label}': missing <time class=\"news-date\">")
        continue
    dt, shown = date.groups()
    if re.fullmatch(r"\d{4}-\d\d", dt):
        expect = f"{months[int(dt[5:]) - 1]} {dt[:4]}"
        if shown != expect:
            err(f"news '{label}': date shows '{shown}', datetime says {expect}")
        if prev and dt > prev:
            err(f"news '{label}': out of date order (newest first)")
        prev = dt
    elif i != 1:
        warn(f"news '{label}': datetime '{dt}' has no month (only the pinned first card should)")
    for link in re.findall(r'<a class="news-link"[^>]*>', art):
        if 'target="_blank"' in link and "↗" not in art and 'd="M7 17 17 7' not in art:
            warn(f"news '{label}': external link without the ↗ icon")
    if 'class="news-thumbnail"' in art and 'width="164" height="108"' not in art:
        err(f"news '{label}': thumbnail must be width=\"164\" height=\"108\"")

# ---------------------------------------------------------------- publications data
data = json.load(io.open("publications_data.json", encoding="utf-8"))
seen = set()
for p in data:
    name = p.get("title", "?")[:60]
    for k in ("type", "title", "authors", "cite", "abstract", "doi", "image"):
        if k not in p:
            err(f"publication '{name}': missing \"{k}\"")
    if p.get("type") not in PUB_TYPES:
        err(f"publication '{name}': type {p.get('type')!r} not one of {sorted(PUB_TYPES)}")
    if p.get("project") and p["project"] not in project_keys:
        err(f"publication '{name}': project {p['project']!r} is not in PROJECTS in build_seo.py")
    if p.get("image") and not os.path.exists(p["image"]):
        err(f"publication '{name}': image {p['image']} not found")
    if p.get("image") and os.path.exists(p["image"]) and os.path.getsize(p["image"]) > 400_000:
        warn(f"publication '{name}': image {p['image']} is {os.path.getsize(p['image']) // 1024} KB (compress it)")
    if "Lotfan, S." not in p.get("authors", ""):
        warn(f"publication '{name}': authors do not contain 'Lotfan, S.' (not bolded on the page)")
    if re.search(r"\bTurkey\b", p.get("cite", "")):
        warn(f"publication '{name}': citation says Turkey (newer entries use Türkiye)")
    if p.get("title") in seen:
        err(f"publication '{name}': duplicate title")
    seen.add(p.get("title"))
years = [int(m[-1]) for p in data for m in [re.findall(r"((?:19|20)\d\d)", p.get("cite", ""))] if m]  # same rule as build_seo.py
if years != sorted(years, reverse=True):
    warn("publications_data.json is not newest first")

# ---------------------------------------------------------------- teaching PDFs
for f in glob.glob("TeachingMaterials/**/*.pdf", recursive=True):
    base = os.path.basename(f)
    if not re.fullmatch(r"(syllabus|exam-archive|review-problems|(lecture|recitation|homework)\d\d(-[a-z0-9]+)*)\.pdf", base):
        warn(f"{f}: name does not follow lectureNN-topic.pdf / recitationNN-topic.pdf / syllabus.pdf")
    if os.path.getsize(f) > 8_000_000:
        warn(f"{f}: {os.path.getsize(f) // 1_000_000} MB (try compressing)")
for img in glob.glob("newsimages/*") + glob.glob("PublicationPage/*") + glob.glob("ResearchPage/*"):
    if os.path.getsize(img) > 600_000:
        warn(f"{img}: {os.path.getsize(img) // 1024} KB (compress it)")

# ---------------------------------------------------------------- report
for w in warns:
    print("WARN ", w)
for e in errors:
    print("ERROR", e)
print(f"\n{len(errors)} error(s), {len(warns)} warning(s) across {len(pages)} pages and {len(data)} publications.")
sys.exit(1 if errors else 0)
