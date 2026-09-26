"""CT qahramoni (foydalanuvchi bergan Meshy/Mixamo skeletli model + animatsiyalar) -> Godot.

Kirish:  assets_src/ct_hero/ct_<animatsiya>.glb — har bir faylda o'sha skelet va bitta animatsiya
         (masalan ct_idle.glb). Animatsiyalarga TEGILMAYDI, faqat:
  1) M416 o'ng qo'l suyagiga biriktiriladi: dasta kaftda, og'zi chap qo'l tomonga, magazin pastga;
  2) chap qo'l IK bilan vertikal tutqichga "yopishtiriladi" (faqat chap yelka-bilak, kaft holati animatsiyadan);
  3) teksturalar 2048 px JPEG ga kichraytiriladi.
Chiqish: godot/characters/ct_hero.glb (to'liq tana, 3-shaxs) va ct_hero_arms.glb (faqat qo'llar + qurol, 1-shaxs),
         godot/characters/ct_hero.json (masshtab, animatsiyalar ro'yxati).
Ishga tushirish: python3 hero_ct.py   (pip install bpy==4.2.0)
"""
import bpy, bmesh, math, os, sys, glob, json
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, "..", "assets_src", "ct_hero")
OUT = os.path.join(HERE, "..", "godot", "characters")
TARGET_H = 1.80            # o'yinchi kapsulasi bo'yi; Godot'da model shu bo'yga keltiriladi
P = "mixamorig:"
ARM_BONES = {P + n for n in ("LeftArm", "LeftForeArm", "LeftHand", "LeftHandMiddle4", "LeftHandFingers",
                              "RightArm", "RightForeArm", "RightHand", "RightHandMiddle4", "RightHandFingers")}


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def palm(arm, side, frame=None):
    """kaft markazi: bilakdan barmoqlar tomonga 8 sm"""
    pb = arm.pose.bones[P + side + "Hand"]
    tip = arm.pose.bones[P + side + "HandMiddle4"]
    w = arm.matrix_world @ pb.head
    t = arm.matrix_world @ tip.head
    return w + (t - w).normalized() * 0.08, w, t


STANCE_FIX = {"idle"}          # oyoq turishi tuzatiladigan (joyida turish) animatsiyalar
ARM_IK_BONES = {P + n for n in ("LeftArm", "LeftForeArm", "RightArm", "RightForeArm", "LeftHand", "RightHand",
                                   "LeftHandFingers", "RightHandFingers")}
LEG_BONES = {P + n for s in ("Left", "Right") for n in (s + "UpLeg", s + "Leg", s + "Foot", s + "ToeBase")}


def fix_stance(arm, act):
    """Turish animatsiyasi uchun ideal oyoq turishi:
      - son (chanoq): og'ish va chayqalish 70% kamaytiriladi (tekis bel), 2 sm pastroq — tizzalar sal bukiladi;
      - oyoqlar yelka kengligida (±12 sm), chap oyoq 7 sm oldinda, o'ng 5 sm orqada, uchlari 8° tashqariga;
      - tizzalar oyoq uchi yo'nalishiga (qutb nishoni tizza oldida).
    Son harakati kalit kadrlarga yoziladi; oyoqlar IK cheklovlari bilan (keyin pishiriladi)."""
    sc = bpy.context.scene
    hips = arm.pose.bones[P + "Hips"]
    hips.rotation_mode = "QUATERNION"
    f0, f1 = int(act.frame_range[0]), int(round(act.frame_range[1]))
    qs, ls = [], []
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        qs.append(hips.rotation_quaternion.copy())
        ls.append(hips.location.copy())
    qm = qs[0].copy()
    for q in qs[1:]:
        qm = qm.slerp(q, 1.0 / (qs.index(q) + 1))
    lm = sum(ls, Vector()) / len(ls)
    # son balandligi: oyoq 98.5% cho'zilgan (tizza sal bukik); yon tomonga chayqalish yarmiga
    sc.frame_set(f0)
    bpy.context.view_layer.update()
    ul = arm.data.bones[P + "LeftUpLeg"]
    leg_len = (arm.data.bones[P + "LeftLeg"].head_local - ul.head_local).length + (arm.data.bones[P + "LeftFoot"].head_local - arm.data.bones[P + "LeftLeg"].head_local).length
    ank_z = (arm.matrix_world @ arm.data.bones[P + "LeftFoot"].head_local).z
    up_now = (arm.matrix_world @ arm.pose.bones[P + "LeftUpLeg"].head).z
    want = ank_z + 0.985 * leg_len
    down = hips.bone.matrix_local.to_3x3().inverted() @ (arm.matrix_world.to_3x3().inverted() @ Vector((0, 0, want - up_now)))
    print(f"son bo'g'imi: {up_now:.3f} m -> {want:.3f} m (oyoq {leg_len:.3f} m)")
    for fc in list(act.fcurves):
        if fc.data_path in (f'pose.bones["{P}Hips"].rotation_quaternion', f'pose.bones["{P}Hips"].location'):
            act.fcurves.remove(fc)
    for i, f in enumerate(range(f0, f1 + 1)):
        hips.rotation_quaternion = qm.slerp(qs[i], 0.3)
        l = ls[i]
        hips.location = lm + (l - lm) * 0.5 + down
        hips.keyframe_insert("rotation_quaternion", frame=f)
        hips.keyframe_insert("location", frame=f)
    # o'qchi turishi: umurtqa chapga buriladi (chap yelka oldinda, jami 24°), bo'yin va bosh qarama-qarshi — nigoh oldinga
    twist = {"Spine1": -12.0, "Spine2": -12.0, "Neck": 12.0, "Head": 12.0}
    Rw = arm.matrix_world.to_3x3()
    for bn, deg in twist.items():
        pb = arm.pose.bones[P + bn]
        pb.rotation_mode = "QUATERNION"
        Bm = (Rw @ pb.bone.matrix_local.to_3x3()).normalized()
        D = (Bm.inverted() @ Matrix.Rotation(math.radians(deg), 3, "Z") @ Bm).to_quaternion()
        path = f'pose.bones["{P}{bn}"].rotation_quaternion'
        qs_ = []
        for f in range(f0, f1 + 1):
            sc.frame_set(f)
            qs_.append(pb.rotation_quaternion.copy())
        for fc in list(act.fcurves):
            if fc.data_path == path:
                act.fcurves.remove(fc)
        for i, f in enumerate(range(f0, f1 + 1)):
            pb.rotation_quaternion = D @ qs_[i]
            pb.keyframe_insert("rotation_quaternion", frame=f)
    sc.frame_set(f0)
    bpy.context.view_layer.update()
    cons = []
    rest_up = {s: arm.matrix_world @ arm.data.bones[P + s + "UpLeg"].head_local for s in ("Left", "Right")}
    for s, sg in (("Left", 1), ("Right", -1)):
        foot = arm.pose.bones[P + s + "Foot"]
        leg = arm.pose.bones[P + s + "Leg"]
        rb = arm.data.bones[P + s + "Foot"]
        ank_rest = arm.matrix_world @ rb.head_local
        tgt = bpy.data.objects.new(f"stance_{s}", None)
        sc.collection.objects.link(tgt)
        yaw = Matrix.Rotation(math.radians(8 * sg), 3, "Z")
        R = yaw @ (arm.matrix_world.to_3x3() @ rb.matrix_local.to_3x3())
        M = R.to_4x4()
        M.translation = Vector((sg * 0.12, rest_up[s].y + (-0.07 if s == "Left" else 0.05), ank_rest.z))
        tgt.matrix_world = M
        pole = bpy.data.objects.new(f"kneepole_{s}", None)
        sc.collection.objects.link(pole)
        pole.location = Vector((sg * 0.19, rest_up[s].y - 0.8, 0.5))
        c = leg.constraints.new("IK")
        c.target, c.pole_target, c.chain_count = tgt, pole, 2
        cr = foot.constraints.new("COPY_ROTATION")
        cr.target = tgt
        cons += [c, cr]
        bpy.context.view_layer.update()
        # tizza aniq oldinga (oyoq uchi ustida): yon og'ish minimal, oldinga chiqish musbat
        best = None
        for a in range(-180, 180, 5):
            c.pole_angle = math.radians(a)
            bpy.context.view_layer.update()
            kn = arm.matrix_world @ leg.head
            an = arm.matrix_world @ foot.head
            sc_ = abs(kn.x - an.x) * 3 + max(0.0, kn.y - an.y + 0.02) * 5
            if best is None or sc_ < best[0]:
                best = (sc_, a)
        c.pole_angle = math.radians(best[1])
    bpy.context.view_layer.update()
    for s in ("Left", "Right"):
        a_ = arm.matrix_world @ arm.pose.bones[P + s + "Foot"].head
        print(f"{s} oyoq: to'piq {tuple(round(x, 3) for x in a_)}")
    return cons


CURL = {"Right": 82.0, "Left": 78.0}     # barmoqlar bukilishi (°): dasta atrofida musht


def hand_geometry(arm, body, side):
    """kaft mesh'idan (suyakning tinch holatdagi mahalliy fazosida): kaft tomoni, ko'rsatkich barmoq tomoni"""
    b = arm.data.bones[P + side + "Hand"]
    Minv = (arm.matrix_world @ b.matrix_local).inverted()
    gi = {g.index: g.name for g in body.vertex_groups}
    pts = []
    for v in body.data.vertices:
        ws = sorted(((g.weight, gi[g.group]) for g in v.groups), reverse=True)
        if ws and ws[0][1] in (P + side + "Hand", P + side + "HandMiddle4"):
            pts.append(Minv @ (body.matrix_world @ v.co))
    A = np.array([p[:] for p in pts])
    y = A[:, 1]
    xz = A[:, [0, 2]] - A[:, [0, 2]].mean(0)
    w, V = np.linalg.eigh(np.cov(xz.T))
    thick = V[:, 0]                      # eng yupqa o'q — kaft normali
    lo, hi = A[y < np.percentile(y, 35)], A[y > np.percentile(y, 70)]
    shift = (hi.mean(0) - lo.mean(0))[[0, 2]]
    if shift @ thick < 0:
        thick = -thick
    palm = Vector((thick[0], 0, thick[1])).normalized()          # barmoq uchlari shu tomonga bukilgan
    K = Vector((0, 1, 0)).cross(palm).normalized()
    th = (lo.mean(0) - A.mean(0))
    index = K if Vector(th).dot(K) > 0 else -K                   # bosh barmoq (ko'rsatkich) tomoni
    return palm, index, float(y.max())


def add_fingers(arm, body):
    """har kaftga "barmoqlar" suyagi (bo'g'imdan uchgacha); barmoq qismi og'irligi unga yumshoq o'tkaziladi"""
    geo = {s: hand_geometry(arm, body, s) for s in ("Right", "Left")}
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for s in ("Right", "Left"):
        h = eb[P + s + "Hand"]
        M = h.matrix.copy()
        palm, index, ymax = geo[s]
        f = eb.new(P + s + "HandFingers")
        f.head = M @ Vector((0, 0.09, 0))
        f.tail = M @ Vector((0, max(0.15, ymax), 0))
        f.align_roll(M.to_3x3() @ palm)
        f.parent = h
        f.use_deform = True
    bpy.ops.object.mode_set(mode="OBJECT")
    gi = {g.index: g.name for g in body.vertex_groups}
    for s in ("Right", "Left"):
        b = arm.data.bones[P + s + "Hand"]
        Minv = (arm.matrix_world @ b.matrix_local).inverted()
        gf = body.vertex_groups.get(P + s + "HandFingers") or body.vertex_groups.new(name=P + s + "HandFingers")
        gh = body.vertex_groups[P + s + "Hand"]
        gi = {g.index: g.name for g in body.vertex_groups}
        for v in body.data.vertices:
            hw = 0.0
            for g in v.groups:
                if gi[g.group] in (P + s + "Hand", P + s + "HandMiddle4"):
                    hw += g.weight
            if hw <= 0:
                continue
            yl = (Minv @ (body.matrix_world @ v.co)).y
            t = min(1.0, max(0.0, (yl - 0.075) / 0.035))
            t = t * t * (3 - 2 * t)
            if t > 0:
                gf.add([v.index], hw * t, "REPLACE")
                gh.add([v.index], hw * (1 - t), "REPLACE")
                g4 = body.vertex_groups.get(P + s + "HandMiddle4")
                if g4:
                    g4.remove([v.index])
    return geo


def curl_fingers(arm, geo):
    """barmoqlarni kaft tomonga bukish (suyakning mahalliy fazosida: Y -> kaft o'qi atrofida)"""
    for s in ("Right", "Left"):
        pb = arm.pose.bones[P + s + "HandFingers"]
        pb.rotation_mode = "QUATERNION"
        # barmoq suyagi roll'i kaftga (Z = kaft) — Y ni Z tomonga burish: X o'qi atrofida musbat burchak
        pb.rotation_quaternion = Matrix.Rotation(math.radians(CURL[s]), 3, "X").to_quaternion()


VM = {"right": 0.14, "down": 0.19, "fwd": 0.34, "yaw": 5.0, "pitch": 3.0}   # CS2 uslubidagi 1-shaxs qurol joyi (ko'zga nisbatan, m)


def first_person_pose(arm, gun, mag, actions, idle, S, grips, geo, hand_pose_fn=None):
    """1-shaxs (viewmodel): qurol bosh suyagiga biriktiriladi — ko'zga (kameraga) nisbatan doim bir joyda:
    VM["right"] o'ngda, ["down"] pastda, ["fwd"] oldinda, og'zi nishon tomonga. Ikkala musht IK bilan qurolga,
    qo'l yetmasa yelkalar (o'mrov) oldinga suriladi — 1-shaxsda tana ko'rinmaydi, bu sezilmaydi."""
    sc = bpy.context.scene
    f0 = int(idle.frame_range[0])
    arm.animation_data.action = idle
    sc.frame_set(f0)
    bpy.context.view_layer.update()
    hb = arm.pose.bones[P + "Head"]
    eye = arm.matrix_world @ hb.head + Vector((0, -0.09, 0.08))
    f_ = Matrix.Rotation(math.radians(VM["yaw"]), 3, "Z") @ Vector((0, -1, 0))
    f_ = (Matrix.Rotation(math.radians(VM["pitch"]), 3, f_.cross(Vector((0, 0, 1))).normalized()) @ f_).normalized()
    u_ = Vector((0, 0, 1))
    u_ = (u_ - f_ * u_.dot(f_)).normalized()
    R = Matrix(((-f_).cross(u_), -f_, u_)).transposed()
    Wvm = R.to_4x4()
    Wvm.translation = eye + Vector((-VM["right"], -VM["fwd"], -VM["down"])) / S
    for o in (gun, mag):
        if o is None:
            continue
        o.parent_bone = P + "Head"
        o.matrix_parent_inverse = Matrix.Identity(4)
        tail = arm.matrix_world @ hb.matrix @ Matrix.Translation((0, hb.length, 0))
        o.matrix_basis = tail.inverted() @ Wvm
    bpy.context.view_layer.update()
    Gw = gun.matrix_world.to_3x3().normalized()

    def pose_for(side):
        point, gdown, palm_dir = grips[side]
        palm_l, index_l, _ = geo[side]
        k_l = -index_l
        A = Matrix((k_l, palm_l, k_l.cross(palm_l))).transposed()
        kw = (Gw @ gdown).normalized()
        pw = Gw @ palm_dir
        pw = (pw - kw * pw.dot(kw)).normalized()
        Mb = Matrix((kw, pw, kw.cross(pw))).transposed() @ A.transposed()
        return Mb, gun.matrix_world @ point - Mb @ (Vector((0, 0.085, 0)) + palm_l * 0.028)
    # o'mrovlarni oldinga surish (kerak bo'lsa)
    Rw = arm.matrix_world.to_3x3()
    base = {}
    for side, sg in (("Left", -1), ("Right", 1)):
        pb = arm.pose.bones[P + side + "Shoulder"]
        pb.rotation_mode = "QUATERNION"
        base[side] = {}
        for name, act in actions.items():
            arm.animation_data.action = act
            fa, fb = int(act.frame_range[0]), int(round(act.frame_range[1]))
            qs = []
            for f in range(fa, fb + 1):
                sc.frame_set(f)
                qs.append(pb.rotation_quaternion.copy())
            base[side][name] = (fa, fb, qs)
    arm.animation_data.action = idle
    chosen = 0
    for prot in range(0, 42, 3):
        for side, sg in (("Left", -1), ("Right", 1)):
            pb = arm.pose.bones[P + side + "Shoulder"]
            Bm = (Rw @ pb.bone.matrix_local.to_3x3()).normalized()
            D = (Bm.inverted() @ Matrix.Rotation(math.radians(prot * sg), 3, "Z") @ Bm).to_quaternion()
            pb.rotation_quaternion = D @ base[side]["idle" if "idle" in base[side] else list(base[side])[0]][2][0]
        bpy.context.view_layer.update()
        ok_all = True
        for side in ("Left", "Right"):
            _, wt = pose_for(side)
            sh = arm.matrix_world @ arm.pose.bones[P + side + "Arm"].head
            L = (arm.data.bones[P + side + "Arm"].length + arm.data.bones[P + side + "ForeArm"].length) * 0.985
            ok_all = ok_all and (wt - sh).length <= L
        chosen = prot
        if ok_all:
            break
    print(f"1-shaxs: o'mrovlar {chosen}° oldinga")
    # o'mrov burilishini hamma animatsiyalarga yozish
    for side, sg in (("Left", -1), ("Right", 1)):
        pb = arm.pose.bones[P + side + "Shoulder"]
        Bm = (Rw @ pb.bone.matrix_local.to_3x3()).normalized()
        D = (Bm.inverted() @ Matrix.Rotation(math.radians(chosen * sg), 3, "Z") @ Bm).to_quaternion()
        for name, act in actions.items():
            fa, fb, qs = base[side][name]
            path = f'pose.bones["{P}{side}Shoulder"].rotation_quaternion'
            for fc in list(act.fcurves):
                if fc.data_path == path:
                    act.fcurves.remove(fc)
            arm.animation_data.action = act
            for i, f in enumerate(range(fa, fb + 1)):
                pb.rotation_quaternion = D @ qs[i]
                pb.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = idle
    sc.frame_set(f0)
    bpy.context.view_layer.update()
    cons = []
    rep = []
    for side in ("Right", "Left"):
        Mb, wt = pose_for(side)
        tgt = bpy.data.objects.new(f"fp_ik_{side}", None)
        sc.collection.objects.link(tgt)
        Mt = Mb.to_4x4()
        Mt.translation = wt
        tgt.matrix_world = Mt
        tgt.parent = gun
        tgt.matrix_parent_inverse = gun.matrix_world.inverted()
        sh = arm.matrix_world @ arm.pose.bones[P + side + "Arm"].head
        pole = bpy.data.objects.new(f"fp_pole_{side}", None)
        sc.collection.objects.link(pole)
        pole.location = (sh + wt) / 2 + Vector((0.3 if side == "Left" else -0.3, 0.15, -0.45))
        c = arm.pose.bones[P + side + "ForeArm"].constraints.new("IK")
        c.target, c.pole_target, c.chain_count, c.use_tail = tgt, pole, 2, True
        best = None
        for a_ in range(-180, 180, 10):
            c.pole_angle = math.radians(a_)
            bpy.context.view_layer.update()
            e = (arm.matrix_world @ arm.pose.bones[P + side + "ForeArm"].head - pole.location).length
            if best is None or e < best[0]:
                best = (e, a_)
        c.pole_angle = math.radians(best[1])
        cr = arm.pose.bones[P + side + "Hand"].constraints.new("COPY_ROTATION")
        cr.target = tgt
        bpy.context.view_layer.update()
        rep.append(f"{side} {((arm.matrix_world @ arm.pose.bones[P + side + 'ForeArm'].tail) - wt).length * 100:.2f} sm")
        cons.append((side, c, cr, tgt, pole))
    print("1-shaxs qurol ushlash:", ", ".join(rep))
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for name, act in actions.items():
        arm.animation_data.action = act
        for pb in arm.pose.bones:
            pb.bone.select = pb.name in ARM_IK_BONES
        fa, fb = int(act.frame_range[0]), int(round(act.frame_range[1]))
        bpy.ops.nla.bake(frame_start=fa, frame_end=fb, only_selected=True, visual_keying=True, clear_constraints=False,
                         use_current_action=True, bake_types={"POSE"})
    bpy.ops.object.mode_set(mode="OBJECT")
    for side, c, cr, tgt, pole in cons:
        arm.pose.bones[P + side + "ForeArm"].constraints.remove(c)
        arm.pose.bones[P + side + "Hand"].constraints.remove(cr)
        bpy.data.objects.remove(tgt)
        bpy.data.objects.remove(pole)
    arm.animation_data.action = idle
    return {"vm": VM, "clavicle_protraction": chosen}


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    files = sorted(glob.glob(os.path.join(SRC, "ct_*.glb")))
    assert files, "assets_src/ct_hero/ct_*.glb yo'q"
    objs = import_glb(files[0])
    arm = [o for o in objs if o.type == "ARMATURE"][0]
    body = [o for o in objs if o.type == "MESH" and o.find_armature() == arm][0]
    for o in objs:
        if o.type == "MESH" and o is not body:
            bpy.data.objects.remove(o)
    # Meshy mesh'i to'liq yopiq emas: ikki tomonlama material — hech bir burchakdan tana "bo'sh" ko'rinmaydi
    for m in body.data.materials:
        m.use_backface_culling = False
    geo = add_fingers(arm, body)
    actions = {}
    # har bir fayldan animatsiya (bir xil skelet) — nomi fayl nomidan: ct_idle.glb -> "idle"
    for f in files:
        name = os.path.basename(f)[3:-4]
        before = set(bpy.data.actions)
        if f != files[0]:
            extra = import_glb(f)
        new = [a for a in bpy.data.actions if (a not in before or f == files[0])]
        best = max(new, key=lambda a: a.frame_range[1] - a.frame_range[0])
        best.name = name
        best.use_fake_user = True
        actions[name] = best
        if f != files[0]:
            for o in extra:
                bpy.data.objects.remove(o)
    for a in list(bpy.data.actions):
        if a not in actions.values():
            bpy.data.actions.remove(a)
    # masshtab: Godot'da model TARGET_H bo'yiga keltiriladi; qurol shunga teskari kichraytiriladi (haqiqiy 0.80 m bo'lsin)
    zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
    h = max(zs) - min(zs)
    S = TARGET_H / h
    import rig_characters as RC
    gun, mag = RC.load_weapon("m416")
    W = RC.WEAPONS["m416"]
    for o in (gun, mag):
        if o:
            o.data.transform(Matrix.Scale(1.0 / S, 4))
    fx, fz = W["fore"]
    gx, gz = W["grip"]
    fore_local = Vector((0, (fx - gx), (fz - gz))) / S        # vertikal tutqich, qurol fazosida (dastaga nisbatan)
    # qurol holati idle ning 1-kadrida: dasta o'ng kaftda, og'iz chap kaft tomonga, magazin pastga
    idle = actions.get("idle") or list(actions.values())[0]
    arm.animation_data.action = idle
    sc = bpy.context.scene
    leg_cons = []
    if "idle" in actions:
        leg_cons = fix_stance(arm, actions["idle"])
    sc.frame_set(int(idle.frame_range[0]))
    bpy.context.view_layer.update()
    pr, wr, tr = palm(arm, "Right")
    pl, wl, tl = palm(arm, "Left")
    # og'iz yo'nalishi: kaftlar chizig'ining gorizontal qismi va tana oldi (−Y) o'rtasi, 6° pastga ("tayyor" turish)
    # --- qurol: qo'ndoq o'ng yelka chuqurchasida, og'iz oldinga (8° markazga) va 10° pastga ("tayyor" turish).
    #     Qurol ko'krak suyagiga (Spine2) biriktiriladi — animatsiyadagi nafas va tebranish bilan birga yuradi;
    #     ikkala qo'l IK bilan qurolga: o'ng — dastaga, chap — vertikal tutqichga (kaft burilishi animatsiyadagidek).
    bx, bz = W["butt"]
    butt_local = Vector((0, (bx - gx), (bz - gz))) / S
    shR = arm.matrix_world @ arm.pose.bones[P + "RightArm"].head
    # tana sirti (jilet bilan): qurol va mushtlar jilet ICHIGA kirmasligi uchun haqiqiy mesh'dan o'lchanadi
    dg = bpy.context.evaluated_depsgraph_get()
    evb = body.evaluated_get(dg)
    meb = evb.to_mesh()
    gi_ = {g.index: g.name for g in body.vertex_groups}
    def top_bone(v):
        return max(((g.weight, gi_[g.group]) for g in v.groups), default=(0, ""))[1]
    torso = np.array([(evb.matrix_world @ meb.vertices[v.index].co)[:] for v in body.data.vertices
                      if not any(k in top_bone(v) for k in ("Arm", "Hand", "Middle4", "Fingers"))])
    evb.to_mesh_clear()
    def front_y(x, z, rx=0.05, rz=0.05):
        m = (np.abs(torso[:, 0] - x) < rx) & (np.abs(torso[:, 2] - z) < rz)
        return float(torso[m, 1].min()) if m.any() else None
    pocket = shR + Vector((0.075, 0.0, -0.01))
    fy = front_y(pocket.x, pocket.z)
    pocket.y = (fy - 0.01) if fy is not None else shR.y - 0.12
    print(f"qo'ndoq: yelka {shR.y:.3f} -> jilet sirti {pocket.y:.3f} (y)")
    def place(yaw, pitch):
        f_ = Matrix.Rotation(math.radians(yaw), 3, "Z") @ Vector((0, -1, 0))
        f_ = (Matrix.Rotation(math.radians(pitch), 3, f_.cross(Vector((0, 0, 1))).normalized()) @ f_).normalized()
        u_ = Vector((0, 0, 1))
        u_ = (u_ - f_ * u_.dot(f_)).normalized()
        Y_ = -f_
        R_ = Matrix((Y_.cross(u_), Y_, u_)).transposed()
        g_ = pocket - R_ @ butt_local
        # musht (dasta atrofida ~6 sm qalinlik) jilet sirtidan oldinda bo'lsin
        need_ = 0.0
        for q in (g_, g_ + R_ @ Vector((0, 0, -0.06 / S))):
            fyg = front_y(q.x, q.z, 0.06, 0.05)
            if fyg is not None:
                need_ = max(need_, q.y - (fyg - 0.065))
        if need_ > 0:
            g_ = g_ + Vector((0, -need_, 0))
        return R_, g_, need_
    # chap kaft vertikal tutqichga yetishi uchun: og'iz chapga eng kam burilish (14°…40°), 10° pastga
    reachL0 = (arm.data.bones[P + "LeftArm"].length + arm.data.bones[P + "LeftForeArm"].length) * 0.985
    shL0 = arm.matrix_world @ arm.pose.bones[P + "LeftArm"].head
    palmL, indexL, _ = geo["Left"]
    kL = -indexL
    AL = Matrix((kL, palmL, kL.cross(palmL))).transposed()
    holeL = Vector((0, 0.085, 0)) + palmL * 0.028
    fore_pt = Vector((0, fore_local.y, 0.029 / S))
    def left_ok(R3, grip_w, pt, gd, pd):
        kw = (R3 @ gd).normalized()
        pw = R3 @ pd
        pw = (pw - kw * pw.dot(kw)).normalized()
        Mb = Matrix((kw, pw, kw.cross(pw))).transposed() @ AL.transposed()
        return (grip_w + R3 @ pt - Mb @ holeL - shL0).length <= reachL0
    hg_pt = Vector((0, (-0.05 - gx) / S, (0.047 - gz) / S))
    found = None
    for target in ("fore", "hand"):
        for yaw in range(14, 42, 2):
            R3, grip_w, need = place(yaw, -10)
            ok_ = left_ok(R3, grip_w, fore_pt, Vector((0, 0.12, -1)), Vector((-1, 0, 0))) if target == "fore" else \
                left_ok(R3, grip_w, hg_pt, Vector((0, 1, 0)), Vector((-0.35, 0, 1)).normalized())
            if ok_:
                found = yaw
                break
        if found is not None:
            break
    if found is None:
        R3, grip_w, need = place(40, -10)
    print(f"qurol: og'iz {yaw}° chapga, 10° pastga; jiletdan {need * 100:.1f} sm oldinga suriladi")
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
    arm_cons = []
    report = []
    # mushtlar: o'ng — to'pponcha dastasida, chap — vertikal tutqichda; dasta mushtning teshigidan o'tadi,
    # ko'rsatkich barmoq tepada, kaft dastaga qaragan (qurol fazosi: +X — personajning chapi, +Y — qo'ndoq, +Z — tepa)
    curl_fingers(arm, geo)
    bpy.context.view_layer.update()
    grips = {
        "Right": (Vector((0, 0.012, -0.035)) / S, Vector((0, 0.35, -1)).normalized(), Vector((1, 0, 0))),
        # vertikal tutqich: model z −0.049…+0.017, o'rtasi −0.016 (dasta boshi −0.045 ga nisbatan +0.029)
        "Left": (Vector((0, fore_local.y, 0.029 / S)), Vector((0, 0.12, -1)).normalized(), Vector((-1, 0, 0))),
    }
    Gw = gun.matrix_world.to_3x3().normalized()
    reachL = (arm.data.bones[P + "LeftArm"].length + arm.data.bones[P + "LeftForeArm"].length) * 0.985
    shL = arm.matrix_world @ arm.pose.bones[P + "LeftArm"].head

    def hand_pose(side, point, gdown, palm_dir):
        palm_l, index_l, ymax = geo[side]
        k_l = -index_l
        A = Matrix((k_l, palm_l, k_l.cross(palm_l))).transposed()
        kw = (Gw @ gdown).normalized()
        pw = Gw @ palm_dir
        pw = (pw - kw * pw.dot(kw)).normalized()
        B = Matrix((kw, pw, kw.cross(pw))).transposed()
        Mb = B @ A.transposed()
        hole = Vector((0, 0.085, 0)) + palm_l * 0.028
        return Mb, gun.matrix_world @ point - Mb @ hole
    # chap qo'l: avval vertikal tutqich; qo'l yetmasa — old qism (handguard) bo'ylab orqaga, pastdan qisib ushlash
    left_choice = None
    for mx in [fx] + [round(x, 3) for x in np.arange(-0.13, -0.035, 0.01)]:
        if mx == fx:
            cand = (Vector((0, fore_local.y, 0.029 / S)), Vector((0, 0.12, -1)).normalized(), Vector((-1, 0, 0)), "vertikal tutqich")
        else:
            cand = (Vector((0, (mx - gx) / S, (0.047 - gz) / S)), Vector((0, 1, 0)), Vector((-0.35, 0, 1)).normalized(), f"old qism (x={mx})")
        Mb_, wt_ = hand_pose("Left", *cand[:3])
        if (wt_ - shL).length <= reachL:
            left_choice = cand
            break
    left_choice = left_choice or cand
    print("chap qo'l:", left_choice[3])
    grips = {
        "Right": (Vector((0, 0.012, -0.035)) / S, Vector((0, 0.35, -1)).normalized(), Vector((1, 0, 0))),
        "Left": left_choice[:3],
    }
    for side in ("Right", "Left"):
        point, gdown, palm_dir = grips[side]
        Mb, target_w = hand_pose(side, point, gdown, palm_dir)
        tgt = bpy.data.objects.new(f"ik_{side}", None)
        sc.collection.objects.link(tgt)
        Mt = Mb.to_4x4()
        Mt.translation = target_w
        tgt.matrix_world = Mt
        tgt.parent = gun
        tgt.matrix_parent_inverse = gun.matrix_world.inverted()
        cr = arm.pose.bones[P + side + "Hand"].constraints.new("COPY_ROTATION")
        cr.target = tgt
        elbow = arm.matrix_world @ arm.pose.bones[P + side + "ForeArm"].head
        shoulder = arm.matrix_world @ arm.pose.bones[P + side + "Arm"].head
        pole = bpy.data.objects.new(f"pole_{side}", None)
        sc.collection.objects.link(pole)
        mid = (shoulder + target_w) / 2
        down_out = Vector((0.25 if side == "Left" else -0.25, 0.1, -0.45))
        pole.location = mid + down_out
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
            e = (arm.matrix_world @ arm.pose.bones[P + side + "ForeArm"].head - pole.matrix_world.translation).length
            if best is None or e < best[0]:
                best = (e, a_)
        c.pole_angle = math.radians(best[1])
        bpy.context.view_layer.update()
        err = ((arm.matrix_world @ arm.pose.bones[P + side + "ForeArm"].tail) - target_w).length
        report.append(f"{side}: bilak nishondan {err * 100:.2f} sm")
        arm_cons.append((arm.pose.bones[P + side + "ForeArm"], c, tgt, pole))
        arm_cons.append((arm.pose.bones[P + side + "Hand"], cr, None, None))
    print("qurol ushlash:", ", ".join(report))
    if os.environ.get("DEBUG_HANDS"):
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        gi_ = {g.index: g.name for g in body.vertex_groups}
        for side in ("Right", "Left"):
            pts = [ev.matrix_world @ me.vertices[v.index].co for v in body.data.vertices
                   if any(gi_[g.group] in (P + side + "Hand", P + side + "HandFingers") and g.weight > 0.5 for g in v.groups)]
            cen = sum(pts, Vector()) / len(pts)
            gp = gun.matrix_world @ grips[side][0]
            hb = arm.pose.bones[P + side + "Hand"]
            print(side, "musht markazi", cen.to_tuple(3), "dasta", gp.to_tuple(3), "farq sm", round((cen - gp).length * 100, 1),
                  "bilak", (arm.matrix_world @ hb.head).to_tuple(3), "n", len(pts))
            # kaft suyagi o'qlari dunyoda
            Mw = (arm.matrix_world @ hb.matrix).to_3x3()
            print("   hand Y", (Mw @ Vector((0, 1, 0))).normalized().to_tuple(2), "palm", (Mw @ geo[side][0]).normalized().to_tuple(2),
                  "index", (Mw @ geo[side][1]).normalized().to_tuple(2))
        ev.to_mesh_clear()
        sc.render.engine = "CYCLES"; sc.cycles.samples = 8; sc.cycles.device = "CPU"
        sc.render.resolution_x = sc.render.resolution_y = 520
        wd = bpy.data.worlds.new("w"); sc.world = wd; wd.use_nodes = True
        wd.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.82, 0.85, 1)
        wd.node_tree.nodes["Background"].inputs[1].default_value = 1.4
        cam = bpy.data.objects.new("dbgcam", bpy.data.cameras.new("dbgcam")); sc.collection.objects.link(cam); sc.camera = cam
        cam.data.lens = 50
        gc = gun.matrix_world @ Vector((0, -0.12 / S, 0))
        gR = gun.matrix_world @ grips["Right"][0]
        views = [("chap", gc, (0.7, -0.15, 0.1)), ("ong", gc, (-0.7, -0.1, 0.15)), ("old", gc, (0.05, -0.8, 0.15)),
                 ("ong_dasta", gR, (-0.35, -0.2, 0.05)), ("ong_dasta_past", gR, (-0.25, -0.2, -0.25)), ("ong_dasta_chap", gR, (0.3, -0.25, 0.0))]
        for nm_, gc, off in views:
            cam.location = gc + Vector(off)
            d_ = gc - cam.location
            cam.rotation_euler = d_.to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = os.path.join(os.environ["DEBUG_HANDS"], f"hands_{nm_}.png")
            bpy.ops.render.render(write_still=True)
    # IK ni kalit kadrlarga pishirish (faqat chap qo'l: yelka va bilak)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    info = {"scale": S, "animations": {}, "height_src": h}
    for name, act in list(actions.items()):
        arm.animation_data.action = act
        stance = name in STANCE_FIX
        for cc in leg_cons:
            cc.mute = not stance
        for pb in arm.pose.bones:
            pb.bone.select = pb.name in ARM_IK_BONES or (stance and pb.name in LEG_BONES)
        f0, f1 = int(act.frame_range[0]), int(round(act.frame_range[1]))
        bpy.ops.nla.bake(frame_start=f0, frame_end=f1, only_selected=True, visual_keying=True, clear_constraints=False,
                         use_current_action=True, bake_types={"POSE"})
        info["animations"][name] = {"frames": f1 - f0 + 1, "length": (f1 - f0) / 30.0}
    bpy.ops.object.mode_set(mode="OBJECT")
    for pbc, cc, tg, po in arm_cons:
        pbc.constraints.remove(cc)
        for o_ in (tg, po):
            if o_ is not None:
                bpy.data.objects.remove(o_)
    for pb in arm.pose.bones:
        for cc in list(pb.constraints):
            pb.constraints.remove(cc)
    for o in [o for o in bpy.data.objects if o.name.startswith(("stance_", "kneepole_"))]:
        bpy.data.objects.remove(o)
    arm.animation_data.action = idle
    # import paytida yaratilgan NLA treklari (asl glTF nomlari bilan) eksportda nomni buzadi — olib tashlanadi
    for tr_ in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr_)
    for nm, a_ in actions.items():
        a_.name = nm
        for k in list(a_.keys()):
            del a_[k]
    for o in (body, gun, mag):
        if o:
            for m in o.data.materials:
                for n in m.node_tree.nodes:
                    if n.type == "TEX_IMAGE" and n.image and max(n.image.size) > 2048:
                        n.image.scale(2048, 2048)
    os.makedirs(OUT, exist_ok=True)

    def export(path, objs):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_animations=True,
                                  export_animation_mode="ACTIONS", export_force_sampling=True, export_image_format="JPEG",
                                  export_jpeg_quality=88, export_yup=True, export_skins=True, export_reset_pose_bones=True)
    parts = [body, gun] + ([mag] if mag else [])
    export(os.path.join(OUT, "ct_hero.glb"), parts)
    # 1-shaxs: faqat bilak va kaftlar (asosiy og'irligi qo'l suyaklarida bo'lgan uchlar) + qurol
    arms = body.copy()
    arms.data = body.data.copy()
    arms.name = "ct_hero_arms"
    sc.collection.objects.link(arms)
    gi = {g.index: g.name for g in arms.vertex_groups}
    keep = []
    for v in arms.data.vertices:
        ws = sorted(((g.weight, gi[g.group]) for g in v.groups), reverse=True)
        keep.append(bool(ws) and ws[0][1] in ARM_BONES)
    bm = bmesh.new()
    bm.from_mesh(arms.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bv for bv in bm.verts if not keep[bv.index]], context="VERTS")
    bm.to_mesh(arms.data)
    bm.free()
    body.hide_set(True)
    fp_info = first_person_pose(arm, gun, mag, actions, idle, S, grips, geo, hand_pose_fn=None)
    info["first_person"] = fp_info
    export(os.path.join(OUT, "ct_hero_arms.glb"), [arms, gun] + ([mag] if mag else []))
    info["weapon"] = "m416"
    info["fore_local"] = list(fore_local)
    json.dump(info, open(os.path.join(OUT, "ct_hero.json"), "w"), indent=1)
    print("tayyor:", list(actions), "masshtab", round(S, 4))


if __name__ == "__main__":
    build()
