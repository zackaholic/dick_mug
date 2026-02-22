; 05_move_z.gcode - Z axis only
; Tests: pen up/down mechanism
;
; Expected: Z moves down to 0 (pen down), pauses, returns to 5 (pen up)

G21 ; mm mode
G90 ; absolute positioning

G0 Z5 F300 ; start pen up
G4 P1 ; pause 1 second

G1 Z0 F300 ; pen down
G4 P2 ; pause 2 seconds (check pen contact)

G0 Z5 F300 ; pen up

M2 ; program end
