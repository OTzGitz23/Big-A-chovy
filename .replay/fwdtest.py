"""For each trading day, take the strongest intersection candidate and compute the
forward outcome under the framework's own exit rules (+2% gross TP / -3.5% SL / T+1).

Answers: was staying flat reasonable, or did it miss real upside?
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                "daily-stock-analysis", "scripts")))
import tencent_kline  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "筛选结果"))
TP = 0.02
SL = 0.035
FEE = 0.004  # round-trip commission+slippage estimate on a small position

CANDIDATES = [
    ("20260922", "600506", "统一股份"),
    ("20260922", "002093", "国脉科技"),
    ("20260923", "000555", "神州信息"),
    ("20260928", "002093", "国脉科技"),
    ("20260929", "002439", "启明星辰"),
    ("20260929", "002232", "启明信息"),
    ("20260930", "002303", "美盈森"),
    ("20260930", "003006", "百亚股份"),
    ("20261008", "002639", "雪人集团"),
    ("20261009", "002029", "七 匹 狼"),
]


def reports_for(date):
    out = []
    for dirpath, _d, files in os.walk(ROOT):
        for name in sorted(files):
            if name.endswith(".md") and date in name:
                out.append(os.path.join(dirpath, name))
    return sorted(out, key=lambda p: re.search(r"_(\d{4})", os.path.basename(p)).group(1)
                  if re.search(r"_(\d{4})", os.path.basename(p)) else "")


def intersection_prices(date, code):
    """All 'current price' values recorded while the code was in the intersection pool."""
    prices = []
    for path in reports_for(date):
        lines = open(path, encoding="utf-8").read().splitlines()
        in_sec = False
        for ln in lines:
            if ln.startswith("## 双池交集"):
                in_sec = True
                continue
            if in_sec and ln.startswith("## "):
                break
            if not in_sec:
                continue
            if re.match(r"^\|\s*" + re.escape(code) + r"\s*\|", ln):
                parts = [p.strip() for p in ln.strip("|").split("|")]
                if len(parts) > 2:
                    try:
                        prices.append(float(parts[2]))
                    except ValueError:
                        pass
    return prices


def klines(code, limit=60):
    prefix = "sh" if code.startswith(("6", "5")) else "sz"
    payload, _h = tencent_kline.fetch_kline_json(prefix + code, limit, timeout=15)
    rows = tencent_kline.kline_rows(payload, prefix + code)
    return [(r[0].replace("-", ""), float(r[1]), float(r[2]), float(r[3]), float(r[4]))
            for r in rows]


def simulate(date, code, name):
    prices = intersection_prices(date, code)
    if not prices:
        return None
    entry = prices[0]
    try:
        ks = klines(code)
    except Exception as exc:
        return f"{date} {name:<12} 取K线失败: {exc}"

    dates = [k[0] for k in ks]
    idx = dates.index(date) if date in dates else None
    if idx is None:
        return f"{date} {name:<12} K线中无该交易日"

    # Exit plan: first close (from T+1 onward) that hits TP or SL wins;
    # otherwise the framework forces exit at T+1 09:45 -> approximate with T+1 close.
    exit_kind, exit_k, exit_ret = None, None, None
    for k in range(idx + 1, len(ks)):
        close = ks[k][2]
        high, low = ks[k][3], ks[k][4]
        # intraday TP/SL check is ambiguous without minute data; use closes conservatively
        ret = close / entry - 1
        if ret >= TP:
            exit_kind, exit_k, exit_ret = "TP", k, TP
            break
        if ret <= -SL:
            exit_kind, exit_k, exit_ret = "SL", k, -SL
            break
    if exit_kind is None:
        if idx + 1 < len(ks):
            exit_kind, exit_k = "T+1close", idx + 1
            exit_ret = ks[idx + 1][2] / entry - 1
        else:
            return f"{date} {name:<12} 数据不足(T+1 未到)"

    t1 = ks[idx + 1][2] / entry - 1 if idx + 1 < len(ks) else None
    latest = ks[-1][2] / entry - 1
    return {
        "date": date, "name": name, "code": code, "entry": entry,
        "t1": t1, "latest": latest,
        "kind": exit_kind, "k": exit_k - idx, "ret": exit_ret,
    }


print("框架退出规则前向模拟:+2% 毛止盈 / −3.5% 止损 / T+1 后按收盘判定")
print("(只评估「当日最强交集」若在交集价买入的后续表现,非实际交易)\n")
print(f"{'日期':<10}{'标的':<13}{'买入价':>8}{'T+1':>9}{'最新':>9}"
      f"{'触发出场':>12}{'毛收益':>9}{'净收益':>9}")
print("-" * 82)

rows = []
for date, code, name in CANDIDATES:
    r = simulate(date, code, name)
    if r is None:
        print(f"{date:<10}{name:<13}{'当日无交集价':>8}")
        continue
    if isinstance(r, str):
        print(r)
        continue
    rows.append(r)
    t1 = f"{r['t1'] * 100:+.1f}%" if r["t1"] is not None else "-"
    net = r["ret"] - FEE
    print(f"{r['date']:<10}{r['name']:<13}{r['entry']:>8.2f}{t1:>9}"
          f"{r['latest'] * 100:>+8.1f}%{r['kind'] + ' T+' + str(r['k']):>12}"
          f"{r['ret'] * 100:>+8.1f}%{net * 100:>+8.1f}%")

print()
if rows:
    gross = sum(r["ret"] for r in rows)
    net = sum(r["ret"] - FEE for r in rows)
    n = len(rows)
    wins = sum(1 for r in rows if r["ret"] > FEE)
    print(f"=== 汇总({n} 个可评估样本,按每笔 1/4 仓位上限计) ===")
    print(f"  毛收益合计 {gross * 100:+.1f}%,平均 {gross / n * 100:+.1f}%/笔")
    print(f"  净收益合计 {net * 100:+.1f}%,平均 {net / n * 100:+.1f}%/笔")
    print(f"  盈利笔数 {wins} / 亏损 {n - wins}")
    print(f"  出场分布: " + ", ".join(
        f"{k}×{sum(1 for r in rows if r['kind'] == k)}"
        for k in sorted({r["kind"] for r in rows})))
