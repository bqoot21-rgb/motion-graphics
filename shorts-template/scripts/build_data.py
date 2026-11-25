"""Build src/data.json from TTS segments: scene timeline + one-line subtitle chunks."""
import json, sys
FPS = 30
MAXC = 15  # max characters per subtitle line (no spaces)
segs = json.load(open(sys.argv[1]))[: int(sys.argv[2])]
ALIAS = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {"lady": "pool"}  # scenes that continue the same shot
for s_ in segs:
    s_["scene"] = ALIAS.get(s_["scene"], s_["scene"])
scenes, cur = [], 0.0
for i, s in enumerate(segs):
    new = not scenes or scenes[-1]["key"] != s["scene"]
    if new:
        if scenes:
            scenes[-1]["dur"] = cur + 0.25 - scenes[-1]["start"]; cur += 0.25
        scenes.append({"key": s["scene"], "start": cur, "segs": []})
    st = cur + (0.2 if new else 0.15)
    words = s["words"]
    toks = s["text"].split(" ")
    if len(toks) != len(words):
        toks = [w[2] for w in words]
    # split into the fewest single lines (<= MAXC chars), balanced, preferring breaks after punctuation
    import math
    L = [len(t) for t in toks]
    n = len(toks)
    total_c = sum(L)
    k = max(1, math.ceil(total_c / MAXC))
    best = None
    def rec(i, parts, acc):
        global best
        if len(parts) == k - 1:
            seg = toks[i:]
            if sum(len(t) for t in seg) > MAXC + 2 and k > 0:
                pass
            cand = parts + [(i, n)]
            lens = [sum(L[a:b]) for a, b in cand]
            if max(lens) > MAXC + 2:
                return
            cost = sum((x - total_c / k) ** 2 for x in lens)
            cost -= sum(8 for a, b in cand[:-1] if toks[b - 1].endswith((",", ".", "?", "!")))
            if best is None or cost < best[0]:
                best = (cost, cand)
            return
        for j in range(i + 1, n - (k - 2 - len(parts))):
            rec(j, parts + [(i, j)], acc)
    while best is None:
        rec(0, [], 0)
        if best is None:
            k += 1
    chunks = [list(zip(toks[a:b], words[a:b])) for a, b in best[1]]
    out = []
    for ch in chunks:
        out.append({"from": st + ch[0][1][0], "to": st + ch[-1][1][1],
                    "words": [{"t": tk, "s": st + w[0], "e": st + w[1]} for tk, w in ch]})
    for a, b in zip(out, out[1:]):
        a["to"] = b["from"]  # hold each line until the next one starts
    scenes[-1]["segs"].append({"i": i, "speaker": s["speaker"], "abs": st, "chunks": out,
                               "end": st + words[-1][1]})
    cur = st + words[-1][1]
scenes[-1]["dur"] = cur + 0.9 - scenes[-1]["start"]
total = scenes[-1]["start"] + scenes[-1]["dur"]
json.dump({"fps": FPS, "total": total, "scenes": scenes}, open(sys.argv[3] if len(sys.argv) > 3 else "src/data.json", "w"), ensure_ascii=False, indent=1)
print(round(total, 2), [(s["key"], round(s["start"], 2)) for s in scenes])
for s in scenes:
    for g in s["segs"]:
        print(g["speaker"], [" ".join(w["t"] for w in c["words"]) for c in g["chunks"]])
