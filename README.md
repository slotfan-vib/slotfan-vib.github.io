# slotfan-vib.github.io

My personal academic website, [saeedlotfan.com](https://saeedlotfan.com) (GitHub Pages, plain HTML/CSS/JS).

## One source for each thing

Change a fact in its source and every page that shows it follows.

| What | Source | Shown on |
|---|---|---|
| Publications (title, authors, abstract, DOI, figure) | `publications_data.json` | Publications, paper pages `papers/*.html`, home counts, Research counts and themes |
| Which project a paper belongs to | `"project": "<key>"` in `publications_data.json` | "Part of project" on Publications and paper pages, project paper counts |
| Funded projects that have papers | `PROJECTS` in `build_seo.py` (page = its story page, or its card `research.html#project-…`) + the card on `research.html` | Research, paper pages, Publications links, home "Funded projects" |
| Research themes | `THEMES` in `site.js` (optional `"themes": [...]` in a paper places it by hand) | Research theme links and counts, Publications theme filter |
| Students | `<article class="person-card">` blocks on `people.html` | People, home "Students mentored" |
| Courses and PDFs | `teaching.html` (folders in `TeachingMaterials/`) | Teaching header counts, download names (`teaching.js`) |
| Asset version (cache busting) | `ASSET_V` in `build_seo.py` | `?v=` on every page |

Numbers are never typed by hand: `site.js` / `teaching.js` recount them in the browser, and
`build_seo.py` writes the same numbers into the HTML for search engines and visitors without JavaScript.

## After any change

```bash
python build_seo.py
python check_site.py
```

`build_seo.py` regenerates the paper pages, the publications JSON-LD and plain list, `sitemap.xml` and
`robots.txt`, writes `ASSET_V` into every page, and recounts the numbers in the HTML. It is safe to
run repeatedly; "Pages brought up to date: none" means everything was already in step.

`check_site.py` checks the conventions below (versions, links, image sizes, news labels and dates,
publication fields, wording, PDF names and sizes) and must end with `0 error(s)` before a push.

## Checklist for every update (handoff)

Read this file first, then make the edit in its source and finish with the two commands above.

1. **Source, not copies.** Change the fact where it lives (table above). Never type a count by hand.
2. **Same wording as the existing cards.** Copy the nearest existing block of the same kind and
   follow the patterns under *Wording conventions*. Paper titles exactly as in
   `publications_data.json`; project titles as on `research.html`; people's titles by the Prof./Dr. rule.
3. **One update touches every place it belongs:**
   - *New paper* → `publications_data.json` (+ `"project"` if any) → news card → `build_seo.py`.
   - *Paper accepted/presented* → news card titled exactly as the data entry, linking the title to
     `papers/<slug>.html` and "Read paper ↗" to the DOI (or "View abstract ↗" before a DOI exists).
   - *Funded project* → project card on Research + "Funded project" news card (date funded);
     on completion, a second news card linking to its story page.
   - *Student* → People card + thesis news card when they defend.
   - *Course material* → PDF in `TeachingMaterials/<COURSE>/`, named and compressed, + its row on Teaching.
4. **Images:** compress (news thumbnails ≲ 150 KB, figures ≲ 400 KB), give `alt`, `width` and `height`
   (news thumbnails are `width="164" height="108"`).
5. **Links:** pages on this site in the same tab with →; other sites in a new tab with ↗ and
   `rel="noopener noreferrer"`.
6. **CSS/JS changed?** Bump `ASSET_V`.
7. **Check on localhost** (desktop, mobile, dark mode) before pushing.

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
