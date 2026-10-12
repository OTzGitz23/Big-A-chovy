"""Seres (601127): longer history + relaxed variants of 'gap up / fade from high'.

Rationale: the exact pattern (>+5% intraday, closed below open) had only ONE
instance in 1.7y. Relax the definition to get a usable sample:
  V1 exact   : intraday high >= +5%, close < open
  V2 gap-up  : open gap >= +3%, close < open
  V3 big fade: intraday high >= +4%, fade from high <= -4% (gave back a lot)
  V4 intraday spike >+5% regardless of close
And report T+1 for each.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                "daily-stock-analysis", "scripts")))
import tencent_kline  # noqa: E402

LIMIT = 2000


def bars(code, limit=LIMIT):
    payload, host = tencent_kline.fetch_kline_json(code, limit, timeout=25)
    rows = tencent_kline.kline_rows(payload, code)
    return [{"date": r[0], "open": float(r[1]), "close": float(r[2]),
             "high": float(r[3]), "low": float(r[4])} for r in rows], host


data, host = bars("sh601127")
print(f"数据源: {host}")
print(f"样本 {len(data)} 根日K:{data[0]['date']} → {data[-1]['date']}")

for i in range(1, len(data)):
    b = data[i]
    prev = data[i - 1]["close"]
    b["open_gap"] = b["open"] / prev - 1
    b["intraday_gain"] = b["high"] / prev - 1
    b["close_ret"] = b["close"] / prev - 1
    b["fade"] = b["close"] / b["high"] - 1


def report(title, idxs):
    print()
    print(f"=== {title} —— {len(idxs)} 次 ===")
    if not idxs:
        print("   无")
        return
    t1s, lows, highs, gaps = [], [], [], []
    for i in idxs:
        t, n = data[i], data[i + 1]
        t1s.append(n["close"] / t["close"] - 1)
        gaps.append(n["open"] / t["close"] - 1)
        lows.append(n["low"] / t["close"] - 1)
        highs.append(n["high"] / t["close"] - 1)
    n_ = len(idxs)
    wins = sum(1 for x in t1s if x > 0)
    print(f"   T+1 收盘: 平均 {sum(t1s) / n_ * 100:+.2f}%  中位 {sorted(t1s)[n_ // 2] * 100:+.2f}%  "
          f"[{min(t1s) * 100:+.1f}% ~ {max(t1s) * 100:+.1f}%]")
    print(f"   T+1 开盘缺口: 平均 {sum(gaps) / n_ * 100:+.2f}%   低开 {sum(1 for g in gaps if g < 0)}/{n_}")
    print(f"   T+1 胜率(收阳): {wins}/{n_} = {wins / n_ * 100:.0f}%")
    print(f"   T+1 盘中低: 平均 {sum(lows) / n_ * 100:+.2f}%   跌破-3.5%: {sum(1 for x in lows if x <= -0.035)}/{n_}")
    print(f"   T+1 盘中高: 平均 {sum(highs) / n_ * 100:+.2f}%   摸到+2%: {sum(1 for x in highs if x >= 0.02)}/{n_}")
    dates = [data[i]["date"] for i in idxs]
    print("   日期: " + ", ".join(dates[:14]) + (" ..." if n_ > 14 else ""))


report("V1 盘中涨≥+5% 且 收盘<开盘",
       [i for i in range(1, len(data) - 1)
        if data[i]["intraday_gain"] >= 0.05 and data[i]["close"] < data[i]["open"]])

report("V2 高开≥+3% 且 收盘<开盘(高开低走)",
       [i for i in range(1, len(data) - 1)
        if data[i]["open_gap"] >= 0.03 and data[i]["close"] < data[i]["open"]])

report("V3 盘中涨≥+4% 且 从高点回落≥4%",
       [i for i in range(1, len(data) - 1)
        if data[i]["intraday_gain"] >= 0.04 and data[i]["fade"] <= -0.04])

report("V4 盘中涨≥+5%(不论收盘)",
       [i for i in range(1, len(data) - 1) if data[i]["intraday_gain"] >= 0.05])

report("V5 高开≥+5%(跳空)",
       [i for i in range(1, len(data) - 1) if data[i]["open_gap"] >= 0.05])
