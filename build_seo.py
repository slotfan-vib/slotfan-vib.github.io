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
import subprocess
from datetime import date

SITE = "https://saeedlotfan.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
TODAY = date.today().isoformat()

# ORCID iD, e.g. "0000-0002-1825-0097". Leave "" to omit ORCID markup.
ORCID = "0000-0001-8616-2120"

# Cache-busting version for shared CSS/JS. Keep it equal to the ?v= used in
# the top-level *.html pages and bump it whenever style.css / site.js change.
ASSET_V = "20261119v"

# Display names for publication types (data keys stay Journal/Conference/
# Presentation so filters and ?type= links keep working). Same wording as the
# home-page news tags and the publications page.
TYPE_LABELS = {"Journal": "Journal paper", "Conference": "Conference paper", "Presentation": "Talk", "Poster": "Poster"}

STATIC_PAGES = [
    ("index.html", "1.0", "weekly"),
    ("research.html", "0.8", "monthly"),
    ("publications.html", "0.9", "weekly"),
    ("teaching.html", "0.6", "monthly"),
    ("people.html", "0.6", "monthly"),
    ("contact.html", "0.5", "yearly"),
    ("projects/rotating-blades.html", "0.8", "monthly"),
]

# Funded projects with their own write-up page. A paper belongs to a project
# when its entry in publications_data.json has "project": "<key>"; it then gets
# a "Part of project" link and grant metadata (publications.html shows it too).
PROJECTS = {
    "rotating-blades": {
        "name": "Dynamics of Rotating Blades",
        "page": "projects/rotating-blades.html",
        "program": "TÜBİTAK 1001",
        "grant": "123M046",
        "years": "2023–2025",
    },
}

STOPWORDS = set("""a an and the of in on for with to by from using based via under
including its their into toward towards new study analysis approach model models
method methods system systems""".split())


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
def project_of(pub):
    return PROJECTS.get(pub.get("project", ""))


def title_tokens(title):
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 3 and w not in STOPWORDS}


def related_for(i, pubs, slugs, n=4):
    """Most similar other papers by shared title words (same project first)."""
    me = title_tokens(pubs[i]["title"])
    pr = project_of(pubs[i])
    scored = []
    for j, other in enumerate(pubs):
        if j == i:
            continue
        score = len(me & title_tokens(other["title"]))
        if pr and project_of(other) is pr:
            score += 5
        if score:
            scored.append((-score, j))
    scored.sort()
    picked = [j for _, j in scored[:n]]
    # Top up with the papers nearest in the (chronological) list, so every
    # paper page links to a few others.
    for j in sorted(range(len(pubs)), key=lambda k: abs(k - i)):
        if len(picked) >= n:
            break
        if j != i and j not in picked:
            picked.append(j)
    return [(pubs[j], slugs[j]) for j in picked]


def build_paper_page(pub, slug, related=(), project=None):
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

    # JSON-LD ScholarlyArticle — attach ORCID to the site owner's author entry.
    def author_node(name):
        node = {"@type": "Person", "name": name}
        if ORCID and name.lower().startswith("lotfan"):
            node["url"] = f"{SITE}/"
            node["identifier"] = f"https://orcid.org/{ORCID}"
            node["sameAs"] = f"https://orcid.org/{ORCID}"
        return node

    jsonld = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": title,
        "name": title,
        "author": [author_node(a) for a in authors],
        "isPartOf": {"@type": "Periodical", "name": venue},
        "abstract": pub["abstract"],
        "url": url,
    }
    if year:
        jsonld["datePublished"] = year
    if doi:
        jsonld["identifier"] = {"@type": "PropertyValue", "propertyName": "DOI", "value": doi}
        jsonld["sameAs"] = f"https://doi.org/{doi}"
    if project:
        jsonld["funding"] = {
            "@type": "Grant",
            "identifier": project["grant"],
            "name": project["name"],
            "url": f"{SITE}/{project['page']}",
            "funder": {"@type": "Organization",
                       "name": "TÜBİTAK – Scientific and Technological Research Council of Türkiye"},
        }

    project_html = ""
    if project:
        project_html = (
            '\n      <aside class="paper-project">\n'
            '        <p class="paper-project-label">Part of a funded project</p>\n'
            f'        <p><a href="../{project["page"]}">{esc(project["name"])}</a>'
            f' <span>{esc(project["program"])} · No. {esc(project["grant"])} · {esc(project["years"])}</span></p>\n'
            '      </aside>'
        )
    related_html = ""
    if related:
        rows = []
        for p2, s2 in related:
            y2 = parse_year(p2["cite"])
            rows.append(f'        <li><a href="{s2}.html">{esc(p2["title"])}</a>'
                        f' <span>{esc(TYPE_LABELS.get(p2["type"], p2["type"]))}{" · " + esc(y2) if y2 else ""}</span></li>')
        related_html = ('\n\n      <h2>Related publications</h2>\n      <ul class="related-list">\n'
                        + "\n".join(rows) + '\n      </ul>')

    type_label = TYPE_LABELS.get(pub["type"], pub["type"])
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
  <link rel="stylesheet" href="../style.css?v={ASSET_V}" />
  <link rel="stylesheet" href="../publications-style.css?v={ASSET_V}" />
  <script>(function(){{try{{var t=localStorage.getItem('theme');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}}})();</script>

  <script type="application/ld+json">
  {json.dumps(jsonld, ensure_ascii=False, indent=2)}
  </script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <nav class="navbar" aria-label="Main navigation">
    <a class="nav-brand" href="../index.html">Saeed&nbsp;Lotfan <span class="brand-tag">Vibrations Lab</span></a>
    <div class="nav-links" id="site-nav">
      <a href="../index.html">Home</a>
      <a href="../research.html">Research</a>
      <a href="../publications.html">Publications</a>
      <a href="../teaching.html">Teaching</a>
      <a href="../people.html">People</a>
      <a href="../contact.html">Contact</a>
    </div>
    <div class="nav-actions">
      <button class="icon-btn theme-toggle" type="button" aria-label="Switch theme">
        <svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
        <svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>
      </button>
      <button class="icon-btn nav-toggle" type="button" aria-label="Toggle menu" aria-expanded="false" aria-controls="site-nav">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
      </button>
    </div>
  </nav>

  <main id="main" class="container">
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

      <p><a class="news-link" href="{esc(source)}" target="_blank" rel="noopener noreferrer">Read paper <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9"/></svg></a></p>{project_html}{related_html}
    </article>
  </main>

  <footer class="footer">&copy; {date.today().year} Saeed Lotfan &middot; Gebze Technical University &middot; All rights reserved.</footer>
  <script src="../site.js?v={ASSET_V}" defer></script>
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
        <h3><a href="papers/{slug}.html">{esc(pub['title'])}</a></h3>
        <p>{esc(pub['authors'])} <em>{esc(pub['cite'])}</em></p>
        <a class="news-link" href="{esc(source)}" target="_blank" rel="noopener noreferrer">Read paper<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9"/></svg></a>
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

    # Replace the static index (a folded plain list that search engines read)
    # between its two markers, including the count in the summary line.
    static_rows = build_static_index(pubs, slugs)
    html_doc = re.sub(
        r"(<!-- static-index:start -->).*?(<!-- static-index:end -->)",
        lambda m: (m.group(1)
                   + f'\n      <summary>Show all {len(pubs)} publications as a plain list</summary>\n\n'
                   + static_rows + "\n      " + m.group(2)),
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


def lastmod(path):
    """Date the file last really changed: its last commit, or today if it has
    uncommitted edits. Google ignores <lastmod> when every page says "today"."""
    try:
        dirty = subprocess.run(["git", "status", "--porcelain", "--", path], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        if dirty:
            return TODAY
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", path], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
        return out or TODAY
    except Exception:
        return TODAY


def build_sitemap(slugs):
    urls = []
    for page, prio, freq in STATIC_PAGES:
        loc = f"{SITE}/" if page == "index.html" else f"{SITE}/{page}"
        urls.append((loc, prio, freq, lastmod(page)))
    for slug in slugs:
        page = f"papers/{slug}.html"
        urls.append((f"{SITE}/{page}", "0.7", "yearly", lastmod(page)))

    body = "\n".join(
        f"  <url>\n"
        f"    <loc>{loc}</loc>\n"
        f"    <lastmod>{mod}</lastmod>\n"
        f"    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{prio}</priority>\n"
        f"  </url>"
        for loc, prio, freq, mod in urls
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
    for i, (pub, slug) in enumerate(zip(pubs, slugs)):
        with open(os.path.join(ROOT, "papers", f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(build_paper_page(pub, slug, related_for(i, pubs, slugs), project_of(pub)))

    inject_publications_html(pubs, slugs)

    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(build_robots())
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(build_sitemap(slugs))

    print(f"Generated {len(pubs)} paper pages, sitemap.xml, robots.txt, "
          f"and updated publications.html.")


if __name__ == "__main__":
    main()
