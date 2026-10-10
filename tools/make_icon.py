"""Program simgesini üretir: 30a.svg, 30a.ico ve 30a-192.png (studio/web/img/).

Simge: programın koyu lacivert zemininde yuvarlak köşeli kare; üstünde turuncu "30A" ve altında krem bir dalga
(üst çubuktaki marka yazısı gibi). Harfler yazı tipiyle değil, kalın çizgilerle çizilir; böylece her bilgisayarda aynı
görünür.

Housing Atlas'taki `tools/make_icon.py`'den uyarlandı. Yalnız standart kütüphane kullanır. Şekiller 256 birimlik bir
tasarım alanında tanımlıdır; SVG bu şekillerden yazılır, PNG'ler her boyut için piksel başına çok örnekle (yumuşatarak)
çizilir. ICO dosyasındaki bütün boyutlar PNG olarak saklanır (Windows Vista ve sonrası).

Kullanım: python tools/make_icon.py [--out KLASÖR]
"""

import argparse
import math
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

DESIGN = 256
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
PNG_SIZE = 192
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "studio" / "web" / "img"

NAVY = "#0E1B26"
ORANGE = "#F5965E"
CREAM = "#E9EEF0"

Point = tuple[float, float]
Box = tuple[float, float, float, float]


def _rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _num(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


@dataclass(frozen=True)
class RoundedRect:
    color: str
    x0: float
    y0: float
    x1: float
    y1: float
    radius: float

    def bbox(self) -> Box:
        return self.x0, self.y0, self.x1, self.y1

    def contains(self, x: float, y: float) -> bool:
        # Köşe dairelerinin merkezlerine kırpılan en yakın noktaya uzaklık.
        cx = min(max(x, self.x0 + self.radius), self.x1 - self.radius)
        cy = min(max(y, self.y0 + self.radius), self.y1 - self.radius)
        return (x - cx) ** 2 + (y - cy) ** 2 <= self.radius**2

    def svg(self) -> str:
        return (f'<rect x="{_num(self.x0)}" y="{_num(self.y0)}" width="{_num(self.x1 - self.x0)}" '
                f'height="{_num(self.y1 - self.y0)}" rx="{_num(self.radius)}" fill="{self.color}"/>')


@dataclass(frozen=True)
class Stroke:
    """Uçları ve dönüşleri yuvarlak, kalın çizgi."""

    color: str
    points: tuple[Point, ...]
    width: float

    def bbox(self) -> Box:
        half = self.width / 2
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return min(xs) - half, min(ys) - half, max(xs) + half, max(ys) + half

    def contains(self, x: float, y: float) -> bool:
        limit = (self.width / 2) ** 2
        return any(_segment_distance_sq(x, y, a, b) <= limit for a, b in zip(self.points, self.points[1:]))

    def svg(self) -> str:
        points = " ".join(f"{_num(x)},{_num(y)}" for x, y in self.points)
        return (f'<polyline points="{points}" fill="none" stroke="{self.color}" stroke-width="{_num(self.width)}" '
                'stroke-linecap="round" stroke-linejoin="round"/>')


Shape = RoundedRect | Stroke
Layer = tuple[Shape, Box, tuple[int, int, int]]


def _segment_distance_sq(x: float, y: float, a: Point, b: Point) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else min(max(((x - ax) * dx + (y - ay) * dy) / length, 0.0), 1.0)
    return (x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2


def _arc(cx: float, cy: float, rx: float, ry: float, start: float, end: float, steps: int = 24) -> list[Point]:
    """Elips yayı; açılar derece, 0° sağ, 90° aşağı (ekran koordinatı)."""
    return [(cx + rx * math.cos(math.radians(start + (end - start) * i / steps)),
             cy + ry * math.sin(math.radians(start + (end - start) * i / steps))) for i in range(steps + 1)]


def _wave(x0: float, x1: float, y: float, amplitude: float, waves: float, steps: int = 48) -> list[Point]:
    return [(x0 + (x1 - x0) * i / steps, y - amplitude * math.sin(2 * math.pi * waves * i / steps))
            for i in range(steps + 1)]


WIDTH = 21
TOP, BOTTOM = 66, 162
MIDDLE = (TOP + BOTTOM) / 2
# "3": iki yay; üst yay ortadaki çizgiye bağlanır, alt yay ondan başlar.
THREE = (
    Stroke(ORANGE, tuple(_arc(53, TOP + 23, 22, 23, 200, 450)), WIDTH),
    Stroke(ORANGE, tuple(_arc(54, BOTTOM - 25, 24, 25, 270, 520)), WIDTH),
)
# "0": kapalı elips.
ZERO = (Stroke(ORANGE, tuple(_arc(124, MIDDLE, 23, (BOTTOM - TOP) / 2, 0, 360, 48)), WIDTH),)
# "A": iki eğik çizgi ve yatay çizgi.
A = (
    Stroke(ORANGE, ((172, BOTTOM), (199, TOP), (226, BOTTOM)), WIDTH),
    Stroke(ORANGE, ((183, 130), (215, 130)), WIDTH - 3),
)
LOGO: tuple[Shape, ...] = (
    RoundedRect(NAVY, 0, 0, 256, 256, 56),
    *THREE, *ZERO, *A,
    Stroke(CREAM, tuple(_wave(46, 210, 200, 9, 2)), 15),
)


def render_svg(shapes: tuple[Shape, ...] = LOGO) -> str:
    body = "\n".join(f"  {shape.svg()}" for shape in shapes)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {DESIGN} {DESIGN}" width="{DESIGN}" '
            f'height="{DESIGN}">\n  <title>30A Studio</title>\n{body}\n</svg>\n')


def _samples_for(size: int) -> int:
    """Piksel başına bir kenardaki örnek sayısı; küçük boyutlarda daha çok örnek."""
    return 8 if size <= 48 else 4


def render_rgba(size: int, shapes: tuple[Shape, ...] = LOGO) -> bytes:
    """Şekilleri size×size piksele çizer; satır satır RGBA baytları döndürür."""
    n = _samples_for(size)
    unit = DESIGN / size
    offsets = [(i + 0.5) / n * unit for i in range(n)]
    layers: list[Layer] = [(shape, shape.bbox(), _rgb(shape.color)) for shape in reversed(shapes)]
    out = bytearray()
    for py in range(size):
        rows = [py * unit + o for o in offsets]
        row_layers = [layer for layer in layers if layer[1][1] <= rows[-1] and layer[1][3] >= rows[0]]
        for px in range(size):
            cols = [px * unit + o for o in offsets]
            out += _pixel(row_layers, cols, rows)
    return bytes(out)


def _pixel(layers: list[Layer], cols: list[float], rows: list[float]) -> bytes:
    red = green = blue = hits = 0
    for y in rows:
        for x in cols:
            for shape, (x0, y0, x1, y1), (r, g, b) in layers:
                if x0 <= x <= x1 and y0 <= y <= y1 and shape.contains(x, y):
                    red += r
                    green += g
                    blue += b
                    hits += 1
                    break
    if not hits:
        return b"\x00\x00\x00\x00"
    total = len(cols) * len(rows)
    return bytes((_div(red, hits), _div(green, hits), _div(blue, hits), _div(255 * hits, total)))


def _div(value: int, divisor: int) -> int:
    """Yarımları yukarı yuvarlayan tam sayı bölmesi."""
    return (2 * value + divisor) // (2 * divisor)


def encode_png(size: int, rgba: bytes) -> bytes:
    stride = size * 4
    raw = b"".join(b"\x00" + rgba[row * stride:(row + 1) * stride] for row in range(size))
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", header) + _png_chunk(b"IDAT", zlib.compress(raw, 9))
            + _png_chunk(b"IEND", b""))


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def encode_ico(pngs: dict[int, bytes]) -> bytes:
    """PNG girdilerinden ICO dosyası (ICONDIR + ICONDIRENTRY'ler + PNG verileri)."""
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = len(header) + 16 * len(pngs)
    entries = bytearray()
    for size, data in pngs.items():
        dim = 0 if size >= 256 else size  # 256 piksel ICO'da 0 olarak yazılır
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return header + bytes(entries) + b"".join(pngs.values())


def build(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pngs = {size: encode_png(size, render_rgba(size)) for size in ICO_SIZES}
    files = {
        out_dir / "30a.svg": render_svg().encode("utf-8"),
        out_dir / "30a.ico": encode_ico(pngs),
        out_dir / f"30a-{PNG_SIZE}.png": encode_png(PNG_SIZE, render_rgba(PNG_SIZE)),
    }
    for path, data in files.items():
        path.write_bytes(data)
    return list(files)


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass
    parser = argparse.ArgumentParser(description="Program simgesini üretir.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="çıktı klasörü")
    args = parser.parse_args(argv)
    for path in build(args.out):
        print(f"Yazıldı: {path}")


if __name__ == "__main__":
    main()
