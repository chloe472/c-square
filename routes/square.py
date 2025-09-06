import json
import logging

from flask import request
from . import app

#from routes import app

logger = logging.getLogger(__name__)

def _to_float_or_none(v):
    # JSON null -> Python None; ensure numbers are floats
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None  # treat non-numeric as missing just in case

def _impute_one(seq):
    """
    Impute a single list:
      1) Convert to floats; None marks missing
      2) Edge-fill leading/trailing gaps
      3) Linear interpolation for interior gaps
      4) Light moving-average smoothing (window=7) only at originally-missing positions
    """
    n = len(seq)
    x = [_to_float_or_none(v) for v in seq]
    missing = [v is None for v in x]

    if n == 0:
        return []

    # If everything is missing, return zeros (safe fallback)
    if all(missing):
        return [0.0] * n

    # Find first and last known
    first = next(i for i, v in enumerate(x) if v is not None)
    last = next(i for i in range(n - 1, -1, -1) if x[i] is not None)

    # Edge-fill: extend nearest known value to the ends
    for i in range(0, first):
        x[i] = x[first]
    for i in range(last + 1, n):
        x[i] = x[last]

    # Linear interpolation over interior gaps
    prev = first
    i = first + 1
    while i < n:
        if x[i] is None:
            # start of a gap
            k = i
            while k < n and x[k] is None:
                k += 1
            # k now points to next known (must exist because we filled edges)
            left = x[prev]
            right = x[k]
            span = k - prev
            for t in range(i, k):
                frac = (t - prev) / span
                x[t] = left + (right - left) * frac
            prev = k
            i = k + 1
        else:
            prev = i
            i += 1

    # Light denoise: moving average (window=7) only for originally-missing points
    w = 7
    r = w // 2
    # prefix sums for O(1) window mean
    prefix = [0.0]
    for val in x:
        prefix.append(prefix[-1] + val)

    def window_mean(a, b):  # [a, b)
        length = b - a
        if length <= 0:
            return x[a]  # shouldn't happen
        return (prefix[b] - prefix[a]) / length

    smoothed = x[:]
    for idx, was_missing in enumerate(missing):
        if was_missing:
            a = max(0, idx - r)
            b = min(n, idx + r + 1)
            smoothed[idx] = window_mean(a, b)

    # Ensure plain floats for JSON
    return [float(v) for v in smoothed]

# ---------- Endpoint ----------

@app.route('/square', methods=['POST'])
def evaluate():
    data = request.get_json()
    logging.info("data sent for evaluation %s", 
                 {"series_count": len(data.get("series", [])) if isinstance(data, dict) else None})

    series = data.get("series", []) if isinstance(data, dict) else []

    # Shape guard
    if not isinstance(series, list):
        result = {"answer": []}
        logging.info("My result :%s", {"answer_len": 0})
        return json.dumps(result)

    answer = [_impute_one(lst) for lst in series]

    result = {"answer": answer}
    logging.info("My result :%s", {"answer_len": len(answer), "series_len": len(answer[0]) if answer else 0})
    #logging.info("My result :{}".format(result))
    return json.dumps(result)
