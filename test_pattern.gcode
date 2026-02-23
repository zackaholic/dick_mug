G21 ; mm mode
G90 ; absolute positioning
$H ; home X and Y
G10 L2 P1 X0 Y0 Z0 ; clear G54 work offset
G92 Z0 ; set current Z as zero (Z must be manually at home)
G0 Z-6 F300 ; pen up
G0 Z-6
G0 X82.5 Y46.5 F2000
G1 Z-8 F300
G1 X122.5 Y46.5 F800
G0 Z-6
G0 X102.5 Y66.5 F2000
G1 Z-8 F300
G1 X102.5 Y26.5 F800
G0 Z-6
G0 X10 Y73 F2000
G1 Z-8 F300
G1 X195 Y73 F800
G1 X195 Y20
G1 X10 Y20
G1 X10 Y73
G0 Z-6 ; pen up
G0 X0 Y10 F2000 ; return to origin
M2 ; program end
