# Mug Plotter

A CNC pen plotter system for drawing on coffee mugs. SVG in, drawing on mug out.

```
SVG file → [svg_to_gcode] → GCode → [streamer] → USB Serial → FluidNC
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Your user needs serial access: `sudo usermod -a -G dialout $USER` (re-login after).

## Usage

```bash
# Convert SVG to GCode
python -m mugplot convert drawing.svg

# Validate SVG conversion against machine envelope (no machine contact)
python -m mugplot check drawing.svg

# Stream GCode to the plotter
python -m mugplot stream drawing.gcode

# Convert + stream in one step (runs bounds check first)
python -m mugplot run drawing.svg

# Check machine status
python -m mugplot status

# Soft reset
python -m mugplot reset

# Interactive Y/Z jog to calibrate the pen dock position
python -m mugplot find-dock
```

Use `-c path/to/config.yaml` to override the default config.

## Pen Dock

The machine has a physical o-ring cavity below the mug platen. When the marker is parked there, the tip is sealed against the gasket to prevent drying out.

**Calibrating the dock** — run once after physical setup:

```bash
python -m mugplot find-dock
```

The tool homes the machine, then opens an interactive jog REPL:

| Command | Effect |
|---------|--------|
| `y+` / `y-` | Jog Y by current step (default 1 mm) |
| `z+` / `z-` | Jog Z by current step |
| `y+2.5` / `z-0.5` | Jog a specific distance |
| `step N` | Change step size (mm) |
| `pos` | Print current X/Y/Z position |
| `done` | Print position + config snippet, exit |
| `q` / `quit` | Exit without saving |

When `done` is entered, the tool prints the values to paste into `config.yaml`:

```yaml
dock_y: 95.0   # mm — Y below platen (positive, > bed_height + origin_y)
dock_z: -12.0  # mm — Z forward to seat in o-ring (negative)
```

**Dock sequence** (appended to every job when `dock_y`/`dock_z` are set):
1. `G0 Z0` — fully retract pen
2. `G0 Y{dock_y}` — lower below platen
3. `G0 Z{dock_z}` — extend forward to seat marker against gasket

Dock moves are excluded from the bounds check automatically (tagged `[dock]` in GCode comments).

## Drawing App

Open `index.html` in a browser for a simple web-based drawing tool. Canvas is 205mm × 73mm, matching the machine's drawing envelope. Save outputs an SVG that can be fed directly to `mugplot run`.

SVGs from any source (Inkscape, Illustrator, etc.) work too — the converter handles lines, bezier curves, and arcs.

## Configuration

Edit `config.yaml` to tune machine parameters:

- **Pen height:** `z_pen_up` / `z_pen_down` — most sensitive param, tune carefully
- **Speeds:** `draw_speed`, `travel_speed`, `z_travel_speed` (mm/min)
- **Drawing envelope:** `bed_width` (205mm X) / `bed_height` (73mm Y) / `origin_y` (10mm Y margin from home)
- **Serial:** `port` (default `/dev/ttyUSB0`), `baud_rate` (115200)
- **Pen dock:** `dock_y` / `dock_z` — set after running `find-dock`; leave commented out until calibrated

## Running Tests

```bash
.venv/bin/pytest tests/ -q
```

Expected result: **20 passing, 1 known failing** (`TestSquareSVG::test_y_flip`).

The failing test has a wrong expected value in its assertion — it doesn't account for `origin_y` in the Y-flip calculation (asserts 140.0, actual correct value is 150.0). It is a test bug, not a code bug. Do not attempt to fix the code to match it; fix the test assertion if you touch it.

## Project Structure

```
mugplot/           Python package
  config.py        YAML config loading + dataclasses
  svg_to_gcode.py  SVG parsing, coord mapping, curve linearization, GCode gen + bounds validation
  streamer.py      Character-counting serial streamer for FluidNC
  cli.py           CLI commands
config.yaml        Machine/serial parameters
index.html         Web drawing app
src/               Drawing app JS/CSS
tests/             pytest suite (21 tests, 1 known failing — see above)
```

## Machine Geometry

- **X** — mug turntable (rotation axis); 0–205 mm
- **Y** — vertical linear rails; positive = down toward platen; 0 = home (top); drawing envelope starts at `origin_y` (10 mm)
- **Z** — pen extension; 0 = fully retracted/home; negative = forward toward mug surface

## Next Steps

- [x] Verify serial connection and streaming
- [x] Confirm homing and axis directions/scale
- [x] Implement pen dock (park position to prevent tip from drying)
- [ ] Physical setup: mount pen, position mug
- [ ] Tune `z_pen_down` — pen contact height (most sensitive param)
- [ ] Run `find-dock` to calibrate and fill in `dock_y` / `dock_z` in config
- [ ] First real SVG: convert and stream a simple shape end-to-end
- [ ] Full workflow: draw in web app → save SVG → `python -m mugplot run drawing.svg`
