; 02_home.gcode - Homing cycle
; Tests: homing switches, homing direction
;
; WARNING: watch the machine! kill power if axes move the wrong way
; Expected: each axis seeks its limit switch, then backs off

G21 ; mm mode
G90 ; absolute positioning

$H ; home all axes

G0 Z5 F300 ; pen up after homing

M2 ; program end
