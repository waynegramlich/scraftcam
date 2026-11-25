# 6.11 Support Assemblies

Assemblies require a path to a 3D solid which basically as 1-to-1 with
something that can be represented as a `.step` file.  Currently,
SolidCraft provides that path to a `.step` file.  Currently the polygon
editor has the ability to produce revolved polygons for drill bits and the
like.  The other thing we need to be able to do is the extrude/remove task
of taking a tree of polygons and depths and producing a 3D solid by
extruding some polygons upwards to create more solid and removing
volume for polygons in the downward direction.  Again, this should
be possible to do from the polygon editor.

In addition, we need to distinguish polygons/solids by color (and
transparency).  For 2D drawings, different materials are represented
with various diagonal line fills.  For 3D solids, color and transparency
is the normal way to distinguish between them.  One mini task to perform
is to turn most tool bits into 2 polygons -- one for the cutting teeth/flutes
and the rest that gets held in place by the tool holder (part or assembly
for collets).  Thus each tool bit would be represented as 2 solids, one that
does the cutting and the other that provides the support structure.  

When attaching polygons "together", 2 shared vertices make sense.
For attaching 3D objects together, I propose using an isosceles
triangle to line up 3D parts.
