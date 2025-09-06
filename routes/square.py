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
import math

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


def _extract_cycle(parents, start_node, n_nodes):
    """
    Backtrack to reconstruct the negative cycle.
    """
    x = start_node
    for _ in range(n_nodes):
        x = parents[x]

    cycle = []
    seen = {}
    cur = x
    while True:
        if cur in seen:
            start_idx = seen[cur]
            cycle_nodes = cycle[start_idx:] + [cur]
            return cycle_nodes
        seen[cur] = len(cycle)
        cycle.append(cur)
        cur = parents[cur]


def _gain_of_cycle(cycle_nodes, edges_by_pair):
    """
    Compute product of rates along cycle.
    """
    prod = 1.0
    for i in range(len(cycle_nodes) - 1):
        u = cycle_nodes[i]
        v = cycle_nodes[i + 1]
        r = edges_by_pair.get((u, v))
        if r is None or r <= 0:
            return 0.0
        prod *= r
    return prod


def _bellman_ford_best_cycle(n, edges):
    """
    Find best arbitrage cycle using Bellman-Ford + -log trick.
    """
    w_edges = []
    edges_by_pair = {}
    for u, v, r in edges:
        if r is None or r <= 0:
            continue
        w = -math.log(r)
        w_edges.append((u, v, w))
        edges_by_pair[(u, v)] = r

    if not w_edges:
        return None, None

    best_cycle_nodes = None
    best_gain = 1.0

    for src in range(n):
        dist = [float("inf")] * n
        par = [-1] * n
        dist[src] = 0.0

        # Relax n-1 times
        for _ in range(n - 1):
            updated = False
            for u, v, w in w_edges:
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    par[v] = u
                    updated = True
            if not updated:
                break

        # Check for negative cycles
        changed_nodes = []
        for u, v, w in w_edges:
            if dist[u] + w < dist[v] - 1e-9:  # looser tolerance
                par[v] = u
                changed_nodes.append(v)

        for node in changed_nodes:
            cycle_nodes = _extract_cycle(par, node, n)
            if cycle_nodes[0] != cycle_nodes[-1]:
                cycle_nodes.append(cycle_nodes[0])
            gain = _gain_of_cycle(cycle_nodes, edges_by_pair)
            if gain > best_gain + 1e-6:
                best_gain = gain
                best_cycle_nodes = cycle_nodes

    logger.info("Best gain found: %s", best_gain)
    logger.info("Best cycle nodes: %s", best_cycle_nodes)

    if best_cycle_nodes is None or best_gain <= 1.0001:
        return None, None

    return best_cycle_nodes, best_gain


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

    cycle_nodes, product_gain = _bellman_ford_best_cycle(n, coerced)

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
