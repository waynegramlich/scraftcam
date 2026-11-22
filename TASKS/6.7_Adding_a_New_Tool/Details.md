# 6.7 Adding a New Tool

(Draft by Claude, 2026-11-15, from the user's discussion at the end of
`T.cm~6.3`; brought up to date 2026-11-22.)

Catalogs (`T.cm~6.3`) are of no use until an end user can model a
tool and hook it into the shop.  Making the model is `T.tfo~6.5`
(outline files); this task is the hooking in, which must be easy.

## Why It Is Hard Today

A kind's facts are spread over the code: its schema in `shops.KINDS`,
its directory (`SHOP_DIRECTORIES`), the reader, `shop_registries`
(`use_shop()`), the tree's label, its sketch (`tool_models.py`), and
the JSON schemas and `Shops.md` generated from `KINDS`.

## Ideas

1. **One place per kind**: the schema, reader, registry, GUI fields,
   JSON schema and `Shops.md` all come from one declaration beside
   the tool's outline file.
2. **Two ways to model a tool**: an outline file (`T.tfo~6.5`), or a
   `.step` from elsewhere (the user's, or a vendor's such as
   McMaster-Carr) under a generic kind naming the file and the few
   facts scraftcam needs (a reference height, a keep-out box).
3. **Assemblies**: tooling put together from parts (a vise with jaws
   and parallels, a fixture plate with clamps), each an outline solid
   or a STEP file, placed (`solid.SolidAssembly`).
4. **Catalogs afterwards**: `T.cm~6.3`'s [New Tool from Row] offers
   any kind, so it stays generic.

## The Steps to Add a New Tool (the user's view)

0. Its model (an outline file).  1. A kind for it in the shop.
2. Start the GUI.  3. Make the catalog ([New Catalog]).  4. Set its
   `index_pages`.  5. [Open Pages].  6. Find the page.  7. Mark the
   product.  8. Make the tool from the row (not built).
9. Finish its fields in its panel.  10. Its tree label and sketch.
11. See it in SolidCraft from its panel (not built).  12. Commit.

## First Case

The Shars magnetic Z-axis zero setter, 303-3104 (2 in), catalog page
414 (`scraftcam/tooling/setters.py`, approved by the user).
