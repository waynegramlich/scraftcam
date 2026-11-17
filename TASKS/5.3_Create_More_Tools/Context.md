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
