import tempfile
import unittest
from pathlib import Path
import subprocess
import struct
import zlib


ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = ROOT / "scripts" / "check_screenshot_regression.py"


def write_png(path: Path, width: int, height: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    row = b"\x00" + (b"\x00\x00\x00" * width)
    raw = row * height
    compressed = zlib.compress(raw)
    idat = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF)
    iend = struct.pack(">I", 0) + b"IEND" + b"" + struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    path.write_bytes(signature + ihdr + idat + iend)


class ScreenshotRegressionCheckTests(unittest.TestCase):
    def test_pass_with_before_after_pair_and_same_size(self):
        temp_root = Path(tempfile.mkdtemp(prefix="screen-check-pass-"))
        target = temp_root / "screenshots" / "20260303" / "leaderboard"
        write_png(target / "20260303-leaderboard-trend-before-v01.png", 300, 200)
        write_png(target / "20260303-leaderboard-trend-after-v01.png", 300, 200)

        result = subprocess.run(
            ["python3", str(CHECK_SCRIPT), str(temp_root / "screenshots")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr + result.stdout)

    def test_fail_when_missing_after(self):
        temp_root = Path(tempfile.mkdtemp(prefix="screen-check-missing-"))
        target = temp_root / "screenshots" / "20260303" / "leaderboard"
        write_png(target / "20260303-leaderboard-trend-before-v01.png", 300, 200)

        result = subprocess.run(
            ["python3", str(CHECK_SCRIPT), str(temp_root / "screenshots")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing pair", result.stderr.lower())

    def test_fail_when_size_mismatch(self):
        temp_root = Path(tempfile.mkdtemp(prefix="screen-check-size-"))
        target = temp_root / "screenshots" / "20260303" / "leaderboard"
        write_png(target / "20260303-leaderboard-trend-before-v01.png", 300, 200)
        write_png(target / "20260303-leaderboard-trend-after-v01.png", 320, 200)

        result = subprocess.run(
            ["python3", str(CHECK_SCRIPT), str(temp_root / "screenshots")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dimension mismatch", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
