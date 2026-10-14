"""Static (keep the first route, wait) vs dynamic (replan) on the same scenario set.

Usage: python scripts/compare_sim.py [map_id ...] [--markdown]
Both policies see the same zone schedule, speed and start. Units are map units and simulated seconds.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.planner import load_maps  # noqa: E402
from app.simulator import compare_policies  # noqa: E402


def main() -> None:
    wanted = [a for a in sys.argv[1:] if not a.startswith("--")]
    for map_id, wmap in load_maps().items():
        if wanted and map_id not in wanted:
            continue
        print(f"## {wmap.data['name']} ({map_id})")
        report(wmap)
        print()


def report(wmap) -> None:
    scenarios = json.loads((ROOT / "config" / "scenarios.json").read_text())["scenarios"]
    result = compare_policies(wmap, scenarios)
    header = ("scenario", "static s", "dynamic s", "static wait s", "dynamic wait s",
              "static dist", "dynamic dist", "faster")
    rows = [(r["name"], r["static"]["makespan_s"], r["dynamic"]["makespan_s"], r["static"]["waiting_s"],
             r["dynamic"]["waiting_s"], r["static"]["distance"], r["dynamic"]["distance"], r["faster"])
            for r in result["rows"]]
    if "--markdown" in sys.argv:
        print("| " + " | ".join(header) + " |")
        print("|" + "---|" * len(header))
        for r in rows:
            print("| " + " | ".join(str(v) for v in r) + " |")
    else:
        for r in [header, *rows]:
            print("  ".join(str(v).ljust(40 if i == 0 else 14) for i, v in enumerate(r)))
    totals = result["total_makespan_s"]
    print()
    print(f"Total makespan over {len(rows)} scenarios: "
          f"static {totals['static']} s, dynamic {totals['dynamic']} s (simulated)")


if __name__ == "__main__":
    main()
