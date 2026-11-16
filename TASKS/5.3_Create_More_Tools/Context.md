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
