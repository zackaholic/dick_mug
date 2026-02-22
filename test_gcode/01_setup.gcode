; 01_setup.gcode - Basic machine setup, no movement
; Tests: serial connection, FluidNC responding, mode settings
;
; Expected: machine accepts commands, no motion

G21 ; mm mode
G90 ; absolute positioning
G0 Z5 F300 ; pen up (safe height)

M2 ; program end
