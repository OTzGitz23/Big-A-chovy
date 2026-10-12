"""Seres (601127): days that ran >5% intraday but closed well off the high.

Focus: 'opened strong / spiked >+5% then fell back' days, and what T+1 did.

Definitions used (all vs previous close):
  intraday_gain = high/prev_close - 1        # how far up it got
  close_ret     = close/prev_close - 1       # where it ended
  fade          = close/high - 1             # how much it gave back from the high
  open_gap      = open/prev_close - 1
Also flags the specific variant: opened >+5% but closed lower.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                "daily-stock-analysis", "scripts")))
import tencent_kline  # noqa: E402


def bars(code, limit=420):
    payload, host = tencent_kline.fetch_kline_json(code, limit, timeout=20)
    rows = tencent_kline.kline_rows(payload, code)
    return [{"date": r[0], "open": float(r[1]), "close": float(r[2]),
             "high": float(r[3]), "low": float(r[4])} for r in rows], host


data, host = bars("sh601127")
print(f"数据源: {host}   样本 {len(data)} 根:{data[0]['date']} → {data[-1]['date']}")

for i in range(1, len(data)):
    prev = data[i - 1]["close"]
    b = data[i]
    b["prev"] = prev
    b["open_gap"] = b["open"] / prev - 1
    b["intraday_gain"] = b["high"] / prev - 1
    b["close_ret"] = b["close"] / prev - 1
    b["fade"] = b["close"] / b["high"] - 1

# --- Pattern A: intraday gain >5% AND faded from the high (close below open)
A = [i for i in range(1, len(data) - 1)
     if data[i]["intraday_gain"] > 0.05 and data[i]["close"] < data[i]["open"]]

# --- Pattern B stricter: intraday gain >5% AND close_ret < 0 (ended red)
B = [i for i in range(1, len(data) - 1)
     if data[i]["intraday_gain"] > 0.05 and data[i]["close_ret"] < 0]

# --- Pattern C: OPENED >+5% (gap up) then fell back below open
C = [i for i in range(1, len(data) - 1)
     if data[i]["open_gap"] > 0.05 and data[i]["close"] < data[i]["open"]]


def show(title, idxs, note):
    print()
    print(f"=== {title} —— 共 {len(idxs)} 次 ===")
    if note:
        print(f"   ({note})")
    if not idxs:
        print("   无")
        return []
    print(f"{'T日':<12}{'开盘缺口':>9}{'盘中最高':>9}{'T涨幅':>8}{'从高点回落':>11}"
          f"{'T+1开':>9}{'T+1收':>9}{'T+1涨幅':>9}{'T+1盘中低':>10}")
    print("-" * 100)
    rows = []
    for i in idxs:
        t, n = data[i], data[i + 1]
        t1 = n["close"] / t["close"] - 1
        t1_gap = n["open"] / t["close"] - 1
        t1_low = n["low"] / t["close"] - 1
        t1_high = n["high"] / t["close"] - 1
        rows.append((t["date"], t["open_gap"], t["intraday_gain"], t["close_ret"],
                     t["fade"], t1_gap, t1, t1_low, t1_high))
        print(f"{t['date']:<12}{t['open_gap'] * 100:>+8.2f}%{t['intraday_gain'] * 100:>+8.2f}%"
              f"{t['close_ret'] * 100:>+7.2f}%{t['fade'] * 100:>+10.2f}%"
              f"{t1_gap * 100:>+8.2f}%{t1 * 100:>+8.2f}%{t1_low * 100:>+9.2f}%"
              f"{t1_high * 100:>+9.2f}%")

    n_ = len(rows)
    t1s = [r[6] for r in rows]
    lows = [r[7] for r in rows]
    highs = [r[8] for r in rows]
    wins = sum(1 for x in t1s if x > 0)
    print(f"\n   T+1 收盘涨幅: 平均 {sum(t1s) / n_ * 100:+.2f}%  中位 {sorted(t1s)[n_ // 2] * 100:+.2f}%  "
          f"最好 {max(t1s) * 100:+.2f}%  最差 {min(t1s) * 100:+.2f}%")
    print(f"   T+1 收阳/收阴: {wins}/{n_ - wins}  (胜率 {wins / n_ * 100:.0f}%)")
    print(f"   T+1 盘中最低: 平均 {sum(lows) / n_ * 100:+.2f}%   曾跌破-3.5%: "
          f"{sum(1 for r in rows if r[7] <= -0.035)}/{n_}")
    print(f"   T+1 盘中最高: 平均 {sum(highs) / n_ * 100:+.2f}%   曾摸到+2%: "
          f"{sum(1 for r in rows if r[8] >= 0.02)}/{n_}")
    return rows


show("A 形态:盘中曾涨超+5%,且收盘低于开盘(冲高回落)", A,
     "对应用户描述:盘中有大涨、收盘回落")
show("B 形态:盘中曾涨超+5%,且当日收盘为跌(收阴)", B, "更严格的'冲高回落'")
show("C 形态:开盘即涨超+5%(跳空高开)后回落收低", C, "若你指的是'开盘就涨5%以上'")
