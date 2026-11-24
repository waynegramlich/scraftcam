# 6.8 Tools, Outlines and the Shop Layout

(Draft by Claude, 2026-11-24, from the user's #627-#633; takes in
`T.tkis~6.7`, Tool Kinds in the Shop.  The user's to revise.)

A tool's facts live in one place on disk, beside its kind's outline,
and the shop's directory tree is what the GUI's tree shows.

* **A directory per tool outline** (#653): `KIND/` holds the kind's
  outline file (`KIND.outline.toml`), its `.svg` and its page.  Most
  ship in the `scraftcam` package and are not edited; a shop's own
  may not reuse a shipped name (#655).  The shop's tools of a kind
  are listed in one `KIND.toml` (#656); catalogs stay in a catalog
  directory each (#654).
* **The outline is the template** (#631, #391): the kind's outline
  file's dimension (letters) table says which fields every tool of
  that kind has in its `.toml`; each tool gives only its values.
  The tool's panel shows one table: letter, default, this tool's
  value.
* **One place per kind** (from `T.tkis~6.7`): the schema, reader,
  registry, GUI fields, JSON schema and `Shops.md` all come from the
  kind's outline file and a short declaration beside it, not from
  facts spread over the code (`shops.KINDS`, `SHOP_DIRECTORIES`,
  `use_shop()`, the tree's labels).
* **Two ways to model a tool**: an outline file (`T.tfo~6.5`), or a
  `.step` from elsewhere (the user's, or a vendor's such as
  McMaster-Carr) under a generic kind naming the file and the few
  facts scraftcam needs.  Assemblies put parts together
  (`solid.SolidAssembly`).
* **The tree shows the files**, outline files included (#615).
* Catalogs (`T.c~6.3`) come afterwards: [New Tool from Row] offers
  any kind.

## First Case

The Shars magnetic Z-axis zero setter, 303-3104 (2 in), catalog page
414 (`scraftcam/tooling/setters.py`).

## Done When

* Adding a tool kind is an outline file plus a short declaration,
  and adding a tool is filling in its kind's table in the GUI.
* The example shop uses the layout, and the tree shows it.
