# LLM Agent Context Log

## 2026-11-15: Z-axis setter modeled (from `T.cm~5.1.10`)

The Shars magnetic Z-axis zero setter (303-3104, catalog page 414)
is `scraftcam/tooling/setters.py` `z_setter(imperial)`, from the
user's description; the user approved it in SolidCraft.  No shop
kind, keep-out, sketch or tests yet (see `T.cm~5.1.10`).

## 2026-11-15: How new tools get in: `T.ant~5.9`

Hooking a tool in (one place per kind, STEP files as an alternative)
is now `T.ant~5.9`; this task's tools wait on it.

## 2026-11-15: Parametric model library, design settled

The user's direction: 5.3 is the excuse to build the library that
lets people (and agents) make parametric parts and assemblies in
Python.  It is documented here for now, later in public `.md` files
(`Models.md`).  It is also `T.ant~5.9`'s idea 1 (one place per kind).
Nothing coded yet.

### The design

* **Plain dataclasses.**  A model is a `@dataclass(slots=True)`,
  editable (not frozen); its fields may be other models, to any
  depth (an assembly is a model whose fields are models).  The
  rules are documented, not guarded: whoever handwrites a class may
  get it wrong on their own.
* **Parameters and results.**  `init=True` fields are parameters;
  `init=False` fields are results that `update()` computes (sizes,
  bounding box, mounting points).  `__post_init__()` calls
  `update()`, so built or edited, there is one code path.
* **Passes until stable.**  `update()` goes top down then bottom up:
  a parent sets each child's parameters, calls its `update()`, reads
  its results.  A child never reads its parent.  Dimensions
  propagate by repeated passes until every result moves less than
  1e-9; usually one or a few passes, and a bound on the passes
  reports a model that never settles (it happens).  The solid is
  built afterwards, in a separate `build()`.
* **Local coordinates, placement.**  Every model builds in its own
  documented coordinates; the parent places a child with a
  `Placement(translation, rotation)` field it owns, composed down
  the tree.  `Rotation` is a quaternion inside, given as axis and
  angle (the user's usual way) or a "point this axis that way"; the
  end user never sees a quaternion.  It is converted to what
  SolidCraft takes only at the edge (not yet looked up: its move or
  occurrence command).
* **Native units: `Length`.**  A length keeps the number exactly as
  written (`Fraction`) and its unit (`in`, `ft`, `mm`, `m`):
  `3-7/8 in`, `20 mm`, so values never read `3.1999999`.  Units are
  converted only where two meet; a result takes the parent's unit
  (cause of past trouble unclear); values round on display.
* **Field metadata.**  Each parameter's `field(metadata=...)` has
  its unit kind (`length`, `angle`, `count`), label and one-line
  help.  The edges (the shop reader, the GUI fields) convert text
  and check values through it; `update()` checks the fields
  together (a cross-field check per field would refuse the
  in-between states of a series of edits).  From the metadata come
  the shop schema and reader (`shops.KINDS`), the GUI fields, the
  JSON schema, `Shops.md` and each model's documentation table.
  The parameters (and the code's source) make the model cache key.
* **Names.**  No `SC` prefix anywhere (the `tooling/` classes have
  none already); a clash is solved with `import ... as ...`.

### First sketch

```python
@dataclass(slots=True)
class Vise(Model):
    # Constructor arguments:
    jaw_width: Length = field(metadata={"unit": "length", ...})
    opening: Length = field(metadata={"unit": "length", ...})
    jaw: JawPlate = field(default_factory=JawPlate)

    # Results (alphabetized):
    jaw_placement: Placement = field(init=False, default=...)

    def update(self) -> None:
        self.jaw.width = self.jaw_width  # The parent sets the child.
        self.jaw.update()
        self.jaw_placement = Placement.at(0.0, self.opening, 0.0)
```

A trial `JawPlate` with `Length`, from the Kurt plate's numbers, is
in the session's scratchpad only (`jaw_dataclass.py`, `units.py`);
it is a starting point, not kept.

### Plan

1. `scraftcam/model.py`: `Length`, `Rotation`, `Placement`, the
   `Model` base, the pass driver, with tests; shown to the user
   before any existing class is touched.
2. The drill vise, first model (an assembly; will uncover issues).
   Waiting on the user's measurements (the Shars catalog, page 318,
   shows no dimensions).
3. Convert `z_setter(imperial)` (`tooling/setters.py`), then the
   existing models one at a time, each made editable with its
   tests: `Parallel`, `JawPlate`, `MachineVise`, `GridPlate`, the
   cutters (`tooling/tools.py`, `tooling/cutter_models.py`,
   `tooling/mount.py`'s layers; 12+ are `frozen=True` today).
4. Documentation grows with each model: `Models.md` (writing a
   model) and a page per model (`T.dtm~2.5.2`).

### Rejected

* `attrs`: converters and validators on every set are a fix for a
  problem we will not have; plain dataclasses, no dependency.
* Our own `__setattr__` guard or `assert not self.frozen` setters:
  icky; the user would rather not make the mistakes.
* Lengths stored in millimeters: conversions leave `3.1999999`.
* One pass with no iteration as a rule: dimensions need a few
  passes.

5.3 - Create More Tools: parametric model library designed: plain editable dataclasses (attrs tried and rejected), update() passes until stable then build(), Placement with quaternion Rotation from axis/angle, native-unit Length (Fraction + unit), field metadata for units, labels and help driving schema, GUI and docs, no SC prefixes; next scraftcam/model.py, then the drill vise.


## 2026-11-16: SolidCraft parameters experiment (`T.cmt~5.3`)

The user asked whether SolidCraft's parameters could carry our
models (option 5.b: `build()` writes SolidCraft parameters and
expressions, so a change in its Parameters panel rebuilds).  Script:
the session scratchpad's `param_block.py`, headless
(`connect("headless")`, needs `PYTHONPATH=.`).  Chunk 1 findings:
* `parameters.add(name=, expression="2 in")` works; values come back
  in mm.  `solid.extrude(distance="height")` makes a feature
  parameter `d1` that `uses` `height` (`parameters.list` shows the
  graph: `used_by`, `uses`).
* `parameters.change(changes={...})` rebuilt in 3 ms (one block),
  reporting `recomputed` and `restored`.
* Trap: `"3-7/8 in"` is read as 3 (design unit, mm) minus 7/8 in =
  -19.225 mm, and the extrude flipped down without complaint.  Our
  `Length` text must be sent as `"(3 + 7/8) in"` (or in mm).
* A bare number is in the design's unit (mm by default).

Chunk 2 findings:
* `sketch.dimension(entities=["l3"], type="length", value="width")`
  ties a sketch side to a parameter (feature parameter `d1`, `uses`
  `width`); two such dimensions left the rectangle at `dof` 0.
* One `changes={...}` call set three parameters, `height` as the
  expression `"width / 4"`, and `"(3 + 7/8) in"` (98.425 mm), all
  right; `recomputed: 2` (sketch and extrude), 3 ms.
* An unknown name (`"nosuch * 2"`) is refused with `SolidCraftError`
  and nothing changes (all or nothing).
* A negative height is taken silently (the extrude flips).  A
  negative width is taken too, but then the sketch fails, the
  extrude fails and the body disappears; the reply's `errors` lists
  both.  So SolidCraft checks names, not values: our `update()`
  checks must come first.

Chunk 3 findings (a window: the AppImage
`../solidcraft/solidcraft-linux-x86_64.AppImage --control 8085`; no
`solidcraft` on the `PATH`, no command or `wmctrl` to raise it;
scratchpad `param_watch.py PORT`):
* Built in the window, then three changes 3 s apart (`height`; then
  `width` and `depth = width / 2` together; then back): each 2-5 ms,
  sizes right.  `favorite=True` puts a parameter among the panel's
  favorites.
* A cycle (`width = depth * 2`, `depth = width / 2`) is refused with
  `SolidCraftError` ("circular reference: width -> depth -> width")
  and nothing changes.  So SolidCraft's expressions are one way
  (a graph with no loops); our "passes until stable" cannot be
  expressed there, only its settled results.

## 2026-11-16: Live parameters, decisions (#15-#24)

* #15, #22: one way only, our Python to SolidCraft.  `update()`
  settles, the differences go out in one `parameters.change(changes=)`
  as plain values, never expressions (so no loops).  Users are told
  not to touch SolidCraft's Parameters panel.
* #19: a field that changes the shape (a hole count) is marked in its
  metadata and makes a new `build()`; others are parameter changes.
  "We catch the change, do the pre-work, and let SolidCraft do the
  rest."
* #20: the cache is updated eventually, never making the user wait;
  a recompute status bar estimates times from earlier ones.
* #21: users see only our names and terms, never SolidCraft's.
* #24: the link goes in step 1 (`model.py`); `JawPlate` is its first
  user.
* Still to discuss: #16/#18/#23 (`Model` plus a separate SolidCraft
  link, `build()` naming parameters).

#17 naming test (scratchpad `param_names.py`): letters, digits and
`_` (the message says starting with a letter, yet `_hidden` was
taken); no `.`, `-`, space or `[`; at most 64 characters; case
matters (`Width` is not `width`); unit names (`in`, `mm`), constants
(`pi`) and functions (`sin`) refused; `d1` is taken although
SolidCraft names its own feature parameters `d1`, `d2`, ...

## 2026-11-16: #17, #25-#29 answered

* #17, #26: a dotted path `vise.jaw.width` is the SolidCraft name
  `vise__jaw__width`; names never start or end with `_`.
* #25: the user prefers subclassing (Pythonic): a base class that
  talks to solid modelers (SolidCraft first; FreeCAD, SolidWorks
  later).  Still open to other proposals.
* #27: agreed (live model being edited, others from the cache,
  rebuilt in the background with a status bar); explaining it to
  users will be a chore.
* #28: agreed: send when a field is finished, never per keystroke.
* #29: deeper: find SolidCraft's window and session limits first.

## 2026-11-16: #30 SolidCraft windows and sessions

From SolidCraft's `README.md` and `docs/mcp.md` (GitHub), our
bindings, and a test (scratchpad `two_windows.py`):
* One design per process: `doc.open` and `file.new` replace the open
  design; no tabs, no design switching found; our bindings have no
  `app.*` or window commands (no raise, no title).
* Several processes at once work, each with its own `--control PORT`
  ("a second app: name it"): 8085 and 8086 ran together, each with
  its own design and parameters (the user's `width = 4 in` in 8085
  untouched).  About 240 MB each (the AppImage launcher 13 MB more).
* The default control port is 27878 (or the next free one); the app
  writes `control/current.port` beside its token.

## 2026-11-16: #35-#39 answered; live model in an assembly

* #35: off-screen (headless) SolidCrafts as many as memory and CPU
  allow; only one visible SolidCraft for now (several visible ones
  ask for trouble).
* #31 (user's #36): the base class is `Model3D` (3D modelers only),
  not the too generic `Model`; other names welcome.
* #32 (user's #37): SolidCraft only; FreeCAD's Python interface may
  never be fixed (CadQuery is nearer).
* #33 (user's #38): agreed.
* #36 (user's #39) tested (scratchpad `live_in_assembly.py`, a
  `HeadlessTransport(allow_paths=[...])`, as headless SolidCraft
  writes only in the project, its temporary folder and given paths):
  a STEP file inserted (component `cached_block`, occurrence
  `cached_block:1`) beside `component.create(name="jaw")` with a
  parameter-driven extrude; `occurrence.move(occurrence="jaw:1",
  translate=[50, 0, 0])` placed it (transform 4x4, translation in
  the bottom row); then `parameters.change` grew the jaw where it
  was placed, the STEP part untouched.  Parameters are one list for
  the whole design, not per component, so the `jaw__` path prefix is
  needed.  Occurrence names are `NAME:N`.

## 2026-11-16: #37-#44 answered; where things stand

Answers (the user's numbers ran one ahead of Claude's; Claude's are
used here):
* #40: full path parameter names (`vise__jaw__width`): unambiguous.
* #37: the base class is `SolidModel` (generic and accurate).
* #38: visible windows: simulation windows are separate, maybe one
  per active machine.  Aim for one visible window for a design;
  more are allowed, but only once the user turns that on.
* #39: SolidCraft only for now; `build()` calls `PyBind` directly.
  Every modeler will need an MCP-like interface soon, so another
  one may come later.
* #41: off-screen SolidCrafts fine, but the processor load must be
  limited, on Linux and on Windows: Claude's proposal below.

### #41 proposal: limiting off-screen load (not yet shown to the user)

SolidCraft's kernel runs one thread per core (`crates/kernel/src/
par.rs`, Rust's `available_parallelism`); `solidcraft-cli mcp` has no
thread option.  On Linux `available_parallelism` follows the CPU
affinity (and a cgroup quota), so limiting the affinity limits both
the cores and the thread count.
1. A pool runs off-screen SolidCrafts one at a time by default (a
   setting raises it); cache builds wait in a queue, the status bar
   (#27) shows the queue.
2. Linux (and WSL): start each as `nice -n 10 taskset -c CPUS
   solidcraft-cli mcp --headless ...` (coreutils and util-linux, on
   every Linux; no `preexec_fn`, unsafe in a threaded Qt program).
   `CPUS` defaults to half the cores (4 of 8 here), leaving the rest
   to the GUI, the visible SolidCraft and LinuxCNC.
3. Windows: `subprocess.Popen(...,
   creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)` (standard
   library), and the affinity set by `ctypes`
   `SetProcessAffinityMask` right after the start (it covers every
   thread of the process).  Not checked: whether Rust's
   `available_parallelism` follows that mask on Windows; if not, the
   threads are many but confined to the given cores.
4. No new background build starts while a machine is running a
   program (simulated or real); one already running finishes.
   LinuxCNC's real time must never compete with a cache build.
5. Settings (number at once, cores) live in `~/.scraftcam/`.

### Where things stand

Design settled for the live link: `SolidModel` (a dataclass base
class) with `update()` settling values, `build()` naming SolidCraft
parameters by full path (`a__b__c`), and a small helper holding what
was last sent; edits go out once a GUI field is finished, as one
`parameters.change(changes=...)` of plain values; a shape-changing
field (metadata) makes a new `build()`; one way only.  Not yet
discussed with the user: the #16 walk-through with a real `JawPlate`
(what `SolidModel` and the helper each do), and the #41 proposal.
Next: those two, then `scraftcam/model.py` (`Length`, `Rotation`,
`Placement`, `SolidModel`, the pass driver, the link), with
`JawPlate` its first user.  Scratchpad scripts (gone after the
session; the findings above are enough to redo them):
`param_block.py`, `param_watch.py`, `param_names.py`,
`two_windows.py`, `live_in_assembly.py`.

## 2026-11-16: #16, #41, #45-#47 answered

* #16: the split agreed: `SolidModel` holds fields and metadata,
  settles by passes, and `build()` makes the features and the named
  parameters; a helper per live SolidCraft holds the connection and
  the last values sent, and chooses a parameter change or a new
  `build()` (shape-changing fields, by metadata).
* #41.1-5: agreed.  #41.4 (no builds while a machine runs) matters
  little: our LinuxCNC is user space, not real time.
* #45: rotations are done with quaternions only; a 4x4 matrix is
  made from one at the very end, for SolidCraft.  Go ahead with the
  experiment.
* #46: agreed, step by step: `Length`, `Rotation`, `Placement` first;
  then `SolidModel`, the pass driver and the helper.
* #47: no drill vise for now.  `JawPlate` first, then the Kurt vise.

## 2026-11-16: #45 experiment: `occurrence.move(matrix=...)`

Scratchpad `rot_test.py` (headless; a 10 x 20 x 5 mm box at the
origin, moved by 90 degrees about Z then +100 mm in X):
* A design's first occurrence is grounded and refuses to move:
  `occurrence.ground(occurrence=, grounded=False)` first.
* `matrix` is row-major, column vectors: `[[R00, R01, R02, tx],
  [R10, ...], [R20, ...]]` (12 numbers; or 16), so p' = R p + t.
  The box went to x 80..100, y 0..10: as expected.
* The `transform` it returns (and `occurrence.properties` has none)
  is the transpose: row vectors, the translation in the bottom row.
* A move is relative: it composes with the current placement (a
  second identical move gave 180 degrees, t = (100, 100, 0)).  No
  command sets an absolute placement (none in `occurrence.*` or
  `component.*`).
* A matrix off rigid by 1e-6 is refused ("not rigid ... above the
  tolerance 1e-9"); `tolerance` raises it to at most 1e-3.
* So the helper keeps each occurrence's last sent `Placement`
  (quaternion and translation) and sends the delta: q_d = q_new
  q_old^-1, t_d = t_new - R(q_d) t_old, made into a matrix only at
  the call.  A unit quaternion gives |R^T R - I| near 1e-16, far
  inside the tolerance.  The returned `transform` can be compared
  with ours to catch drift.

## 2026-11-16: #45-#52 answered; `model.py` chunk 1

* #45/#48: errors pile up when many 4x4 matrices are multiplied;
  SolidCraft does exactly that with relative moves, so the helper
  compares its returned `transform` with ours and sends a
  correction past 1e-8 (1e-7 might be visible; 1e-9 is not).
* #49: degrees; radians are converted with 9 decimals (the user:
  at least 6).
* #50 -> #53 (on hold): preferred units.  Until then a composed
  `Placement`'s translation is in mm.
* #51: the new `JawPlate` takes the Kurt plate's numbers; the old
  class stays until the user has seen it.
* Chunk 1 done: `scraftcam/model.py` (`parse_number()`,
  `number_text()`, `Length`, `Angle`, `Rotation`, `Placement` with
  `compose()`, `inverse()`, `delta()`, `matrix()`) and
  `tests/test_model.py` (12 tests, pass; all checkers clean).
  Next: `SolidModel`, the pass driver, the helper.

## 2026-11-16: #53-#58 answered; `model.py` chunk 2

* #53: preferred units per model: whoever designs a model sets its
  unit (`SolidModel.UNIT`); its results use it.
* #54: `Length(3, "in")`, `Angle(90)` take plain ints.
* #55: `meta(unit, label, help_text, shape=False)`; `unit` one of
  `UNIT_KINDS` (`length`, `angle`, `count`, `text`, `flag`).
* #56: a wall clock limit, not a pass count: `settle(seconds=5.0)`
  raises `NotSettledError` naming the results still moving.
  A `nan` (from a result run off to `inf`) counts as moving.
* #57: `SolidCraftLink`; more modelers (each with an MCP-like
  interface) later, not now.
* #58: the user is left out of `JawPlate`'s parameters: Claude
  converts, and reports how long the changes took.
* Chunk 2 done (about 2 minutes by the clock): `SolidModel`
  (`settle()`, `results()`, `parameters()` with dotted paths,
  `parameter_fields()`), `meta()`, `NotSettledError`; 16 tests pass,
  checkers clean.  Next: `SolidCraftLink`, then `JawPlate`.

## 2026-11-16: #59-#63; `JawPlate` chunk 3

* #59 expanded for the user (prefix names per model in a design),
  not yet answered.  #60: agreed (users never see it).  #61:
  headless in development; a window only when the user wants to
  see.  #62: internal, skipped.
* Chunk 3 (about 3 minutes by the clock, 18:43-18:47):
  `scraftcam/tooling/jaw_plate.py` `JawPlate(SolidModel)`, unit
  inches, the Kurt numbers as defaults (old `tools.JawPlate` kept);
  `update()` has the old checks plus results `half_length`,
  `half_spacing`, `volume`; `build(solidcraft, name)` adds every
  `Length` parameter and result as `NAME__PATH` and dimensions the
  sketches by them.  `tests/test_jaw_plate.py` (4 tests, 0.7 s, the
  SolidCraft one skipped without `solidcraft-cli`): built headless,
  then `jaw__width` and `jaw__counterbore_depth` changed in one call;
  volume within 1e-4 and the box right both times.
* SolidCraft sketch findings: `sketch.dimension(entities=["origin",
  "c1"], type="vertical")` conflicts with a horizontal one ("origin"
  with a circle is not what it seems); `["origin", "c1.center"]`
  works for both (dof 0).  `x`/`y` are not dimension entities.
  `sketch.create(plane="YZ", offset="jaw__half_length")` takes a
  parameter, so the face's sketch follows the thickness.  Volume
  differs from ours by about 1e-5 relative.

## 2026-11-16: Where things stand (before `git commit`)

* #59: decided: a model added to a design is always given a number,
  `NAME_NNN` (e.g. `jaw_plate_001__width`); the names are hardly
  seen by users.
* Done: `scraftcam/model.py` (`Length`, `Angle`, `Rotation`,
  `Placement`, `SolidModel`, `meta()`, `settle()` with a wall clock
  limit), `scraftcam/tooling/jaw_plate.py` (`JawPlate`, live
  parameters), `tests/test_model.py` (16), `tests/test_jaw_plate.py`
  (4); all pass, checkers clean.
* Next: #64 the user sees the plate in a SolidCraft window; then #65
  `SolidCraftLink` (remembers what was sent; sends changed values in
  one `parameters.change`, rebuilds on a `shape` field; places by
  quaternion deltas; drift check past 1e-8, #48; `_NNN` names, #59);
  then #66 the Kurt vise on `SolidModel`, retiring `tools.JawPlate`.

## 2026-11-16: Where things stand (before `/clear`)

* #64: the plate was built in a window (`--control 8085`, the
  AppImage `../solidcraft/solidcraft-linux-x86_64.AppImage`); the
  first live change tried, width 4 in, was rightly refused by
  `update()` (20 mm counterbores on 3-7/8 in centers do not fit), and
  the user closed the window before the 5 in retry.  To show it
  again: start the window, raise it (KDE on X11: a KWin script via
  `qdbus org.kde.KWin /Scripting ...loadScript`, setting
  `workspace.activeClient` to the client whose caption has
  "SolidCraft"), `sc.file.new()`, `JawPlate().build(sc,
  "jaw_plate_001")`, then every 5 s one `parameters.change` (width
  5 in; counterbore depth 5/8 in), timing each.  No `view` fit
  command exists.  Offer it; the user decides.
* Next: #65 `SolidCraftLink` (see the plan above), with `_NNN`
  names (#59); then #66 the Kurt vise.  Work goes in ~3 minute
  chunks, each ending with a numbered summary and a top 5.
* `git`: `1eff0d4` (model.py, jaw_plate.py, tests), pushed.

## 2026-11-16: #64 shown; #65 `SolidCraftLink` chunk 1

* #64 done: the user saw the plate in a window (`--control 8085`):
  "a vice jaw with 2 countersunk holes".  Build 730 ms; width 5 in
  140 ms; counterbore depth 5/8 in 93 ms (headless: 2-5 ms; the
  window's redraw, or a covered window, `solidcraft-to-front`).
  Raising on this KDE: `loadScript FILE NAME`, then
  `org.kde.kwin.Scripting.start` (no `/Scripting/ScriptN ... run`).
* #66: the user will say what they see once the Kurt vise is shown.
* #65 chunk 1: `scraftcam/solidcraft_link.py` `SolidCraftLink`
  (`add(model, base, placement)` -> `BASE_NNN`, each model in its own
  component, ungrounded; `send(name)` -> `unchanged`/`changed`/
  `rebuilt`; `place()` by quaternion delta, drift past `DRIFT` 1e-8
  corrected by a matrix; `remove()`), `SolidModel.build()` on the
  base class.  Found: `component.delete` takes the component's
  features; its parameters are then deleted one by one by prefix
  (24 ms for 10); a rebuilt occurrence is at identity and ungrounded
  (only the design's first is grounded), so its placement is sent
  whole again.  `tests/test_solidcraft_link.py` (4 tests, 0.2 s,
  headless); checkers clean.
* Not yet: models nested in models placed by their parents (children
  composed down the tree); `Angle` parameters (only `Length`s are
  sent); a GUI field calling `send()`.

## 2026-11-16: #69-#73 answered; where things stand (before `/clear`)

* #69: try one SolidCraft sub-component per child model.
* #70: no window demo of the link needed.
* #71: a tool, like anything, is an assembly: parts (a `SolidModel`,
  or a `.step` equivalent) in sub-assemblies up to the final
  assembly.  Each model is a component; a part is a leaf.
* GUI direction (the user, thinking aloud, not settled): organize a
  model's panel by its layers and their SVG diagrams, a global layer
  always visible plus a sub-panel per layer; the user tweaks tools
  and saves them into their shop.  Tools are the dry run; the end
  products people design come after.  Claude's proposal: layers are
  child models, the global layer the parent's own fields.
* #72 -> new `T.sdfm~2.5.2.1` (SVG diagrams from models; SolidCraft
  has `sketch.insert_svg` but no SVG export in our bindings).
  #73 -> new `T.oacv~5.1.9.1` (original and changed values,
  highlighted).  Both Open with draft `Details.md`; the user decides
  in the morning where they belong (Claude suggested #72 under
  `T.dtm~2.5.2`, which is where it was put).
* Next (after the user's morning review): #69, child models as
  sub-components placed by the parent's `update()`, composed by
  `SolidCraftLink`; then the Kurt vise as an assembly with its jaw
  plates as parts.

## 2026-11-17: `Parallel` on `SolidModel` (from `T.sdfm~2.5.2.1`)

`scraftcam/tooling/parallel.py` `Parallel(SolidModel)` (inches, any
number of holes), its side a `scraftcam/outline.py` `Profile`; the
old `tools.Parallel` stays until the GUI is debugged (the user).
`SolidModel.solidcraft_values()` is the link's new hook (`JawPlate`
unchanged).  Next here, still: #69 child models as sub-components,
then the Kurt vise.  See `T.sdfm~2.5.2.1`.
