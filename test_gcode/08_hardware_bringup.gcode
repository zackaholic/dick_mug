; 08_hardware_bringup.gcode - Full hardware bringup test
; Tests: X/Y travel, Z pen up/down, streaming
;
; Assumptions:
;   - Machine is homed (X=0, Y=0)
;   - Z starts at 0 (fully retracted, away from surface)
;   - Drawing envelope: X 0-205, Y 10-83
;   - Z pen up: -6, Z pen down: -8
;
; Expected: lifts Z, draws a cross in the center of the
;           drawing envelope, returns to origin

G21 ; mm mode
G90 ; absolute positioning
$H ; home X and Y
G10 L2 P1 X0 Y0 Z0 ; clear G54 work offset
G92 Z0 ; set current Z position as zero (Z must be manually at home)

; lift Z to travel height
G0 Z-6 F300

; travel to center of drawing envelope (X=102, Y=46)
G0 X102 Y46 F2000

; pen down
G1 Z-8 F300

; horizontal bar of cross
G1 X92 Y46 F800
G1 X112 Y46

; pen up, reposition for vertical bar
G0 Z-6 F300
G0 X102 Y36

; pen down
G1 Z-8 F300

; vertical bar of cross
G1 X102 Y56 F800

; pen up
G0 Z-6 F300

; return to origin
G0 X0 Y10 F2000

M2 ; program end
