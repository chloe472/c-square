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
      A) {"goods": [...], "rates": [edges_for_part1, edges_for_part2]}
         where each edges_for_partX is [[u,v,rate], ...]
      B) [{"goods": [...], "rates": [...]}, {"goods": [...], "rates": [...]}]
    Returns: goods, [edges1, edges2]
    """
    if isinstance(payload, list):
        # Case B
        if len(payload) != 2:
            raise ValueError("Top-level array must contain exactly two challenge items.")
        goods0 = payload[0].get("goods")
        goods1 = payload[1].get("goods", goods0)
        if goods0 is None:
            raise ValueError("Missing 'goods' in first item.")
        goods = goods0
        edges1 = payload[0].get("rates", [])
        edges2 = payload[1].get("rates", [])
        return goods, [edges1, edges2]

    # Case A
    goods = payload.get("goods")
    rates = payload.get("rates")
    if goods is None or rates is None:
        raise ValueError("Payload must include 'goods' and 'rates'.")
    if not isinstance(rates, list) or len(rates) < 2 or not all(isinstance(x, list) for x in rates[:2]):
        raise ValueError("Expected 'rates' to be a list with two lists of [u,v,rate] edges for the two challenges.")
    return goods, [rates[0], rates[1]]


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
    Brute-force all possible cycles up to length n.
    Works well for small graphs (n <= 10).
    """
    edges_by_pair = {}
    for u, v, r in edges:
        if r is None or r <= 0:
            continue
        edges_by_pair[(u, v)] = r

    best_cycle = None
    best_gain = 1.0

    for length in range(2, n + 1):
        for path in itertools.permutations(range(n), length):
            # close the cycle
            path = list(path) + [path[0]]
            prod = _gain_of_cycle(path, edges_by_pair)
            if prod > best_gain + 1e-9:
                best_gain = prod
                best_cycle = path

    if best_cycle is None or best_gain <= 1.0001:
        return None, None

    return best_cycle, best_gain


def _solve_one(goods, edges, want_best=True):
    """
    Solve one part of the challenge.
    """
    coerced = []
    for e in edges:
        if not isinstance(e, (list, tuple)) or len(e) < 3:
            continue
        try:
            u = int(e[0])
            v = int(e[1])
            r = float(e[2])
        except Exception:
            continue
        if 0 <= u < len(goods) and 0 <= v < len(goods) and r > 0:
            coerced.append((u, v, r))

    n = len(goods)
    if n == 0:
        return {"path": [], "gain": 0}

    cycle_nodes, product_gain = _brute_force_best_cycle(n, coerced)

    if not cycle_nodes:
        return {"path": [], "gain": 0}

    path_names = [goods[i] for i in cycle_nodes]
    gain_percent = (product_gain - 1.0) * 100.0
    gain_percent = round(gain_percent, 4)

    return {"path": path_names, "gain": gain_percent}


@app.route('/The-Ink-Archive', methods=['POST'])
def the_ink_archive():
    try:
        data = request.get_json(force=True, silent=False)
        logger.info("data sent for evaluation %s", data)

        goods, both_edges = _normalize_payload(data)

        part1 = _solve_one(goods, both_edges[0], want_best=False)
        part2 = _solve_one(goods, both_edges[1], want_best=True)

        result = [part1, part2]
        logger.info("My result: %s", result)
        return json.dumps(result), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.exception("Error in /The-Ink-Archive")
        return json.dumps({"error": str(e)}), 400, {'Content-Type': 'application/json'}
