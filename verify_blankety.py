# at top of verify_blankety.py
URL = "http://127.0.0.1:8080/blankety"   

import random, math, time, json, statistics
import requests

#URL = "https://c-square-4.onrender.com/blankety"  # <- your deployed URL+path

def make_signal(n=1000):
    # mix trend + seasonal + wiggles
    a = random.uniform(-0.003, 0.003)                 # linear trend
    b = random.uniform(-0.000002, 0.000002)           # quadratic
    amp = random.uniform(0.2, 1.0)
    freq = random.uniform(2*math.pi/200, 2*math.pi/50)
    phase = random.uniform(0, 2*math.pi)
    x = []
    for t in range(n):
        base = a*t + b*(t**2) + amp*math.sin(freq*t + phase)
        noise = random.gauss(0, 0.03)
        x.append(base + noise)
    return x

def insert_nulls(x, p=0.25, long_gap_prob=0.1):
    n = len(x)
    y = x[:]
    null_idx = set()
    i = 0
    while i < n:
        if random.random() < long_gap_prob:  # sometimes long gaps
            L = random.randint(10, 80)
            for k in range(i, min(n, i+L)):
                y[k] = None
                null_idx.add(k)
            i += L
        else:
            if random.random() < p:
                y[i] = None
                null_idx.add(i)
            i += 1
    return y, sorted(null_idx)

def mae_at(indices, truth, pred):
    if not indices: return 0.0
    return sum(abs(truth[i] - pred[i]) for i in indices) / len(indices)

def build_payload():
    series = []
    truths = []
    missing_positions = []
    for _ in range(100):
        x = make_signal(1000)
        y, miss = insert_nulls(x, p=0.25, long_gap_prob=0.15)
        series.append(y)
        truths.append(x)
        missing_positions.append(miss)
    # add a couple nasty edge cases
    all_null = [None]*1000
    series[0] = all_null
    truths[0] = [0.0]*1000
    missing_positions[0] = list(range(1000))
    return {"series": series}, truths, missing_positions

def main():
    payload, truths, missing = build_payload()

    t0 = time.time()
    resp = requests.post(URL, json=payload, timeout=25)
    dt = time.time() - t0
    print("HTTP", resp.status_code, "in", f"{dt:.3f}s")
    resp.raise_for_status()
    data = resp.json()

    ans = data.get("answer", [])
    assert isinstance(ans, list) and len(ans) == 100, "answer must be 100 lists"
    # invariants + metrics
    passes = 0
    for i, (pred, truth, miss_idx) in enumerate(zip(ans, truths, missing)):
        assert isinstance(pred, list) and len(pred) == 1000, f"row {i} has wrong length"
        # no null/NaN/Inf
        for v in pred:
            assert v is not None and isinstance(v, (int, float)) and math.isfinite(float(v)), f"bad number at row {i}"
        err = mae_at(miss_idx, truth, [float(v) for v in pred])
        if err < 0.1:
            passes += 1
    print(f"Passes: {passes}/100  (target ≥ 80 is usually good)")
    print("Avg length:", statistics.mean(len(r) for r in ans))

if __name__ == "__main__":
    main()
