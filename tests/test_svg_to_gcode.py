"""Tests for SVG to GCode conversion."""

from pathlib import Path

import pytest

from mugplot.config import MachineConfig
from mugplot.svg_to_gcode import svg_to_gcode, convert_file

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def cfg():
    return MachineConfig(
        bed_width=60.0,
        bed_height=150.0,
        flip_y=True,
        z_pen_up=5.0,
        z_pen_down=0.0,
        draw_speed=800.0,
        travel_speed=2000.0,
        z_travel_speed=300.0,
        curve_tolerance=0.1,
    )


def _parse_gcode(lines):
    """Extract just the G/M commands and coordinates, skipping comments."""
    cmds = []
    for line in lines:
        stripped = line.split(";")[0].strip()
        if stripped:
            cmds.append(stripped)
    return cmds


class TestSquareSVG:
    def test_produces_valid_gcode(self, cfg):
        lines = svg_to_gcode(FIXTURES / "square.svg", cfg)
        cmds = _parse_gcode(lines)

        # Should start with G21, G90
        assert cmds[0] == "G21"
        assert cmds[1] == "G90"
        # Should end with M2
        assert cmds[-1] == "M2"

    def test_has_pen_up_and_down(self, cfg):
        lines = svg_to_gcode(FIXTURES / "square.svg", cfg)
        text = "\n".join(lines)
        assert "Z5" in text  # pen up
        assert "Z0" in text  # pen down

    def test_coordinates_in_bounds(self, cfg):
        lines = svg_to_gcode(FIXTURES / "square.svg", cfg)
        for line in lines:
            stripped = line.split(";")[0].strip()
            if not stripped:
                continue
            for part in stripped.split():
                if part.startswith("X"):
                    x = float(part[1:])
                    assert 0 <= x <= cfg.bed_width, f"X={x} out of bounds"
                elif part.startswith("Y"):
                    y = float(part[1:])
                    assert 0 <= y <= cfg.bed_height, f"Y={y} out of bounds"

    def test_y_flip(self, cfg):
        """SVG Y=10 with viewBox height 150 should map to machine Y=140."""
        lines = svg_to_gcode(FIXTURES / "square.svg", cfg)
        # The square goes from SVG Y=10 to Y=50
        # With flip: machine Y = 150 - svg_y = 140 and 100
        y_values = []
        for line in lines:
            stripped = line.split(";")[0].strip()
            for part in stripped.split():
                if part.startswith("Y"):
                    y_values.append(float(part[1:]))
        assert 140.0 in y_values
        assert 100.0 in y_values


class TestCurveSVG:
    def test_curve_linearization_produces_multiple_points(self, cfg):
        lines = svg_to_gcode(FIXTURES / "curve.svg", cfg)
        # A cubic bezier should produce more than just start+end
        draw_moves = [l for l in lines if l.startswith("G1") and "X" in l]
        assert len(draw_moves) > 2, "Curve should be linearized into multiple segments"


class TestMultipathSVG:
    def test_multiple_paths_have_pen_lifts(self, cfg):
        lines = svg_to_gcode(FIXTURES / "multipath.svg", cfg)
        # Count pen-up moves (Z5 or z_pen_up) — expect at least:
        # 1 initial + 2 per-path pen-ups + 1 footer = 4
        pen_ups = [l for l in lines if "Z5" in l]
        assert len(pen_ups) >= 3  # initial + 2 paths + footer


class TestConvertFile:
    def test_writes_gcode_file(self, cfg, tmp_path):
        output = tmp_path / "test.gcode"
        result = convert_file(FIXTURES / "square.svg", output, cfg)
        assert result == output
        assert output.exists()
        content = output.read_text()
        assert "G21" in content
        assert "M2" in content

    def test_default_output_name(self, cfg, tmp_path):
        # Copy fixture to tmp so output doesn't pollute fixtures
        svg = tmp_path / "drawing.svg"
        svg.write_text((FIXTURES / "square.svg").read_text())
        result = convert_file(svg, cfg=cfg)
        assert result == tmp_path / "drawing.gcode"
        assert result.exists()
