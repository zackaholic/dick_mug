; 06_square.gcode - 10mm square
; Tests: both axes together, direction consistency, pen up/down
;
; Expected: draws a 10mm square starting at (5, 5)
; Verify: square looks square, sides are ~10mm, correct orientation

G21 ; mm mode
G90 ; absolute positioning
G0 Z5 F300 ; pen up

; travel to start
G0 X5 Y5 F2000

; pen down
G1 Z0 F300

; draw square
G1 X15 Y5 F800
G1 X15 Y15
G1 X5 Y15
G1 X5 Y5

; pen up
G0 Z5 F300

; return to origin
G0 X0 Y0 F2000
M2 ; program end
