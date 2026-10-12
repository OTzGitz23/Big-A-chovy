"""Seres (601127): what happens on T+1 after a day that gained >5%?

Uses Tencent's forward-adjusted (前复权) daily klines, matching what the
screening report itself uses.
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                "daily-stock-analysis", "scripts")))
import tencent_kline  # noqa: E402

LIMIT = 400  # enough daily bars to cover many months


def bars(code, limit=LIMIT):
    payload, host = tencent_kline.fetch_kline_json(code, limit, timeout=20)
    rows = tencent_kline.kline_rows(payload, code)
    out = []
    for r in rows:
        out.append({
            "date": r[0],
            "open": float(r[1]),
            "close": float(r[2]),
            "high": float(r[3]),
            "low": float(r[4]),
        })
    return out, host


data, host = bars("sh601127")
print(f"数据源: {host}")
print(f"拿到 {len(data)} 根日K:{data[0]['date']} → {data[-1]['date']}")

for b in data:
    b["chg"] = None
for i in range(1, len(data)):
    prev = data[i - 1]["close"]
    if prev:
        data[i]["chg"] = data[i]["close"] / prev - 1

# T days with >5% gain, that have a T+1 bar available
events = []
for i in range(1, len(data) - 1):
    c = data[i]["chg"]
    if c is not None and c > 0.05:
        events.append(i)

print()
print(f"=== 收盘涨幅 >5% 的交易日:{len(events)} 次 ===")
print(f"{'T日':<12}{'T涨幅':>8}{'T收':>8}{'T+1开':>8}{'T+1高':>8}{'T+1低':>8}"
      f"{'T+1收':>8}{'T+1涨幅':>9}{'开盘缺口':>9}{'最高':>8}{'最低':>8}")
print("-" * 110)

rows = []
for i in events:
    t, n = data[i], data[i + 1]
    t1_chg = n["close"] / t["close"] - 1
    gap = n["open"] / t["close"] - 1
    hi = n["high"] / t["close"] - 1
    lo = n["low"] / t["close"] - 1
    rows.append((t["date"], t["chg"], t["close"], n["open"], n["high"], n["low"],
                 n["close"], t1_chg, gap, hi, lo))
    print(f"{t['date']:<12}{t['chg'] * 100:>+7.2f}%{t['close']:>8.2f}{n['open']:>8.2f}"
          f"{n['high']:>8.2f}{n['low']:>8.2f}{n['close']:>8.2f}"
          f"{t1_chg * 100:>+8.2f}%{gap * 100:>+8.2f}%{hi * 100:>+7.2f}%{lo * 100:>+7.2f}%")

if rows:
    n = len(rows)
    print()
    print(f"=== 统计(T日涨>5% 共 {n} 次) ===")
    t1 = [r[7] for r in rows]
    gaps = [r[8] for r in rows]
    his = [r[9] for r in rows]
    los = [r[10] for r in rows]
    wins = sum(1 for x in t1 if x > 0)
    print(f"  T+1 收盘涨跌:  平均 {sum(t1) / n * 100:+.2f}%   "
          f"中位 {sorted(t1)[n // 2] * 100:+.2f}%   "
          f"最好 {max(t1) * 100:+.2f}%   最差 {min(t1) * 100:+.2f}%")
    print(f"  T+1 开盘缺口:  平均 {sum(gaps) / n * 100:+.2f}%   "
          f"中位 {sorted(gaps)[n // 2] * 100:+.2f}%")
    print(f"  T+1 盘中最高:  平均 {sum(his) / n * 100:+.2f}%   "
          f"(相对 T 日收盘)")
    print(f"  T+1 盘中最低:  平均 {sum(los) / n * 100:+.2f}%")
    print(f"  T+1 收阳 {wins} / 收阴 {n - wins}  (胜率 {wins / n * 100:.0f}%)")
    # framework-relevant: could +2% be reached, was -3.5% hit first?
    tp = sum(1 for r in rows if r[9] >= 0.02)
    sl = sum(1 for r in rows if r[10] <= -0.035)
    print(f"  T+1 盘中曾摸到 +2%: {tp}/{n}   曾跌破 -3.5%: {sl}/{n}")
    both = sum(1 for r in rows if r[9] >= 0.02 and r[10] <= -0.035)
    print(f"  同日两者都触及(顺序未知): {both}")
