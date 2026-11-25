# Moving a Corner

A new outline starts as a triangle.  Here you choose a corner,
move one, and take the move back.

* Click the lower left corner to choose it: the buttons that act
  on corners now act on it.
  <!-- do: click Vertex V1 -->
* Drag the top corner up and to the right.  The edges follow it.
  <!-- do: drag Vertex V3 -> (1, 6) -->
* Press [Undo] to take the move back: the corner goes back.
  <!-- do: button Undo -->

<!-- recording
format = 2
scraftcam = "0.1.0"
outline = ""

[[states]]
step = 1
call = "click Vertex V1"
state = '''
file: (new)
revolve: False
corners:
  V1: (-4, -3)
  V2: (4, -3)
  V3: (0, 4)
dimensions:
letters:
chosen corners: [Vertex V1]
chosen dimensions: []
chosen edges: []
problems:
  Every corner floats: nothing ties the outline to the origin (drag a corner onto it, or dimension one from it).
undo depth: 0
'''

[[states]]
step = 2
call = "drag Vertex V3 -> (1, 6)"
state = '''
file: (new)
revolve: False
corners:
  V1: (-4, -3)
  V2: (4, -3)
  V3: (1, 6)
dimensions:
letters:
chosen corners: [Vertex V1, Vertex V3]
chosen dimensions: []
chosen edges: []
problems:
  Every corner floats: nothing ties the outline to the origin (drag a corner onto it, or dimension one from it).
undo depth: 1
'''

[[states]]
step = 3
call = "button Undo"
state = '''
file: (new)
revolve: False
corners:
  V1: (-4, -3)
  V2: (4, -3)
  V3: (0, 4)
dimensions:
letters:
chosen corners: []
chosen dimensions: []
chosen edges: []
problems:
  Every corner floats: nothing ties the outline to the origin (drag a corner onto it, or dimension one from it).
undo depth: 0
'''
-->
