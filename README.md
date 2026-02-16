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

# Stream GCode to the plotter
python -m mugplot stream drawing.gcode

# Convert + stream in one step
python -m mugplot run drawing.svg

# Check machine status
python -m mugplot status

# Soft reset
python -m mugplot reset
```

Use `-c path/to/config.yaml` to override the default config.

## Drawing App

Open `index.html` in a browser for a simple web-based drawing tool. Canvas is 60mm x 150mm (standard mug wrap area). Save outputs SVG files that can be fed directly to `mugplot convert`.

SVGs from any source (Inkscape, Illustrator, etc.) work too — the converter handles lines, bezier curves, and arcs.

## Configuration

Edit `config.yaml` to tune machine parameters:

- **Pen height:** `z_pen_up` / `z_pen_down` — most sensitive param, needs physical tuning
- **Speeds:** `draw_speed`, `travel_speed`, `z_travel_speed` (mm/min)
- **Bed size:** `bed_width` (60mm X) / `bed_height` (150mm Y)
- **Serial:** `port` (default `/dev/ttyUSB0`), `baud_rate` (115200)

## Project Structure

```
mugplot/           Python package
  config.py        YAML config loading + dataclasses
  svg_to_gcode.py  SVG parsing, coord mapping, curve linearization, GCode gen
  streamer.py      Character-counting serial streamer for FluidNC
  cli.py           CLI commands
config.yaml        Machine/serial parameters
index.html         Web drawing app
src/               Drawing app JS/CSS
```

## Next Steps

- [ ] First hardware test: `python -m mugplot status` to verify serial connection
- [ ] Tune `z_pen_down` with physical pen/mug setup
- [ ] Stream a small test square to verify axis directions and scale
- [ ] Convert and stream a local SVG file (e.g. from Inkscape) to the plotter
- [ ] End-to-end: draw in web app → save SVG → `python -m mugplot run drawing.svg`
