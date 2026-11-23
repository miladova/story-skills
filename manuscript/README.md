# The Birch and the Bell

*A Novella of Warsaw, 1958* — 10 chapters, 52,812 words

> The bell does not choose who hears it.

## What is here

| Path | What it is |
|------|------------|
| `manuscript.md` | The whole novella in one file (title page, contents, ten chapters, afterword, historical note). Best for reading or sharing. |
| `the-birch-and-the-bell.epub` | EPUB 3 e-book, built from the story project. |
| `the-birch-and-the-bell.docx` | Word document, built from the story project. |
| `the-birch-and-the-bell.pdf` | Typeset PDF, 5.5 × 8.5 in, 190 pages: title page, contents with page numbers, running heads, chapter openers, roman-numeral front matter, and PDF bookmarks. Built by `build_pdf.py`. |
| `chapters/` | One file per chapter, plain markdown. The working drafts. |
| `_front.md` | Title page and contents, used to assemble `manuscript.md`. |
| `project/` | A Story Skills project (`story.md`, characters, locations, factions, artifacts, arcs, scenes, timeline, continuity state, front/back matter). Run commands from inside it, e.g. `node ../../bin/story.js wordcount`. |

## The story

Warsaw, 1958. Halina Sowa, deputy head of the Propaganda and Agitation Department of the Party's Central Committee, is handed a file and an ultimatum: persuade the priest Janusz Wilga to join the state's Commission of Priests and be a bishop on the state's terms, or the file — his Gestapo confession of 1943, and her own signature on a 1945 report that got a man shot — goes public.

They were children together in the village of Brzóza. She joined the People's Guard; he joined the Home Army and then the priesthood. In a parish hall in Praga in November 1958, each of them confesses to the other what the war made them do. What follows is not a romance and not a trial: it is the slow, unsentimental work of two people deciding what they can still be, in a country that has uses for both of them.

## Chapter list

1. The Funeral of Brunon Kowalik — 4,227
2. The File — 5,204
3. The Parish of the Transfiguration — 4,590
4. The Sermon — 5,971
5. The Years of the Locust — 7,136
6. The Bishop's Cross — 4,595
7. The Tenth of December — 5,476
8. The Fourth Sunday of Advent — 5,331
9. The Vigil — 5,924
10. The Birch and the Bell — 4,358

## Historical frame

Real: Cardinal Wyszyński's return from internment after October 1956; the raid on the Primate's Institute at Jasna Góra on 21 July 1958; the post-1956 arrangement under which the Church presented a single candidate for each see and the state could only accept or refuse; the Wojtyła appointment of 1958; the Propaganda and Agitation Department, the Security Service, and the Office for Religious Affairs. Invented: Brzóza, the Kowals, the Wilgas, Rydel, Bochenek, and the parish on Brzeska Street. See "A Note on History" at the end.

## Rebuilding everything

`manuscript.md` is assembled from `_front.md` + `chapters/*.md` + `project/matter/`
(the afterword and the historical note), joined with `\n\n---\n\n`, with each
part's trailing rule stripped first so the separators do not double:

```bash
python3 assemble.py          # rewrites manuscript.md
python3 build_pdf.py         # typesets the PDF (two passes, for the contents)
```
cd project
node ../../bin/story.js validate
node ../../bin/story.js build --format epub
node ../../bin/story.js build --format docx
cp dist/the-birch-and-the-bell.epub dist/the-birch-and-the-bell.docx ..
```

`build_pdf.py` needs `fpdf2`, plus italic and bold-italic faces of DejaVu Serif,
which matplotlib ships:

```bash
pip3 install --target /tmp/pylibs fpdf2 matplotlib
PYTHONPATH=/tmp/pylibs python3 build_pdf.py
```

`chapters/*.md` are the source of truth for prose; `project/chapters/*.md` are
regenerated from them by `sync.py`, which preserves each chapter's frontmatter.

Note: the `story validate` word-count warning is expected — the brief set a flexible target of about 40,000 words and the manuscript runs to about 52,812, which is recorded as an exemption in `project/continuity/exemptions.md`.
