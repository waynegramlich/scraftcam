# The `scraftcam` GUI

One GUI for the shop, the designs and the machines.  It is being
built a step at a time (`TASKS/5.1.9_...`); this file grows with it.
So far: the top line (step 1) and the tree (step 2).

## Starting It

From the repository's top directory:

```
python3 -m scraftcam.run [--shop=SHOP] [--design=DESIGN] [--mcp=PORT]
```

or, from anywhere (not on Windows), `scraftcam/run.py` with the same
arguments.

* `--shop`: the shop's `shop.toml`, or its directory.  With none, the
  first `shop.toml` in the current directory or one of its parents is
  used, as `git` finds its repository.
* `--design`: the design, a Python file or a package directory.
* `--mcp`: serve MCP on that port of 127.0.0.1 (see below); none by
  default.
* `--headless`: Qt draws offscreen, so no display is needed (tests).
* `--outline [FILE]`: edits an outline file in the first panel,
  saving every change (no file: a new outline, kept nowhere).
* `--tutorial FILE`: plays a recording (`NAME.steps.md`) in the first
  panel, with its narration panel; with `--headless`, checks every
  step and exits 1 on a mismatch.
* `--record [FILE]`: records what is done in that editor as steps,
  and what is said unless `--no-speech` (`outline_panel.py`).

`PySide6` (Qt) is fetched into `~/.scraftcam/packages/` the first time.

## The Window

From the top down:

* **The top line**, left to right:
  * [Stop All]: only while more than one machine runs; stops them all.
  * [Tree]: shows or hides the tree on the left.
  * The shop's name (its `name`, else its directory's) and the
    design's name; "(none)" when there is none.
  * The latest message; red for a problem.
  * [+ Panel]: adds a panel on the right.
  * [x] (narrow, to save room): closes the window.  A window that
    controls a running machine will not close ("Stop the shop mill
    first").
* **The action rows**: what can be done to the item selected:
  "No shop yet: [New Shop]", and [Edit] (below).
* **The tree** on the left, then **the panels**, side by side; drag
  the splitters between them.

The window starts small (720 x 480), so SolidCraft fits beside it.

## The Tree and the Panels

One tree, with two roots:

* The shop, "NAME (shop)": its directories, and each `.toml` file in
  them, shown by its `name` (else its file name).
* The design, "NAME (design)": the `.py` files and packages in its
  directory and below.  A file with a `main()` is "(design)", any
  other "(python)".  The files are read, never run.  At most 100 are
  shown; give a design a directory of its own.

Directories come first, then files, alphabetically.  A file that does
not read cleanly is red, "(error)", with the problem (e.g. "syntax
error", with its line) as its tooltip.  The tree follows changes made
outside the GUI (an editor, `git`) by itself.

Clicking an item shows it in the current panel, the one outlined;
clicking a panel makes it current, and [+ Panel] adds a new current
one.  A panel shows a `.toml` file's text (read only), a Python file's
or package's docstring, or the problem with a file that does not read
cleanly.

### [Edit]

For a Python file, or a file with a problem, [Edit] opens it in:

1. the environment variable `VISUAL`'s editor (a GUI editor, e.g.
   `VISUAL=kate`), else
2. the environment variable `EDITOR`'s, in a terminal window (a
   terminal editor, e.g. `EDITOR=nano`), else
3. the desktop's default editor, with a reminder (once a session)
   that `VISUAL` and `EDITOR` exist.

## A New Shop

With no shop, [New Shop] (which also opens by itself when the GUI
starts) asks:

* the directory (`shop/` under the current directory by default),
* the shop's name, with [Create] beside it (grey until there is a
  name; Enter presses it),
* its units: Imperial (in) or Metric (mm),
* which machines it has: computer controlled ones, then manual ones
  used for prep work (only the CNC mill can be driven so far).  More
  than one machine of a kind is entered later, with the shop's
  machines.

[Create] writes the directory's `shop.toml`; it never writes over an
existing one.  The shop is yours: keep it under version control.  When
it is not in a `git` or `hg` repository, the top line suggests one
(or says to install `git` or `hg`).

## MCP

With `--mcp PORT`, the GUI serves MCP (`../exposed/`) on that port,
so Claude (or a test) can drive it; each call runs on Qt's main
thread.  `scraftcam.exposed.client` starts one headless and calls it
from the shell:

```
python3 -m scraftcam.exposed.client start --gui [SHOP] --port 8765
python3 -m scraftcam.exposed.client call status --port 8765
python3 -m scraftcam.exposed.client stop --port 8765
```

The functions (`window_exposed.py`; a window is numbered from 0):

| Function | Arguments | Does |
| --- | --- | --- |
| `status` | none | What the windows show. |
| `top_button` | `label`, `window_number` | Presses a top line or action row button, as a person would; refused if it is hidden. |
| `new_shop` | `directory`, `name`, `units`, `machines` | Makes a shop, as [New Shop] would. |
| `tree` | `window_number` | The tree's labels, nested. |
| `select` | `path`, `window_number` | Clicks the item for a file or directory; answers what the current panel shows. |
| `quit_all` | none | Closes every window, unless one refuses. |

## The Code

* `app.py`: the model, with no Qt: what every window shows.
* `tree.py`: the shop's and the design's trees, with no Qt.
* `editor.py`: which editor [Edit] opens, with no Qt.
* `window.py`: the windows and the new shop dialog.
* `views.py`: the tree, the panels, and the watcher.
* `window_exposed.py`: the GUI's functions reached over MCP.
* `outline_panel.py`: `--outline`, `--tutorial` and `--record`.
* `../run.py`: the command line.
