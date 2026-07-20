#!/usr/bin/env python3
"""
build_seo.py — regenerate SEO assets from publications_data.json.

Produces / updates:
  * publications.html  -> JSON-LD ItemList + static crawlable index (ALL papers)
  * papers/<slug>.html -> one landing page per paper (Highwire citation_* meta
                          tags + ScholarlyArticle JSON-LD, for Scholar / AI tools)
  * sitemap.xml        -> every page including the per-paper landing pages
  * robots.txt         -> crawler policy (AI crawlers welcomed) + sitemap pointer

Run after editing publications_data.json:  python3 build_seo.py
The script is idempotent — safe to run repeatedly.
"""

import json
import re
import os
import html
from datetime import date

SITE = "https://saeedlotfan.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
TODAY = date.today().isoformat()

# ORCID iD, e.g. "0000-0002-1825-0097". Leave "" to omit ORCID markup.
ORCID = ""

STATIC_PAGES = [
    ("index.html", "1.0", "weekly"),
    ("research.html", "0.8", "monthly"),
    ("publications.html", "0.9", "weekly"),
    ("teaching.html", "0.6", "monthly"),
    ("people.html", "0.6", "monthly"),
    ("contact.html", "0.5", "yearly"),
]


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
def load_pubs():
    with open(os.path.join(ROOT, "publications_data.json"), encoding="utf-8") as f:
        return json.load(f)


def slugify(title):
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80].rstrip("-")


def parse_year(cite):
    years = re.findall(r"(19|20)\d{2}", cite)
    m = re.findall(r"\b((?:19|20)\d{2})\b", cite)
    return m[-1] if m else ""


def parse_authors(author_str):
    """Return a list of 'Surname, I.' strings, tolerant of the varied formats."""
    authors = []
    for surname, initials in re.findall(r"([^,]+?)\s*,?\s*((?:[A-Z]\.){1,3})", author_str):
        surname = surname.strip()
        surname = re.sub(r"^(and|&)\s+", "", surname, flags=re.I).strip()
        if surname:
            authors.append(f"{surname}, {initials}")
    return authors


def parse_venue(pub):
    """Journal/conference name = text before the first comma of the citation."""
    return pub["cite"].split(",")[0].strip().rstrip(".")


def parse_volume_issue_pages(cite):
    volume = issue = firstpage = lastpage = ""
    m = re.search(r",\s*(\d+)\((\d+(?:-\d+)?)\)", cite)  # 27(80)
    if m:
        volume, issue = m.group(1), m.group(2)
    else:
        m = re.search(r",\s*(\d+(?:[-–]\d+)?)\s*,\s*pp", cite)  # 218, pp...
        if m:
            volume = m.group(1)
    m = re.search(r"pp\.?\s*([0-9]+)\s*[-–]\s*([0-9]+)", cite)
    if m:
        firstpage, lastpage = m.group(1), m.group(2)
    else:
        m = re.search(r"pp\.?\s*([0-9]+)", cite)
        if m:
            firstpage = m.group(1)
    return volume, issue, firstpage, lastpage


def parse_doi(pub):
    m = re.search(r"10\.\d{4,9}/[^\s\"'<>]+", pub.get("doi", ""))
    return m.group(0) if m else ""


def esc(s):
    return html.escape(s or "", quote=True)


# --------------------------------------------------------------------------- #
# Per-paper landing pages
# --------------------------------------------------------------------------- #
def build_paper_page(pub, slug):
    title = pub["title"]
    authors = parse_authors(pub["authors"])
    year = parse_year(pub["cite"])
    venue = parse_venue(pub)
    volume, issue, firstpage, lastpage = parse_volume_issue_pages(pub["cite"])
    doi = parse_doi(pub)
    source = pub.get("doi", "")
    url = f"{SITE}/papers/{slug}.html"

    is_journal = pub["type"] == "Journal"
    venue_tag = "citation_journal_title" if is_journal else "citation_conference_title"

    meta = [f'<meta name="citation_title" content="{esc(title)}">']
    for a in authors:
        meta.append(f'<meta name="citation_author" content="{esc(a)}">')
    if year:
        meta.append(f'<meta name="citation_publication_date" content="{esc(year)}">')
        meta.append(f'<meta name="citation_online_date" content="{esc(year)}">')
    meta.append(f'<meta name="{venue_tag}" content="{esc(venue)}">')
    if volume:
        meta.append(f'<meta name="citation_volume" content="{esc(volume)}">')
    if issue:
        meta.append(f'<meta name="citation_issue" content="{esc(issue)}">')
    if firstpage:
        meta.append(f'<meta name="citation_firstpage" content="{esc(firstpage)}">')
    if lastpage:
        meta.append(f'<meta name="citation_lastpage" content="{esc(lastpage)}">')
    if doi:
        meta.append(f'<meta name="citation_doi" content="{esc(doi)}">')
    if source:
        meta.append(f'<meta name="citation_abstract_html_url" content="{esc(source)}">')
    citation_meta = "\n  ".join(meta)

    # JSON-LD ScholarlyArticle
    jsonld = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": title,
        "name": title,
        "author": [{"@type": "Person", "name": a} for a in authors],
        "isPartOf": {"@type": "Periodical", "name": venue},
        "abstract": pub["abstract"],
        "url": url,
    }
    if year:
        jsonld["datePublished"] = year
    if doi:
        jsonld["identifier"] = {"@type": "PropertyValue", "propertyName": "DOI", "value": doi}
        jsonld["sameAs"] = f"https://doi.org/{doi}"
    author_page = {"@type": "Person", "name": "Saeed Lotfan", "url": f"{SITE}/"}
    if ORCID:
        author_page["identifier"] = f"https://orcid.org/{ORCID}"

    type_label = {"Journal": "Journal Article", "Conference": "Conference Paper"}.get(
        pub["type"], pub["type"]
    )
    desc = (pub["abstract"][:180].rsplit(" ", 1)[0] + "…") if pub["abstract"] else title

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)} | Saeed Lotfan</title>
  <meta name="description" content="{esc(desc)}" />
  <meta name="author" content="Saeed Lotfan" />
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large" />
  <link rel="canonical" href="{url}" />

  {citation_meta}

  <meta property="og:type" content="article" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:image" content="{SITE}/{esc(pub.get('image',''))}" />
  <meta property="og:site_name" content="Saeed Lotfan" />

  <link rel="icon" href="../favicon.png" type="image/png" />
  <link rel="stylesheet" href="../style.css" />
  <link rel="stylesheet" href="../publications-style.css" />

  <script type="application/ld+json">
  {json.dumps(jsonld, ensure_ascii=False, indent=2)}
  </script>
</head>
<body>
  <nav class="navbar" aria-label="Main navigation">
    <a href="../index.html">Home</a>
    <a href="../research.html">Research</a>
    <a href="../publications.html">Publications</a>
    <a href="../teaching.html">Teaching</a>
    <a href="../people.html">People</a>
    <a href="../contact.html">Contact</a>
  </nav>

  <main class="container">
    <article class="publication-detail">
      <p><a href="../publications.html">&larr; All publications</a></p>
      <h1>{esc(title)}</h1>
      <p class="pub-authors">{esc(pub['authors'])}</p>
      <p class="pub-cite"><em>{esc(pub['cite'])}</em>
        <span class="pub-tag {pub['type']}">{esc(type_label)}</span></p>

      <figure class="pub-figure">
        <img src="../{esc(pub.get('image',''))}" alt="Figure for {esc(title)}" loading="lazy" />
      </figure>

      <h2>Abstract</h2>
      <p>{esc(pub['abstract'])}</p>

      <p><a href="{esc(source)}" target="_blank" rel="noopener noreferrer">View published paper &rarr;</a></p>
    </article>
  </main>

  <footer class="footer">&copy; {date.today().year} Saeed Lotfan. All rights reserved.</footer>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# publications.html injection (JSON-LD ItemList + static crawlable index)
# --------------------------------------------------------------------------- #
def build_itemlist_jsonld(pubs, slugs):
    items = []
    for i, (pub, slug) in enumerate(zip(pubs, slugs), start=1):
        doi = parse_doi(pub)
        item = {
            "@type": "ScholarlyArticle",
            "headline": pub["title"],
            "author": [{"@type": "Person", "name": a} for a in parse_authors(pub["authors"])],
            "isPartOf": {"@type": "Periodical", "name": parse_venue(pub)},
            "url": f"{SITE}/papers/{slug}.html",
        }
        year = parse_year(pub["cite"])
        if year:
            item["datePublished"] = year
        if doi:
            item["sameAs"] = f"https://doi.org/{doi}"
        items.append({"@type": "ListItem", "position": i, "item": item})

    author = {
        "@type": "Person",
        "name": "Saeed Lotfan",
        "url": f"{SITE}/",
        "affiliation": {"@type": "CollegeOrUniversity", "name": "Gebze Technical University"},
    }
    if ORCID:
        author["identifier"] = f"https://orcid.org/{ORCID}"
        author["sameAs"] = f"https://orcid.org/{ORCID}"

    data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Publications | Saeed Lotfan",
        "url": f"{SITE}/publications.html",
        "description": "Publications by Saeed Lotfan in nonlinear vibrations, structural "
        "dynamics, computational mechanics, rotordynamics, reduced-order modeling, "
        "and related areas.",
        "author": author,
        "mainEntity": {
            "@type": "ItemList",
            "name": "Publications by Saeed Lotfan",
            "numberOfItems": len(items),
            "itemListElement": items,
        },
    }
    return (
        '  <script type="application/ld+json">\n  '
        + json.dumps(data, ensure_ascii=False, indent=2)
        + "\n  </script>"
    )


def build_static_index(pubs, slugs):
    rows = []
    for pub, slug in zip(pubs, slugs):
        source = pub.get("doi", "")
        rows.append(
            f"""      <article class="publication-seo-item">
        <h4><a href="papers/{slug}.html">{esc(pub['title'])}</a></h4>
        <p>{esc(pub['authors'])} <em>{esc(pub['cite'])}</em></p>
        <a href="{esc(source)}" target="_blank" rel="noopener noreferrer">View paper</a>
      </article>"""
        )
    return "\n\n".join(rows)


def inject_publications_html(pubs, slugs):
    path = os.path.join(ROOT, "publications.html")
    with open(path, encoding="utf-8") as f:
        html_doc = f.read()

    # Replace the head JSON-LD block (there is exactly one ld+json script).
    html_doc = re.sub(
        r'  <script type="application/ld\+json">.*?</script>',
        lambda m: build_itemlist_jsonld(pubs, slugs),
        html_doc,
        count=1,
        flags=re.S,
    )

    # Replace the static index rows (between the heading and the section close).
    static_rows = build_static_index(pubs, slugs)
    html_doc = re.sub(
        r'(<h3 id="publication-static-heading">Selected Publication Index</h3>)'
        r"(.*?)(\n\s*</section>)",
        lambda m: m.group(1) + "\n\n" + static_rows + m.group(3),
        html_doc,
        count=1,
        flags=re.S,
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)


# --------------------------------------------------------------------------- #
# robots.txt + sitemap.xml
# --------------------------------------------------------------------------- #
def build_robots():
    ai_bots = [
        "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-Web",
        "anthropic-ai", "PerplexityBot", "Google-Extended", "Applebot-Extended",
        "CCBot", "Bytespider", "Amazonbot", "cohere-ai",
    ]
    lines = ["# robots.txt for saeedlotfan.com", "User-agent: *", "Allow: /", ""]
    lines.append("# Explicitly welcome AI / research crawlers")
    for bot in ai_bots:
        lines += [f"User-agent: {bot}", "Allow: /", ""]
    lines.append(f"Sitemap: {SITE}/sitemap.xml")
    return "\n".join(lines) + "\n"


def build_sitemap(slugs):
    urls = []
    for page, prio, freq in STATIC_PAGES:
        loc = f"{SITE}/" if page == "index.html" else f"{SITE}/{page}"
        urls.append((loc, prio, freq))
    for slug in slugs:
        urls.append((f"{SITE}/papers/{slug}.html", "0.7", "yearly"))

    body = "\n".join(
        f"  <url>\n"
        f"    <loc>{loc}</loc>\n"
        f"    <lastmod>{TODAY}</lastmod>\n"
        f"    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{prio}</priority>\n"
        f"  </url>"
        for loc, prio, freq in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )


# --------------------------------------------------------------------------- #
def main():
    pubs = load_pubs()

    # Stable, unique slugs.
    slugs, seen = [], {}
    for pub in pubs:
        base = slugify(pub["title"])
        slug = base
        n = seen.get(base, 0)
        if n:
            slug = f"{base}-{n + 1}"
        seen[base] = n + 1
        slugs.append(slug)

    os.makedirs(os.path.join(ROOT, "papers"), exist_ok=True)
    for pub, slug in zip(pubs, slugs):
        with open(os.path.join(ROOT, "papers", f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(build_paper_page(pub, slug))

    inject_publications_html(pubs, slugs)

    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(build_robots())
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(build_sitemap(slugs))

    print(f"Generated {len(pubs)} paper pages, sitemap.xml, robots.txt, "
          f"and updated publications.html.")


if __name__ == "__main__":
    main()
