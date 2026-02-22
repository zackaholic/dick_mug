; 07_direction_check.gcode - L-shape to verify axis orientation
; Tests: which direction is +X, which is +Y, are they correct?
;
; Expected: draws an "L" shape
;   - Long stroke along +X (horizontal)
;   - Short stroke along +Y from the start (vertical)
; If the L looks mirrored or rotated, an axis direction is wrong

G21 ; mm mode
G90 ; absolute positioning
G0 Z5 F300 ; pen up

; travel to start
G0 X5 Y5 F2000

; pen down
G1 Z0 F300

; horizontal stroke along +X (20mm)
G1 X25 Y5 F800

; pen up, return to start
G0 Z5 F300
G0 X5 Y5 F2000

; pen down
G1 Z0 F300

; vertical stroke along +Y (10mm)
G1 X5 Y15 F800

; pen up
G0 Z5 F300

; return to origin
G0 X0 Y0 F2000
M2 ; program end
