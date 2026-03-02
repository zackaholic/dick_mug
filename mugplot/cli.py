"""CLI for the mug plotter: convert, stream, run, status, reset."""

import argparse
import sys
from pathlib import Path

from .config import load_config
from .svg_to_gcode import svg_to_gcode, convert_file, check_gcode_bounds
from .streamer import GCodeStreamer, load_gcode


def _progress(sent: int, total: int):
    pct = sent * 100 // total if total else 100
    bar = "#" * (pct // 2) + "-" * (50 - pct // 2)
    print(f"\r[{bar}] {sent}/{total} ({pct}%)", end="", flush=True)


def cmd_convert(args, config):
    output = convert_file(args.input, args.output, config.machine)
    print(f"Wrote {output}")


def cmd_stream(args, config):
    gcode = load_gcode(args.input)
    print(f"Loaded {len(gcode)} lines from {args.input}")

    streamer = GCodeStreamer(config.serial)
    with streamer:
        print(f"Connected to {config.serial.port}")
        status = streamer.query_status()
        if "Alarm" in status:
            print(f"Warning: machine is in ALARM state. Homing will clear it.")
        result = streamer.stream(gcode, progress=_progress)

    print()  # newline after progress bar
    print(f"Sent {result.lines_sent} lines in {result.elapsed:.1f}s")
    if result.errors:
        print(f"Errors ({len(result.errors)}):")
        for e in result.errors:
            print(f"  {e}")
    if result.completed:
        print("Done.")
    else:
        print("Stream did not complete.")
        sys.exit(1)


def cmd_check(args, config):
    gcode = svg_to_gcode(args.input, config.machine)
    x_max = config.machine.origin_x + config.machine.bed_width
    y_max = config.machine.origin_y + config.machine.bed_height
    print(f"Envelope: X[{config.machine.origin_x}, {x_max}] Y[{config.machine.origin_y}, {y_max}]")
    print(f"Z: up={config.machine.z_pen_up} down={config.machine.z_pen_down}")
    print(f"Generated {len(gcode)} GCode lines")

    violations = check_gcode_bounds(gcode, config.machine)
    if violations:
        print(f"VIOLATIONS ({len(violations)}):")
        for v in violations:
            print(f"  {v}")
        sys.exit(1)
    else:
        print("OK — all coordinates within bounds.")


def cmd_run(args, config):
    print(f"Converting {args.input}...")
    gcode = svg_to_gcode(args.input, config.machine)

    violations = check_gcode_bounds(gcode, config.machine)
    if violations:
        print(f"WARNING: {len(violations)} out-of-bounds coordinate(s):")
        for v in violations:
            print(f"  {v}")
        print("Aborting. Run 'mugplot check' for details.")
        sys.exit(1)

    # Strip comments for streaming
    cleaned = []
    for line in gcode:
        stripped = line.split(";")[0].strip()
        if stripped:
            cleaned.append(stripped)

    print(f"Generated {len(cleaned)} GCode lines")

    streamer = GCodeStreamer(config.serial)
    with streamer:
        print(f"Connected to {config.serial.port}")
        result = streamer.stream(cleaned, progress=_progress)

    print()
    print(f"Sent {result.lines_sent} lines in {result.elapsed:.1f}s")
    if result.errors:
        for e in result.errors:
            print(f"  {e}")
    if result.completed:
        print("Done.")
    else:
        print("Stream did not complete.")
        sys.exit(1)


def cmd_find_dock(args, config):
    mc = config.machine
    sc = config.serial

    streamer = GCodeStreamer(sc)
    streamer.connect()

    print("Homing...")
    ok, resp = streamer.send_command("$H")
    if not ok:
        print(f"Home failed: {resp}")
        streamer.close()
        sys.exit(1)
    streamer.wait_idle(timeout=60.0)
    print("Homed.")

    print()
    print("Axes: Y = vertical (positive = down), Z = pen extension (negative = forward)")
    print("Commands: y+  y-  z+  z-  [y+N / z-2.5]  step N  pos  done  q")
    print()

    step = 1.0

    while True:
        try:
            raw = input("find-dock> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        low = raw.lower()

        if low in ("q", "quit"):
            break

        if low == "done":
            pos = streamer.get_position()
            if pos:
                x, y, z = pos
                print(f"Current position: X={x} Y={y} Z={z}")
                print()
                print("Paste into config.yaml under machine:")
                print(f"  dock_y: {y}")
                print(f"  dock_z: {z}")
            else:
                print("Could not read position.")
            break

        if low == "pos":
            pos = streamer.get_position()
            if pos:
                x, y, z = pos
                print(f"X={x} Y={y} Z={z}")
            else:
                print("Could not read position.")
            continue

        if low.startswith("step"):
            parts = low.split()
            if len(parts) == 2:
                try:
                    step = float(parts[1])
                    print(f"Step size: {step} mm")
                except ValueError:
                    print("Usage: step <mm>")
            else:
                print("Usage: step <mm>")
            continue

        # Jog commands: y+, y-, z+, z-, y+N, y-N, z+N, z-N
        import re as _re
        m = _re.fullmatch(r"([yz])([+-])(\d*\.?\d*)", low)
        if m:
            axis = m.group(1).upper()
            sign = 1.0 if m.group(2) == "+" else -1.0
            dist_str = m.group(3)
            dist = float(dist_str) if dist_str else step
            speed = mc.z_travel_speed if axis == "Z" else mc.travel_speed
            jog = f"$J=G91 {axis}{sign * dist:.3f} F{mc.travel_speed if axis == 'Y' else mc.z_travel_speed:.0f}"
            ok, resp = streamer.send_command(jog)
            if not ok:
                print(f"Jog error: {resp}")
            streamer.wait_idle(timeout=15.0)
            pos = streamer.get_position()
            if pos:
                _, y, z = pos
                print(f"Y={y:.3f}  Z={z:.3f}")
            continue

        print(f"Unknown command: {raw}")

    streamer.close()


def cmd_status(args, config):
    streamer = GCodeStreamer(config.serial)
    with streamer:
        status = streamer.query_status()
        if status:
            print(status)
        else:
            print("No status response (timeout)")


def cmd_reset(args, config):
    streamer = GCodeStreamer(config.serial)
    with streamer:
        streamer.soft_reset()
        print("Soft reset sent.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="mugplot",
        description="Mug plotter: SVG to GCode conversion and streaming",
    )
    parser.add_argument(
        "-c", "--config", default=None, help="Path to config.yaml"
    )

    sub = parser.add_subparsers(dest="command")

    # convert
    p_convert = sub.add_parser("convert", help="Convert SVG to GCode file")
    p_convert.add_argument("input", help="Input SVG file")
    p_convert.add_argument("output", nargs="?", default=None, help="Output .gcode file")

    # stream
    p_stream = sub.add_parser("stream", help="Stream GCode file to FluidNC")
    p_stream.add_argument("input", help="Input .gcode file")

    # check
    p_check = sub.add_parser("check", help="Validate SVG conversion without touching the machine")
    p_check.add_argument("input", help="Input SVG file")

    # run
    p_run = sub.add_parser("run", help="Convert SVG and stream to FluidNC")
    p_run.add_argument("input", help="Input SVG file")

    # status
    sub.add_parser("status", help="Query machine status")

    # reset
    sub.add_parser("reset", help="Send soft reset")

    # find-dock
    sub.add_parser("find-dock", help="Interactive Y/Z jog to calibrate pen dock position")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config(args.config)

    commands = {
        "convert": cmd_convert,
        "check": cmd_check,
        "stream": cmd_stream,
        "run": cmd_run,
        "status": cmd_status,
        "reset": cmd_reset,
        "find-dock": cmd_find_dock,
    }
    commands[args.command](args, config)
