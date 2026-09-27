"""Qumtepa — Terrorchi (T) 3-shaxs modeli: "Desert Shadow Operative" (foydalanuvchi bergan, Meshy auto-rig, Mixamo skeleti).

Kirish:  assets_src/t_shadow_operative.glb   (tana + 28 suyakli skelet, A-poza, 2048/4096 teksturalar)
Chiqish: godot/characters/t_shadow.glb       (tana + skelet + 3-shaxs animatsiyalari; qurol yo'q — Godot "weapon" suyagiga ulaydi)
         godot/characters/t_shadow_info.json (animatsiyalar ro'yxati, tezliklar, qurol ushlash nuqtalari)
         docs/characters/t_shadow/*.png       (PREVIEW=1 — tekshiruv kadrlari)

Faqat 3-SHAXS (boshqalar ko'radigan tana, botlar). Birinchi shaxs (o'yinchi kamerasidagi qo'l va qurol) bu modelga
umuman bog'liq emas — u alohida (character_model.gd, first_person=true).

Skelet o'zgarmaydi (og'irliklar — modelning o'ziniki), faqat:
  * suyaklar bizning nomlarga o'tkaziladi (mixamorig:Spine2 -> chest, ...), qo'l/oyoq suyaklarining "roll"i
    rig_characters.py dagi qoidaga keltiriladi (kaft normali — Z o'qi) — shunda o'sha IK va poza kodi ishlaydi;
  * qo'shiladi: root, weapon (ko'krakka bog'langan, qurol shu yerga ulanadi), mag, IK nishonlari (eksport qilinmaydi);
  * bo'y 1.80 m ga keltiriladi (o'yindagi kapsula bilan bir xil).
Animatsiyalar: haqiqiy odam harakati (CMU motion capture) — turish, yurish/yugurish/o'tirib yurish (4 tomonga), sakrash,
bomba qo'yish, o'lim; qo'llar IK bilan qurolda; o'q uzish, qayta o'qlash. Qo'shimcha qo'l pozalari (Godot'da faqat
qo'l/yelka suyaklariga filtr bilan qo'yiladi): to'pponcha, pichoq, granata, bomba (C4).

Ishga tushirish: python3 rig_t_shadow.py   (bpy 4.2, ~3 daqiqa; PREVIEW=1 — kadrlar ham)
"""
import bpy, math, json, os, sys
import numpy as np
from mathutils import Vector, Matrix, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_characters as RC

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "assets_src", "t_shadow_operative.glb")
OUT = os.path.join(HERE, "..", "godot", "characters")
H = 1.80
WNAME = "akm"                       # 3-shaxs qurol ushlash geometriyasi (avtomat o'lchami); qurolning o'zi Godot'da ulanadi

RENAME = {"Hips": "hips", "Spine": "spine", "Spine1": "spine1", "Spine2": "chest", "Neck": "neck", "Head": "head",
          "HeadTop_End": "head_end", "LeftShoulder": "clavicle.L", "LeftArm": "upper_arm.L", "LeftForeArm": "forearm.L",
          "LeftHand": "hand.L", "LeftHandMiddle4": "fingers.L", "RightShoulder": "clavicle.R", "RightArm": "upper_arm.R",
          "RightForeArm": "forearm.R", "RightHand": "hand.R", "RightHandMiddle4": "fingers.R",
          "LeftUpLeg": "thigh.L", "LeftLeg": "shin.L", "LeftFoot": "foot.L", "LeftToeBase": "toe.L", "LeftToe_End": "toe_end.L",
          "RightUpLeg": "thigh.R", "RightLeg": "shin.R", "RightFoot": "foot.R", "RightToeBase": "toe.R", "RightToe_End": "toe_end.R"}


def load():
    RC.reset()
    bpy.ops.import_scene.gltf(filepath=SRC)
    body = arm = None
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o.parent is None:
            bpy.data.objects.remove(o)                # ortiqcha Icosphere
        elif o.type == "MESH":
            body = o
        elif o.type == "ARMATURE":
            arm = o
    assert body and arm
    # o'lcham: bo'y 1.80 m, oyoq osti z=0, markaz x=0
    bpy.context.view_layer.update()
    v = RC.verts_np(body)
    Mw = np.array(body.matrix_world)
    vw = v @ Mw[:3, :3].T + Mw[:3, 3]
    s = H / (vw[:, 2].max() - vw[:, 2].min())
    arm.scale = arm.scale * s
    bpy.context.view_layer.update()
    vw = RC.verts_np(body) @ np.array(body.matrix_world)[:3, :3].T + np.array(body.matrix_world)[:3, 3]
    arm.location.z -= vw[:, 2].min()
    arm.location.x -= (vw[:, 0].max() + vw[:, 0].min()) / 2
    bpy.context.view_layer.update()
    for o in (arm, body):
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    arm.name = "Skeleton"
    arm.data.name = "Skeleton"
    body.name = "t_shadow_body"
    return body, arm


def rename_and_roll(ob, body):
    for b in ob.data.bones:
        k = b.name.replace("mixamorig:", "")
        if k in RENAME:
            b.name = RENAME[k]
    for vg in body.vertex_groups:
        k = vg.name.replace("mixamorig:", "")
        if k in RENAME:
            vg.name = RENAME[k]
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    eb = ob.data.edit_bones
    if "headfront" in eb:
        eb.remove(eb["headfront"])
    FWD = Vector((0, -1, 0))
    for n in ("hips", "spine", "spine1", "chest", "neck", "head", "head_end"):
        eb[n].align_roll(FWD)
    for s, sg in (("L", 1), ("R", -1)):
        eb[f"clavicle.{s}"].align_roll(FWD)
        for n in (f"upper_arm.{s}", f"forearm.{s}"):
            eb[n].align_roll(Vector((0, 1, 0)))
        for n in (f"hand.{s}", f"fingers.{s}"):
            d = (eb[n].tail - eb[n].head).normalized()
            palm = Vector((-sg, 0, 0))
            eb[n].align_roll((palm - d * palm.dot(d)).normalized())
        for n in (f"thigh.{s}", f"shin.{s}"):
            eb[n].align_roll(FWD)
        for n in (f"foot.{s}", f"toe.{s}", f"toe_end.{s}"):
            eb[n].align_roll(Vector((0, 0, 1)))
    # J — bo'g'im nuqtalari (rig_characters bilan bir xil nomlar)
    J = {"hips": eb["thigh.L"].head.copy() * 0}
    hz = (eb["thigh.L"].head.z + eb["thigh.R"].head.z) / 2
    J["hips"] = Vector((0, eb["hips"].head.y, hz))
    for n in ("spine", "spine1", "chest", "neck", "head"):
        J[n] = eb[n].head.copy()
    J["head_end"] = eb["head"].tail.copy()
    for s in ("L", "R"):
        J[f"hip.{s}"] = eb[f"thigh.{s}"].head.copy()
        J[f"knee.{s}"] = eb[f"shin.{s}"].head.copy()
        J[f"ankle.{s}"] = eb[f"foot.{s}"].head.copy()
        J[f"toe.{s}"] = eb[f"toe.{s}"].head.copy()
        J[f"clav.{s}"] = eb[f"clavicle.{s}"].head.copy()
        J[f"shoulder.{s}"] = eb[f"upper_arm.{s}"].head.copy()
        J[f"elbow.{s}"] = eb[f"forearm.{s}"].head.copy()
        J[f"wrist.{s}"] = eb[f"hand.{s}"].head.copy()
        J[f"hand_end.{s}"] = eb[f"fingers.{s}"].tail.copy()
    # qo'shimcha suyaklar
    def bone(name, head, tail, parent=None, roll_to=None, deform=True):
        b = eb.new(name)
        b.head, b.tail = Vector(head), Vector(tail)
        if roll_to is not None:
            b.align_roll(Vector(roll_to))
        if parent:
            b.parent = eb[parent]
        b.use_deform = deform
        return b
    bone("root", (0, 0, 0), (0, 0.25, 0), roll_to=(0, 0, 1))
    eb["hips"].parent = eb["root"]
    bone("weapon", (0, 0, 1.3), (0, -0.2, 1.3), "chest", (0, 0, 1))
    bone("mag", (0, -0.1, 1.2), (0, -0.1, 1.08), "weapon", (0, -1, 0))
    bone("ik_hand.R", (0, 0, 0), (0, 0, 0.1), "weapon", (1, 0, 0), deform=False)
    bone("ik_hand.L", (0, 0, 0), (0, 0, 0.1), "weapon", (0, 0, 1), deform=False)
    bone("pole_elbow.R", (-0.6, 0.25, 1.05), (-0.6, 0.25, 1.15), "chest", deform=False)
    bone("pole_elbow.L", (0.45, -0.1, 0.85), (0.45, -0.1, 0.95), "chest", deform=False)
    for s in ("L", "R"):
        a = J[f"ankle.{s}"]
        bone(f"ik_foot.{s}", a, J[f"toe.{s}"], "root", (0, 0, 1), deform=False)
        bone(f"pole_knee.{s}", (a.x, -0.9, 0.55), (a.x, -0.9, 0.65), "hips", deform=False)
    for b in eb:
        b.use_connect = False if b.name in ("root",) else b.use_connect
    bpy.ops.object.mode_set(mode="OBJECT")
    for n in ("fingers.L", "fingers.R", "head_end", "toe_end.L", "toe_end.R"):
        ob.data.bones[n].use_deform = ob.data.bones[n].use_deform
    return J


# qo'shimcha qo'l pozalari (qurol suyagi ko'krakka nisbatan qayerda, qo'llar qayerda) — idle trekining 0-kadrida
def hold_actions(P, info):
    """to'pponcha / pichoq / granata / C4: qurol suyagi boshqa joyda, IK nishonlari qurol fazosida boshqa joyda.
    Bu kliplar Godot'da faqat yelka-qo'l suyaklariga (va weapon) qo'yiladi — pastki tana harakati o'zgarmaydi."""
    acts = {}
    idle = P.idle_track
    ob = P.ob
    rest = P.rest
    ikR0 = rest["weapon"].inverted() @ rest["ik_hand.R"]
    ikL0 = rest["weapon"].inverted() @ rest["ik_hand.L"]
    J = P.J
    sh = (J["shoulder.L"] + J["shoulder.R"]) / 2
    def pose(name, wpos, wrot, r_off, l_world=None, l_off=None, frames=((1, {}),), loop=True):
        """wpos / l_world — armatura fazosida (X — chap, −Y — old, Z — tepa), tananing burilishidan qat'i nazar"""
        act = RC.new_action(ob, name)
        last = 1
        for fr, extra in frames:
            RC.pose_track(P, idle, 0, lean=extra.get("lean", 2))
            bpy.context.view_layer.update()
            wp = Vector(extra.get("wpos", wpos))
            wr = extra.get("wrot", wrot)
            M = Matrix.Translation(wp) @ wr.to_4x4() @ rest["weapon"].to_3x3().to_4x4()
            P.set_world("weapon", M)
            wM = ob.pose.bones["weapon"].matrix
            P.set_world("ik_hand.R", wM @ Matrix.Translation(Vector(r_off)) @ ikR0.to_3x3().to_4x4())
            if l_world is not None:
                lw = Vector(extra.get("l_world", l_world))
                P.set_world("ik_hand.L", Matrix.Translation(lw) @ (wM @ ikL0).to_3x3().to_4x4()
                            @ Matrix.Rotation(math.radians(extra.get("l_rot", 60)), 4, "X"))
            else:
                P.set_world("ik_hand.L", wM @ Matrix.Translation(Vector(l_off)) @ ikL0.to_3x3().to_4x4())
            P.key(fr)
            last = fr
        acts[name] = (act, last)
    cz = J["chest"].z
    shR = J["shoulder.R"]
    Rf = Matrix.Identity(3)
    # to'pponcha: ikki qo'l bilan oldinga cho'zilgan (CS2 dagidek), qurol ko'krak-iyak orasida, markazdan biroz o'ngda
    pose("hold_pistol", (-0.06, -0.42, cz + 0.06), Rf, (0, 0, 0), l_off=(0.035, 0.02, -0.03))
    # pichoq: o'ng qo'l oldinda-pastda, tig' oldinga; chap qo'l ko'krak oldida
    pose("hold_knife", (shR.x - 0.02, -0.34, cz - 0.2), Matrix.Rotation(math.radians(-20), 3, "X"), (0, 0, 0),
         l_world=(0.14, -0.2, cz - 0.08))
    # granata: o'ng qo'l yelka yonida (otishga tayyor), chap qo'l oldinga (mo'ljal)
    pose("hold_nade", (shR.x - 0.08, -0.02, cz + 0.16), Matrix.Rotation(math.radians(60), 3, "X"), (0, 0, 0),
         l_world=(0.12, -0.36, cz + 0.02))
    # granata otish: qo'l orqadan oldinga-tepaga
    pose("throw", (shR.x - 0.08, -0.02, cz + 0.16), Matrix.Rotation(math.radians(60), 3, "X"), (0, 0, 0),
         l_world=(0.12, -0.36, cz + 0.02), loop=False,
         frames=((1, {}), (6, {"wpos": (shR.x - 0.1, 0.12, cz + 0.24)}),
                 (11, {"wpos": (shR.x + 0.08, -0.42, cz + 0.12), "wrot": Matrix.Rotation(math.radians(-30), 3, "X"), "lean": 12}),
                 (18, {"wpos": (shR.x + 0.1, -0.3, cz - 0.2), "wrot": Matrix.Rotation(math.radians(-60), 3, "X"), "lean": 8})))
    # pichoq zarbasi: o'ngdan chapga kesish
    pose("slash", (shR.x - 0.02, -0.34, cz - 0.2), Matrix.Rotation(math.radians(-20), 3, "X"), (0, 0, 0),
         l_world=(0.14, -0.2, cz - 0.08), loop=False,
         frames=((1, {}), (4, {"wpos": (shR.x - 0.12, -0.2, cz + 0.02), "wrot": Matrix.Rotation(math.radians(40), 3, "Z")}),
                 (8, {"wpos": (0.1, -0.42, cz - 0.1), "wrot": Matrix.Rotation(math.radians(-50), 3, "Z"), "lean": 8}),
                 (14, {})))
    # C4: ikki qo'l bilan qorin oldida
    pose("hold_c4", (-0.02, -0.3, J["hips"].z + 0.22), Matrix.Rotation(math.radians(-20), 3, "X"), (-0.06, 0, 0), l_off=(0.12, 0.0, 0.0))
    return acts


def main():
    body, ob = load()
    J = rename_and_roll(ob, body)
    W = RC.WEAPONS[WNAME]
    # qurol suyagi: rig_characters.build dagidek (qo'ndoq o'ng yelka chuqurchasida)
    base = RC.weapon_base(J, W)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    eb = ob.data.edit_bones
    off = base.translation
    eb["weapon"].head = off
    eb["weapon"].tail = off + Vector((0, -0.2, 0))
    eb["weapon"].align_roll(Vector((0, 0, 1)))
    mx0, mx1, mz0, mz1 = W["mag_box"]
    gx, gz = W["grip"]
    mc = off + Vector((0, (mx0 + mx1) / 2 - gx, mz1 - gz))
    eb["mag"].head = mc
    eb["mag"].tail = mc + Vector((0, 0, -0.12))
    eb["mag"].align_roll(Vector((0, -1, 0)))
    bpy.ops.object.mode_set(mode="OBJECT")
    RC.place_ik_bones(ob, W)
    P = RC.Poser(ob, J, WNAME)
    P.CURL = {"R": 0, "L": 0}                       # modelda barmoq suyaklari yo'q
    P.clear()
    bpy.context.view_layer.update()
    RC.stance_pose(P)
    bpy.context.view_layer.update()
    chest1 = ob.pose.bones["chest"].matrix.copy()
    shR = ob.pose.bones["upper_arm.R"].head
    bx, bz = W["butt"]
    pocket = shR + Vector((0.065, -0.045, -0.07))
    grip = pocket - Vector((0, (bx - gx), (bz - gz)))
    Wm = Matrix.Translation(grip) @ ob.data.bones["weapon"].matrix_local.to_3x3().to_4x4()
    P.weapon_offset = chest1.inverted() @ Wm
    P.mag_rest_local = ob.data.bones["weapon"].matrix_local.inverted() @ ob.data.bones["mag"].matrix_local
    P.clear()
    RC.setup_constraints(ob)
    RC.stance_pose(P)
    RC.place_weapon(P)
    RC.ik_feet_static(P)
    RC.tune_poles(ob)
    bpy.context.view_layer.update()
    pbs = ob.pose.bones
    for s_ in ("L", "R"):
        print(f"IK {s_}: bilak->nishon {(pbs[f'forearm.{s_}'].tail - pbs[f'ik_hand.{s_}'].head).length:.3f} m, "
              f"oyoq->nishon {(pbs[f'shin.{s_}'].tail - pbs[f'ik_foot.{s_}'].head).length:.3f} m")
    P.clear()
    info = {"gaits": {}}
    acts = RC.make_actions(P, info)
    acts.update(hold_actions(P, info))
    baked = RC.bake_all(ob, acts)
    if os.environ.get("PREVIEW"):
        RC.PREVIEW_FRAMES[:] = RC.PREVIEW_FRAMES + [("hold_pistol", 1), ("hold_knife", 1), ("hold_nade", 1), ("hold_c4", 1),
                                                    ("throw", 11), ("slash", 8)]
        RC.preview(ob, "t_shadow", baked)
    RC.shrink_textures(body, 1024)
    os.makedirs(OUT, exist_ok=True)
    # IK yordamchi suyaklar eksport qilinmaydi (deform=False), qurol va magazin suyaklari — eksport qilinadi
    RC.export(os.path.join(OUT, "t_shadow.glb"), [body], ob)
    info.update(height=H, weapon_geom=WNAME, grip=list(ob.data.bones["weapon"].head_local),
                eye=list(J["head"] + Vector((0, -0.09, 0.08))), anims=sorted(baked.keys()))
    json.dump(info, open(os.path.join(OUT, "t_shadow_info.json"), "w"), indent=1, default=float)
    print("tayyor: t_shadow.glb,", len(baked), "animatsiya:", ", ".join(sorted(baked)))


if __name__ == "__main__":
    main()
