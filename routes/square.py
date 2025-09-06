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
import logging
import re
import xml.etree.ElementTree as ET
from collections import deque

from flask import request, Response
from routes import app  # <-- single app lives in routes.py

logger = logging.getLogger(__name__)

# -------------------------
# Helpers: board parsing
# -------------------------

def _parse_viewbox(svg_root):
    vb = svg_root.attrib.get("viewBox", "0 0 512 512")
    parts = list(map(float, re.split(r"\s+", vb.strip())))
    if len(parts) != 4:
        w = float(svg_root.attrib.get("width", 512))
        h = float(svg_root.attrib.get("height", 512))
        return 0.0, 0.0, w, h
    return parts[0], parts[1], parts[2], parts[3]

def _gcd_pair(a, b):
    while b:
        a, b = b, a % b
    return int(abs(a))

def _gcd_list(vals):
    vals = [abs(int(round(v))) for v in vals if abs(v) > 1e-6]
    if not vals:
        return 32
    g = vals[0]
    for v in vals[1:]:
        g = _gcd_pair(g, v)
    return max(g, 1)

def _collect_line_centers(svg_root):
    xs, ys, lines = [], [], []
    for line in svg_root.iter():
        if line.tag.lower().endswith("line"):
            try:
                x1 = float(line.attrib["x1"]); y1 = float(line.attrib["y1"])
                x2 = float(line.attrib["x2"]); y2 = float(line.attrib["y2"])
            except Exception:
                continue
            stroke = line.attrib.get("stroke", "").strip().upper()
            lines.append((x1, y1, x2, y2, stroke))
            xs.extend([x1, x2]); ys.extend([y1, y2])
    return xs, ys, lines

def _infer_grid_size_and_dims(xs, ys, view_w, view_h):
    x_diffs, y_diffs = [], []
    sx = sorted(set(round(x, 6) for x in xs))
    sy = sorted(set(round(y, 6) for y in ys))
    for i in range(len(sx)):
        for j in range(i+1, len(sx)):
            x_diffs.append(abs(sx[j] - sx[i]))
    for i in range(len(sy)):
        for j in range(i+1, len(sy)):
            y_diffs.append(abs(sy[j] - sy[i]))
    cell_x = _gcd_list(x_diffs) or 32
    cell_y = _gcd_list(y_diffs) or 32
    s = max(1, min(cell_x, cell_y))
    width = int(round(view_w / s))
    height = int(round(view_h / s))
    return s, width, height

def _coord_to_square(x, y, s, width, height, view_h):
    c = int(round((x - s/2.0) / s))
    r_from_bottom = int(round((view_h - y - s/2.0) / s))
    r = min(max(r_from_bottom, 0), height - 1)
    c = min(max(c, 0), width - 1)
    idx_in_row = c if (r % 2 == 0) else (width - 1 - c)
    return r * width + (idx_in_row + 1)

def _build_jumps(svg_text):
    try:
        svg_root = ET.fromstring(svg_text)
    except ET.ParseError:
        logger.warning("SVG parse failed; defaulting to 16x16 with no jumps.")
        return 16 * 16, {}

    _, _, view_w, view_h = _parse_viewbox(svg_root)
    xs, ys, lines = _collect_line_centers(svg_root)
    if not lines:
        s = 32
        width = int(round(view_w / s)) or 16
        height = int(round(view_h / s)) or 16
        return width * height, {}

    s, width, height = _infer_grid_size_and_dims(xs, ys, view_w, view_h)
    N = width * height

    jumps = {}
    for (x1, y1, x2, y2, stroke) in lines:
        a = _coord_to_square(x1, y1, s, width, height, view_h)
        b = _coord_to_square(x2, y2, s, width, height, view_h)
        start, end = a, b
        if stroke == "GREEN" and end < start:
            start, end = end, start
        if stroke == "RED" and end > start:
            start, end = end, start
        if start != end:
            jumps[start] = end
    return N, jumps

# -------------------------
# Game mechanics (Power Up)
# -------------------------

def _apply_move(pos, face, mode, N):
    if mode == 0:
        step = face
        new_mode = 1 if face == 6 else 0
    else:
        step = 1 << face  # 2**face
        new_mode = 0 if face == 1 else 1
    target = step if pos == 0 else pos + step
    if target > N:
        target = N - (target - N)
        if target < 1:
            target = 1
    return target, new_mode

def _apply_jump(pos, jumps):
    return jumps.get(pos, pos)

# -------------------------
# Solver: make player 2 win
# -------------------------

def _solve_rolls(N, jumps, max_len=400):
    start = (0, 0, 0, 0, 0)
    q = deque([(start, "")])
    visited = {start}

    while q:
        (p1, m1, p2, m2, t), path = q.popleft()
        if len(path) >= max_len:
            continue
        for face in (6,5,4,3,2,1) if t == 1 else (1,2,3,4,5,6):
            if t == 0:
                npos, nm = _apply_move(p1, face, m1, N)
                npos = _apply_jump(npos, jumps)
                if npos == N:
                    continue
                ns = (npos, nm, p2, m2, 1)
            else:
                npos, nm = _apply_move(p2, face, m2, N)
                npos = _apply_jump(npos, jumps)
                if npos == N:
                    return path + str(face)
                ns = (p1, m1, npos, nm, 0)
            if ns not in visited:
                visited.add(ns)
                q.append((ns, path + str(face)))
    return "123456" * 5

# -------------------------
# Flask routes
# -------------------------

@app.route("/slpu", methods=["POST"])
def slpu():
    try:
        svg_text = request.data.decode("utf-8", errors="ignore")
    except Exception:
        svg_text = ""
    logger.info("Received SVG length=%d", len(svg_text))
    N, jumps = _build_jumps(svg_text)
    logger.info("Parsed board: N=%d, jumps=%d", N, len(jumps))
    rolls = _solve_rolls(N, jumps, max_len=600)
    logger.info("Computed rolls length=%d", len(rolls))
    out_svg = f'<svg xmlns="http://www.w3.org/2000/svg"><text>{rolls}</text></svg>'
    return Response(out_svg, mimetype="image/svg+xml")

@app.route('/square', methods=['POST'])
def evaluate():
    try:
        data = request.get_json(force=True, silent=True) or {}
        input_value = data.get("input", 0)
        result = input_value * input_value
    except Exception:
        logger.exception("Error in /square")
        result = None
    return {"result": result}
