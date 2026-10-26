#!/usr/bin/env python3
"""Build an .excalidraw file from a JSON spec and check the drawing before it is written.

  python3 build_diagram.py .project-docs/diagrams/<name>.json            # check, then write
  python3 build_diagram.py .project-docs/diagrams/<name>.json --check    # check only

The spec holds data only: nodes placed in a lane (a column, e.g. a layer or a runtime) and a
row (one dimension of the block, e.g. Option or step), arrows between nodes, and tags that give
colour and a legend entry for any other dimension (auth, environment, status). Positions are
computed here, so the same spec always gives the same file. check() runs on the computed
geometry and reports boxes that overlap, text that does not fit, arrows that cross or pass
through a box, badges on top of boxes, emoji or circled digits, and text matching the project's
stale-patterns.json. It does not judge how the diagram reads: open it and look.

The spec format is in ../rules/diagrams.md. Standard library only.
"""
from __future__ import annotations

import json
import re
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import REPO, STALE_FILE  # noqa: E402  project root and stale-pattern file

INK = "#1e1e1e"
LINE = "#495057"
ROUGHNESS = 1  # 1 = hand-drawn look in Excalidraw
PALETTE = {  # style -> (background, stroke)
    "white": ("#ffffff", INK),
    "grey": ("#f8f9fa", "#868e96"),
    "blue": ("#d0ebff", "#1864ab"),
    "green": ("#d3f9d8", "#2b8a3e"),
    "red": ("#ffe3e3", "#c92a2a"),
    "violet": ("#e5dbff", "#5f3dc4"),
    "yellow": ("#fff3bf", "#f08c00"),
    "orange": ("#ffd8a8", "#e8590c"),
}
# Sizes in px. Layout and check read the same numbers.
NODE_W, NODE_H = 204, 76
LANE_W = NODE_W + 32      # 16 px inside each side of a lane
LANE_GAP = 120            # free space where elbow arrows run between lanes
FRAME_PAD = 14            # frame drawn around a lane that runs on a runtime
ROW_H = 110
ROW_LABEL_W, MARGIN = 120, 24
TITLE_H, HEADER_H, LEGEND_H, BLOCK_GAP = 44, 40, 52, 60
FONT, FONT_SMALL = 15, 13
LINE_H = 1.25
CHAR_EM = 0.6             # average glyph width in em; an estimate, Thai glyphs run wider
DEFAULT_LIMITS = {"lanes": 5, "rows": 8, "blocks": 3}
FORBIDDEN = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿️①-⓿❶-➓]")
FILE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*\.excalidraw$")


# ---------------------------------------------------------------- text and element helpers

def text_w(s: str, size: float) -> float:
    return len(s) * size * CHAR_EM


def wrap(text: str, width: float, size: float) -> list[str]:
    """Greedy word wrap on spaces. An explicit newline always starts a new line."""
    limit = max(int(width / (size * CHAR_EM)), 4)
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            if cur and len(cur) + 1 + len(word) > limit:
                lines.append(cur)
                cur = word
            else:
                cur = f"{cur} {word}" if cur else word
        lines.append(cur)
    return lines


def inner_box(kind: str, w: float, h: float) -> tuple[float, float]:
    """Room for a label. A diamond or an ellipse has less than its bounding box."""
    if kind == "diamond":
        return w * 0.5, h * 0.6
    if kind == "ellipse":
        return w * 0.7, h * 0.7
    return w - 16, h - 8


def seed(key: str) -> int:
    return zlib.crc32(key.encode("utf-8")) % 2147483647  # stable across runs, unlike hash()


def element(id_, kind, x, y, w, h, stroke, bg, **extra):
    el = {
        "id": id_, "type": kind,
        "x": round(x, 1), "y": round(y, 1), "width": round(w, 1), "height": round(h, 1),
        "angle": 0, "strokeColor": stroke, "backgroundColor": bg,
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": ROUGHNESS, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": {"type": 3} if kind == "rectangle" else None,
        "seed": seed(id_), "version": 1, "versionNonce": seed(id_ + "nonce"),
        "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False,
    }
    el.update(extra)
    return el


def text_el(id_, x, y, text, size=FONT, width=None, align="left", container=None):
    lines = text.split("\n")
    width = width or max(text_w(line, size) for line in lines)
    return element(id_, "text", x, y, width, len(lines) * size * LINE_H, INK, "transparent",
                   roughness=0, text=text, fontSize=size, fontFamily=2, textAlign=align,
                   verticalAlign="middle" if container else "top", containerId=container,
                   originalText=text, lineHeight=LINE_H, autoResize=True)


def boxed(id_, kind, x, y, w, h, style, text, size=FONT, stroke_width=2):
    """A box with its label centred inside, stored the way Excalidraw stores a bound text."""
    bg, stroke = PALETTE[style]
    ew, _ = inner_box(kind, w, h)
    lines = wrap(text, ew, size)
    th = len(lines) * size * LINE_H
    box = element(id_, kind, x, y, w, h, stroke, bg, strokeWidth=stroke_width,
                  boundElements=[{"type": "text", "id": f"{id_}:t"}])
    label = text_el(f"{id_}:t", x + (w - ew) / 2, y + (h - th) / 2, "\n".join(lines), size,
                    width=ew, align="center", container=id_)
    return [box, label]


def arrow_el(id_, points):
    x0, y0 = points[0]
    rel = [[round(px - x0, 1), round(py - y0, 1)] for px, py in points]
    xs, ys = [p[0] for p in rel], [p[1] for p in rel]
    return element(id_, "arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys), LINE, "transparent",
                   points=rel, lastCommittedPoint=None, startBinding=None, endBinding=None,
                   startArrowhead=None, endArrowhead="arrow")


def style_of(name, problems, where):
    if name in PALETTE:
        return name
    problems.append(f"{where}: unknown style '{name}' (use one of: {', '.join(PALETTE)})")
    return "white"


def resolve_tags(tag_map, tags, used, problems, where):
    """Return (label, style) of the first tag that has a style. Every tag used is kept for the legend."""
    found = None
    for dim, value in (tag_map or {}).items():
        cfg = tags.get(dim, {}).get(value)
        if cfg is None:
            problems.append(f"{where}: tag {dim}={value} is not defined under 'tags' in the spec")
            continue
        if "style" not in cfg:
            continue
        label = cfg.get("label", value)
        style = style_of(cfg["style"], problems, f"{where}: tag {dim}={value}")
        used.setdefault((dim, value), (label, style))
        if found is None:
            found = (label, style)
    return found


# ---------------------------------------------------------------- layout

def layout_block(block, top, spec, limits, drawing, problems):
    """Place one block at height `top`. Returns (elements, height)."""
    bid = block.get("id", "block")
    where = f"block '{bid}'"
    row_by = block.get("row_by")
    rows = spec.get("dimensions", {}).get(row_by)
    if rows is None:
        problems.append(f"{where}: row_by '{row_by}' is not a dimension in the spec")
        return [], 0
    lanes = block.get("lanes") or []
    if not 0 < len(lanes) <= limits["lanes"]:
        problems.append(f"{where}: {len(lanes)} lanes; the limit is {limits['lanes']}")
    if len(rows) > limits["rows"]:
        problems.append(f"{where}: {len(rows)} rows; the limit is {limits['rows']}")
    lane_at = {lane.get("id"): i for i, lane in enumerate(lanes)}
    row_at = {value: j for j, value in enumerate(rows)}
    row_names = spec.get("row_labels", {}).get(row_by, {})
    tags = spec.get("tags", {})

    x0 = ROW_LABEL_W + MARGIN

    def lane_x(i):
        return x0 + i * (LANE_W + LANE_GAP)

    header_y = top + TITLE_H
    rows_top = header_y + HEADER_H

    def row_y(j):
        return rows_top + j * ROW_H

    rows_bottom = rows_top + len(rows) * ROW_H
    block_w = x0 + len(lanes) * LANE_W + max(len(lanes) - 1, 0) * LANE_GAP + MARGIN
    used = {}  # (dim, value) -> (label, style), for the legend
    els = [text_el(f"{bid}:title", MARGIN, top, block.get("title", bid), size=18)]

    for i, lane in enumerate(lanes):
        lane_id = lane.get("id")
        if lane.get("frame"):  # frames go first so they sit behind the boxes
            conf = lane["frame"] if isinstance(lane["frame"], dict) else {}
            color = style_of(conf.get("color", "grey"), problems, f"{where}: frame of lane '{lane_id}'")
            bg, stroke = PALETTE[color]
            els.append(element(f"{bid}:frame:{lane_id}", "rectangle", lane_x(i) - FRAME_PAD, header_y,
                               LANE_W + 2 * FRAME_PAD, HEADER_H + len(rows) * ROW_H + FRAME_PAD,
                               stroke, bg, strokeStyle=conf.get("style", "solid")))
        label = lane.get("label", lane_id)
        if text_w(label, 16) > LANE_W:
            problems.append(f"{where}: lane label '{label}' is wider than the lane")
        els.append(text_el(f"{bid}:lane:{lane_id}", lane_x(i), header_y + 10, label, size=16))

    for j, value in enumerate(rows):
        label = row_names.get(value, value)
        lines = wrap(label, ROW_LABEL_W, FONT)
        if max(text_w(line, FONT) for line in lines) > ROW_LABEL_W:
            problems.append(f"{where}: row label '{label}' is wider than its column")
        y = row_y(j) + (ROW_H - len(lines) * FONT * LINE_H) / 2
        els.append(text_el(f"{bid}:row:{value}", MARGIN, y, "\n".join(lines)))

    placed, cells = {}, {}  # placed: node id -> lane, row and box
    for node in block.get("nodes") or []:
        nid = node.get("id")
        here = f"{where}: node '{nid}'"
        if nid in drawing["nodes"] or nid in placed:
            problems.append(f"{here}: id is used twice")
            continue
        if node.get("lane") not in lane_at or node.get("row") not in row_at:
            problems.append(f"{here}: lane or row is not in this block")
            continue
        i, j = lane_at[node["lane"]], row_at[node["row"]]
        if (i, j) in cells:
            problems.append(f"{here}: same lane and row as '{cells[(i, j)]}' (one node per cell)")
            continue
        cells[(i, j)] = nid
        shape = node.get("shape", "rectangle")
        if shape not in ("rectangle", "ellipse", "diamond"):
            problems.append(f"{here}: unknown shape '{shape}'")
            shape = "rectangle"
        found = resolve_tags(node.get("tags"), tags, used, problems, here)
        if "style" in node:
            style = style_of(node["style"], problems, here)
        else:
            style = found[1] if found else "white"
        text = node.get("text", "")
        ew, eh = inner_box(shape, NODE_W, NODE_H)
        lines = wrap(text, ew, FONT)
        if max(text_w(line, FONT) for line in lines) > ew or len(lines) * FONT * LINE_H > eh:
            problems.append(f"{here}: text does not fit the box: {text!r}")
        x = lane_x(i) + (LANE_W - NODE_W) / 2
        y = row_y(j) + (ROW_H - NODE_H) / 2
        els += boxed(nid, shape, x, y, NODE_W, NODE_H, style, text)
        placed[nid] = {"lane": i, "row": j, "box": (x, y, x + NODE_W, y + NODE_H)}
        drawing["nodes"][nid] = placed[nid]["box"]

    routes = []  # (arrow id, spec, from, to, from-node, to-node, kind)
    for k, edge in enumerate(block.get("edges") or []):
        eid = edge.get("id", f"{bid}:edge:{k}")
        here = f"{where}: arrow '{eid}'"
        a, b = placed.get(edge.get("from")), placed.get(edge.get("to"))
        if a is None or b is None:
            problems.append(f"{here}: from or to is not a node of this block")
            continue
        if eid in drawing["edges"] or any(r[0] == eid for r in routes):
            problems.append(f"{here}: id is used twice")
            continue
        if a["lane"] == b["lane"]:
            kind = "vertical"
        elif a["row"] == b["row"]:
            kind = "horizontal"
        else:
            kind = "elbow"
        routes.append((eid, edge, edge["from"], edge["to"], a, b, kind))

    # elbow arrows share the gap between two lanes; each gets its own x so their vertical pieces do not meet
    gaps = {}
    for route in routes:
        if route[6] == "elbow":
            gaps.setdefault(min(route[4]["lane"], route[5]["lane"]), []).append(route)
    x_mid = {}
    gap_w = LANE_GAP - 2 * (FRAME_PAD + 6)
    for g, group in gaps.items():
        group.sort(key=lambda r: (r[4]["row"], r[5]["row"]))
        for k, route in enumerate(group):
            x_mid[route[0]] = lane_x(g) + LANE_W + FRAME_PAD + 6 + (k + 1) * gap_w / (len(group) + 1)

    for eid, edge, src, dst, a, b, kind in routes:
        ax0, ay0, ax1, ay1 = a["box"]
        bx0, by0, bx1, by1 = b["box"]
        acx, acy = (ax0 + ax1) / 2, (ay0 + ay1) / 2
        bcy = (by0 + by1) / 2
        if kind == "vertical":
            pts = [(acx, ay1), (acx, by0)] if b["row"] > a["row"] else [(acx, ay0), (acx, by1)]
        elif kind == "horizontal":
            pts = [(ax1, acy), (bx0, bcy)] if b["lane"] > a["lane"] else [(ax0, acy), (bx1, bcy)]
        else:
            mx = x_mid[eid]
            pts = ([(ax1, acy), (mx, acy), (mx, bcy), (bx0, bcy)] if b["lane"] > a["lane"]
                   else [(ax0, acy), (mx, acy), (mx, bcy), (bx1, bcy)])
        els.append(arrow_el(eid, pts))
        drawing["edges"][eid] = {"from": src, "to": dst, "points": pts}

        tag = resolve_tags(edge.get("tag"), tags, used, problems, f"{where}: arrow '{eid}'")
        label = edge.get("badge") or (tag[0] if tag else None)
        if not label:
            continue
        style = style_of(edge["badge_style"], problems, f"{where}: arrow '{eid}'") if "badge_style" in edge \
            else (tag[1] if tag else "grey")
        bw, bh = text_w(label, FONT_SMALL) + 24, 26
        if kind == "vertical":  # label sits to the right of the line
            cx, cy = pts[0][0] + 8 + bw / 2, (pts[0][1] + pts[1][1]) / 2
        elif kind == "horizontal":  # label sits above the line
            cx, cy = (pts[0][0] + pts[1][0]) / 2, acy - 21
        else:  # label sits on the vertical piece
            cx, cy = x_mid[eid], (acy + bcy) / 2
        left, top_y = cx - bw / 2, cy - bh / 2
        els += boxed(f"{eid}:badge", "rectangle", left, top_y, bw, bh, style, label,
                     size=FONT_SMALL, stroke_width=1.5)
        drawing["badges"][eid] = (left, top_y, left + bw, top_y + bh)

    legend_y = rows_bottom + FRAME_PAD + 14
    lx = MARGIN
    for (dim, value), (label, style) in used.items():
        bg, stroke = PALETTE[style]
        els.append(element(f"{bid}:legend:{dim}:{value}", "rectangle", lx, legend_y, 16, 16, stroke, bg))
        els.append(text_el(f"{bid}:legend:{dim}:{value}:t", lx + 22, legend_y, label, size=FONT_SMALL))
        lx += 22 + text_w(label, FONT_SMALL) + 28
    if used and lx - 28 > block_w:
        problems.append(f"{where}: legend is wider than the block; use fewer tags")

    height = TITLE_H + HEADER_H + len(rows) * ROW_H + (LEGEND_H if used else 0)
    return els, height


def stale_patterns():
    """Regexes from the project's stale-patterns.json. A hit in a diagram is an error."""
    if not STALE_FILE.exists():
        return []
    cfg = json.loads(STALE_FILE.read_text(encoding="utf-8"))
    return [(re.compile(p["regex"]), p.get("why", "")) for p in cfg.get("patterns", [])]


def build(spec: dict):
    """Return (elements, drawing, problems) for the whole spec."""
    problems = []
    limits = {**DEFAULT_LIMITS, **spec.get("limits", {})}
    for dim, values in spec.get("dimensions", {}).items():
        if not all(isinstance(v, str) for v in values):
            problems.append(f"dimension '{dim}': values must be strings, e.g. \"0.1\"")
    blocks = spec.get("blocks") or []
    if not blocks:
        problems.append("spec has no blocks")
    if len(blocks) > limits["blocks"]:
        problems.append(f"{len(blocks)} blocks in one file; the limit is {limits['blocks']}")
    drawing = {"nodes": {}, "edges": {}, "badges": {}}
    elements, top = [], 0
    for block in blocks:
        block_els, height = layout_block(block, top, spec, limits, drawing, problems)
        elements += block_els
        top += height + BLOCK_GAP
    stale = stale_patterns()
    for el in elements:
        if el["type"] != "text":
            continue
        text = el["text"]
        if FORBIDDEN.search(text):
            problems.append(f"text uses an emoji or a circled digit (write plain numbers): {text!r}")
        for regex, why in stale:
            if regex.search(text):
                problems.append(f"text {text!r} matches stale value /{regex.pattern}/: {why}")
    return elements, drawing, problems


# ---------------------------------------------------------------- check

def overlaps(a, b):
    """Two boxes (x0, y0, x1, y1) overlap in their interiors. Touching edges do not count."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def pieces(points):
    """Each straight piece of an arrow as its bounding box. Every piece is horizontal or vertical."""
    return [(min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1]))
            for p, q in zip(points, points[1:])]


def piece_hits_box(s, box):
    return s[0] < box[2] and s[2] > box[0] and s[1] < box[3] and s[3] > box[1]


def pieces_touch(s, t):
    return s[0] <= t[2] and s[2] >= t[0] and s[1] <= t[3] and s[3] >= t[1]


def check(drawing: dict) -> list[str]:
    """Geometry checks on the computed boxes, badges and arrows. Returns the problems found."""
    problems = []
    nodes, edges, badges = drawing["nodes"], drawing["edges"], drawing["badges"]
    segs = {eid: pieces(e["points"]) for eid, e in edges.items()}
    node_ids, edge_ids = list(nodes), list(edges)

    for i, a in enumerate(node_ids):
        for b in node_ids[i + 1:]:
            if overlaps(nodes[a], nodes[b]):
                problems.append(f"boxes overlap: '{a}' and '{b}'")
    for eid in edge_ids:
        e = edges[eid]
        for nid, box in nodes.items():
            if nid not in (e["from"], e["to"]) and any(piece_hits_box(s, box) for s in segs[eid]):
                problems.append(f"arrow '{eid}' passes through box '{nid}'")
    for i, a in enumerate(edge_ids):
        for b in edge_ids[i + 1:]:
            ea, eb = edges[a], edges[b]
            if {ea["from"], ea["to"]} & {eb["from"], eb["to"]}:
                continue  # arrows that leave or enter the same box meet at that box
            if any(pieces_touch(s, t) for s in segs[a] for t in segs[b]):
                problems.append(f"arrows cross: '{a}' and '{b}'")
    for eid, box in badges.items():
        for nid, nbox in nodes.items():
            if overlaps(box, nbox):
                problems.append(f"label of arrow '{eid}' covers box '{nid}'")
        for other in edge_ids:
            if other != eid and any(piece_hits_box(s, box) for s in segs[other]):
                problems.append(f"label of arrow '{eid}' covers arrow '{other}'")
    bids = list(badges)
    for i, a in enumerate(bids):
        for b in bids[i + 1:]:
            if overlaps(badges[a], badges[b]):
                problems.append(f"labels overlap: arrows '{a}' and '{b}'")
    return problems


# ---------------------------------------------------------------- command line

def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    try:
        spec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        print(f"ERROR  cannot read the spec: {err}")
        return 2
    elements, drawing, problems = build(spec)
    target_rel = spec.get("file", "")
    if not target_rel:
        problems.append("spec has no 'file'")
    elif not FILE_NAME.match(Path(target_rel).name):
        problems.append(f"file name '{Path(target_rel).name}' must be lower-case words joined by dashes, ending .excalidraw")
    problems += check(drawing)
    if problems:
        for p in problems:
            print(f"ERROR  {p}")
        print(f"{len(problems)} problem(s); nothing written")
        return 1
    if check_only:
        print(f"OK  {len(elements)} elements, no problems (--check: nothing written)")
        return 0
    target = REPO / target_rel
    data = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
            "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"}, "files": {}}
    if target.exists():  # keep what the editor stored besides the elements
        data.update({k: v for k, v in json.loads(target.read_text(encoding="utf-8")).items() if k != "elements"})
    data["elements"] = elements
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {target}: {len(elements)} elements, no problems")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
