# LLM Agent Context Log

Trimmed 2026-11-15: only what is still in force, and where things
stand; the full history is in `hg` and `git`.  Issue numbers are
sticky: #14-#22 (2026-11-07) and #23-#68 (2026-11-15); a few later
lists were numbered afresh in the conversation and are not cited.

## `catxtract` Today

* `scraftcam/catalog/catxtract.py` (Qt, `App(QWidget)`, `App(pdf,
  out_dir, parent=None)`) and `pdf.py` (the only module touching the
  PDF libraries: `Rect`, `Page`, `Document`; `pdfplumber` for text,
  images and tables, `pypdfium2` for drawing; fetched on first
  `Document()` by `packages.require()` into `~/.scraftcam/packages/`).
  Run alone: `python3 -m scraftcam.catalog.catxtract PDF OUTDIR`.
* Output, per page: `page_NNN/page_NNN.md` (`# Page NNN`, a
  Previous/Next links line to the nearest saved pages, then the
  regions), `page_NNN.json` (`{"regions": [...], "ignored": [...]}`),
  `page_NNN_K.png`.  A page with no directory is not done.
* Mouse only: page row (Prev. New, Prev., Next, Next New, Goto, Index
  Update, Quit), region row, mode row (Title, Text, Image, Table,
  Index).  Drag adds, click selects, right click ignores.  Leaving a
  page saves it if it has, or had, regions, untouched suggestions
  included.  Index mode writes `Item`/`Pages` tables (`index_rows()`,
  `page_link()`); [Index Update] rewrites every saved index page.
* A page with nothing saved starts with regions carried over from the
  nearest earlier saved page (`suggest()`); the user usually presses
  Clear.  #46 (agreed): carry over only on request.  Not done.
* Tests: `tests/test_catalog_pdf.py` (a hand-written one page PDF;
  `write_pdf()`, `READY`), offscreen `AppTest`.
* `SharsMD/` (256 pages, the user's earlier whole-catalog work) and
  `2026_Shars_Catalog.pdf` stay at the top of the tree, ignored by
  `git` and `hg` (#53).  Never read catalog pages or their images.

## Decisions in Force (2026-11-15)

* Records: only products actually purchased go under version control
  (#23, #48); the PDF plus a page number gives the rest.  People mark
  only the images, tables and text of the product bought; the index
  is the one exception (#47 round).  A product record is the shop
  item itself: tool kinds already have `manufacturer`,
  `manufacturer_pn`, `vendor`, `vendor_pn`, `cost`, `acquired`; to
  add: `catalog`, `catalog_page` (#49).  One record per product (#30).
* No images or other source material under version control (#25).
* Catalogs live in the shop: `catalogs/VENDOR/EDITION/catalog.toml`
  (kind `catalog`: `vendor`, `edition`, `pdf`, `pages` required;
  `index_pages` (form `page_ranges`: `[[451, 455], 460]`, shown
  `451-455, 460`), `page_offset` (PDF page less printed page),
  `url`) (#43, #50, #63, #66).  Beside it, `pages/`: the PDF (copied
  or a symbolic link) and `catxtract`'s files, never under version
  control (#58).
* [New Catalog]: in the action row for the shop's root and
  `catalogs/`; vendor, edition, PDF ([Choose...]), "Link to it" or
  "Copy it"; then offers the ignore lines (git
  `**/catalogs/*/*/pages/`, hg `re:(^|/)catalogs/[^/]+/[^/]+/pages/`,
  both checked in real repositories) (#51, #61).
* [Open Pages]: beside [Edit TOML File] in a catalog's panel; opens
  `catxtract` in its own window, never in a panel (#68), at the first
  index page plus `page_offset`; one per catalog; closed (and saved)
  when the GUI's last window closes.
* The catalog's panel opening on a searchable index (#64): not built.
* Web sites (McMaster-Carr): on hold; never break a vendor's
  anti-scraping rules.  A part number is a McMaster-Carr product's
  key; its 2D PDF drawing (SOLIDWORKS, Letter, a text layer with the
  part number, title and bare dimensions) and `.step` may be
  downloaded by hand, one product at a time (#37, #54-#57).
* #67: some day, delete page markup that no shop item cites (needs
  `catalog_page`); index pages are kept.

## Where Things Are

* `shops.py`: `KINDS["catalog"]`, `SHOP_DIRECTORIES` (`catalogs`),
  `CATALOG`, `CATALOG_PAGES`, `ITEM_PATTERNS`, the shop's `catalogs`
  list; form `page_ranges` (`_page_ranges_problem()`,
  `page_ranges_text()`, `page_ranges_value()`); one-value checks in
  `VALUE_PROBLEMS`.  `shop_schema.SIMPLE["page_ranges"]`.
* `gui/app.py`: `CATALOGS`, `IGNORE_LINES`, `IGNORE_FILES`,
  `ignores_needed()`, `add_ignores()`, `pdf_pages()`,
  `new_catalog_text()`, `App.new_catalog()`.
* `gui/window.py`: `new_catalog_row`, `NewCatalogDialog`,
  `offer_ignores()`, `open_pages(panel)`, `index_start()`,
  `CATALOG_WINDOWS`, `close_catalogs()`.  `gui/views.py`:
  `Panel.pages_button`, `open_pages`, `OPEN_PAGES`.  `gui/tree.py`:
  a catalog's `pages/` hidden; `EXPLANATIONS["catalogs"]`.
  `gui/machines.py`: `is_catalogs_directory()`.  `gui/fields.py`:
  `page_ranges` in `PLAIN`.
* `tooling/setters.py`: `ZSetter`, `z_setter(imperial)` (the Shars
  303-3104 Z setter, page 414), shown by `python3 -m
  scraftcam.tooling.setters 8081 [metric]`; approved by the user in
  SolidCraft.  Guessed: cylinder rise .25 in, ring width .1 in,
  pointer .04 x .02 in; metric 50 mm, scaled.
* Tests: `tests/test_gui_catalogs.py`; `TestCatalogs` in
  `test_shops`; `test_catalog_pages` in `test_gui_tree`.  Every test
  copying `examples/shop` leaves `catalogs` out.

## Tried and Dropped (do not bring back)

* Printing McMaster-Carr pages to PDF (clipped on paper and in the
  PDF, no part number); "Save Page As..."; `cups-pdf` (same layout).
  Repeated downloads got a `Forbidden`.
* Catalogs under `~/.scraftcam/` or in the HMI's tabs (#14-#18,
  replaced by the GUI and the shop directory); `catxtract` inside a
  panel; marking the whole catalog.
* `files/` as the unversioned directory's name (now `pages/`);
  `index_first`/`index_last` (now `index_pages`); [Open Pages] in the
  top line's action rows.
* The user's first catalog run in `examples/shop` (undone 2026-11-15:
  catalog, markup and ignore lines removed; layout cleaned).

## Where Things Stand (2026-11-15, suspended)

Suspended by the user: catalogs are of no use until an end user can
model a tool and hook it in easily, which is now `T.ant~5.9` (Adding
a New Tool).  Left here, for when it comes back:
1. S3: a marked row -> a shop item ([New Tool from Row]), generic over
   kinds once `T.ant~5.9` gives one place per kind; split merged
   columns ("Order No. Price" on page 414).
2. `catalog`, `catalog_page` fields on shop items.
3. #46 carry-over on request; #64 the index in the panel; #67.
4. The user has not yet redone the catalog run (the steps are in
   `T.ant~5.9`'s `Details.md`).
Tests run 2026-11-15: `test_shops`, `test_shop_schema`,
`test_gui_tree`, `test_gui_fields`, `test_gui_catalogs`,
`test_gui_window`, `test_gui_machines`, `test_gui_templates`,
`test_catalog_pdf`; all pass.  Not run: the whole suite.
