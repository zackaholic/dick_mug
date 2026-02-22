; 04_move_y.gcode - Y axis only
; Tests: Y motor direction and movement
;
; Expected: Y moves 10mm in positive direction, pauses, returns to 0

G21 ; mm mode
G90 ; absolute positioning
G0 Z5 F300 ; pen up

G0 X0 Y0 F2000 ; start at origin
G4 P1 ; pause 1 second

G0 Y10 F800 ; move Y +10mm (slow so you can watch)
G4 P1 ; pause 1 second

G0 Y0 F800 ; return Y to 0

G0 Z5 ; pen up
G0 X0 Y0 F2000 ; return to origin
M2 ; program end
