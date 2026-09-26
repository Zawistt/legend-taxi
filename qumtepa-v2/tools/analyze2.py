"""Stage-2 checks on top of the stage-1 nav grid: spawn fairness, AI point reachability,
zone sanity, and a blueprint with zones/spawns/bot points."""
import json, math
from PIL import Image, ImageDraw, ImageFont
import analyze as A          # runs stage-1 analysis and exposes route/sp/walk helpers
import layout as L

SPEED = A.SPEED
EXITS = {"T": {"Long doors": (-14.0, -22.0), "Top mid chiqishi": (0.0, -16.0), "Tunnels": (9.0, -21.5)},
         "CT": {"A ramp yo'li": (-9.5, 17.0), "CT mid chiqishi": (0.0, 14.0), "B ramp yo'li": (9.5, 17.0)}}

spawn_report = {}
for team, pts in L.SPAWNS.items():
    rows = []
    for p in pts:
        ex = {k: round(A.sp(p, q)[0] / SPEED, 2) for k, q in EXITS[team].items()}
        rows.append({"pos": p, "nearest_exit_s": min(ex.values()), "exits": ex,
                     "A_s": round(A.route([p, L.A_PLANT])[0] / SPEED, 2),
                     "B_s": round(A.route([p, L.B_PLANT])[0] / SPEED, 2)})
    ne = [r["nearest_exit_s"] for r in rows]
    spawn_report[team] = {"slots": rows, "nearest_exit_spread_s": round(max(ne) - min(ne), 2)}


def walkable(x, z):
    ix, iz = A.to_px(x, z)
    return bool(A.walk[iz, ix])


def on_platform(x, z):
    for x0, z0, x1, z1, h in A.meta["plat"]:
        if x0 <= x <= x1 and z0 <= z <= z1:
            return h
    return 0.0


ai_report = []
for label, kind, team, x, z in L.AI_POINTS:
    start = L.T_SPAWN if team == "T" else L.CT_SPAWN
    d, _ = A.route([start, (x, z)])
    ai_report.append({"label": label, "kind": kind, "team": team, "pos": [x, on_platform(x, z), z],
                      "walkable": walkable(x, z) or on_platform(x, z) > 0, "from_spawn_s": round(d / SPEED, 1),
                      "callout": A.region((x, z))})

zone_checks = {
    "A plant inside A zone": L.BOMB_ZONES["A"][0] <= L.A_PLANT[0] <= L.BOMB_ZONES["A"][2] and L.BOMB_ZONES["A"][1] <= L.A_PLANT[1] <= L.BOMB_ZONES["A"][3],
    "B plant inside B zone": L.BOMB_ZONES["B"][0] <= L.B_PLANT[0] <= L.BOMB_ZONES["B"][2] and L.BOMB_ZONES["B"][1] <= L.B_PLANT[1] <= L.BOMB_ZONES["B"][3],
    "spawns inside own buy zone": all(L.BUY_ZONES[t][0] <= x <= L.BUY_ZONES[t][2] and L.BUY_ZONES[t][1] <= z <= L.BUY_ZONES[t][3]
                                      for t, pts in L.SPAWNS.items() for x, z in pts),
    "all spawns walkable": all(walkable(x, z) for pts in L.SPAWNS.values() for x, z in pts),
    "all AI points reachable": all(a["walkable"] and math.isfinite(a["from_spawn_s"]) for a in ai_report),
}
# retake budget: CT rotation + defuse must fit in the bomb timer
retake = {"worst_CT_arrival_s": max(A.R["CT → A"]["time"], A.R["CT rotatsiya A → B"]["time"]),
          "defuse_s": L.ROUND["defuse_time"], "bomb_timer_s": L.ROUND["bomb_timer"]}
retake["spare_s"] = round(retake["bomb_timer_s"] - retake["worst_CT_arrival_s"] - retake["defuse_s"], 1)

out = {"spawns": spawn_report, "ai_points": ai_report, "zone_checks": zone_checks, "retake": retake}
json.dump(out, open("analysis_stage2.json", "w"), ensure_ascii=False, indent=1)
json.dump({"bombsites": L.BOMB_ZONES, "buyzones": L.BUY_ZONES, "spawns": L.SPAWNS,
           "strategic": [[a["label"], a["kind"], a["team"], a["pos"][0], a["pos"][1], a["pos"][2]] for a in ai_report]},
          open("zones_data.json", "w"), ensure_ascii=False)

# ---------------------------------------------------------------- blueprint with zones
img = Image.open("blueprint_v2.png").convert("RGBA")
ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
P = A.P
for k, (x0, z0, x1, z1) in L.BOMB_ZONES.items():
    d.rectangle([*P(x0, z0), *P(x1, z1)], fill=(217, 65, 46, 45), outline=(217, 65, 46, 255), width=3)
for k, (x0, z0, x1, z1) in L.BUY_ZONES.items():
    d.rectangle([*P(x0, z0), *P(x1, z1)], fill=(58, 163, 90, 40), outline=(40, 130, 70, 255), width=3)
for team, pts in L.SPAWNS.items():
    col = (214, 96, 30, 255) if team == "T" else (40, 92, 170, 255)
    for i, (x, z) in enumerate(pts):
        cx_, cy_ = P(x, z)
        d.ellipse([cx_ - 9, cy_ - 9, cx_ + 9, cy_ + 9], fill=col, outline=(255, 255, 255, 255), width=2)
        d.text((cx_, cy_), str(i + 1), font=ImageFont.truetype(A.FB, 11), fill=(255, 255, 255, 255), anchor="mm")
KC = {"plant": (217, 65, 46), "hold": (40, 92, 170), "entry": (214, 96, 30), "retake": (31, 138, 154), "rotate": (138, 79, 192)}
for a in ai_report:
    cx_, cy_ = P(a["pos"][0], a["pos"][2])
    c = KC[a["kind"]]
    d.polygon([(cx_, cy_ - 9), (cx_ + 8, cy_ + 6), (cx_ - 8, cy_ + 6)], fill=(*c, 255), outline=(255, 255, 255, 255))
img = Image.alpha_composite(img, ov).convert("RGB")
d = ImageDraw.Draw(img)
# replace side panel
X = A.OX + 50 * A.S + 36
d.rectangle([X - 10, 0, img.size[0], img.size[1]], fill=(236, 224, 200))
f16 = ImageFont.truetype(A.F, 16); fb16 = ImageFont.truetype(A.FB, 16)
f22 = ImageFont.truetype(A.FB, 22); f30 = ImageFont.truetype(A.FB, 30); f14 = ImageFont.truetype(A.F, 14)
y = A.OY
d.text((X, y), "Qumtepa v2 — 2-bosqich", font=f30, fill=(40, 28, 18)); y += 46
d.text((X, y), "Zonalar, spawn'lar, botlar uchun nuqtalar", font=f16, fill=(90, 70, 50)); y += 36
d.text((X, y), "Spawn adolatliligi", font=f22, fill=(40, 28, 18)); y += 32
for team in ("T", "CT"):
    r = spawn_report[team]
    ne = [s["nearest_exit_s"] for s in r["slots"]]
    d.text((X, y), f"{team}: chiqishgacha {min(ne):.1f}–{max(ne):.1f} s (farq {r['nearest_exit_spread_s']:.2f} s)", font=f16, fill=(40, 28, 18)); y += 24
y += 12
d.text((X, y), "Raund qoidalari", font=f22, fill=(40, 28, 18)); y += 32
RD = L.ROUND
for line in (f"Tayyorgarlik {RD['freeze']:.0f} s, sotib olish {RD['buy_time']:.0f} s",
             f"Raund {int(RD['round_time']) // 60}:{int(RD['round_time']) % 60:02d}, bomba taymeri {RD['bomb_timer']:.0f} s",
             f"O'rnatish {RD['plant_time']:.0f} s, zararsizlantirish {RD['defuse_time']:.0f} s",
             f"Qaytarib olish zaxirasi: {retake['spare_s']:.1f} s", f"G'alaba: {RD['win_rounds']} raund"):
    d.text((X, y), line, font=f16, fill=(40, 28, 18)); y += 24
y += 12
d.text((X, y), "Tekshiruvlar", font=f22, fill=(40, 28, 18)); y += 32
names = {"A plant inside A zone": "A plant zona ichida", "B plant inside B zone": "B plant zona ichida",
         "spawns inside own buy zone": "Spawn'lar sotib olish zonasida", "all spawns walkable": "Spawn'lar bo'sh joyda",
         "all AI points reachable": f"{len(ai_report)} ta bot nuqtasiga yetib boriladi"}
for k, v in zone_checks.items():
    d.text((X, y), ("✓ " if v else "✗ ") + names[k], font=f16, fill=(40, 110, 50) if v else (170, 30, 20)); y += 24
y += 16
for col, txt in (((217, 65, 46), "Bomba zonasi"), ((58, 163, 90), "Sotib olish zonasi"), ((214, 96, 30), "T spawn (1–5)"), ((40, 92, 170), "CT spawn (1–5)")):
    d.rectangle([X, y + 3, X + 16, y + 17], fill=col); d.text((X + 26, y), txt, font=f14, fill=(40, 28, 18)); y += 22
y += 6
d.text((X, y), "Uchburchaklar — botlar uchun nuqtalar:", font=f14, fill=(40, 28, 18)); y += 22
for k, c in KC.items():
    nm = {"plant": "plant", "hold": "ushlash", "entry": "kirish", "retake": "qaytarib olish", "rotate": "aylanish"}[k]
    d.polygon([(X + 8, y + 2), (X + 16, y + 16), (X, y + 16)], fill=c); d.text((X + 26, y), nm, font=f14, fill=(40, 28, 18)); y += 22
img.save("blueprint_stage2.png")
print(json.dumps({"spawns": {t: spawn_report[t]["nearest_exit_spread_s"] for t in spawn_report}, "zone_checks": zone_checks,
                  "retake": retake, "unreachable": [a["label"] for a in ai_report if not a["walkable"]]}, ensure_ascii=False, indent=1))
for t in ("T", "CT"):
    for s in spawn_report[t]["slots"]:
        print(t, s["pos"], "exit", s["nearest_exit_s"], "A", s["A_s"], "B", s["B_s"])
