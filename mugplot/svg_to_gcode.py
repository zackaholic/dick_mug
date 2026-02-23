"""SVG to GCode converter for the mug plotter.

Parses SVG paths using svgpathtools, maps coordinates to machine space,
linearizes curves via adaptive subdivision, and generates GCode.
"""

import re
from pathlib import Path

from svgpathtools import svg2paths2, Line, CubicBezier, QuadraticBezier, Arc

from .config import MachineConfig


def _point_to_xy(point: complex) -> tuple[float, float]:
    """Convert a complex point (svgpathtools convention) to (x, y)."""
    return (point.real, point.imag)


def _linearize_segment(segment, tolerance: float) -> list[tuple[float, float]]:
    """Adaptively linearize a path segment into (x, y) points.

    For Line segments, returns just the endpoint.
    For curves, recursively bisects until chord deviation < tolerance.
    Returns points excluding the segment start (caller handles continuity).
    """
    if isinstance(segment, Line):
        return [_point_to_xy(segment.end)]

    # Adaptive subdivision for curves
    return _subdivide(segment, 0.0, 1.0, tolerance)


def _subdivide(
    segment, t_start: float, t_end: float, tolerance: float
) -> list[tuple[float, float]]:
    """Recursively subdivide a curve segment until it's flat enough."""
    start = segment.point(t_start)
    end = segment.point(t_end)
    t_mid = (t_start + t_end) / 2.0
    mid_actual = segment.point(t_mid)

    # Chord midpoint vs actual curve midpoint
    mid_chord = (start + end) / 2.0
    deviation = abs(mid_actual - mid_chord)

    if deviation <= tolerance or (t_end - t_start) < 1e-6:
        return [_point_to_xy(end)]

    left = _subdivide(segment, t_start, t_mid, tolerance)
    right = _subdivide(segment, t_mid, t_end, tolerance)
    return left + right


def _map_coord(
    x: float, y: float, cfg: MachineConfig, svg_height: float
) -> tuple[float, float]:
    """Map SVG coordinates to machine coordinates."""
    mx = x + cfg.origin_x
    if cfg.flip_y:
        my = (svg_height - y) + cfg.origin_y
    else:
        my = y + cfg.origin_y
    return (mx, my)


def _fmt(v: float) -> str:
    """Format a float for GCode — strip trailing zeros."""
    return f"{v:.3f}".rstrip("0").rstrip(".")


def svg_to_gcode(svg_path: str | Path, cfg: MachineConfig | None = None) -> list[str]:
    """Convert an SVG file to a list of GCode lines.

    Args:
        svg_path: Path to the SVG file.
        cfg: Machine configuration. Uses defaults if None.

    Returns:
        List of GCode strings (without newlines).
    """
    if cfg is None:
        cfg = MachineConfig()

    paths, attributes, svg_attributes = svg2paths2(str(svg_path))

    # Determine SVG dimensions for Y-flip
    svg_height = cfg.bed_height  # default
    viewbox = svg_attributes.get("viewBox", "")
    if viewbox:
        parts = viewbox.split()
        if len(parts) == 4:
            svg_height = float(parts[3])
    elif "height" in svg_attributes:
        h_str = svg_attributes["height"].replace("mm", "").replace("px", "").strip()
        try:
            svg_height = float(h_str)
        except ValueError:
            pass

    lines: list[str] = []

    # Header
    lines.append("G21 ; mm mode")
    lines.append("G90 ; absolute positioning")
    if cfg.home_on_start:
        lines.append("$H ; home X and Y")
    lines.append("G10 L2 P1 X0 Y0 Z0 ; clear G54 work offset")
    lines.append("G92 Z0 ; set current Z as zero (Z must be manually at home)")
    lines.append(f"G0 Z{_fmt(cfg.z_pen_up)} F{_fmt(cfg.z_travel_speed)} ; pen up")

    current_feed = None

    for path in paths:
        if len(path) == 0:
            continue

        # Linearize all segments in this path
        points: list[tuple[float, float]] = []
        first_seg = path[0]
        start_x, start_y = _point_to_xy(first_seg.start)
        points.append(_map_coord(start_x, start_y, cfg, svg_height))

        for segment in path:
            raw_pts = _linearize_segment(segment, cfg.curve_tolerance)
            for rx, ry in raw_pts:
                points.append(_map_coord(rx, ry, cfg, svg_height))

        if len(points) < 2:
            continue

        # Pen up + rapid to path start
        lines.append(f"G0 Z{_fmt(cfg.z_pen_up)}")
        sx, sy = points[0]
        if current_feed != cfg.travel_speed:
            lines.append(f"G0 X{_fmt(sx)} Y{_fmt(sy)} F{_fmt(cfg.travel_speed)}")
            current_feed = cfg.travel_speed
        else:
            lines.append(f"G0 X{_fmt(sx)} Y{_fmt(sy)}")

        # Pen down
        lines.append(f"G1 Z{_fmt(cfg.z_pen_down)} F{_fmt(cfg.z_travel_speed)}")
        current_feed = cfg.z_travel_speed

        # Draw moves
        for px, py in points[1:]:
            if current_feed != cfg.draw_speed:
                lines.append(f"G1 X{_fmt(px)} Y{_fmt(py)} F{_fmt(cfg.draw_speed)}")
                current_feed = cfg.draw_speed
            else:
                lines.append(f"G1 X{_fmt(px)} Y{_fmt(py)}")

    # Footer
    lines.append(f"G0 Z{_fmt(cfg.z_pen_up)} ; pen up")
    lines.append(f"G0 X{_fmt(cfg.origin_x)} Y{_fmt(cfg.origin_y)} F{_fmt(cfg.travel_speed)} ; return to origin")
    lines.append("M2 ; program end")

    return lines


_COORD_RE = re.compile(r"([XYZ])([-\d.]+)", re.IGNORECASE)


def check_gcode_bounds(gcode_lines: list[str], cfg: MachineConfig) -> list[str]:
    """Check generated GCode coordinates against the configured drawing envelope.

    Args:
        gcode_lines: GCode lines (may include comments).
        cfg: Machine configuration defining the safe envelope.

    Returns:
        List of violation strings. Empty if all coordinates are in bounds.
    """
    x_min = cfg.origin_x
    x_max = cfg.origin_x + cfg.bed_width
    y_min = cfg.origin_y
    y_max = cfg.origin_y + cfg.bed_height
    z_min = min(cfg.z_pen_down, cfg.z_pen_up) - 1.0  # small tolerance
    z_max = max(cfg.z_pen_down, cfg.z_pen_up) + 1.0

    violations = []
    for i, line in enumerate(gcode_lines, 1):
        # Strip comments
        clean = line.split(";")[0].upper()
        if not re.match(r"\s*G[01]\b", clean):
            continue
        for axis, val_str in _COORD_RE.findall(clean):
            val = float(val_str)
            lineno = f"line {i}"
            if axis == "X" and not (x_min <= val <= x_max):
                violations.append(f"{lineno}: X{val} out of range [{x_min}, {x_max}]")
            elif axis == "Y" and not (y_min <= val <= y_max):
                violations.append(f"{lineno}: Y{val} out of range [{y_min}, {y_max}]")
            elif axis == "Z" and not (z_min <= val <= z_max):
                violations.append(f"{lineno}: Z{val} out of range [{z_min:.1f}, {z_max:.1f}]")

    return violations


def convert_file(
    svg_path: str | Path,
    output_path: str | Path | None = None,
    cfg: MachineConfig | None = None,
) -> Path:
    """Convert SVG to GCode and write to file.

    Args:
        svg_path: Input SVG path.
        output_path: Output .gcode path. Defaults to same name with .gcode extension.
        cfg: Machine configuration.

    Returns:
        Path to the written GCode file.
    """
    svg_path = Path(svg_path)
    if output_path is None:
        output_path = svg_path.with_suffix(".gcode")
    else:
        output_path = Path(output_path)

    gcode_lines = svg_to_gcode(svg_path, cfg)
    output_path.write_text("\n".join(gcode_lines) + "\n")
    return output_path
