
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
    return [_to_numeric(v) for v in smoothed]


def _to_numeric(v, decimals=6):
    """Round to a few decimals; if it's essentially an int, return int."""
    x = round(float(v), decimals)
    iv = int(x)
    return iv if abs(x - iv) < 10**(-decimals) else x


@app.route('/square', methods=['POST'])
@app.route('/blankety', methods=['POST'])

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


'''
# routes/square.py
import json
import logging
from flask import request
from . import app

logger = logging.getLogger(__name__)

def _to_numeric(v, decimals=2):
    """Round nicely; if very close to int, return an int for cleaner JSON."""
    x = round(float(v), decimals)
    iv = int(x)
    return iv if abs(x - iv) < 10 ** (-decimals) else x

def _to_float_or_none(v):
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _impute_one(seq):
    """
    1) Cast to floats; mark missing.
    2) Edge-fill leading/trailing gaps with nearest known value.
    3) Fill interior gaps via cubic Hermite using *secant* slopes (robust).
    4) Light smoothing ONLY for long gaps (length >= 3).
    """
    n = len(seq)
    if n == 0:
        return []

    x = [_to_float_or_none(v) for v in seq]
    missing = [v is None for v in x]

    # All missing -> safe zeros
    if all(v is None for v in x):
        return [0.0] * n

    # Find first & last known
    first = next(i for i, v in enumerate(x) if v is not None)
    last = next(i for i in range(n - 1, -1, -1) if x[i] is not None)

    # Edge-fill
    for i in range(0, first):
        x[i] = x[first]
    for i in range(last + 1, n):
        x[i] = x[last]

    # Fill interior gaps with cubic Hermite; use secant slope across gap
    L = first
    while L < n:
        # advance to a known
        while L < n and x[L] is None:
            L += 1
        if L >= n:
            break
        # find next known after any None run
        R = L + 1
        while R < n and x[R] is None:
            R += 1
        if R >= n:
            break
        if R == L + 1:
            L = R
            continue

        yL, yR = x[L], x[R]
        h = R - L
        sec = (yR - yL) / h  # robust slope

        for t in range(L + 1, R):
            u = (t - L) / h
            u2 = u * u
            u3 = u2 * u
            H00 = 2 * u3 - 3 * u2 + 1
            H10 = u3 - 2 * u2 + u
            H01 = -2 * u3 + 3 * u2
            H11 = u3 - u2
            x[t] = H00 * yL + H10 * h * sec + H01 * yR + H11 * h * sec

        L = R

    # Safety: if any None remain, copy nearest known (should be rare)
    for i in range(n):
        if x[i] is None:
            j = i - 1
            while j >= 0 and x[j] is None:
                j -= 1
            if j >= 0:
                x[i] = x[j]
            else:
                k = i + 1
                while k < n and x[k] is None:
                    k += 1
                x[i] = x[k] if k < n else 0.0

    # -------- selective smoothing (only long gaps) --------
    # mark indices that were inside long missing runs (len >= 3)
    long_gap_idx = set()
    i = 0
    while i < n:
        if missing[i]:
            j = i
            while j < n and missing[j]:
                j += 1
            if (j - i) >= 3:
                long_gap_idx.update(range(i, j))
            i = j
        else:
            i += 1

    if long_gap_idx:
        w = 7
        r = w // 2
        prefix = [0.0]
        for val in x:
            prefix.append(prefix[-1] + val)

        def mean(a, b):
            return (prefix[b] - prefix[a]) / (b - a) if b > a else x[a]

        for idx in long_gap_idx:
            a = max(0, idx - r)
            b = min(n, idx + r + 1)
            x[idx] = mean(a, b)

    return [_to_numeric(v) for v in x]


# expose BOTH paths to be safe
@app.route('/blankety', methods=['POST'])
@app.route('/square', methods=['POST'])
def evaluate():
    # Parse JSON and fail gracefully if it's invalid
    try:
        data = request.get_json(force=True)  # raise if invalid JSON
    except Exception as e:
        logger.exception("Invalid JSON body")
        return json.dumps({"error": "invalid_json", "detail": str(e)}), 400, {
            "Content-Type": "application/json"
        }

    # Validate the shape
    series = data.get("series") if isinstance(data, dict) else None
    if not isinstance(series, list):
        logger.warning("Missing/invalid 'series' – returning empty answer")
        return json.dumps({"answer": []}), 200, {"Content-Type": "application/json"}

    answer = []
    for i, lst in enumerate(series):
        if not isinstance(lst, list):
            logger.warning("Row %d is not a list; returning empty row", i)
            answer.append([])
            continue
        try:
            answer.append(_impute_one(lst))
        except Exception:
            # Don't 500 the whole request if one row is funky
            logger.exception("Imputation failed at row %d; filling zeros", i)
            answer.append([0.0] * len(lst))

    return json.dumps({"answer": answer}), 200, {"Content-Type": "application/json"}
'''

