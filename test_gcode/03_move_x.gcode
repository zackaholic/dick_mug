; 03_move_x.gcode - X axis only
; Tests: X motor direction and movement
;
; Expected: X moves 10mm in positive direction, pauses, returns to 0

G21 ; mm mode
G90 ; absolute positioning
G0 Z5 F300 ; pen up

G0 X0 Y0 F2000 ; start at origin
G4 P1 ; pause 1 second

G0 X10 F800 ; move X +10mm (slow so you can watch)
G4 P1 ; pause 1 second

G0 X0 F800 ; return X to 0

G0 Z5 ; pen up
G0 X0 Y0 F2000 ; return to origin
M2 ; program end
