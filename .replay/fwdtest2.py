"""Most favourable estimate for the framework's +2% take-profit: did each day's
HIGH ever reach entry*1.02, and each day's LOW ever reach entry*0.965?

Using daily high/low is optimistic in the rule's favour: it assumes the order was
filled at the exact extreme. If even this generous test fails to find wins, the
'no position' outcome is robust.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                "daily-stock-analysis", "scripts")))
import tencent_kline  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "筛选结果"))
TP, SL, FEE = 0.02, 0.035, 0.004

CANDIDATES = [
    ("20260922", "600506", "统一股份"),
    ("20260922", "002093", "国脉科技"),
    ("20260923", "000555", "神州信息"),
    ("20260928", "002093", "国脉科技"),
    ("20260929", "002439", "启明星辰"),
    ("20260929", "002232", "启明信息"),
    ("20260930", "002303", "美盈森"),
    ("20260930", "003006", "百亚股份"),
]


def intersection_prices(date, code):
    out = []
    for dirpath, _d, files in os.walk(ROOT):
        for name in sorted(files):
            if not name.endswith(".md") or date not in name:
                continue
            lines = open(os.path.join(dirpath, name), encoding="utf-8").read().splitlines()
            in_sec = False
            for ln in lines:
                if ln.startswith("## 双池交集"):
                    in_sec = True
                    continue
                if in_sec and ln.startswith("## "):
                    break
                if in_sec and re.match(r"^\|\s*" + re.escape(code) + r"\s*\|", ln):
                    parts = [p.strip() for p in ln.strip("|").split("|")]
                    if len(parts) > 2:
                        try:
                            out.append(float(parts[2]))
                        except ValueError:
                            pass
    return out


def klines(code, limit=60):
    prefix = "sh" if code.startswith(("6", "5")) else "sz"
    payload, _h = tencent_kline.fetch_kline_json(prefix + code, limit, timeout=15)
    rows = tencent_kline.kline_rows(payload, prefix + code)
    return [(r[0].replace("-", ""), float(r[1]), float(r[2]), float(r[3]), float(r[4]))
            for r in rows]


print("最有利估计:用「日最高/最低」判断 ±阈值是否曾触及(假设成交在极值点)")
print("仍遵守 T+1 约束:买入当日不可卖,出场从 T+1 开始\n")
print(f"{'日期':<10}{'标的':<13}{'买入价':>8}{'T+1高':>8}{'T+1低':>8}"
      f"{'触+2%':>8}{'触-3.5%':>9}{'结果':>16}")
print("-" * 88)

rows = []
for date, code, name in CANDIDATES:
    prices = intersection_prices(date, code)
    if not prices:
        print(f"{date:<10}{name:<13}{'无交集价':>8}")
        continue
    entry = prices[0]
    ks = klines(code)
    dates = [k[0] for k in ks]
    idx = dates.index(date) if date in dates else None
    if idx is None:
        print(f"{date:<10}{name:<13}{entry:>8.2f}   K线无该日")
        continue

    tp_hit = sl_hit = None
    for k in range(idx + 1, len(ks)):
        _d, _o, _c, high, low = ks[k]
        if tp_hit is None and high >= entry * (1 + TP):
            tp_hit = k
        if sl_hit is None and low <= entry * (1 - SL):
            sl_hit = k
        # whichever extreme came first is ambiguous intraday; assume TP first if both same day
        if tp_hit or sl_hit:
            break

    if tp_hit and (sl_hit is None or tp_hit <= sl_hit):
        res, ret = f"止盈 +2% (T+{tp_hit - idx})", TP
    elif sl_hit:
        res, ret = f"止损 -3.5% (T+{sl_hit - idx})", -SL
    else:
        # neither extreme reached within the window -> framework T+1 09:45 exit
        k = idx + 1
        if k < len(ks):
            ret = ks[k][2] / entry - 1
            res = f"T+1 收盘退出"
        else:
            continue

    t1h = ks[idx + 1][3] / entry - 1 if idx + 1 < len(ks) else None
    t1l = ks[idx + 1][4] / entry - 1 if idx + 1 < len(ks) else None
    rows.append((date, name, ret))
    print(f"{date:<10}{name:<13}{entry:>8.2f}"
          f"{t1h * 100:>+7.1f}%{t1l * 100:>+7.1f}%"
          f"{'是' if tp_hit else '否':>8}{'是' if sl_hit else '否':>9}{res:>16}")

print()
gross = sum(r for _d, _n, r in rows)
n = len(rows)
print(f"=== 最有利估计汇总({n} 笔) ===")
print(f"  毛收益合计 {gross * 100:+.1f}%   平均 {gross / n * 100:+.1f}%/笔")
print(f"  净收益合计 {(gross - FEE * n) * 100:+.1f}%   平均 {(gross / n - FEE) * 100:+.1f}%/笔")
print(f"  盈利 {sum(1 for _d, _n, r in rows if r > FEE)} / 亏损 {sum(1 for _d, _n, r in rows if r <= FEE)}")
