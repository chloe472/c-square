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
import re
import math
from flask import request

from routes import app

logger = logging.getLogger(__name__)

# ----------------------------
# Helpers: Challenge 1 transforms + inverses
# ----------------------------

VOWELS = set("aeiouAEIOU")
ALPHA = "abcdefghijklmnopqrstuvwxyz"
ALPHA_UP = ALPHA.upper()

def mirror_words(x: str) -> str:
    return " ".join(w[::-1] for w in x.split(" "))

def encode_mirror_alphabet(x: str) -> str:
    # Atbash (self-inverse)
    res = []
    for ch in x:
        if 'a' <= ch <= 'z':
            res.append(chr(ord('z') - (ord(ch) - ord('a'))))
        elif 'A' <= ch <= 'Z':
            res.append(chr(ord('Z') - (ord(ch) - ord('A'))))
        else:
            res.append(ch)
    return "".join(res)

def toggle_case(x: str) -> str:
    return "".join(ch.lower() if ch.isupper() else ch.upper() if ch.islower() else ch for ch in x)

def swap_pairs(x: str) -> str:
    # swapping pairs twice restores original (self-inverse)
    def swap_word(w: str) -> str:
        chars = list(w)
        for i in range(0, len(chars) - 1, 2):
            chars[i], chars[i+1] = chars[i+1], chars[i]
        return "".join(chars)
    return " ".join(swap_word(w) for w in x.split(" "))

def encode_index_parity(x: str) -> str:
    # Even indices first, then odd, per word
    def enc_word(w: str) -> str:
        even = [w[i] for i in range(0, len(w), 2)]
        odd  = [w[i] for i in range(1, len(w), 2)]
        return "".join(even + odd)
    return " ".join(enc_word(w) for w in x.split(" "))

def decode_index_parity(x: str) -> str:
    # Inverse of encode_index_parity
    def dec_word(w: str) -> str:
        n = len(w)
        even_len = (n + 1) // 2
        even = list(w[:even_len])
        odd  = list(w[even_len:])
        out = []
        ei = oi = 0
        for i in range(n):
            if i % 2 == 0:
                out.append(even[ei]); ei += 1
            else:
                out.append(odd[oi]); oi += 1
        return "".join(out)
    return " ".join(dec_word(w) for w in x.split(" "))

def double_consonants(x: str) -> str:
    def is_consonant(ch: str) -> bool:
        return ch.isalpha() and ch not in VOWELS
    out = []
    for ch in x:
        if is_consonant(ch):
            out.append(ch)
            out.append(ch)
        else:
            out.append(ch)
    return "".join(out)

def undouble_consonants(x: str) -> str:
    # Collapse double consonants inserted by encoder
    def is_consonant(ch: str) -> bool:
        return ch.isalpha() and ch not in VOWELS
    out = []
    i = 0
    while i < len(x):
        ch = x[i]
        if i + 1 < len(x) and is_consonant(ch) and x[i+1] == ch:
            out.append(ch)
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)

# Map from name -> (forward_fn, inverse_fn)
TRANSFORMS = {
    "mirror_words":              (mirror_words,              mirror_words),
    "encode_mirror_alphabet":    (encode_mirror_alphabet,    encode_mirror_alphabet),
    "toggle_case":               (toggle_case,               toggle_case),
    "swap_pairs":                (swap_pairs,                swap_pairs),
    "encode_index_parity":       (encode_index_parity,       decode_index_parity),
    "double_consonants":         (double_consonants,         undouble_consonants),
}

def parse_transform_list(spec: str):
    """
    Parse a string like "[encode_mirror_alphabet(x), double_consonants(x), ...]"
    into a list of transform names in the given order.
    """
    names = re.findall(r'([a-z_]+)\s*\(\s*x\s*\)', spec or "")
    return names

def reverse_obfuscation(transform_spec: str, transformed: str) -> str:
    names = parse_transform_list(transform_spec)
    # Apply inverses in reverse order
    value = transformed
    for name in reversed(names):
        if name not in TRANSFORMS:
            raise ValueError(f"Unknown transform '{name}'")
        _, inv_fn = TRANSFORMS[name]
        value = inv_fn(value)
    return value

# ----------------------------
# Helpers: Challenge 2 pattern → digit via 5x7 OCR
# ----------------------------

# 5x7 digit templates (columns=5, rows=7). '1' = filled, '0' = empty.
DIGITS_5x7 = {
    "0": [
        "01110",
        "10001",
        "10011",
        "10101",
        "11001",
        "10001",
        "01110",
    ],
    "1": [
        "00100",
        "01100",
        "00100",
        "00100",
        "00100",
        "00100",
        "01110",
    ],
    "2": [
        "01110",
        "10001",
        "00001",
        "00010",
        "00100",
        "01000",
        "11111",
    ],
    "3": [
        "11110",
        "00001",
        "00001",
        "01110",
        "00001",
        "00001",
        "11110",
    ],
    "4": [
        "00010",
        "00110",
        "01010",
        "10010",
        "11111",
        "00010",
        "00010",
    ],
    "5": [
        "11111",
        "10000",
        "11110",
        "00001",
        "00001",
        "10001",
        "01110",
    ],
    "6": [
        "00110",
        "01000",
        "10000",
        "11110",
        "10001",
        "10001",
        "01110",
    ],
    "7": [
        "11111",
        "00001",
        "00010",
        "00100",
        "01000",
        "01000",
        "01000",
    ],
    "8": [
        "01110",
        "10001",
        "10001",
        "01110",
        "10001",
        "10001",
        "01110",
    ],
    "9": [
        "01110",
        "10001",
        "10001",
        "01111",
        "00001",
        "00010",
        "01100",
    ],
}

def coords_to_digit(coords):
    """
    coords: list of [lat, lon] strings or floats.
    Steps:
      1) parse to floats and drop obvious outliers by distance-to-centroid z-score > 1.5
      2) min-max normalize to [0,1] in both axes
      3) rasterize into 7 rows x 5 cols occupancy grid
      4) compare to templates by Hamming distance, return best digit
    """
    pts = []
    for lat, lon in coords:
        try:
            pts.append((float(lat), float(lon)))
        except Exception:
            continue
    if not pts:
        return None

    # Outlier removal (simple)
    cx = sum(p[0] for p in pts)/len(pts)
    cy = sum(p[1] for p in pts)/len(pts)
    dists = [math.hypot(p[0]-cx, p[1]-cy) for p in pts]
    mean_d = sum(dists)/len(dists)
    std_d = math.sqrt(sum((d-mean_d)**2 for d in dists)/len(dists)) or 1.0
    filtered = [p for p, d in zip(pts, dists) if (abs(d-mean_d)/std_d) <= 1.5]
    if len(filtered) >= 3:
        pts = filtered

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    rangex = (maxx - minx) or 1.0
    rangey = (maxy - miny) or 1.0

    # Grid: rows=7 (top=0), cols=5 (left=0)
    rows, cols = 7, 5
    grid = [[0 for _ in range(cols)] for _ in range(rows)]

    for x, y in pts:
        nx = (x - minx) / rangex
        ny = (y - miny) / rangey
        c = min(cols-1, max(0, int(round(nx*(cols-1)))))
        r = min(rows-1, max(0, int(round((1.0 - ny)*(rows-1)))))  # invert y so higher lat appears upper row
        grid[r][c] = 1

    # Flatten current grid into strings
    grid_str = ["".join(str(cell) for cell in row) for row in grid]

    # Compare to templates with Hamming (allowing slight sparsity by dilating occupied cells to neighbors)
    def hamming(a_rows, b_rows):
        return sum(1 for ar, br in zip(a_rows, b_rows) for ac, bc in zip(ar, br) if ac != bc)

    # Best match
    best_digit, best_cost = None, 1e9
    for d, tmpl in DIGITS_5x7.items():
        cost = hamming(grid_str, tmpl)
        if cost < best_cost:
            best_digit, best_cost = d, cost

    return best_digit

# ----------------------------
# Helpers: Challenge 3 ciphers
# ----------------------------

def parse_log_entry(entry: str) -> dict:
    parts = [p.strip() for p in entry.split("|")]
    kv = {}
    for p in parts:
        if ":" in p:
            k, v = p.split(":", 1)
            kv[k.strip()] = v.strip()
    return kv

def rot13(s: str) -> str:
    out = []
    for ch in s:
        if 'a' <= ch <= 'z':
            out.append(chr((ord(ch)-97+13)%26+97))
        elif 'A' <= ch <= 'Z':
            out.append(chr((ord(ch)-65+13)%26+65))
        else:
            out.append(ch)
    return "".join(out)

def railfence3_decrypt(cipher: str) -> str:
    # 3-rail decryption
    n = len(cipher)
    pattern = []
    rail, dir_down = 0, 1
    for _ in range(n):
        pattern.append(rail)
        rail += dir_down
        if rail == 2:
            dir_down = -1
        elif rail == 0:
            dir_down = 1

    counts = [pattern.count(0), pattern.count(1), pattern.count(2)]
    idxs = [0, counts[0], counts[0]+counts[1]]
    rails = [""]*3
    # Fill rails with appropriate slices
    rails[0] = cipher[0:idxs[1]]
    rails[1] = cipher[idxs[1]:idxs[2]]
    rails[2] = cipher[idxs[2]:]

    # Reconstruct
    pos = [0,0,0]
    out = []
    for r in pattern:
        out.append(rails[r][pos[r]])
        pos[r] += 1
    return "".join(out)

def keyword_decrypt(cipher: str, keyword: str="SHADOW") -> str:
    # Build cipher alphabet = keyword (dedup) + remaining letters, using uppercase.
    kw = []
    for ch in keyword.upper():
        if ch.isalpha() and ch not in kw:
            kw.append(ch)
    rest = [ch for ch in ALPHA_UP if ch not in kw]
    cipher_alpha = "".join(kw + rest)
    plain_alpha = ALPHA_UP

    # Map cipher->plain
    m = {c:p for c, p in zip(cipher_alpha, plain_alpha)}
    out = []
    for ch in cipher:
        if ch.upper() in m:
            dec = m[ch.upper()]
            out.append(dec if ch.isupper() else dec.lower())
        else:
            out.append(ch)
    return "".join(out)

def polybius_decrypt(payload: str):
    # 5x5 Polybius with I/J combined. Accepts:
    #  - space-separated pairs: "23 15 42"
    #  - continuous digits of even length: "231542"
    #  - pairs separated by non-digits: "23-15|42"
    square_letters = [c for c in "ABCDEFGHIKLMNOPQRSTUVWXYZ"]  # J merged with I
    # Build grid map
    idx_to_letter = {}
    i = 0
    for r in range(1, 6):
        for c in range(1, 6):
            idx_to_letter[(r, c)] = square_letters[i]
            i += 1

    # Extract digit pairs
    digs = re.findall(r'\d', payload)
    pairs = []
    if len(digs) >= 2 and len(digs) % 2 == 0:
        for i in range(0, len(digs), 2):
            r = int(digs[i]); c = int(digs[i+1])
            pairs.append((r, c))
    else:
        # Try tokenized pairs like "23", "15"
        toks = re.findall(r'\b([1-5]{2})\b', payload)
        for t in toks:
            pairs.append((int(t[0]), int(t[1])))

    if not pairs:
        return payload  # nothing to do

    out = []
    for r, c in pairs:
        if 1 <= r <= 5 and 1 <= c <= 5:
            out.append(idx_to_letter[(r, c)])
        else:
            out.append("?")
    return "".join(out)

def decrypt_log_entry(entry: str) -> str:
    kv = parse_log_entry(entry)
    ctype = kv.get("CIPHER_TYPE", "").strip().upper()
    payload = kv.get("ENCRYPTED_PAYLOAD", "")

    if ctype == "RAILFENCE":
        return railfence3_decrypt(payload)
    elif ctype == "KEYWORD":
        return keyword_decrypt(payload, "SHADOW")
    elif ctype == "POLYBIUS":
        return polybius_decrypt(payload)
    elif ctype == "ROTATION_CIPHER":
        # Example shows ROT13 ("SVERJNYY" -> "FIREWALL")
        return rot13(payload)
    else:
        # Unknown – return payload unchanged
        return payload

# ----------------------------
# Challenge 4 hook
# ----------------------------

def final_decrypt(maybe_ciphertext: str, key1: str, key2: str, key3: str) -> str:
    """
    Flexible hook. If your challenge provides a final encrypted message,
    use values from challenges 1–3 to decrypt. For now:
    - If ciphertext looks like ROT13, try ROT13.
    - Else, attempt Atbash.
    - Else, return as-is.
    """
    if not maybe_ciphertext:
        return "MISSING_FINAL_MESSAGE"
    # try ROT13 heuristic: rot13 changes letters; if result has many vowels, keep it
    r13 = rot13(maybe_ciphertext)
    if sum(ch in "aeiouAEIOU" for ch in r13) >= max(3, len(r13)//4):
        return r13
    atb = encode_mirror_alphabet(maybe_ciphertext)
    if sum(ch in "aeiouAEIOU" for ch in atb) >= max(3, len(atb)//4):
        return atb
    return maybe_ciphertext

# ----------------------------
# Endpoint
# ----------------------------

@app.route('/operation-safeguard', methods=['POST'])
def operation_safeguard():
    data = request.get_json(force=True, silent=True) or {}
    logging.info("data sent for evaluation %s", data)

    # --- Challenge 1 ---
    ch1 = data.get("challenge_one", {}) or {}
    try:
        t_spec = ch1.get("transformations", "")
        transformed = ch1.get("transformed_encrypted_word", "") or ""
        result_ch1 = reverse_obfuscation(t_spec, transformed) if transformed else ""
    except Exception as e:
        logging.exception("Challenge 1 failed")
        result_ch1 = f"ERROR: {e}"

    # --- Challenge 2 ---
    coords = data.get("challenge_two") or []
    try:
        result_ch2 = coords_to_digit(coords) if coords else ""
    except Exception as e:
        logging.exception("Challenge 2 failed")
        result_ch2 = f"ERROR: {e}"

    # --- Challenge 3 ---
    ch3_entry = data.get("challenge_three", "") or ""
    try:
        result_ch3 = decrypt_log_entry(ch3_entry) if ch3_entry else ""
    except Exception as e:
        logging.exception("Challenge 3 failed")
        result_ch3 = f"ERROR: {e}"

    # --- Challenge 4 (optional input key: 'final_encrypted_message') ---
    final_cipher = data.get("final_encrypted_message", "") or ""
    try:
        result_ch4 = final_decrypt(final_cipher, str(result_ch1), str(result_ch2), str(result_ch3))
    except Exception as e:
        logging.exception("Challenge 4 failed")
        result_ch4 = f"ERROR: {e}"

    result = {
        "challenge_one": result_ch1,
        "challenge_two": result_ch2,
        "challenge_three": result_ch3,
        "challenge_four": result_ch4,
    }
    logging.info("My result :%s", result)
    return app.response_class(
        response=json.dumps(result),
        mimetype="application/json",
        status=200,
    )
