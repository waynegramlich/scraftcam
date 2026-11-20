# 5.9 Adding a New Tool

(Draft by Claude, 2026-11-15, from the user's discussion at the end of
`T.cm~6.3`; the user's to revise.)

Catalogs (`T.cm~6.3`) are of no use until an end user can model a
tool and hook it in.  Claude may model the tools for the user, but
hooking one in must be easy.  The end user also needs to model their
assemblies and the parts in them.

## Why It Is Hard Today

A kind's facts are spread over the code: its schema in `shops.KINDS`,
its directory (`SHOP_DIRECTORIES`), the reader, `shop_registries`
(`use_shop()`), the tree's label, its sketch (`tool_models.py`,
`Tool_Models.md`), and the JSON schemas and `Shops.md` generated from
`KINDS`.  Adding the Shars Z setter (`tooling/setters.py`,
`z_setter(imperial)`) to the shop would take code in four or more of
those places.

## Ideas

1. **One place per kind.**  A tool's model declares its kind beside
   its build function: its name, its parameters with their units
   (`imperial`, `diameter: length`), its label, its sketch.  The
   schema, the reader, the registry, the GUI's fields, the JSON schema
   and `Shops.md` all come from that declaration, so adding a tool is
   one model file.
2. **Two ways to model a tool.**
   * A parametric model in Python (`z_setter()`, the cutters, the
     grid plate): Claude writes these; one file per tool, hooked in by
     idea 1.
   * A file from elsewhere, with no Python: a `.step` drawn by the
     user in SolidCraft, or a vendor's (McMaster-Carr offers `.step`
     files).  A generic kind (e.g. `step_tooling`) names the file and
     the few facts scraftcam needs (a reference height, a keep-out
     box).  `model_cache.py` already puts STEP files into a design.
3. **Assemblies and parts.**  Not yet settled what is meant: (a) the
   design being made, built from several parts (today's Python
   designs under `--design`), or (b) tooling the user puts together
   from parts (a vise with jaws and parallels, a fixture plate with
   clamps).  For (b), the same mechanism: an assembly kind listing
   parts, each a parametric model or a STEP file, each placed.
4. **Catalogs afterwards.**  `T.cm~6.3`'s S3 ([New Tool from Row])
   needs a kind to fill in; with idea 1, any kind can be offered, so it
   stays generic.

## The Steps to Add a New Tool (the user's view)

0. Its model (code): done for the Z setter.
1. A kind for it in the shop (code today; idea 1 would remove it).
2. Start the GUI.  3. Make the catalog ([New Catalog]).  4. Set its
   `index_pages`.  5. [Open Pages].  6. Find the page (Goto; no
   searchable index yet).  7. Mark the product.
8. Make the tool from the row (S3, not built).
9. Finish its fields in its panel.
10. Its tree label and sketch (code today).
11. See it in SolidCraft from its panel (not built).
12. Commit.

## First Case

The Shars magnetic Z-axis zero setter, 303-3104 (2 in), catalog page
414: modeled (`scraftcam/tooling/setters.py`), approved by the user in
SolidCraft.
