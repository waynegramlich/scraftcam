# 6.11 Support Assemblies

(Draft by Claude, 2026-11-24, from the user's #660-#668 in
`T.toasl~6.8`; the user's to revise.)

Every tool is an assembly: a drill bit is one solid, while a vise,
the Z setter or a fly cutter is several.  An assembly's file says
what its parts are, where they sit, and where the tool must not go.

## Decided

* **Every tool is an assembly** (#667).  Some have one solid; many
  solids are a simple extrusion of a `RoundedPolygon`
  (`T.rps~6.6`), others a revolve.
* **One `.toml` per assembly** (#660): a list of polygon outlines,
  each as a single outline file is today (e.g. the drill's), and the
  position of each part.
* **One letters (dimension) table at the top** (#665): it is the
  template for the shop's tool entries (`T.toasl~6.8` #631, #656),
  and every part's outline and position can use its letters.
* **Seeing down only** (#660a, #671): an assembly reaches only files
  in or below its own directory, never up the directory chain;
  letters pass down, from the assembly to its parts.  A part's
  letter named like an assembly letter is an error (#673).
* **Moving parts** (#662), such as a vise's jaw opening or the Z
  setter's plunger, are letters set by the setup or job.
* **`.step` parts are inert blobs** (#663): a placement only, no
  letters.
* **Keep-out zones are the user's design** (#666), not the parts'
  solids: the user says what each zone is, e.g. a vise has a base
  zone, a fixed jaw zone and a moving jaw zone.  Zones are fast to
  compute with: each is a box or an extruded convex polygon, sized
  in the assembly's letters; a moving part's zone follows its letter
  (#669).  Every non-cutting tool has them (`T.kz~4`).
* **The cutter is a point** (#672, #675): when checking, the zones
  grow by the cutter's radius, so the cutter shrinks to a point; the
  holder and collet are not checked (the tool breaks long before
  they touch).  A zone grows into a bigger box or polygon, not exact
  rounded corners (#677).
* **Every tool file is an assembly** (#670): no plain outline file
  read as one part.  A `.step` is generated per tool and cached
  in the cache for now (#674; not the long-run answer), rebuilt only
  when a hash of its assembly file and letter values changes (#676).
* **In the GUI** (#665): an assembly panel, with its letters, its
  parts (each opened in the outline editor), their positions, its
  keep-out zones and the assembled solid (tabs, `T.gc~6.10` #586).

## First Cases

* The drill (one solid), then the Shars magnetic Z setter, 303-3104
  (`scraftcam/tooling/setters.py`), then the vise.

## Done When

* The drill, Z setter and vise are assembly files, drawn and edited
  in the GUI, with the vise's keep-out zones.
