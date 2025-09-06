'''
import json
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
'''
import json
import logging
from collections import defaultdict

from flask import request
from routes import app

logger = logging.getLogger(__name__)


@app.route('/investigate', methods=['POST'])
def investigate():
    """
    Identify all edges that lie on at least one cycle (non-bridges) in each network.
    Returns them as 'extraChannels' preserving the original input order.
    """
    data = request.get_json(silent=True) or {}
    logging.info("data sent for investigation: %s", data)

    networks = data.get("networks", [])
    out_networks = []

    for net in networks:
        network_id = net.get("networkId")
        edges_raw = net.get("network", [])

        # Map spy names -> indices
        idx = {}
        def get_idx(name):
            if name not in idx:
                idx[name] = len(idx)
            return idx[name]

        # Build edge list with ids and adjacency including edge ids
        edges = []  # list of (u, v, original_dict)
        for e in edges_raw:
            u = get_idx(e["spy1"])
            v = get_idx(e["spy2"])
            edges.append((u, v, e))

        n = len(idx)
        adj = [[] for _ in range(n)]
        for eid, (u, v, _) in enumerate(edges):
            # undirected: store edge id on both sides
            adj[u].append((v, eid))
            adj[v].append((u, eid))

        # Tarjan's algorithm to find bridges.
        time = 0
        disc = [-1] * n    # discovery times
        low = [0] * n
        bridges = set()

        def dfs(u, parent_eid):
            nonlocal time
            disc[u] = time
            low[u] = time
            time += 1
            for v, eid in adj[u]:
                if eid == parent_eid:
                    continue
                if disc[v] == -1:
                    dfs(v, eid)
                    low[u] = min(low[u], low[v])
                    # Bridge check: if no back-edge from v or its subtree to u or above
                    if low[v] > disc[u]:
                        bridges.add(eid)
                else:
                    # Back edge
                    low[u] = min(low[u], disc[v])

        # Run DFS from every unvisited node (handle disconnected graphs)
        for u in range(n):
            if disc[u] == -1:
                dfs(u, parent_eid=-1)

        # Extra channels = edges that are NOT bridges (i.e., part of at least one cycle)
        extra = []
        for eid, (u, v, orig) in enumerate(edges):
            if eid not in bridges:
                extra.append(orig)

        out_networks.append({
            "networkId": network_id,
            "extraChannels": extra
        })

    result = {"networks": out_networks}
    logging.info("investigation result: %s", result)
    return json.dumps(result)
'''
# routes/square.py
import logging
import json
from collections import OrderedDict
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)


@app.route('/investigate', methods=['POST'])
def investigate():
    """
    Return, for each network, all edges that are part of at least one cycle
    (non-bridge edges). Accepts:
      1) {"networks": [ {...}, ... ]}
      2) [ {...}, ... ]
      3) { "networkId": "...", "network": [ ... ] }
    """
    data = request.get_json(silent=True)

    # Normalize payload shapes
    if isinstance(data, list):
        networks = data
    elif isinstance(data, dict):
        if isinstance(data.get("networks"), list):
            networks = data["networks"]
        elif "networkId" in data and "network" in data:
            networks = [data]
        else:
            return jsonify({"error": "Invalid payload format"}), 400
    else:
        return jsonify({"error": "Invalid payload format"}), 400

    out_networks = []

    for net in networks:
        network_id = net.get("networkId")
        edges_raw = net.get("network", [])

        # Map spy names -> indices
        idx = {}
        def get_idx(name):
            if name not in idx:
                idx[name] = len(idx)
            return idx[name]

        # Edges and adjacency
        edges = []
        for e in edges_raw:
            u = get_idx(e["spy1"])
            v = get_idx(e["spy2"])
            edges.append((u, v, e))

        n = len(idx)
        adj = [[] for _ in range(n)]
        for eid, (u, v, _) in enumerate(edges):
            adj[u].append((v, eid))
            adj[v].append((u, eid))

        # Tarjan's bridges
        time = 0
        disc = [-1] * n
        low = [0] * n
        bridges = set()

        def dfs(u, parent_eid):
            nonlocal time
            disc[u] = time
            low[u] = time
            time += 1
            for v, eid in adj[u]:
                if eid == parent_eid:
                    continue
                if disc[v] == -1:
                    dfs(v, eid)
                    low[u] = min(low[u], low[v])
                    if low[v] > disc[u]:
                        bridges.add(eid)
                else:
                    low[u] = min(low[u], disc[v])

        for u in range(n):
            if disc[u] == -1:
                dfs(u, parent_eid=-1)

        # Non-bridges are extra channels
        extra = []
        for eid, (_, _, orig) in enumerate(edges):
            if eid not in bridges:
                extra.append(orig)

        # Preserve key order: networkId first, then extraChannels
        item = OrderedDict()
        item["networkId"] = network_id
        item["extraChannels"] = extra
        out_networks.append(item)

    # Top-level also as OrderedDict to be safe
    result = OrderedDict()
    result["networks"] = out_networks

    # Use json.dumps to preserve insertion order
    return json.dumps(result), 200, {"Content-Type": "application/json"}

