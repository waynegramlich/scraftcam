# 5 Integration

Bringing the separate pieces together into one working system: the
shop, its machines, tooling and stock, the mount, the G-code and the
controller.  (Rewritten by Claude 2026-11-22 at the user's request;
the GUI side of this list is `T.g~6`, keep-out checking `T.ikz~4`.)

## Done

* One repository and package (`T.rd~5.1`), the Qt HMI (`T.hs~5.1.5`).
* The mount setup in the `.nc` as `(SCC: ...)` comments (TOML), drawn
  by the HMI with keep-out toggles, origin choice and step-through
  notes (`T.emsagc~5.2`).
* Carousel slot plan and swap prompts for one program, the time to
  the next tool change (`T.hs~5.1.5`).

## Left

* A path per tool change (`T.npfetc~5.4`); a job as a directory of
  `.nc` files and its carousel plan (`T.cpfj~5.7`).
* Standard materials (`T.sm2~5.5`); a project moved between shops
  (`T.ipfds~5.6`); several LinuxCNC simulators at once
  (`T.rslsao~5.8`).
* Automatic tool selection from the shop's tools.
* Multipart manufacturing; probe support.
* An operator document for a machine run.
