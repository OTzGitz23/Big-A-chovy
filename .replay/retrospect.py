"""Summarize screening reports for a retrospective: per-date pool/intersection stats."""
import os
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "筛选结果")
)

# Collect report paths per date
per_date = defaultdict(list)
for dirpath, _dirs, files in os.walk(ROOT):
    for name in files:
        if not name.endswith(".md"):
            continue
        m = re.search(r"(\d{8})_(\d{4})", name)
        if not m:
            continue
        per_date[m.group(1)].append((m.group(2), os.path.join(dirpath, name)))


def grab(text, pattern):
    m = re.search(pattern, text)
    return m.group(1) if m else None


print(f"{'日期':<10} {'份数':>4} {'首份':>5} {'末份':>5} "
      f"{'早涨/跌':>12} {'末涨/跌':>12} {'末涨停/跌停':>12} "
      f"{'超短':>4} {'确认':>4} {'交集':>4} {'可开仓':>5}")
print("-" * 110)

for date in sorted(per_date):
    items = sorted(per_date[date])
    first_t, first_p = items[0]
    last_t, last_p = items[-1]
    with open(first_p, encoding="utf-8") as fh:
        first_txt = fh.read()
    with open(last_p, encoding="utf-8") as fh:
        last_txt = fh.read()

    def breadth(txt):
        m = re.search(r"上涨 (\d+) / 下跌 (\d+)", txt)
        if not m:
            return "?"
        lim = re.search(r"涨停 (\d+)，跌停 (\d+)", txt)
        lim_s = f"{lim.group(1)}/{lim.group(2)}" if lim else "?"
        return f"{m.group(1)}/{m.group(2)}", lim_s

    fb = breadth(first_txt)
    lb = breadth(last_txt)
    pool = re.search(r"超短池 (\d+) 只；.*?趋势确认池 (\d+) 只；交集 (\d+) 只", last_txt)
    openable = re.search(r"可新开仓 (\d+) 只", last_txt)
    short = pool.group(1) if pool else "?"
    conf = pool.group(2) if pool else "?"
    inter = pool.group(3) if pool else "?"
    op = openable.group(1) if openable else "?"

    fb_s = fb[0] if isinstance(fb, tuple) else "?"
    lb_s, lb_lim = lb if isinstance(lb, tuple) else ("?", "?")
    print(f"{date:<10} {len(items):>4} {first_t:>5} {last_t:>5} "
          f"{fb_s:>12} {lb_s:>12} {lb_lim:>12} "
          f"{short:>4} {conf:>4} {inter:>4} {op:>5}")

# Any report with openable > 0?
print()
print("=== 全天任一报告出现「可新开仓 > 0」的日期 ===")
found = False
for date in sorted(per_date):
    hits = []
    for t, path in sorted(per_date[date]):
        with open(path, encoding="utf-8") as fh:
            txt = fh.read()
        m = re.search(r"可新开仓 (\d+) 只", txt)
        if m and int(m.group(1)) > 0:
            hits.append(f"{t}({m.group(1)})")
    if hits:
        found = True
        print(f"  {date}: {', '.join(hits)}")
if not found:
    print("  无 —— 所有日期、所有报告的可开仓数均为 0")

# Intersection detail across dates
print()
print("=== 各日交集标的(去重) ===")
for date in sorted(per_date):
    names = defaultdict(int)
    for _t, path in per_date[date]:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        in_sec = False
        for ln in lines:
            if ln.startswith("## 双池交集"):
                in_sec = True
                continue
            if in_sec and ln.startswith("## "):
                break
            if in_sec and re.match(r"^\|\s*\d{6}\s*\|", ln):
                parts = [p.strip() for p in ln.strip("|").split("|")]
                if len(parts) > 2:
                    names[f"{parts[0]} {parts[1]}"] += 1
    if names:
        top = sorted(names.items(), key=lambda kv: -kv[1])
        print(f"  {date}: " + "; ".join(f"{k}({v}份)" for k, v in top))
    else:
        print(f"  {date}: 无交集")
