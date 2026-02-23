"""GCode serial streamer with character-counting flow control for FluidNC/Grbl.

Implements the character-counting protocol for maximum throughput:
track bytes in flight, only send when buffer space is available,
dequeue on ok/error responses.
"""

import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

import serial

from .config import SerialConfig


@dataclass
class StreamResult:
    lines_sent: int = 0
    errors: list[str] = field(default_factory=list)
    elapsed: float = 0.0
    completed: bool = False


class SerialPort(Protocol):
    """Protocol for serial port (allows mock injection)."""

    def write(self, data: bytes) -> int: ...
    def readline(self) -> bytes: ...
    def read(self, size: int = 1) -> bytes: ...
    def close(self) -> None: ...
    @property
    def in_waiting(self) -> int: ...


ProgressCallback = Callable[[int, int], None]  # (lines_sent, total_lines)


def _strip_gcode(line: str) -> str:
    """Strip comments and whitespace from a GCode line."""
    # Remove inline comments (everything after semicolon)
    if ";" in line:
        line = line[: line.index(";")]
    # Remove parenthetical comments
    while "(" in line and ")" in line:
        start = line.index("(")
        end = line.index(")", start)
        line = line[:start] + line[end + 1 :]
    return line.strip()


def load_gcode(path: str | Path) -> list[str]:
    """Load GCode from file, stripping comments and blank lines."""
    lines = []
    for raw in Path(path).read_text().splitlines():
        cleaned = _strip_gcode(raw)
        if cleaned:
            lines.append(cleaned)
    return lines


class GCodeStreamer:
    """Streams GCode to FluidNC over serial with character-counting flow control."""

    def __init__(self, cfg: SerialConfig | None = None, port: SerialPort | None = None):
        self.cfg = cfg or SerialConfig()
        self._port = port
        self._owns_port = port is None

    def connect(self) -> str:
        """Open serial connection and wait for FluidNC startup banner.

        Returns the startup banner text.
        """
        if self._port is not None:
            return ""

        self._port = serial.Serial(
            port=self.cfg.port,
            baudrate=self.cfg.baud_rate,
            timeout=self.cfg.timeout,
        )
        self._owns_port = True

        # Drain startup banner or any leftover bytes from a previous session
        banner_lines = []
        deadline = time.monotonic() + self.cfg.connect_timeout
        while time.monotonic() < deadline:
            line = self._port.readline().decode("utf-8", errors="replace").strip()
            if line:
                banner_lines.append(line)
                if line.startswith("Grbl") or "ready" in line.lower():
                    break

        # Flush any remaining bytes (leftover responses from previous streams)
        time.sleep(0.1)
        while self._port.in_waiting:
            self._port.read(self._port.in_waiting)
            time.sleep(0.05)

        return "\n".join(banner_lines)

    def close(self):
        """Close the serial connection."""
        if self._port and self._owns_port:
            self._port.close()
            self._port = None

    def send_realtime(self, cmd: bytes):
        """Send a real-time command (single byte, bypasses buffer).

        Common commands:
            b'?' - status query
            b'!' - feed hold
            b'~' - cycle resume
            b'\\x18' - soft reset (Ctrl-X)
        """
        if self._port is None:
            raise RuntimeError("Not connected")
        self._port.write(cmd)

    def query_status(self) -> str:
        """Send ? and return the status report string."""
        if self._port is None:
            raise RuntimeError("Not connected")

        # Flush any pending input
        while self._port.in_waiting:
            self._port.read(self._port.in_waiting)

        self._port.write(b"?")
        deadline = time.monotonic() + self.cfg.timeout
        while time.monotonic() < deadline:
            line = self._port.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("<") and line.endswith(">"):
                return line
        return ""

    def soft_reset(self):
        """Send Ctrl-X soft reset."""
        self.send_realtime(b"\x18")

    def stream(
        self,
        gcode_lines: list[str],
        progress: ProgressCallback | None = None,
    ) -> StreamResult:
        """Stream GCode lines using character-counting flow control.

        Args:
            gcode_lines: Pre-cleaned GCode lines (no comments/blanks).
            progress: Optional callback(lines_sent, total_lines).

        Returns:
            StreamResult with stats.
        """
        if self._port is None:
            raise RuntimeError("Not connected — call connect() first")

        result = StreamResult()
        total = len(gcode_lines)
        start_time = time.monotonic()

        bytes_in_flight = 0
        sent_lengths: deque[int] = deque()
        send_idx = 0
        ack_count = 0

        buf_size = self.cfg.rx_buffer_size

        while ack_count < total:
            # Send lines while buffer has space
            while send_idx < total:
                line = gcode_lines[send_idx]
                line_bytes = len(line) + 1  # +1 for \n
                if bytes_in_flight + line_bytes >= buf_size:
                    break
                self._port.write((line + "\n").encode("utf-8"))
                bytes_in_flight += line_bytes
                sent_lengths.append(line_bytes)
                send_idx += 1

            # Read response
            resp = self._port.readline().decode("utf-8", errors="replace").strip()

            if not resp:
                # Timeout — check if we've sent everything
                if send_idx >= total and ack_count >= send_idx:
                    break
                continue

            if resp == "ok":
                if sent_lengths:
                    bytes_in_flight -= sent_lengths.popleft()
                ack_count += 1
                result.lines_sent = ack_count
                if progress:
                    progress(ack_count, total)

            elif resp.startswith("error:"):
                if sent_lengths:
                    bytes_in_flight -= sent_lengths.popleft()
                ack_count += 1
                result.errors.append(f"Line {ack_count}: {resp}")
                result.lines_sent = ack_count
                if progress:
                    progress(ack_count, total)

            elif resp.startswith("ALARM:"):
                result.errors.append(f"ALARM at line {ack_count}: {resp}")
                break

            # Ignore status reports and other messages during streaming

        result.elapsed = time.monotonic() - start_time
        result.completed = ack_count >= total and not any(
            e.startswith("ALARM") for e in result.errors
        )
        return result

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()
