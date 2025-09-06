'''import json
import logging

from flask import request

from routes import app

logger = logging.getLogger(__name__)


@app.route('/square', methods=['POST'])
def evaluate():
    data = request.get_json()
    logging.info("data sent for evaluation {}".format(data))
    input_value = data.get("input")
    result = input_value * input_value
    logging.info("My result :{}".format(result))
    return json.dumps(result)
'''
import json
import logging
import itertools

from flask import request
from routes import app

logger = logging.getLogger(__name__)

def _normalize_payload(payload):
    """
    Judge sends: [ {goods:[...], ratios:[...]}, {goods:[...], ratios:[...]} ]
    Returns: [(goods1, rates1), (goods2, rates2)]
    """
    if not isinstance(payload, list) or len(payload) != 2:
        raise ValueError("Top-level payload must be a list of two items (part1, part2).")

    def pick_rates(obj):
        if "ratios" in obj:
            return obj["ratios"]
        if "rates" in obj:
            return obj["rates"]
        raise ValueError("Missing 'ratios' (or 'rates') in item.")

    part1_goods = payload[0].get("goods")
    part2_goods = payload[1].get("goods")
    if not part1_goods or not part2_goods:
        raise ValueError("Missing 'goods' in input.")

    part1_rates = pick_rates(payload[0])
    part2_rates = pick_rates(payload[1])
    return [(part1_goods, part1_rates), (part2_goods, part2_rates)]


def _rates_to_edges(goods, rates_obj):
    """
    Convert a part's 'ratios'/'rates' into canonical edge list [(u, v, r), ...].

    Accepts:
      - Edge list: [[u,v,rate], ...] (u,v may be float like 2.0 -> cast to int)
      - NxN matrix: [[1, r01, ...], [r10, 1, ...], ...]
    """
    n = len(goods)
    edges = []

    # Detect matrix
    is_matrix = (
        isinstance(rates_obj, list)
        and len(rates_obj) == n
        and all(isinstance(row, list) for row in rates_obj)
    )
    if is_matrix:
        for i, row in enumerate(rates_obj):
            m = min(n, len(row))
            for j in range(m):
                if j == i:
                    continue
                try:
                    r = float(row[j])
                except Exception:
                    continue
                if r > 0:
                    edges.append((i, j, r))
        return edges

    # Otherwise assume list of [u, v, r]
    if isinstance(rates_obj, list):
        for e in rates_obj:
            if not isinstance(e, (list, tuple)) or len(e) < 3:
                continue
            try:
                # indices sometimes come as floats in judge data (e.g., 2.0)
                u = int(float(e[0]))
                v = int(float(e[1]))
                r = float(e[2])
            except Exception:
                continue
            if 0 <= u < n and 0 <= v < n and r > 0:
                edges.append((u, v, r))

    return edges


def _gain_of_cycle(cycle_nodes, edges_by_pair):
    """Product of rates along a closed cycle [n0,...,nk,n0]."""
    prod = 1.0
    for i in range(len(cycle_nodes) - 1):
        u, v = cycle_nodes[i], cycle_nodes[i + 1]
        r = edges_by_pair.get((u, v))
        if r is None or r <= 0:
            return 0.0
        prod *= r
    return prod


def _brute_force_first_profitable_cycle(n, edges, eps=1e-12):
    """
    Return the best profitable cycle (>1+eps) among the SHORTEST length >= 3.
    I.e., search length=3; if any profitable cycles exist, return the max product among them.
    If none at length 3, try length 4, etc.
    """
    edges_by_pair = {(u, v): r for (u, v, r) in edges if r > 0}

    for length in range(3, n + 1):  # require at least 3 trades
        best_cycle = None
        best_prod = 1.0
        for path in itertools.permutations(range(n), length):
            path = list(path) + [path[0]]  # close
            prod = _gain_of_cycle(path, edges_by_pair)
            if prod > 1.0 + eps and prod > best_prod + eps:
                best_prod = prod
                best_cycle = path
        if best_cycle is not None:
            return best_cycle, best_prod

    return None, None



def _brute_force_best_cycle(n, edges, eps=1e-12):
    """
    Return the maximum-gain simple cycle (length 2..n).
    """
    edges_by_pair = {(u, v): r for (u, v, r) in edges if r > 0}
    best_cycle = None
    best_gain = 1.0

    for length in range(2, n + 1):
        for path in itertools.permutations(range(n), length):
            path = list(path) + [path[0]]
            prod = _gain_of_cycle(path, edges_by_pair)
            if prod > best_gain + eps:
                best_gain = prod
                best_cycle = path

    if best_cycle is None or best_gain <= 1.0 + eps:
        return None, None
    return best_cycle, best_gain


def _solve_one(goods, rates_obj, want_best):
    """
    Coerce rates, find cycle, format response. No rounding on gain.
    """
    edges = _rates_to_edges(goods, rates_obj)
    n = len(goods)
    if n == 0 or not edges:
        return {"path": [], "gain": 0}

    if want_best:
        cycle_nodes, product_gain = _brute_force_best_cycle(n, edges)
    else:
        cycle_nodes, product_gain = _brute_force_first_profitable_cycle(n, edges)

    if not cycle_nodes:
        return {"path": [], "gain": 0}

    path_names = [goods[i] for i in cycle_nodes]
    gain_percent = (product_gain - 1.0) * 100.0  # raw float (no rounding)
    return {"path": path_names, "gain": gain_percent}

@app.route('/The-Ink-Archive', methods=['POST'])
def the_ink_archive():
    try:
        data = request.get_json(force=True, silent=False)
        logger.info("data sent for evaluation %s", data)

        both_parts = _normalize_payload(data)

        part1_goods, part1_rates = both_parts[0]
        part2_goods, part2_rates = both_parts[1]

        part1 = _solve_one(part1_goods, part1_rates, want_best=False)
        part2 = _solve_one(part2_goods, part2_rates, want_best=True)

        result = [part1, part2]
        logger.info("My result: %s", result)
        return json.dumps(result), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.exception("Error in /The-Ink-Archive")
        return json.dumps({"error": str(e)}), 400, {'Content-Type': 'application/json'}
