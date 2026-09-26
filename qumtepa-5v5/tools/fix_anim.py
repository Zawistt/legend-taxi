"""3-shaxs animatsiyasini tuzatish (Blender bpy, oynasiz rejim): CT qahramoni, M416.

Ishlatish: python3 fix_anim.py <asl.glb> <chiqish.glb> <animatsiya_nomi> [--checks <papka>]
Asl fayl o'zgarmaydi. Qilinadigan ishlar (tartib bilan):
  1. ortiqcha action'lar o'chiriladi, asosiysi <nom> deb ataladi; 24 -> 30 kadr/s (vaqt bo'yicha qayta namuna);
  2. o'lcham 1.80 m, yo'nalish −Y (glTF +Z), origin oyoqlar orasida polda; transformlar qo'llanadi;
  3. root motion (son siljishi) olib tashlanadi; loop: boshi-oxiri farqi butun klip bo'ylab taqsimlanadi,
     takroriy oxirgi kadr yo'q; titrash uchun yengil (1-2-1) silliqlash;
  4. qaddi-qomat: umurtqa ≤ 4° (oldinga), yelkalar tekis, bosh o'z yo'nalishida qoladi;
     qurol ushlash uchun tana buriladi (chap yelka oldinda) — egilish emas, burilish;
  5. M416 "WeaponSocket" (o'ng qo'l suyagiga bog'langan bo'sh nuqta) orqali; qurol ko'krakka nisbatan joylashadi,
     ikkala qo'l IK bilan: o'ng musht — dastada, chap musht — stvol ostida (qo'llar orasi 35–45 sm);
     kaftlarda barmoq suyaklari yo'q, shuning uchun har kaftga bitta "Fingers" suyagi qo'shilib, musht bukiladi;
  6. oyoqlar IK bilan: tovon va uchi polda (0 ± 0.5 sm), oyoq harakatsiz — sirpanish 0;
  7. hamma kadr 30 kadr/s da bake qilinadi, cheklovlar olib tashlanadi, eksport: faqat skelet + model + WeaponSocket.
"""
import bpy, math, os, sys, json
import numpy as np
from mathutils import Vector, Matrix, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hero_ct as HC           # kaft geometriyasi, barmoq suyaklari
import rig_characters as RC    # M416 modeli va o'lchamlari

P = "mixamorig:"
FPS_IN, FPS_OUT = 24, 30
TARGET_H = 1.80
SPINE_MAX = 2.0          # umurtqa: oldinga ≤ 2° (talab ±5°; bel ham ±5° ichida qolishi uchun)
REACH = 0.975            # oyoq: son→to'piq ≤ 97.5% (tizza ~25° bukik)
HIP_DROP_MAX = 0.04      # son ko'pi bilan 4 sm pastga
TWIST = 36.0             # qurol ushlash uchun tana burilishi (yelkalar balandligi o'zgarmaydi)


def log(*a):
    print("[tuzatish]", *a)


def evaluated_verts(body):
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


def top_bones(body):
    gi = {g.index: g.name for g in body.vertex_groups}
    out = []
    for v in body.data.vertices:
        ws = sorted(((g.weight, gi[g.group]) for g in v.groups), reverse=True)
        out.append(ws[0][1] if ws else "")
    return np.array(out)


def bones_in_order(arm):
    order = []
    def walk(b):
        order.append(b.name)
        for c in b.children:
            walk(c)
    for b in arm.data.bones:
        if b.parent is None:
            walk(b)
    return order


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src, dst, name = args[0], args[1], args[2]
    checks = sys.argv[sys.argv.index("--checks") + 1] if "--checks" in sys.argv else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS_IN
    bpy.ops.import_scene.gltf(filepath=src)
    arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
    body = [o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() == arm][0]
    for o in list(bpy.data.objects):
        if o not in (arm, body):
            bpy.data.objects.remove(o)
    # --- 1) asosiy action, qolganlari o'chiriladi
    acts = sorted(bpy.data.actions, key=lambda a: a.frame_range[1] - a.frame_range[0], reverse=True)
    main_act = acts[0]
    removed = [a.name for a in acts[1:]]
    for a in acts[1:]:
        bpy.data.actions.remove(a)
    arm.animation_data.action = main_act
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)
    f_in0, f_in1 = main_act.frame_range
    dur = (f_in1 - f_in0) / FPS_IN
    n_out = int(round(dur * FPS_OUT))                 # oxirgi (takroriy) kadrsiz
    log(f"asosiy action: {main_act.name}, {f_in1 - f_in0 + 1:.0f} kadr @ {FPS_IN} = {dur:.3f} s -> {n_out} kadr @ {FPS_OUT}; o'chirildi: {removed}")
    top = top_bones(body)
    feet_mask = np.isin(top, [P + s + n for s in ("Left", "Right") for n in ("Foot", "ToeBase", "Toe_End")])
    # --- 2) global transform: oyoqlar markazi -> origin, pol -> z=0, yo'nalish -> −Y, bo'y -> 1.80
    sc.frame_set(int(f_in0))
    bpy.context.view_layer.update()
    V0 = evaluated_verts(body)
    h0 = V0[:, 2].max() - V0[:, 2].min()
    S = TARGET_H / h0
    # yo'nalish: son va yelka chiziqlaridan (oyoq uchlari tashqariga ochiq bo'lishi mumkin — ular hisobga olinmaydi)
    lr = np.zeros(2)
    for a_, b_ in (("LeftUpLeg", "RightUpLeg"), ("LeftArm", "RightArm")):
        d = np.array(arm.matrix_world @ arm.pose.bones[P + a_].head) - np.array(arm.matrix_world @ arm.pose.bones[P + b_].head)
        lr += d[:2] / np.linalg.norm(d[:2])
    fwd = np.array([lr[1], -lr[0]])                       # chap (+X) -> old (−Y)
    facing = math.atan2(fwd[0], -fwd[1])
    fv = V0[feet_mask]
    ankL = np.array(arm.matrix_world @ arm.pose.bones[P + "LeftFoot"].head)
    ankR = np.array(arm.matrix_world @ arm.pose.bones[P + "RightFoot"].head)
    c0 = np.array([(ankL[0] + ankR[0]) / 2, (ankL[1] + ankR[1]) / 2, fv[:, 2].min()])      # to'piqlar o'rtasi, pol
    Rz = Matrix.Rotation(-facing, 4, "Z")
    G = Matrix.Scale(S, 4) @ Rz @ Matrix.Translation(-Vector(c0))
    Grot = Rz.to_3x3()
    log(f"bo'y {h0:.3f} m -> {TARGET_H} (×{S:.4f}), yo'nalish {math.degrees(facing):.1f}° -> 0°, pol {c0[2] * 100:.2f} sm -> 0")
    # namuna olish: har chiqish kadri uchun har suyakning (yangi) dunyo matritsasi
    order = bones_in_order(arm)
    samples = []
    for i in range(n_out + 1):
        f = f_in0 + i * FPS_IN / FPS_OUT
        sc.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
        bpy.context.view_layer.update()
        fr = {}
        for bn in order:
            M = arm.matrix_world @ arm.pose.bones[bn].matrix
            pos = G @ M.translation
            rot = (Grot @ M.to_3x3().normalized())
            fr[bn] = (Vector(pos), rot.to_quaternion())
        samples.append(fr)
    # tinch holatni ham o'zgartiramiz: animatsiyasiz holatda obyektlarga G qo'llanib, transform "apply"
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    arm.matrix_world = G @ arm.matrix_world
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # body armatura bolasi: uning transformi ham qo'llanadi
    bpy.context.view_layer.update()
    # --- 3) yangi action: 30 kadr/s, root motion yo'q, loop, silliqlash
    new = bpy.data.actions.new(name)
    arm.animation_data.action = None          # poza animatsiyasiz hisoblanadi, kalitlar keyin egri chiziqlarga yoziladi
    hips = P + "Hips"
    keys = {bn: {"q": [], "l": []} for bn in order}
    hp = np.array([samples[i][hips][0][:] for i in range(n_out + 1)])
    drift = (hp[-1, :2] - hp[0, :2])
    mean_xy = hp[:, :2].mean(0) - drift * 0.5
    log(f"root motion: son {np.linalg.norm(drift) * 100:.2f} sm siljigan -> olib tashlanadi")
    # loop: dunyo burilishlari va son joyi, boshi-oxiri farqi vaqt bo'yicha taqsimlanadi
    for bn in order:
        q0 = samples[0][bn][1]
        qn = samples[n_out][bn][1]
        if q0.dot(qn) < 0:
            qn = -qn
        corr = q0 @ qn.inverted()
        for i in range(n_out + 1):
            w = i / n_out
            c = Quaternion().slerp(corr, w)
            p, q = samples[i][bn]
            samples[i][bn] = (p, c @ q)
    for i in range(n_out + 1):
        p, q = samples[i][hips]
        w = i / n_out
        p = Vector((p.x - drift[0] * w - mean_xy[0], p.y - drift[1] * w - mean_xy[1], p.z))
        samples[i][hips] = (p, q)
    samples = samples[:n_out]                        # takroriy oxirgi kadr olib tashlanadi
    # yengil silliqlash (1-2-1, halqali) — faqat burilishlar
    sm = []
    for i in range(n_out):
        fr = {}
        for bn in order:
            qa, qb, qc = samples[(i - 1) % n_out][bn][1], samples[i][bn][1], samples[(i + 1) % n_out][bn][1]
            q = qb.slerp(qa, 0.25).slerp(qb.slerp(qc, 0.25), 0.5)
            fr[bn] = (samples[i][bn][0], q)
        sm.append(fr)
    samples = sm
    # --- 4) poza: son + suyaklar dunyo holati bo'yicha, keyin umurtqa, yelka, burilish, bosh
    rest = {bn: arm.data.bones[bn].matrix_local.copy() for bn in order}
    # BONE ota: namunada dunyo burilishi suyakning o'z o'qlari (rest orientatsiya bilan) — pose.matrix sifatida beriladi

    def set_world(bn, pos, q):
        pb = arm.pose.bones[bn]
        M = q.to_matrix().to_4x4()
        M.translation = pos
        pb.matrix = M
        bpy.context.view_layer.update()

    def rotate_about(bn, pivot, R3):
        pb = arm.pose.bones[bn]
        M = pb.matrix.copy()
        T = Matrix.Translation(pivot) @ R3.to_4x4() @ Matrix.Translation(-pivot)
        pb.matrix = T @ M
        bpy.context.view_layer.update()
    stats = {"spine_before": [], "spine_after": [], "shoulder_before": [], "shoulder_after": []}
    for i in range(n_out):
        fr = samples[i]
        for bn in order:
            pb = arm.pose.bones[bn]
            pb.rotation_mode = "QUATERNION"
            p, q = fr[bn]
            set_world(bn, p, q) if bn == hips else None
            if bn != hips:
                pb.matrix = Matrix.LocRotScale(p, q, Vector((1, 1, 1)))
                bpy.context.view_layer.update()
                pb.location = (0, 0, 0)       # suyaklar cho'zilmaydi — faqat burilish
                bpy.context.view_layer.update()
        head_rot = (arm.pose.bones[P + "Head"].matrix.to_3x3()).copy()
        h = arm.pose.bones[hips].head.copy()
        nk = arm.pose.bones[P + "Neck"].head.copy()
        v = nk - h
        fwd3 = Vector((0, -1, 0))
        tilt = math.degrees(math.atan2(v.dot(fwd3), v.z))           # + oldinga
        stats["spine_before"].append(tilt)
        la, ra = arm.pose.bones[P + "LeftArm"].head, arm.pose.bones[P + "RightArm"].head
        d = la - ra
        stats["shoulder_before"].append(math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))))
        # 1) qurol ushlash uchun burilish (vertikal o'q): chap yelka oldinga — egilish emas
        for bn in ("Spine1", "Spine2"):
            piv = arm.pose.bones[P + bn].head.copy()
            rotate_about(P + bn, piv, Matrix.Rotation(math.radians(-TWIST / 2), 3, "Z"))
        # 2) umurtqa egilishi va yelkalar: kichik qadamlar, har qadam o'lchanadi (yomonlashsa — teskari tomonga)
        def tilt_now():
            v_ = arm.pose.bones[P + "Neck"].head - arm.pose.bones[hips].head
            return math.degrees(math.atan2(v_.dot(fwd3), v_.z))

        def sh_now():
            d_ = arm.pose.bones[P + "LeftArm"].head - arm.pose.bones[P + "RightArm"].head
            return math.degrees(math.atan2(d_.z, math.hypot(d_.x, d_.y)))

        def rot_spine(deg):
            for bn in ("Spine", "Spine1", "Spine2"):
                piv = arm.pose.bones[P + bn].head.copy()
                rotate_about(P + bn, piv, Matrix.Rotation(math.radians(deg / 3.0), 3, "X"))

        def rot_sh(deg):
            piv = arm.pose.bones[P + "Spine2"].head.copy()
            d_ = arm.pose.bones[P + "LeftArm"].head - arm.pose.bones[P + "RightArm"].head
            ax = Vector((d_.x, d_.y, 0)).normalized().cross(Vector((0, 0, 1)))    # ko'krak oldi (gorizontal)
            rotate_about(P + "Spine2", piv, Matrix.Rotation(math.radians(deg), 3, ax))

        def reduce(measure, target_fn, apply, tol):
            for _ in range(30):
                err = target_fn(measure())
                if abs(err) <= tol:
                    return
                step = max(-3.0, min(3.0, err))
                apply(-step)
                if abs(target_fn(measure())) > abs(err):
                    apply(2 * step)
                    if abs(target_fn(measure())) > abs(err):
                        apply(-step)
                        return
        for _ in range(4):
            reduce(tilt_now, lambda t: (t - SPINE_MAX) if t > SPINE_MAX else ((t + SPINE_MAX) if t < -SPINE_MAX else 0.0), rot_spine, 0.05)
            reduce(sh_now, lambda x: x, rot_sh, 0.1)
        # bosh o'z yo'nalishida (oldinga) qoladi: bo'yin yarmini, bosh qolganini qoplaydi
        hb = arm.pose.bones[P + "Head"]
        cur = hb.matrix.to_3x3()
        corr = head_rot @ cur.inverted()
        piv = arm.pose.bones[P + "Neck"].head.copy()
        rotate_about(P + "Neck", piv, Quaternion().slerp(corr.to_quaternion(), 0.5).to_matrix())
        cur = hb.matrix.to_3x3()
        M = hb.matrix.copy()
        M3 = head_rot.to_4x4()
        M3.translation = M.translation
        hb.matrix = M3
        bpy.context.view_layer.update()
        # natija o'lchovlari
        h = arm.pose.bones[hips].head
        v = arm.pose.bones[P + "Neck"].head - h
        stats["spine_after"].append(math.degrees(math.atan2(v.dot(fwd3), v.z)))
        d = arm.pose.bones[P + "LeftArm"].head - arm.pose.bones[P + "RightArm"].head
        stats["shoulder_after"].append(math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))))
        for pb in arm.pose.bones:
            keys[pb.name]["q"].append(pb.rotation_quaternion.copy())
            keys[pb.name]["l"].append(pb.location.copy())
    # kalitlarni egri chiziqlarga yozish (kvaternion ishorasi uzluksiz)
    for bn in order:
        qs = keys[bn]["q"]
        for k in range(1, len(qs)):
            if qs[k].dot(qs[k - 1]) < 0:
                qs[k] = -qs[k]
        for comp, path, vals in ((4, f'pose.bones["{bn}"].rotation_quaternion', qs), (3, f'pose.bones["{bn}"].location', keys[bn]["l"])):
            for ci in range(comp):
                fc = new.fcurves.new(path, index=ci, action_group=bn)
                fc.keyframe_points.add(len(vals))
                co = []
                for k, v in enumerate(vals):
                    co += [k + 1, v[ci]]
                fc.keyframe_points.foreach_set("co", co)
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
                fc.update()
    arm.animation_data.action = new
    sc.frame_set(1); bpy.context.view_layer.update()
    sc.render.fps = FPS_OUT
    sc.frame_start, sc.frame_end = 1, n_out
    for k in stats:
        a = np.array(stats[k])
        log(f"{k}: {a.min():.1f}…{a.max():.1f}°")
    # --- 5) qo'llar va qurol (hero_ct usullari: barmoq suyagi, musht geometriyasi, IK)
    sc.frame_set(1); bpy.context.view_layer.update()
    geo = HC.add_fingers(arm, body)
    sc.frame_set(1)
    bpy.context.view_layer.update()
    gun, mag = RC.load_weapon("m416")
    W = RC.WEAPONS["m416"]
    gx, gz = W["grip"]
    bx, bz = W["butt"]
    butt_local = Vector((0, bx - gx, bz - gz))
    V = evaluated_verts(body)
    top = top_bones(body)
    torso = V[~np.array([any(k in t for k in ("Arm", "Hand", "Middle4", "Fingers")) for t in top])]

    def front_y(x, z, rx=0.05, rz=0.05):
        m = (np.abs(torso[:, 0] - x) < rx) & (np.abs(torso[:, 2] - z) < rz)
        return float(torso[m, 1].min()) if m.any() else None
    shR = arm.pose.bones[P + "RightArm"].head.copy()
    shL = arm.pose.bones[P + "LeftArm"].head.copy()
    pocket = shR + Vector((0.075, 0, -0.01))
    fy = front_y(pocket.x, pocket.z)
    pocket.y = (fy - 0.01) if fy is not None else shR.y - 0.12
    palmL, indexL, _ = geo["Left"]
    kL = -indexL
    AL = Matrix((kL, palmL, kL.cross(palmL))).transposed()
    holeL = Vector((0, 0.085, 0)) + palmL * 0.028
    reachL = (arm.data.bones[P + "LeftArm"].length + arm.data.bones[P + "LeftForeArm"].length) * 0.99
    # chap musht stvol ostida (old qism o'qi mushtdan o'tadi), M416 modelida x = −0.18 (dastadan ~37 sm)
    under = Vector((0, -0.18 - gx, 0.047 - gz))

    def place(yaw, pitch):
        f_ = Matrix.Rotation(math.radians(yaw), 3, "Z") @ Vector((0, -1, 0))
        f_ = (Matrix.Rotation(math.radians(pitch), 3, f_.cross(Vector((0, 0, 1))).normalized()) @ f_).normalized()
        u_ = Vector((0, 0, 1))
        u_ = (u_ - f_ * u_.dot(f_)).normalized()
        R_ = Matrix(((-f_).cross(u_), -f_, u_)).transposed()
        g_ = pocket - R_ @ butt_local
        need = 0.0
        for q in (g_, g_ + R_ @ Vector((0, 0, -0.06))):
            fyg = front_y(q.x, q.z, 0.06, 0.05)
            if fyg is not None:
                need = max(need, q.y - (fyg - 0.065))
        return R_, g_ + Vector((0, -max(0.0, need), 0))

    def left_wrist(R_, g_):
        kw = (R_ @ Vector((0, 1, 0))).normalized()           # old qism o'qi (ko'rsatkich -> jimjiloq: qo'ndoq tomon)
        pw = R_ @ Vector((-0.35, 0, 1)).normalized()
        pw = (pw - kw * pw.dot(kw)).normalized()
        Mb = Matrix((kw, pw, kw.cross(pw))).transposed() @ AL.transposed()
        return g_ + R_ @ under - Mb @ holeL
    chosen = None
    for pitch in (-10, -14, -18):
        for yaw in range(0, 44, 2):
            R3, grip_w = place(yaw, pitch)
            if (left_wrist(R3, grip_w) - shL).length <= reachL:
                chosen = (yaw, pitch)
                break
        if chosen:
            break
    if chosen is None:
        chosen = (40, -18)
        R3, grip_w = place(*chosen)
    log(f"qurol: og'iz {chosen[0]}° chapga, {-chosen[1]}° pastga; qo'ndoq jilet sirtida (y={pocket.y:.3f})")
    for yy in (0, 20, 40):
        R_, g_ = place(yy, -10)
        lw = left_wrist(R_, g_)
    Wm = R3.to_4x4()
    Wm.translation = grip_w
    sp = arm.pose.bones[P + "Spine2"]
    for o in (gun, mag):
        if o is None:
            continue
        o.parent = arm
        o.parent_type = "BONE"
        o.parent_bone = P + "Spine2"
        o.matrix_parent_inverse = Matrix.Identity(4)
        tail = arm.matrix_world @ sp.matrix @ Matrix.Translation((0, sp.length, 0))
        o.matrix_basis = tail.inverted() @ Wm
    bpy.context.view_layer.update()
    HC.curl_fingers(arm, geo)
    bpy.context.view_layer.update()
    grips = {"Right": (Vector((0, 0.012, -0.035)), Vector((0, 0.35, -1)).normalized(), Vector((1, 0, 0))),
             "Left": (under, Vector((0, 1, 0)), Vector((-0.35, 0, 1)).normalized())}
    Gw = gun.matrix_world.to_3x3().normalized()
    cons = []
    for side in ("Right", "Left"):
        point, gdown, palm_dir = grips[side]
        palm_l, index_l, _ = geo[side]
        k_l = -index_l
        A = Matrix((k_l, palm_l, k_l.cross(palm_l))).transposed()
        kw = (Gw @ gdown).normalized()
        pw = Gw @ palm_dir
        pw = (pw - kw * pw.dot(kw)).normalized()
        Mb = Matrix((kw, pw, kw.cross(pw))).transposed() @ A.transposed()
        wt = gun.matrix_world @ point - Mb @ (Vector((0, 0.085, 0)) + palm_l * 0.028)
        tgt = bpy.data.objects.new(f"ik_{side}", None)
        sc.collection.objects.link(tgt)
        Mt = Mb.to_4x4()
        Mt.translation = wt
        tgt.matrix_world = Mt
        tgt.parent = gun
        tgt.matrix_parent_inverse = gun.matrix_world.inverted()
        shd = arm.pose.bones[P + side + "Arm"].head
        pole = bpy.data.objects.new(f"pole_{side}", None)
        sc.collection.objects.link(pole)
        pole.location = (shd + wt) / 2 + Vector((0.3 if side == "Left" else -0.3, 0.12, -0.45))
        pole.parent = arm
        pole.parent_type = "BONE"
        pole.parent_bone = P + "Spine2"
        pole.matrix_parent_inverse = (arm.matrix_world @ sp.matrix @ Matrix.Translation((0, sp.length, 0))).inverted()
        c = arm.pose.bones[P + side + "ForeArm"].constraints.new("IK")
        c.target, c.pole_target, c.chain_count, c.use_tail = tgt, pole, 2, True
        best = None
        for a_ in range(-180, 180, 10):
            c.pole_angle = math.radians(a_)
            bpy.context.view_layer.update()
            e = (arm.pose.bones[P + side + "ForeArm"].head - pole.matrix_world.translation).length
            if best is None or e < best[0]:
                best = (e, a_)
        c.pole_angle = math.radians(best[1])
        cr = arm.pose.bones[P + side + "Hand"].constraints.new("COPY_ROTATION")
        cr.target = tgt
        cons += [(side + "ForeArm", c), (side + "Hand", cr)]
        bpy.context.view_layer.update()
        err = (arm.pose.bones[P + side + "ForeArm"].tail - wt).length
        log(f"{side} qo'l: bilak nishondan {err * 100:.2f} sm")
    # WeaponSocket: o'ng qo'l suyagiga bog'langan bo'sh nuqta, qurolning dasta nuqtasida (qurol o'qlari bilan)
    bpy.context.view_layer.update()
    rh = arm.pose.bones[P + "RightHand"]
    sock = bpy.data.objects.new("WeaponSocket", None)
    sc.collection.objects.link(sock)
    sock.empty_display_size = 0.05
    sock.parent = arm
    sock.parent_type = "BONE"
    sock.parent_bone = P + "RightHand"
    sock.matrix_parent_inverse = Matrix.Identity(4)
    tail = arm.matrix_world @ rh.matrix @ Matrix.Translation((0, rh.length, 0))
    sock.matrix_basis = tail.inverted() @ gun.matrix_world
    bpy.context.view_layer.update()
    off = (arm.matrix_world @ rh.matrix).inverted() @ gun.matrix_world
    offset = {"position_m": [round(x, 4) for x in off.translation],
              "rotation_deg_xyz": [round(math.degrees(a), 2) for a in off.to_euler("XYZ")],
              "rotation_quat_wxyz": [round(x, 5) for x in off.to_quaternion()]}
    log("WeaponSocket offset (o'ng qo'l suyagiga nisbatan):", offset)
    # --- 6) oyoqlar: tovon va uchi polda, harakatsiz (IK)
    V = evaluated_verts(body)
    feet_cons = []
    feet_info = []
    def plan(s):
        foot = arm.pose.bones[P + s + "Foot"]
        leg = arm.pose.bones[P + s + "Leg"]
        # o'rtacha joy (hamma kadrlar bo'yicha)
        acc = Vector()
        for i in range(n_out):
            sc.frame_set(i + 1)
            bpy.context.view_layer.update()
            acc += foot.head
        ank = acc / n_out
        sc.frame_set(1)
        bpy.context.view_layer.update()
        V = evaluated_verts(body)
        legL = arm.data.bones[P + s + "UpLeg"].length + arm.data.bones[P + s + "Leg"].length
        hipj = arm.pose.bones[P + s + "UpLeg"].head.copy()
        # oyoq tagi tekisligi: oyoq uchlari (mahalliy) — tinch holatda tovon va uch bir balandlikda bo'ladigan burilish
        bm = arm.data.bones[P + s + "Foot"].matrix_local
        fmask = np.isin(top, [P + s + n for n in ("Foot", "ToeBase", "Toe_End")])
        Vl = np.array([(bm.inverted() @ Vector(p))[:] for p in V[fmask]])     # joriy kadrda emas — tinch holat kerak
        Rf = (foot.matrix.to_3x3()).normalized()
        # oyoq tagi tekisligi: botinka ostidagi eng past uchlarga (2.5 sm ichida) tekislik moslanadi, u gorizontal qilinadi
        Wv = V[fmask]
        a_ = np.array(foot.head)
        sole = Wv[Wv[:, 2] < Wv[:, 2].min() + 0.025]
        if len(sole) < 12:
            sole = Wv[np.argsort(Wv[:, 2])[:40]]
        A_ = np.c_[sole[:, 0], sole[:, 1], np.ones(len(sole))]
        coef = np.linalg.lstsq(A_, sole[:, 2], rcond=None)[0]           # z = a·x + b·y + c
        n_ = Vector((-coef[0], -coef[1], 1.0)).normalized()
        t_ = np.array(arm.pose.bones[P + s + "Toe_End"].head)
        fd = (t_ - a_); fd[2] = 0; fd /= np.linalg.norm(fd)
        lat = np.array([-fd[1], fd[0], 0.0])
        # old-orqa qiyalik: tovon (orqa 25%) va uch (old 25%) eng past nuqtalaridan; yon qiyalik: tag tekisligidan
        proj = (Wv - a_) @ fd
        heel_z = Wv[proj < np.percentile(proj, 25)][:, 2].min()
        toe_z = Wv[proj > np.percentile(proj, 75)][:, 2].min()
        Lf = float(np.percentile(proj, 90) - np.percentile(proj, 10))
        pitch = math.degrees(math.atan2(toe_z - heel_z, Lf))
        roll = math.degrees(math.asin(max(-1, min(1, n_.dot(Vector(lat.tolist()))))))
        Rfix = Matrix.Rotation(math.radians(-roll), 3, Vector(fd.tolist())) @ Matrix.Rotation(math.radians(pitch), 3, Vector(lat.tolist()))
        Rt = Rfix @ Rf
        # tovon/uch polga: nishon burilishi bilan oyoq uchlari qayerga tushishini hisoblab, balandlikni tanlaymiz
        rel = [(Vector(p) - foot.head) for p in Wv]
        newz = [(Rfix @ r).z for r in rel]
        z_ank = -min(newz)
        return foot, leg, ank, legL, hipj, Rt, z_ank, fmask, pitch, roll

    # son biroz pastga (tizzalar sal bukik): ikkala oyoq ham to'piq nishoniga ≤ REACH bilan yetishi uchun kerakli pasayish
    drop = 0.0
    for s in ("Left", "Right"):
        _, _, ank, legL, hipj, _, z_ank, _, _, _ = plan(s)
        h_ = math.hypot(ank.x - hipj.x, ank.y - hipj.y)
        hz = z_ank + math.sqrt(max(0.0, (REACH * legL) ** 2 - h_ ** 2))
        drop = max(drop, hipj.z - hz)
    drop = min(max(drop, 0.0), HIP_DROP_MAX)
    if drop > 0:
        dl = arm.data.bones[hips].matrix_local.to_3x3().inverted() @ Vector((0, 0, -drop))
        for fc in arm.animation_data.action.fcurves:
            if fc.data_path == f'pose.bones["{hips}"].location':
                for kp in fc.keyframe_points:
                    kp.co[1] += dl[fc.array_index]
                fc.update()
        arm.animation_data.action = arm.animation_data.action
        sc.frame_set(2)
        sc.frame_set(1)
        bpy.context.view_layer.update()
        log(f"son {drop * 100:.1f} sm pastga tushirildi (tizzalar sal bukik)")
    for s, sg in (("Left", 1), ("Right", -1)):
        foot, leg, ank, legL, hipj, Rt, z_ank, fmask, pitch, roll = plan(s)
        log(f"{s}: son bo'g'imi z {hipj.z:.3f}, to'piq nishoni z {z_ank:.3f}, gorizontal {math.hypot(ank.x - hipj.x, ank.y - hipj.y):.3f}, oyoq {legL:.3f}")
        # oyoq bemalol yetsin (tizza sal bukik): son bo'g'imidan to'piqgacha ≤ REACH × oyoq uzunligi (nishon balandligida)
        dvec = Vector((ank.x, ank.y, z_ank)) - hipj
        need_h = math.sqrt(max(0.0, (REACH * legL) ** 2 - dvec.z ** 2))
        horiz = Vector((dvec.x, dvec.y, 0))
        if horiz.length > need_h:
            ank = Vector((hipj.x, hipj.y, 0)) + horiz.normalized() * need_h
            log(f"{s} oyoq: tizza sal bukik turishi uchun to'piq {((horiz.length - need_h) * 100):.1f} sm ichkariga")
        tgt = bpy.data.objects.new(f"foot_{s}", None)
        sc.collection.objects.link(tgt)
        M = Rt.to_4x4()
        M.translation = Vector((ank.x, ank.y, z_ank))
        tgt.matrix_world = M
        pole = bpy.data.objects.new(f"knee_{s}", None)
        sc.collection.objects.link(pole)
        pole.location = Vector((ank.x + sg * 0.05, ank.y - 0.8, 0.5))
        c = leg.constraints.new("IK")
        c.target, c.pole_target, c.chain_count = tgt, pole, 2
        cr = foot.constraints.new("COPY_ROTATION")
        cr.target = tgt
        feet_cons += [(s + "Leg", c), (s + "Foot", cr)]
        best = None
        for a2 in range(-180, 180, 5):
            c.pole_angle = math.radians(a2)
            bpy.context.view_layer.update()
            kn, an2 = leg.head, foot.head
            sc_ = abs(kn.x - an2.x) * 3 + max(0.0, kn.y - an2.y + 0.02) * 5
            if best is None or sc_ < best[0]:
                best = (sc_, a2)
        c.pole_angle = math.radians(best[1])
        log(f"{s} oyoq: tag tekisligi {pitch:+.1f}° (old-orqa) va {roll:+.1f}° (yon) edi -> gorizontal, to'piq {z_ank * 100:.1f} sm")
        feet_info.append((s, tgt, fmask))
    # teskari aloqa: deformatsiyalangan botinka o'lchanadi (tovon va uch eng past nuqtalari, yon qiyalik) va nishon tuzatiladi
    sc.frame_set(1)
    for it in range(4):
        bpy.context.view_layer.update()
        V2 = evaluated_verts(body)
        worst = 0.0
        for s, tgt, fmask in feet_info:
            Wv = V2[fmask]
            fb = arm.pose.bones[P + s + "Foot"]
            a_ = np.array(fb.head)
            t_ = np.array(arm.pose.bones[P + s + "Toe_End"].head)
            fd = t_ - a_; fd[2] = 0; fd /= np.linalg.norm(fd)
            lat = np.array([-fd[1], fd[0], 0.0])
            proj = (Wv - a_) @ fd
            side = (Wv - a_) @ lat
            back, front = proj < np.percentile(proj, 25), proj > np.percentile(proj, 75)
            heel_z, toe_z = Wv[back][:, 2].min(), Wv[front][:, 2].min()
            Lf = float(np.percentile(proj, 90) - np.percentile(proj, 10))
            mid = front | back
            inn, out = Wv[mid & (side > np.percentile(side, 70))][:, 2].min(), Wv[mid & (side < np.percentile(side, 30))][:, 2].min()
            W_ = float(np.percentile(side, 90) - np.percentile(side, 10))
            pitch = math.atan2(toe_z - heel_z, Lf)
            roll = math.atan2(inn - out, W_)
            R = Matrix.Rotation(-roll, 3, Vector(fd.tolist())) @ Matrix.Rotation(pitch, 3, Vector(lat.tolist()))
            M = tgt.matrix_world.copy()
            p0 = M.translation.copy()
            M = (Matrix.Translation(p0) @ R.to_4x4() @ Matrix.Translation(-p0)) @ M
            M.translation.z -= min(heel_z, toe_z, inn, out)
            tgt.matrix_world = M
            worst = max(worst, abs(heel_z - toe_z), abs(inn - out), abs(min(heel_z, toe_z)))
            log(f"  {s} oyoq ({it + 1}): tovon {heel_z * 100:+.2f} sm, uch {toe_z * 100:+.2f} sm, ichki {inn * 100:+.2f}, tashqi {out * 100:+.2f}")
        if worst < 0.002:
            break
    # --- 7) bake (hamma suyaklar, vizual), cheklovlar olib tashlanadi
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.bone.select = True
    bpy.ops.nla.bake(frame_start=1, frame_end=n_out, only_selected=True, visual_keying=True, clear_constraints=True,
                     use_current_action=True, bake_types={"POSE"})
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        if o.name.startswith(("ik_", "pole_", "foot_", "knee_")):
            bpy.data.objects.remove(o)
    act = arm.animation_data.action
    act.name = name
    for k in list(act.keys()):
        del act[k]
    for a in list(bpy.data.actions):
        if a is not act:
            bpy.data.actions.remove(a)
    # tekshiruv renderlari uchun qurol bilan saqlash (ixtiyoriy)
    info = {"name": name, "frames": n_out, "fps": FPS_OUT, "scale": S, "facing_fixed_deg": math.degrees(facing),
            "floor_shift_cm": -c0[2] * 100, "weapon": "m416", "weapon_yaw_pitch_deg": chosen, "WeaponSocket": offset,
            "removed_actions": removed}
    if checks:
        os.makedirs(checks, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(checks, f"{name}_qurol_bilan.blend"))
    # eksport: faqat skelet + model + WeaponSocket (qurolsiz, kamera/chiroqsiz)
    for o in (gun, mag):
        if o:
            bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in (arm, body, sock):
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    for m in body.data.materials:
        m.use_backface_culling = False
    # origin — to'piqlar o'rtasida, polda (hamma kadrlar bo'yicha o'rtacha)
    mids = []
    for i in range(n_out):
        sc.frame_set(i + 1)
        bpy.context.view_layer.update()
        mids.append((arm.pose.bones[P + "LeftFoot"].head + arm.pose.bones[P + "RightFoot"].head) / 2)
    mid = sum(mids, Vector()) / len(mids)
    sc.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    arm.location = (-mid.x, -mid.y, 0)
    bpy.context.view_layer.update()
    arm.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    log(f"origin: to'piqlar o'rtasiga {mid.x * 100:.1f}, {mid.y * 100:.1f} sm surildi")
    bpy.ops.object.select_all(action="DESELECT")
    for o in (arm, body, sock):
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", use_selection=True, export_animations=True,
                              export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_step=1,
                              export_yup=True, export_skins=True, export_reset_pose_bones=True, export_cameras=False,
                              export_lights=False, export_image_format="AUTO")
    json.dump(info, open(os.path.splitext(dst)[0] + ".json", "w"), indent=1)
    log("tayyor:", dst)


if __name__ == "__main__":
    main()
