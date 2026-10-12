"""Backtest: sell on a 'spike >+5% then fade' day, rebuy N days later.
Compare against simply holding. Seres (601127).

Trigger variants:
  S1  intraday high >= +5% and close < open        (yesterday's shape)
  S2  intraday high >= +5% and fade from high >= 4%
  S3  intraday gain >= +5% (any close)
Buy-back horizons N in {1,2,3,5,10}.
Costs: 0.4% round-trip per sell+rebuy cycle.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                "daily-stock-analysis", "scripts")))
import tencent_kline  # noqa: E402

FEE = 0.004  # round trip on the sell+rebuy pair


def bars(code, limit=2000):
    payload, host = tencent_kline.fetch_kline_json(code, limit, timeout=25)
    rows = tencent_kline.kline_rows(payload, code)
    return [{"date": r[0], "open": float(r[1]), "close": float(r[2]),
             "high": float(r[3]), "low": float(r[4])} for r in rows], host


data, host = bars("sh601127")
print(f"数据源: {host}   样本 {len(data)} 根:{data[0]['date']} → {data[-1]['date']}\n")

for i in range(1, len(data)):
    b = data[i]
    prev = data[i - 1]["close"]
    b["open_gap"] = b["open"] / prev - 1
    b["intraday_gain"] = b["high"] / prev - 1
    b["close_ret"] = b["close"] / prev - 1
    b["fade"] = b["close"] / b["high"] - 1


def triggers(kind):
    idx = []
    for i in range(1, len(data) - 1):
        b = data[i]
        if kind == "S1" and b["intraday_gain"] >= 0.05 and b["close"] < b["open"]:
            idx.append(i)
        elif kind == "S2" and b["intraday_gain"] >= 0.05 and b["fade"] <= -0.04:
            idx.append(i)
        elif kind == "S3" and b["intraday_gain"] >= 0.05:
            idx.append(i)
    return idx


print("策略:在触发日收盘卖出,持币 N 个交易日后收盘买回;赚价差 − 往返费用")
print("对照:一直持有(买入价 = 每个触发日的收盘价,期末卖出)\n")
print(f"{'触发':<6}{'N':>4}{'次数':>6}{'均差(卖-买)':>14}{'扣费后均':>11}"
      f"{'胜率':>8}{'最好':>9}{'最差':>9}")
print("-" * 74)

for kind in ("S1", "S2", "S3"):
    idxs = triggers(kind)
    if not idxs:
        print(f"{kind:<6}  无触发")
        continue
    for N in (1, 2, 3, 5, 10):
        diffs, t1_rets = [], []
        for i in idxs:
            j = i + N
            if j >= len(data):
                continue
            sell_px = data[i]["close"]
            buy_px = data[j]["close"]
            diffs.append(sell_px / buy_px - 1)          # gained if rebuy cheaper
            t1_rets.append(data[j]["close"] / sell_px - 1)  # holding instead
        if not diffs:
            continue
        n = len(diffs)
        avg = sum(diffs) / n
        wins = sum(1 for d in diffs if d > FEE)
        print(f"{kind:<6}{N:>4}{n:>6}{avg * 100:>+13.2f}%{(avg - FEE) * 100:>10.2f}%"
              f"{wins / n * 100:>7.0f}%{max(diffs) * 100:>+8.1f}%{min(diffs) * 100:>+8.1f}%")
    print()

# Focus: the exact shape seen on 2026-10-08
print("=== 昨日形态(S1)的逐次明细,N=5 ===")
for i in triggers("S1"):
    j = i + 5
    if j >= len(data):
        continue
    sell_px, buy_px = data[i]["close"], data[j]["close"]
    print(f"  {data[i]['date']} 卖 {sell_px:>7.2f} → {data[j]['date']} 买 {buy_px:>7.2f}  "
          f"价差 {sell_px / buy_px - 1:+7.2%}  扣费 {sell_px / buy_px - 1 - FEE:+7.2%}")

# Compare against NEVER selling (buy & hold across the same span)
print()
print("=== 对照:同一区间一直持有 vs 卖出再买回 ===")
for kind in ("S1", "S3"):
    idxs = triggers(kind)
    for N in (3, 5):
        strat, hold = [], []
        for i in idxs:
            j = i + N
            if j >= len(data):
                continue
            sell_px, buy_px = data[i]["close"], data[j]["close"]
            strat.append(sell_px / buy_px - 1 - FEE)
            hold.append(data[j]["close"] / sell_px - 1)   # held through, sold at j
        if not strat:
            continue
        ns, nh = len(strat), len(hold)
        print(f"  {kind} N={N}: 卖出再买回 {sum(strat) / ns * 100:+.2f}%/次   "
              f"一直持有 {sum(hold) / nh * 100:+.2f}%/次   "
              f"差额 {(sum(strat) - sum(hold)) / ns * 100:+.2f}%")
