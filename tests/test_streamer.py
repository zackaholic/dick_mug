"""Tests for GCode streamer with mock serial."""

import pytest

from mugplot.config import SerialConfig
from mugplot.streamer import GCodeStreamer, load_gcode, _strip_gcode


class MockSerial:
    """Mock serial port that responds 'ok' to every line."""

    def __init__(self, responses=None):
        self._responses = list(responses) if responses else []
        self._resp_idx = 0
        self.written: list[bytes] = []
        self._in_waiting = 0

    def write(self, data: bytes) -> int:
        self.written.append(data)
        # Queue an 'ok' for each line sent (if no custom responses)
        if not self._responses:
            self._responses.append(b"ok\r\n")
        return len(data)

    def readline(self) -> bytes:
        if self._resp_idx < len(self._responses):
            resp = self._responses[self._resp_idx]
            self._resp_idx += 1
            return resp
        return b""

    def read(self, size: int = 1) -> bytes:
        return b""

    def close(self):
        pass

    @property
    def in_waiting(self) -> int:
        return self._in_waiting


class TestStripGcode:
    def test_strip_semicolon_comment(self):
        assert _strip_gcode("G0 X10 ; move") == "G0 X10"

    def test_strip_paren_comment(self):
        assert _strip_gcode("G1 X5 (feed) Y10") == "G1 X5  Y10"

    def test_strip_blank(self):
        assert _strip_gcode("   ") == ""

    def test_pure_comment(self):
        assert _strip_gcode("; this is a comment") == ""


class TestStreamBasic:
    def test_stream_single_line(self):
        mock = MockSerial(responses=[b"ok\r\n"])
        cfg = SerialConfig(rx_buffer_size=128)
        streamer = GCodeStreamer(cfg, port=mock)

        result = streamer.stream(["G0 X10"])

        assert result.lines_sent == 1
        assert result.completed
        assert not result.errors
        assert b"G0 X10\n" in mock.written

    def test_stream_multiple_lines(self):
        mock = MockSerial(responses=[b"ok\r\n", b"ok\r\n", b"ok\r\n"])
        cfg = SerialConfig(rx_buffer_size=128)
        streamer = GCodeStreamer(cfg, port=mock)

        result = streamer.stream(["G0 X10", "G1 X20 F800", "G0 X0"])

        assert result.lines_sent == 3
        assert result.completed

    def test_stream_handles_error(self):
        mock = MockSerial(responses=[b"ok\r\n", b"error:20\r\n", b"ok\r\n"])
        cfg = SerialConfig(rx_buffer_size=128)
        streamer = GCodeStreamer(cfg, port=mock)

        result = streamer.stream(["G0 X10", "G99", "G0 X0"])

        assert result.lines_sent == 3
        assert len(result.errors) == 1
        assert "error:20" in result.errors[0]
        assert result.completed  # errors don't stop streaming

    def test_stream_handles_alarm(self):
        mock = MockSerial(responses=[b"ok\r\n", b"ALARM:1\r\n"])
        cfg = SerialConfig(rx_buffer_size=128)
        streamer = GCodeStreamer(cfg, port=mock)

        result = streamer.stream(["G0 X10", "G0 X100"])

        assert not result.completed
        assert any("ALARM" in e for e in result.errors)

    def test_progress_callback(self):
        mock = MockSerial(responses=[b"ok\r\n", b"ok\r\n"])
        cfg = SerialConfig(rx_buffer_size=128)
        streamer = GCodeStreamer(cfg, port=mock)

        calls = []
        result = streamer.stream(["G0 X10", "G0 X20"], progress=lambda s, t: calls.append((s, t)))

        assert calls == [(1, 2), (2, 2)]


class TestCharacterCounting:
    def test_respects_buffer_limit(self):
        # Use a tiny buffer so lines must be sent one at a time
        long_line = "G1 X12.345 Y67.890 F800"  # ~25 chars + \n = 26 bytes
        mock = MockSerial(responses=[b"ok\r\n", b"ok\r\n"])
        cfg = SerialConfig(rx_buffer_size=30)  # only fits one line at a time
        streamer = GCodeStreamer(cfg, port=mock)

        result = streamer.stream([long_line, long_line])

        assert result.lines_sent == 2
        assert result.completed


class TestLoadGcode:
    def test_load_strips_comments(self, tmp_path):
        gcode = tmp_path / "test.gcode"
        gcode.write_text("G21 ; mm\n; comment\nG0 X10\n\n")
        lines = load_gcode(gcode)
        assert lines == ["G21", "G0 X10"]


class TestRealTimeCommands:
    def test_query_status(self):
        mock = MockSerial(responses=[b"<Idle|MPos:0.000,0.000,0.000>\r\n"])
        mock._in_waiting = 0
        cfg = SerialConfig()
        streamer = GCodeStreamer(cfg, port=mock)

        status = streamer.query_status()
        assert status.startswith("<Idle")
        assert b"?" in mock.written

    def test_soft_reset(self):
        mock = MockSerial()
        cfg = SerialConfig()
        streamer = GCodeStreamer(cfg, port=mock)

        streamer.soft_reset()
        assert b"\x18" in mock.written
