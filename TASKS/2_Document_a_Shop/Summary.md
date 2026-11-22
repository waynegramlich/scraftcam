# Summary of `T.ds` Document a Shop

A shop is described in TOML files with a unit on every number,
loaded, checked (every problem named with its file and entry) and
asked questions; `examples/shop/` replaced `machine.toml`, and the
demo runs from it.  Done in `T.msaf~2.1` (materials, speeds and
feeds), `T.si~2.2` (shop information), `T.m~2.3` (mounting) and
`T.tm~2.5` (tool models); the schema became `shops.KINDS`, edited in
the GUI (`T.g~6`).  Closed 2026-11-22 (#407), the rest moved: stock
to `T.sm2~5.5`; work holding and tool models to `T.tfo~6.5`; the
tool table per machine to `T.g~6` #164; other machine kinds (router,
lathe, laser, 3D printer) to `T.g~6` #137; multi-setup parts to `T.parj~5`.

Tags: `T.sm2~5.5`, `T.tfo~6.5`, `T.g~6`, `T.parj~5`.
