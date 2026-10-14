"""Write docs/tabletop_<map id>.svg for every use case: the paper floor that matches the 3D view.

Print as large as you can. The numbered corner squares are the four calibration clicks, in order.
All maps share one footprint, so swapping the sheet under a fixed camera needs no recalibration
as long as the corner squares land in the same place.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.planner import load_maps  # noqa: E402

PAD = 4
LIME = "#bfd732"


def render(m: dict) -> str:
    W, H = m["width"], m["height"]
    nodes = {n["id"]: n for n in m["nodes"]}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-PAD} {-PAD - 5} {W + 2 * PAD} {H + 2 * PAD + 5}" '
        f'width="{(W + 2 * PAD) * 2.5}mm" height="{(H + 2 * PAD + 5) * 2.5}mm" font-family="Arial, sans-serif">',
        f'<rect x="{-PAD}" y="{-PAD - 5}" width="{W + 2 * PAD}" height="{H + 2 * PAD + 5}" fill="white"/>',
        f'<text x="0" y="-4.5" font-size="3.2" font-weight="bold">FlowTwin: {m["name"]}</text>',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="none" stroke="black" stroke-width="0.4"/>',
    ]
    for s in m["structures"]:  # printed flat and pale so the detector does not mistake them for props
        parts.append(f'<rect x="{s["x"] - s["w"] / 2}" y="{s["y"] - s["d"] / 2}" width="{s["w"]}" height="{s["d"]}" '
                     f'fill="#e6e6e6"/>')
        if s.get("label"):
            parts.append(f'<text x="{s["x"]}" y="{s["y"] + 0.8}" font-size="1.9" text-anchor="middle" '
                         f'fill="#666666">{s["label"]}</text>')
    for e in m["edges"]:
        a, b = nodes[e["a"]], nodes[e["b"]]
        parts.append(f'<line x1="{a["x"]}" y1="{a["y"]}" x2="{b["x"]}" y2="{b["y"]}" stroke="#bbbbbb" '
                     f'stroke-width="3.4" stroke-linecap="round"/>')
    for z in m["zones"]:
        points = " ".join(f"{x},{y}" for x, y in z["polygon"])
        x0, y0 = z["polygon"][0]
        parts.append(f'<polygon points="{points}" fill="none" stroke="{LIME}" stroke-width="0.6" '
                     f'stroke-dasharray="1.5 1"/>')
        parts.append(f'<text x="{x0 + 1}" y="{y0 - 0.8}" font-size="2.4" font-weight="bold">{z["label"]}</text>')
    for n in m["nodes"]:
        parts.append(f'<circle cx="{n["x"]}" cy="{n["y"]}" r="2" fill="white" stroke="black" stroke-width="0.3"/>')
        if n["kind"] != "aisle":
            parts.append(f'<text x="{n["x"]}" y="{n["y"] + 5}" font-size="2.2" text-anchor="middle">{n["label"]}</text>')
    for i, (x, y) in enumerate([(0, 0), (W, 0), (W, H), (0, H)], start=1):
        parts.append(f'<rect x="{x - 1.5}" y="{y - 1.5}" width="3" height="3" fill="black"/>')
        dx, dy = (4 if x == 0 else -4), (5 if y == 0 else -3)
        parts.append(f'<text x="{x + dx}" y="{y + dy}" font-size="2.6" font-weight="bold" '
                     f'text-anchor="middle">{i}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    out_dir = ROOT / "docs"
    out_dir.mkdir(exist_ok=True)
    for map_id, wmap in load_maps().items():
        out = out_dir / f"tabletop_{map_id}.svg"
        out.write_text(render(wmap.data), encoding="utf-8")
        print("wrote", out)


if __name__ == "__main__":
    main()
