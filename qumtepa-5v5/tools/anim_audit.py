"""3-shaxs animatsiyalarini tahlil qilish (Blender bpy, oynasiz rejim).

Ishlatish:  python3 anim_audit.py <fayl.glb> <chiqish_papkasi> [--render]
Natija:     <chiqish>/<nom>_audit.json va <nom>_audit.md (jadval), --render bo'lsa 0/25/50/75% kadrlar
            oldidan, yonidan va tepadan (PNG).
Koordinatalar (Blender): Z — tepa, qahramon −Y ga qaraydi (glTF +Z oldinga), pol z = 0.
"""
import bpy, bmesh, math, json, os, sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

P = "mixamorig:"
LIMITS = {"float_cm": 1.0, "slide_cm": 1.0, "spine_deg": 5.0, "shoulder_deg": 3.0, "hands_cm": (35.0, 45.0)}


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 24
    bpy.ops.import_scene.gltf(filepath=path)
    arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
    body = [o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() == arm][0]
    return arm, body


def vgroups(body):
    gi = {g.index: g.name for g in body.vertex_groups}
    top = []
    for v in body.data.vertices:
        ws = sorted(((g.weight, gi[g.group]) for g in v.groups), reverse=True)
        top.append(ws[0][1] if ws else "")
    return np.array(top)


def evaluated(body):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    M = np.array(ev.matrix_world)
    V = V @ M[:3, :3].T + M[:3, 3]
    ev.to_mesh_clear()
    return V


def bone_head(arm, name):
    return np.array(arm.matrix_world @ arm.pose.bones[P + name].head)


def ang(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    return math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b)))))


def quat_angle(q1, q2):
    d = abs(float(np.dot(q1, q2)))
    return math.degrees(2 * math.acos(min(1.0, d)))


def audit_action(arm, body, act, top, torso_faces):
    sc = bpy.context.scene
    arm.animation_data.action = act
    f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
    frames = list(range(f0, f1 + 1))
    feet = {s: np.isin(top, [P + s + n for n in ("Foot", "ToeBase", "Toe_End")]) for s in ("Left", "Right")}
    hands = {s: np.isin(top, [P + s + n for n in ("Hand", "HandMiddle4")]) for s in ("Left", "Right")}
    rec = {k: [] for k in ("height", "zmin", "footL", "footR", "heelL", "heelR", "toeL", "toeR", "footL_xy", "footR_xy",
                           "hips", "spine", "lumbar", "shoulder", "kneeL", "kneeR", "kneeL_rev", "kneeR_rev",
                           "hands_cm", "hands_fwd", "hands_dz", "inside_R", "inside_L", "fwd")}
    quats = {pb.name: [] for pb in arm.pose.bones}
    for f in frames:
        sc.frame_set(f)
        bpy.context.view_layer.update()
        V = evaluated(body)
        rec["height"].append(float(V[:, 2].max() - V[:, 2].min()))
        rec["zmin"].append(float(V[:, 2].min()))
        fwd_toes = []
        for s, k in (("Left", "L"), ("Right", "R")):
            fv = V[feet[s]]
            rec["foot" + k].append(float(fv[:, 2].min()))
            ank = bone_head(arm, s + "Foot")
            toe = bone_head(arm, s + "Toe_End")
            fd = toe - ank; fd[2] = 0
            fd /= max(1e-6, np.linalg.norm(fd))
            fwd_toes.append(fd)
            proj = (fv - ank) @ fd
            heel = fv[proj < np.percentile(proj, 30)]
            toe_ = fv[proj > np.percentile(proj, 70)]
            rec["heel" + k].append(float(heel[:, 2].min()))
            rec["toe" + k].append(float(toe_[:, 2].min()))
            low = fv[fv[:, 2] < fv[:, 2].min() + 0.01]
            rec["foot" + k + "_xy"].append(low[:, :2].mean(0).tolist())
        fwd = fwd_toes[0] + fwd_toes[1]
        fwd /= max(1e-6, np.linalg.norm(fwd))
        rec["fwd"].append(fwd.tolist())
        hips = bone_head(arm, "Hips")
        rec["hips"].append(hips.tolist())
        neck = bone_head(arm, "Neck")
        sp1 = bone_head(arm, "Spine1")
        up = np.array([0, 0, 1.0])
        v = neck - hips
        rec["spine"].append(ang(v, up) * (1 if v @ fwd >= 0 else -1))         # + oldinga, − orqaga
        v2 = sp1 - hips
        rec["lumbar"].append(ang(v2, up) * (1 if v2 @ fwd >= 0 else -1))
        la, ra = bone_head(arm, "LeftArm"), bone_head(arm, "RightArm")
        d = la - ra
        rec["shoulder"].append(math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))))
        for s, k in (("Left", "L"), ("Right", "R")):
            h, kn, an = bone_head(arm, s + "UpLeg"), bone_head(arm, s + "Leg"), bone_head(arm, s + "Foot")
            rec["knee" + k].append(180.0 - ang(h - kn, an - kn))                    # 0 — to'g'ri, + bukilgan
            # tizza son-to'piq chizig'idan oldinda (+) yoki orqada (− — teskari bukilish)
            t = np.clip((kn - h) @ (an - h) / max(1e-6, (an - h) @ (an - h)), 0, 1)
            off = kn - (h + t * (an - h))
            rec["knee" + k + "_rev"].append(float(off @ fwd))
        palms = {}
        for s in ("Left", "Right"):
            w = bone_head(arm, s + "Hand")
            m4 = bone_head(arm, s + "HandMiddle4")
            palms[s] = w + (m4 - w) / max(1e-6, np.linalg.norm(m4 - w)) * 0.08
        dv = palms["Left"] - palms["Right"]
        rec["hands_cm"].append(float(np.linalg.norm(dv) * 100))
        dh = dv.copy(); dh[2] = 0
        rec["hands_fwd"].append(ang(dh, fwd) if np.linalg.norm(dh) > 1e-4 else 90.0)
        rec["hands_dz"].append(float(dv[2] * 100))
        # qo'l tanaga kirganmi: kaft markazidan nur — tana (qo'lsiz) yuzalari bilan kesishishlar soni toq bo'lsa, ichkarida
        tri = V[torso_faces]
        bvh = BVHTree.FromPolygons([Vector(p) for p in V], torso_faces.tolist())
        for s, k in (("Left", "L"), ("Right", "R")):
            o = Vector(palms[s])
            n = 0
            cur = o.copy()
            for _ in range(20):
                hit = bvh.ray_cast(cur, Vector((0.013, 0.021, 1.0)).normalized(), 5.0)
                if hit[0] is None:
                    break
                n += 1
                cur = hit[0] + Vector((0.013, 0.021, 1.0)).normalized() * 1e-4
            rec["inside_" + k].append(n % 2 == 1)
        for pb in arm.pose.bones:
            q = pb.rotation_quaternion if pb.rotation_mode == "QUATERNION" else pb.rotation_euler.to_quaternion()
            quats[pb.name].append(np.array(q[:]))
    # --- xulosalar
    R = {"frames": len(frames), "frame_range": [f0, f1], "fps": sc.render.fps, "duration_s": (f1 - f0) / sc.render.fps}
    R["height_m"] = [round(min(rec["height"]), 3), round(max(rec["height"]), 3)]
    R["floor_zmin_cm"] = round(min(rec["zmin"]) * 100, 2)
    for k in ("L", "R"):
        a = np.array(rec["foot" + k]) * 100
        R[f"foot{k}_cm"] = [round(a.min(), 2), round(a.max(), 2)]
        R[f"heel{k}_cm"] = [round(min(rec["heel" + k]) * 100, 2), round(max(rec["heel" + k]) * 100, 2)]
        R[f"toe{k}_cm"] = [round(min(rec["toe" + k]) * 100, 2), round(max(rec["toe" + k]) * 100, 2)]
        stance = a < a.min() + 2.0
        xy = np.array(rec["foot" + k + "_xy"])
        slide = 0.0
        i = 0
        while i < len(stance):
            if stance[i]:
                j = i
                while j + 1 < len(stance) and stance[j + 1]:
                    j += 1
                seg = xy[i:j + 1]
                slide = max(slide, float(np.linalg.norm(seg - seg[0], axis=1).max() * 100))
                i = j + 1
            else:
                i += 1
        R[f"slide{k}_cm"] = round(slide, 2)
        R[f"float{k}_frames"] = int((a > LIMITS["float_cm"]).sum())
        R[f"sink{k}_frames"] = int((a < -LIMITS["float_cm"]).sum())
    H = np.array(rec["hips"])
    R["root_xy_cm"] = round(float(np.linalg.norm(H[-1, :2] - H[0, :2]) * 100), 2)
    R["root_xy_max_cm"] = round(float(np.linalg.norm(H[:, :2] - H[0, :2], axis=1).max() * 100), 2)
    R["root_z_range_cm"] = round(float((H[:, 2].max() - H[:, 2].min()) * 100), 2)
    R["origin"] = [round(x, 3) for x in arm.matrix_world.translation]
    ff = np.array([rec["footL_xy"][0], rec["footR_xy"][0]]).mean(0)
    R["feet_center_xy_cm"] = [round(ff[0] * 100, 1), round(ff[1] * 100, 1)]
    fw = np.array(rec["fwd"][0])
    R["facing_deg_from_minusY"] = round(math.degrees(math.atan2(fw[0], -fw[1])), 1)
    # loop
    loop = []
    for n, qs in quats.items():
        loop.append((quat_angle(qs[0], qs[-1]), n))
    loop.sort(reverse=True)
    R["loop_max_deg"] = [round(loop[0][0], 2), loop[0][1].replace(P, "")]
    R["loop_hips_cm"] = round(float(np.linalg.norm(H[-1] - H[0]) * 100), 2)
    # titrash: burchak tezligining keskin o'zgarishi (2-hosila) — kichik "sakrashlar"
    jit = []
    for n, qs in quats.items():
        a = np.array([quat_angle(qs[i], qs[i + 1]) for i in range(len(qs) - 1)])
        if len(a) < 3:
            continue
        acc = np.abs(np.diff(a))
        thr = max(0.5, 4 * float(np.median(acc)))
        spikes = int((acc > thr).sum())
        jit.append((spikes, round(float(acc.max()), 2), n.replace(P, "")))
    jit.sort(reverse=True)
    R["jitter_top"] = jit[:5]
    R["jitter_total_spikes"] = int(sum(j[0] for j in jit))
    for k, lim in (("spine", LIMITS["spine_deg"]), ("lumbar", None), ("shoulder", LIMITS["shoulder_deg"])):
        a = np.array(rec[k])
        R[f"{k}_deg"] = [round(a.min(), 1), round(a.max(), 1)]
    for k in ("L", "R"):
        R[f"knee{k}_deg"] = [round(min(rec["knee" + k]), 1), round(max(rec["knee" + k]), 1)]
        R[f"knee{k}_reverse_frames"] = int((np.array(rec["knee" + k + "_rev"]) < -0.005).sum())
    R["hands_cm"] = [round(min(rec["hands_cm"]), 1), round(max(rec["hands_cm"]), 1)]
    R["hands_line_vs_forward_deg"] = [round(min(rec["hands_fwd"]), 1), round(max(rec["hands_fwd"]), 1)]
    R["hands_height_diff_cm"] = [round(min(rec["hands_dz"]), 1), round(max(rec["hands_dz"]), 1)]
    R["hand_inside_body_frames"] = {"R": int(sum(rec["inside_R"])), "L": int(sum(rec["inside_L"]))}
    return R


def render(arm, body, act, out, tag):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.samples = 6; sc.cycles.device = "CPU"
    sc.render.resolution_x, sc.render.resolution_y = 380, 460
    if sc.world is None:
        w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
        w.node_tree.nodes["Background"].inputs[0].default_value = (0.82, 0.84, 0.87, 1)
        w.node_tree.nodes["Background"].inputs[1].default_value = 1.3
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
        sun.data.energy = 2.5; sun.rotation_euler = (math.radians(40), 0, math.radians(30))
        bpy.ops.mesh.primitive_plane_add(size=4)
        g = bpy.context.active_object; g.name = "pol"
        mat = bpy.data.materials.new("pol"); mat.use_nodes = True
        mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.5, 0.5, 0.52, 1); g.data.materials.append(mat)
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
        cam.data.type = "ORTHO"
    cam = sc.camera
    arm.animation_data.action = act
    f0, f1 = act.frame_range
    paths = []
    for pct in (0, 25, 50, 75):
        f = int(round(f0 + (f1 - f0) * pct / 100))
        sc.frame_set(f)
        for vn, loc, rot, osc in (("old", (0, -5, 0.95), (90, 0, 0), 2.2), ("yon", (5, 0, 0.95), (90, 0, 90), 2.2),
                                  ("tepa", (0, 0, 5), (0, 0, 0), 1.6)):
            cam.location = loc; cam.rotation_euler = [math.radians(a) for a in rot]; cam.data.ortho_scale = osc
            p = os.path.join(out, f"{tag}_{pct:02d}_{vn}.png")
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            paths.append(p)
    return paths


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path, out = args[0], args[1]
    os.makedirs(out, exist_ok=True)
    arm, body = load(path)
    top = vgroups(body)
    armish = ("Arm", "Hand", "Middle4", "Fingers", "Shoulder")
    torso_v = ~np.array([any(k in t for k in armish) for t in top])
    faces = np.array([p.vertices[:3] for p in body.data.polygons if len(p.vertices) >= 3 and all(torso_v[i] for i in p.vertices[:3])])
    report = {"file": os.path.basename(path), "bones": [b.name.replace(P, "") for b in arm.data.bones],
              "actions": {a.name: [round(a.frame_range[0], 2), round(a.frame_range[1], 2)] for a in bpy.data.actions},
              "animations": {}}
    tag = os.path.splitext(os.path.basename(path))[0]
    for act in list(bpy.data.actions):
        r = audit_action(arm, body, act, top, faces)
        report["animations"][act.name] = r
        if "--render" in sys.argv and r["frames"] > 5:
            r["renders"] = render(arm, body, act, out, tag)
    json.dump(report, open(os.path.join(out, f"{tag}_audit.json"), "w"), indent=1)
    print(json.dumps(report, indent=1)[:6000])


if __name__ == "__main__":
    main()
