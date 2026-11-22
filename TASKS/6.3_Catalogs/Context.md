# LLM Agent Context Log

Squeezed 2026-11-19; the full history is in `hg` and `git`.  Status:
Suspended while `T.tfo~6.5` makes tools to add (catalogs are of no
use until an end user can model a tool and hook it in, `T.tkis~6.7`).
Its decisions guide new tools' shop fields.

## `catxtract`

* `scraftcam/catalog/catxtract.py` (Qt `App(pdf, out_dir,
  parent=None)`) and `pdf.py` (the only module touching
  `pdfplumber`/`pypdfium2`, fetched by `packages.require()`).  Alone:
  `python3 -m scraftcam.catalog.catxtract PDF OUTDIR`.
* Per page: `page_NNN/page_NNN.md`, `.json` (`regions`, `ignored`),
  `page_NNN_K.png`; no directory means not done.  Mouse only; drag
  adds, click selects, right click ignores; leaving a page saves it.
  Index mode writes `Item`/`Pages` tables; [Index Update].
* Tests: `test_catalog_pdf`.  `SharsMD/` and `2026_Shars_Catalog.pdf`
  stay at the top, ignored (#53); never read catalog pages or images.

## Decisions in Force

* Only purchased products go under version control (#23, #48); no
  images or source material (#25).  A product record is the shop
  item itself (`manufacturer`, `manufacturer_pn`, `vendor`,
  `vendor_pn`, `cost`, `acquired`; to add `catalog`, `catalog_page`,
  #49).  One record per product (#30).
* Catalogs: `catalogs/VENDOR/EDITION/catalog.toml` (kind `catalog`:
  `vendor`, `edition`, `pdf`, `pages`; `index_pages` as
  `page_ranges`, `page_offset`, `url`); beside it an unversioned
  `pages/` (the PDF or a link, `catxtract`'s files).
* [New Catalog] (root and `catalogs/` action rows) offers the ignore
  lines (git `**/catalogs/*/*/pages/`, hg
  `re:(^|/)catalogs/[^/]+/[^/]+/pages/`).  [Open Pages] in a
  catalog's panel opens `catxtract` in its own window at the first
  index page plus `page_offset`, one per catalog, closed with the
  GUI's last window.
* McMaster-Carr web pages on hold: never break a vendor's rules;
  2D PDFs and `.step` by hand, one product at a time.

## Where Things Are

`shops.py` (`KINDS["catalog"]`, `CATALOG`, `CATALOG_PAGES`,
`page_ranges` helpers), `shop_schema.SIMPLE["page_ranges"]`,
`gui/app.py` (`new_catalog()`, ignore helpers), `gui/window.py`
(`NewCatalogDialog`, `open_pages()`, `CATALOG_WINDOWS`), `gui/views.py`
(`Panel.pages_button`), `gui/tree.py` (`pages/` hidden).  Tests:
`test_gui_catalogs`, `TestCatalogs` in `test_shops`,
`test_catalog_pages` in `test_gui_tree`; tests copying `examples/shop`
leave `catalogs` out.

## Left for When It Comes Back

S3 a marked row -> a shop item ([New Tool from Row]), generic over
kinds; split merged columns ("Order No. Price", page 414);
`catalog`/`catalog_page` fields; #46 carry-over of regions only on
request; #64 a searchable index in the panel; #67 delete markup no
item cites.  The user has not redone the catalog run (steps in
`T.tkis~6.7`'s `Details.md`).

## Tried and Dropped

Printing McMaster-Carr pages to PDF, "Save Page As...", `cups-pdf`;
catalogs under `~/.scraftcam/` or in the HMI; `catxtract` in a panel;
marking the whole catalog; `files/` (now `pages/`);
`index_first`/`index_last` (now `index_pages`).
