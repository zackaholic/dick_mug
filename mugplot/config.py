"""Configuration loading and dataclasses for mug plotter."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class MachineConfig:
    bed_width: float = 60.0
    bed_height: float = 150.0
    origin_x: float = 0.0
    origin_y: float = 0.0
    flip_y: bool = True
    z_pen_up: float = 5.0
    z_pen_down: float = 0.0
    z_travel_speed: float = 300.0
    draw_speed: float = 800.0
    travel_speed: float = 2000.0
    curve_tolerance: float = 0.1
    home_on_start: bool = False


@dataclass
class SerialConfig:
    port: str = "/dev/ttyUSB0"
    baud_rate: int = 115200
    rx_buffer_size: int = 128
    timeout: float = 2.0
    connect_timeout: float = 10.0


@dataclass
class Config:
    machine: MachineConfig = field(default_factory=MachineConfig)
    serial: SerialConfig = field(default_factory=SerialConfig)


def load_config(path: Path | str | None = None) -> Config:
    """Load config from YAML file. Falls back to defaults if no file given."""
    if path is None:
        path = Path(__file__).parent.parent / "config.yaml"
    else:
        path = Path(path)

    if not path.exists():
        return Config()

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    machine = MachineConfig(**raw.get("machine", {}))
    serial = SerialConfig(**raw.get("serial", {}))
    return Config(machine=machine, serial=serial)
