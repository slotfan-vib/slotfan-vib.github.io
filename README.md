# slotfan-vib.github.io

My personal academic website, [saeedlotfan.com](https://saeedlotfan.com) (GitHub Pages, plain HTML/CSS/JS).

## One source for each thing

Change a fact in its source and every page that shows it follows.

| What | Source | Shown on |
|---|---|---|
| Publications (title, authors, abstract, DOI, figure) | `publications_data.json` | Publications, paper pages `papers/*.html`, home counts, Research counts and themes |
| Which project a paper belongs to | `"project": "<key>"` in `publications_data.json` | "Part of project" on Publications and paper pages, project paper counts |
| Funded projects with a story page | `PROJECTS` in `build_seo.py` + the card on `research.html` | Research, paper pages, Publications links, home "Funded projects" |
| Research themes | `THEMES` in `site.js` (optional `"themes": [...]` in a paper places it by hand) | Research theme links and counts, Publications theme filter |
| Students | `<article class="person-card">` blocks on `people.html` | People, home "Students mentored" |
| Courses and PDFs | `teaching.html` (folders in `TeachingMaterials/`) | Teaching header counts, download names (`teaching.js`) |
| Asset version (cache busting) | `ASSET_V` in `build_seo.py` | `?v=` on every page |

Numbers are never typed by hand: `site.js` / `teaching.js` recount them in the browser, and
`build_seo.py` writes the same numbers into the HTML for search engines and visitors without JavaScript.

## After any change

```bash
python build_seo.py
```

It regenerates the paper pages, the publications JSON-LD and plain list, `sitemap.xml` and
`robots.txt`, writes `ASSET_V` into every page, and recounts the numbers in the HTML. It is safe to
run repeatedly; "Pages brought up to date: none" means everything was already in step.

## How to add…

- **A paper:** add an entry to `publications_data.json` (newest first; `type` is `Journal`, `Conference`,
  `Presentation` or `Poster`; figure in `PublicationPage/`). Add `"project": "<key>"` if a funded project
  produced it. Run `build_seo.py`. Add a news card on the home page if wanted.
- **A news card:** copy one `<article class="news-item">` on `index.html`, newest first. Follow the
  wording patterns below. The "Show all news (N)" count updates itself.
- **A student:** copy one `person-card` on `people.html` into the right group. Run `build_seo.py`.
- **A funded project:** copy a `project-card` on `research.html`; add a news card. If it gets a story page,
  add it to `PROJECTS` and `STATIC_PAGES` in `build_seo.py`. Run `build_seo.py`.
- **A lecture PDF:** compress it, name it like the others (e.g. `lecture07-topic-words.pdf`) in the course
  folder, and copy one row in that course on `teaching.html`. Run `build_seo.py`.
- **A CSS/JS change:** bump `ASSET_V` in `build_seo.py`, then run it.

## Wording conventions

- Types: Journal paper · Conference paper · Talk · Poster (filters: Journal papers, Conference papers,
  Talks & posters). News also uses M.Sc. thesis, Funded project, Student project, Open positions.
- Titles: "Prof." only for full professors; "Dr." for assistant and associate professors.
- Degrees B.Sc., M.Sc., Ph.D.; year ranges with an unspaced en dash (2022–Present); serial comma
  (a, b, and c); Turkish spelling (Türkiye, Sabancı, Koç, Ciğeroğlu).
- News: type label first, then the date (Mon YYYY).
  - Journal: "Accepted in *Journal*. With Prof./Dr. X (University)."
  - Conference/Talk/Poster: "Presented at the *Full Name* (ACRONYM), D–D Month, City, Country."
  - Funded project: "Accepted for funding under *TÜBİTAK 1001* – … (years). My role: PI/Researcher.
    Principal investigator/Researcher: …"
  - M.Sc. thesis: thesis title; "My master's student **Name** successfully defended…"
- Links: pages on this site open in the same tab (→); other sites open in a new tab (↗).
