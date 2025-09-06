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
    Accept either:
      A) {"goods": [...], "rates": [part1_rates, part2_rates]}
         where each part*_rates is EITHER a list of [u,v,rate] OR an NxN matrix of rates
      B) [{"goods": [...], "rates": ...}, {"goods": [...], "rates": ...}]
    Returns: goods, [rates1, rates2] (raw; coercion done later)
    """
    if isinstance(payload, list):
        if len(payload) != 2:
            raise ValueError("Top-level array must contain exactly two challenge items.")
        goods0 = payload[0].get("goods")
        if goods0 is None:
            raise ValueError("Missing 'goods' in first item.")
        rates1 = payload[0].get("rates", [])
        rates2 = payload[1].get("rates", [])
        return goods0, [rates1, rates2]

    goods = payload.get("goods")
    rates = payload.get("rates")
    if goods is None or rates is None:
        raise ValueError("Payload must include 'goods' and 'rates'.")
    if not isinstance(rates, list) or len(rates) < 2:
        raise ValueError("Expected 'rates' to be a list with two items (part1, part2).")
    return goods, [rates[0], rates[1]]


def _rates_to_edges(goods, rates_obj):
    """
    Convert a single part's 'rates' into canonical edge list [(u, v, r), ...].

    Accepts:
      - Edge list: [[u,v,rate], ...]
      - NxN matrix: [[1, r01, ...], [r10, 1, ...], ...]
    """
    n = len(goods)
    edges = []

    # Detect adjacency matrix
    is_matrix = (
        isinstance(rates_obj, list)
        and len(rates_obj) == n
        and all(isinstance(row, list) for row in rates_obj)
        and all(len(row) == len(rates_obj[0]) for row in rates_obj)
    )

    if is_matrix:
        # Treat any positive entry as an edge; usually diagonal is 1.0
        for i in range(n):
            row = rates_obj[i]
            mcols = len(row)
            # Allow rectangular but prefer square; cap at n columns
            for j in range(min(n, mcols)):
                try:
                    r = float(row[j])
                except Exception:
                    continue
                if j == i:
                    continue  # ignore self-edge
                if r > 0:
                    edges.append((i, j, r))
        return edges

    # Otherwise assume list of edges
    if isinstance(rates_obj, list):
        for e in rates_obj:
            if not isinstance(e, (list, tuple)) or len(e) < 3:
                continue
            try:
                u = int(e[0]); v = int(e[1]); r = float(e[2])
            except Exception:
                continue
            if 0 <= u < n and 0 <= v < n and r > 0:
                edges.append((u, v, r))

    return edges


def _gain_of_cycle(cycle_nodes, edges_by_pair):
    """Compute product of rates along cycle."""
    prod = 1.0
    for i in range(len(cycle_nodes) - 1):
        u = cycle_nodes[i]
        v = cycle_nodes[i + 1]
        r = edges_by_pair.get((u, v))
        if r is None or r <= 0:
            return 0.0
        prod *= r
    return prod


def _brute_force_best_cycle(n, edges):
    """
    Brute-force all simple cycles up to length n.
    Works well for small graphs (n <= 10).
    """
    edges_by_pair = {}
    for u, v, r in edges:
        if r is None or r <= 0:
            continue
        edges_by_pair[(u, v)] = r

    best_cycle = None
    best_gain = 1.0

    # Try all cycle lengths >= 2
    for length in range(2, n + 1):
        for path in itertools.permutations(range(n), length):
            path = list(path) + [path[0]]  # close the loop
            prod = _gain_of_cycle(path, edges_by_pair)
            if prod > best_gain + 1e-9:
                best_gain = prod
                best_cycle = path

    if best_cycle is None or best_gain <= 1.0000001:
        return None, None

    return best_cycle, best_gain


def _solve_one(goods, rates_obj):
    """
    Solve one part: coerce rates to edges, find best arbitrage cycle, return path+gain*100.
    """
    edges = _rates_to_edges(goods, rates_obj)
    n = len(goods)
    if n == 0 or not edges:
        return {"path": [], "gain": 0}

    cycle_nodes, product_gain = _brute_force_best_cycle(n, edges)
    if not cycle_nodes:
        return {"path": [], "gain": 0}

    path_names = [goods[i] for i in cycle_nodes]
    gain_percent = round((product_gain - 1.0) * 100.0, 6)  # a bit more precision for judge
    return {"path": path_names, "gain": gain_percent}


@app.route('/The-Ink-Archive', methods=['POST'])
def the_ink_archive():
    try:
        data = request.get_json(force=True, silent=False)
        logger.info("data sent for evaluation %s", data)

        goods, both_rates = _normalize_payload(data)

        part1 = _solve_one(goods, both_rates[0])   # any profitable cycle (we return best)
        part2 = _solve_one(goods, both_rates[1])   # maximum gain cycle

        result = [part1, part2]
        logger.info("My result: %s", result)
        return json.dumps(result), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.exception("Error in /The-Ink-Archive")
        return json.dumps({"error": str(e)}), 400, {'Content-Type': 'application/json'}
