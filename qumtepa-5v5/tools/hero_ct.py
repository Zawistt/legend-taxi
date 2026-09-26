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
ARM_BONES = {P + n for n in ("LeftArm", "LeftForeArm", "LeftHand", "LeftHandMiddle4", "RightArm", "RightForeArm", "RightHand", "RightHandMiddle4")}


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
ARM_IK_BONES = {P + n for n in ("LeftArm", "LeftForeArm", "RightArm", "RightForeArm")}
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
    pocket = shR + Vector((0.075, -0.05, -0.075))
    fwd = Matrix.Rotation(math.radians(14), 3, "Z") @ Vector((0, -1, 0))
    fwd = (Matrix.Rotation(math.radians(-10), 3, fwd.cross(Vector((0, 0, 1))).normalized()) @ fwd).normalized()
    up = Vector((0, 0, 1))
    up = (up - fwd * up.dot(fwd)).normalized()
    Y = -fwd
    Z = up
    X = Y.cross(Z)
    R3 = Matrix((X, Y, Z)).transposed()
    grip_w = pocket - R3 @ butt_local
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
    # chap kaft (animatsiyada ochiq, barmoq suyaklari yo'q): vertikal tutqichdan oldinroqda qurol old qismini pastdan ushlaydi
    under = Vector((0, -0.29, 0.05)) / S
    for side, point in (("Right", Vector((0, 0, 0))), ("Left", under)):
        _, w_, t_ = palm(arm, side)
        hd = (t_ - w_).normalized()
        tgt = bpy.data.objects.new(f"ik_{side}", None)
        sc.collection.objects.link(tgt)
        tgt.parent = gun
        tgt.matrix_parent_inverse = Matrix.Identity(4)
        target_w = gun.matrix_world @ point - hd * 0.08          # bilak: kaft markazi nuqtada bo'lsin
        tgt.location = gun.matrix_world.inverted() @ target_w
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
    print("qurol ushlash:", ", ".join(report))
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
        bpy.data.objects.remove(tg)
        bpy.data.objects.remove(po)
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
    export(os.path.join(OUT, "ct_hero_arms.glb"), [arms, gun] + ([mag] if mag else []))
    info["weapon"] = "m416"
    info["fore_local"] = list(fore_local)
    json.dump(info, open(os.path.join(OUT, "ct_hero.json"), "w"), indent=1)
    print("tayyor:", list(actions), "masshtab", round(S, 4))


if __name__ == "__main__":
    build()
