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
```

Use `-c path/to/config.yaml` to override the default config.

## Drawing App

Open `index.html` in a browser for a simple web-based drawing tool. Canvas is 205mm × 73mm, matching the machine's drawing envelope. Save outputs an SVG that can be fed directly to `mugplot run`.

SVGs from any source (Inkscape, Illustrator, etc.) work too — the converter handles lines, bezier curves, and arcs.

## Configuration

Edit `config.yaml` to tune machine parameters:

- **Pen height:** `z_pen_up` / `z_pen_down` — most sensitive param, tune carefully
- **Speeds:** `draw_speed`, `travel_speed`, `z_travel_speed` (mm/min)
- **Drawing envelope:** `bed_width` (205mm X) / `bed_height` (73mm Y) / `origin_y` (10mm Y margin from home)
- **Serial:** `port` (default `/dev/ttyUSB0`), `baud_rate` (115200)

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
```

## Next Steps

- [x] Verify serial connection and streaming
- [x] Confirm homing and axis directions/scale
- [ ] Physical setup: mount pen, position mug
- [ ] Tune `z_pen_down` — pen contact height (most sensitive param)
- [ ] First real SVG: convert and stream a simple shape end-to-end
- [ ] Full workflow: draw in web app → save SVG → `python -m mugplot run drawing.svg`
