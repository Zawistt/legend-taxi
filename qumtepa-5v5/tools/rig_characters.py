"""Qumtepa 5v5 — personajlar: skelet, og'irliklar, qurol ushlash va animatsiyalar (Blender bpy).

Kirish: assets_src/{t_operator,ct_soldier,akm,m416}.glb (Meshy, skeletsiz, A-poza).
Chiqish (godot/characters/):
  t_operator.glb, ct_soldier.glb — skelet + tana + qurol (qo'lda) + barcha animatsiyalar (uchinchi shaxs, botlar)
  t_arms.glb, ct_arms.glb        — faqat qo'llar + qurol, o'sha skelet va animatsiyalar (birinchi shaxs ko'rinishi)
  rig_info.json                  — ko'z nuqtasi, animatsiya tezliklari va qadam fazalari (Godot skriptlari uchun)

Ishga tushirish:  pip install bpy==4.2.0 ;  python3 rig_characters.py   (~2 daqiqa)

Qurol ushlash: qurolda ikkita nuqta bor — o'ng qo'l (to'pponcha dastasi) va chap qo'l (old dasta / tutqich).
Qo'llar IK bilan shu nuqtalarga yopishadi, kaft yo'nalishi ham nuqtadan olinadi, shuning uchun qurol har qanday
harakatda (yugurish, o'tirish, sakrash, o'q uzish, o'q-dori almashtirish) qo'ldan chiqmaydi. Oyoqlar ham IK bilan
yerga "qadaladi": tayanch fazasida oyoq yerda sirpanmasdan orqaga ketadi, siltanish fazasida ko'tariladi.
"""
import bpy, bmesh, math, json, os, sys
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "assets_src")
OUT = os.path.join(HERE, "..", "godot", "characters")
FPS = 30
H = 1.80                                  # personaj bo'yi, m

# qurollar: haqiqiy uzunlik; o'ng qo'l (dasta), chap qo'l, qo'ndoq, o'q-dori qutisi — model koordinatalarida
# (Blender: uzunlik X bo'yicha, og'iz −X da; qiymatlar haqiqiy o'lchamga keltirilgandan keyin, metr)
WEAPONS = {
    "akm": dict(length=0.88, grip=(0.180, -0.020), fore=(-0.170, 0.040), fore_kind="under", butt=(0.435, 0.030),
                mag_box=(-0.105, 0.030, -0.13, 0.012), sight=0.125),
    "m416": dict(length=0.80, grip=(0.183, -0.045), fore=(-0.112, -0.030), fore_kind="vertical", butt=(0.370, 0.000),
                 mag_box=(-0.035, 0.075, -0.14, -0.005), sight=0.130),
}
CHARS = {"t_operator": "akm", "ct_soldier": "m416"}

# ------------------------------------------------------------------ yordamchilar
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    objs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    assert len(objs) == 1, path
    o = objs[0]
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def verts_np(o):
    a = np.empty(len(o.data.vertices) * 3)
    o.data.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


def set_verts(o, v):
    o.data.vertices.foreach_set("co", v.reshape(-1))
    o.data.update()


def shrink_textures(o, size):
    for m in o.data.materials:
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image and max(n.image.size) > size:
                n.image.scale(size, size)
                n.image.pack()


# ------------------------------------------------------------------ 1) personaj: o'lcham va bo'g'imlar
def load_character(name):
    o = import_glb(os.path.join(SRC, f"{name}.glb"))
    o.name = name + "_body"
    v = verts_np(o)
    v[:, 2] -= v[:, 2].min()
    v *= H / v[:, 2].max()
    v[:, 0] -= (v[:, 0].max() + v[:, 0].min()) / 2
    v[:, 1] -= np.median(v[(v[:, 2] > 0.9) & (v[:, 2] < 1.4), 1])
    set_verts(o, v)
    return o, v


def joints_from_mesh(v):
    """A-poza tanadan bo'g'im nuqtalari (Blender: X — personajning chapi, −Y — oldi, Z — tepa)"""
    def sl(z0, z1, xmin=-9, xmax=9):
        m = (v[:, 2] >= z0) & (v[:, 2] < z1) & (v[:, 0] >= xmin) & (v[:, 0] <= xmax)
        return v[m]
    # oraliq (crotch): markazda (|x|<0.025) tepa yo'q bo'lgan eng baland balandlik
    crotch = 0.6
    for z in np.arange(0.55, 1.0, 0.01):
        s = sl(z, z + 0.02, -0.3, 0.3)
        if len(s) and not np.any(np.abs(s[:, 0]) < 0.025):
            crotch = z
    J = {}
    hip_z = crotch + 0.09
    for side, sg in (("L", 1), ("R", -1)):
        def leg_c(z0, z1):
            s = sl(z0, z1)
            s = s[(s[:, 0] * sg > 0.02) & (np.abs(s[:, 0]) < 0.34)]
            return np.array([s[:, 0].mean(), np.median(s[:, 1])])
        up = leg_c(crotch - 0.08, crotch - 0.02)
        knee_z = 0.285 * H
        kn = leg_c(knee_z - 0.03, knee_z + 0.03)
        an = leg_c(0.07, 0.11)
        J[f"hip.{side}"] = Vector((up[0] * 0.8, 0.0, hip_z))
        J[f"knee.{side}"] = Vector((kn[0], kn[1] - 0.02, knee_z))
        J[f"ankle.{side}"] = Vector((an[0], an[1] + 0.02, 0.085))
        foot = sl(0.0, 0.06)
        foot = foot[foot[:, 0] * sg > 0.02]
        J[f"toe.{side}"] = Vector((an[0], foot[:, 1].min() + 0.04, 0.03))
        J[f"toe_end.{side}"] = Vector((an[0], foot[:, 1].min(), 0.02))
    J["hips"] = Vector((0, 0.0, hip_z))
    J["spine"] = Vector((0, 0.0, hip_z + 0.11))
    J["spine1"] = Vector((0, -0.005, hip_z + 0.24))
    J["chest"] = Vector((0, 0.0, hip_z + 0.37))
    neck_z = 0.845 * H
    J["neck"] = Vector((0, 0.01, neck_z))
    J["head"] = Vector((0, 0.0, neck_z + 0.07))
    J["head_end"] = Vector((0, 0.0, H))
    # qo'llar: tanadan ajralgan uchlari (|x| katta) — asosiy o'q bo'yicha chiziq
    sh_z = 0.79 * H
    for side, sg in (("L", 1), ("R", -1)):
        arm = v[(v[:, 0] * sg > 0.27) & (v[:, 2] > 0.55) & (v[:, 2] < sh_z)]
        c = arm.mean(0)
        _, _, vt = np.linalg.svd(arm - c)
        d = vt[0]
        if d[2] > 0:
            d = -d                                   # pastga (qo'l uchiga) qarasin
        proj = (arm - c) @ d
        tip = c + d * proj.max()
        torso = sl(sh_z - 0.04, sh_z + 0.04, -0.4, 0.4)
        sh_x = np.abs(torso[:, 0]).max() - 0.07
        shoulder = np.array([sg * sh_x, 0.0, sh_z])
        dd = tip - shoulder
        L = np.linalg.norm(dd)
        dd /= L
        wrist = shoulder + dd * (L - 0.17)
        elbow = shoulder + dd * ((L - 0.17) * 0.52) + np.array([0, 0.025, 0])
        J[f"clav.{side}"] = Vector((sg * 0.03, -0.01, sh_z - 0.02))
        J[f"shoulder.{side}"] = Vector(shoulder)
        J[f"elbow.{side}"] = Vector(elbow)
        J[f"wrist.{side}"] = Vector(wrist)
        J[f"hand_end.{side}"] = Vector(tip)
        J[f"knuckle.{side}"] = Vector(wrist + (tip - wrist) * 0.48)
    return J


# ------------------------------------------------------------------ 2) skelet
DEFORM = ["hips", "spine", "spine1", "chest", "neck", "head",
          "clavicle.L", "upper_arm.L", "forearm.L", "hand.L", "fingers.L", "clavicle.R", "upper_arm.R", "forearm.R", "hand.R", "fingers.R",
          "thigh.L", "shin.L", "foot.L", "toe.L", "thigh.R", "shin.R", "foot.R", "toe.R"]


def build_armature(J, wname):
    W = WEAPONS[wname]
    arm = bpy.data.armatures.new("Skeleton")
    ob = bpy.data.objects.new("Skeleton", arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.edit_bones

    def bone(name, head, tail, parent=None, roll_to=None, connect=False, deform=True):
        b = eb.new(name)
        b.head, b.tail = Vector(head), Vector(tail)
        if roll_to is not None:
            b.align_roll(Vector(roll_to))
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        b.use_deform = deform
        return b

    FWD = (0, -1, 0)
    bone("root", (0, 0, 0), (0, 0.25, 0), roll_to=(0, 0, 1))
    bone("hips", J["hips"], J["spine"], "root", roll_to=FWD)
    bone("spine", J["spine"], J["spine1"], "hips", FWD, True)
    bone("spine1", J["spine1"], J["chest"], "spine", FWD, True)
    bone("chest", J["chest"], J["neck"], "spine1", FWD, True)
    bone("neck", J["neck"], J["head"], "chest", FWD, True)
    bone("head", J["head"], J["head_end"], "neck", FWD, True)
    for s, sg in (("L", 1), ("R", -1)):
        bone(f"clavicle.{s}", J[f"clav.{s}"], J[f"shoulder.{s}"], "chest", FWD)
        bone(f"upper_arm.{s}", J[f"shoulder.{s}"], J[f"elbow.{s}"], f"clavicle.{s}", (0, 1, 0), True)
        bone(f"forearm.{s}", J[f"elbow.{s}"], J[f"wrist.{s}"], f"upper_arm.{s}", (0, 1, 0), True)
        # kaft ichkariga (tanaga) qaraydi: Z o'qi = kaft normali
        d = (J[f"hand_end.{s}"] - J[f"wrist.{s}"]).normalized()
        palm = Vector((-sg, 0, 0))
        palm = (palm - d * palm.dot(d)).normalized()
        bone(f"hand.{s}", J[f"wrist.{s}"], J[f"knuckle.{s}"], f"forearm.{s}", palm, True)
        bone(f"fingers.{s}", J[f"knuckle.{s}"], J[f"hand_end.{s}"], f"hand.{s}", palm, True)
        bone(f"thigh.{s}", J[f"hip.{s}"], J[f"knee.{s}"], "hips", FWD)
        bone(f"shin.{s}", J[f"knee.{s}"], J[f"ankle.{s}"], f"thigh.{s}", FWD, True)
        bone(f"foot.{s}", J[f"ankle.{s}"], J[f"toe.{s}"], f"shin.{s}", (0, 0, 1), True)
        bone(f"toe.{s}", J[f"toe.{s}"], J[f"toe_end.{s}"], f"foot.{s}", (0, 0, 1), True)
    # qurol: suyak boshi — o'ng qo'l ushlaydigan nuqta (dasta), yo'nalishi — og'iz tomonga (−Y), Z — tepa
    bone("weapon", (0, 0, 0), (0, -0.2, 0), "chest", (0, 0, 1))
    mx0, mx1, mz0, mz1 = W["mag_box"]
    gx, gz = W["grip"]
    mag_c = Vector((0, (mx0 + mx1) / 2 - gx, mz1 - gz))
    bone("mag", mag_c, mag_c + Vector((0, 0, -0.12)), "weapon", (0, -1, 0))
    # IK nishonlari (eksport qilinmaydi): bilak qayerda va kaft qayoqqa qarashi
    bone("ik_hand.R", (0, 0, 0), (0, 0, 0.1), "weapon", (1, 0, 0), deform=False)
    bone("ik_hand.L", (0, 0, 0), (0, 0, 0.1), "weapon", (0, 0, 1), deform=False)
    bone("pole_elbow.R", (-0.6, 0.25, 1.05), (-0.6, 0.25, 1.15), "chest", deform=False)
    bone("pole_elbow.L", (0.45, -0.1, 0.85), (0.45, -0.1, 0.95), "chest", deform=False)
    for s, sg in (("L", 1), ("R", -1)):
        a = J[f"ankle.{s}"]
        bone(f"ik_foot.{s}", a, J[f"toe.{s}"], "root", (0, 0, 1), deform=False)
        bone(f"pole_knee.{s}", (a.x, -0.9, 0.55), (a.x, -0.9, 0.65), "hips", deform=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    ob["weapon_name"] = wname
    return ob


# ------------------------------------------------------------------ 3) og'irliklar (masofa + tomon cheklovlari + silliqlash)
def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t


def skin(body, ob, J):
    v = verts_np(body)
    bones = [b for b in ob.data.bones if b.use_deform and b.name not in ("weapon", "mag")]
    names = [b.name for b in bones]
    n, k = len(v), len(bones)
    D = np.zeros((n, k))
    for j, b in enumerate(bones):
        a, c = np.array(b.head_local), np.array(b.tail_local)
        d, t = seg_dist(v, a, c)
        D[:, j] = d
    mask = np.ones((n, k), bool)
    x = v[:, 0]
    crotch = J["hips"].z - 0.09
    for j, nm in enumerate(names):
        if nm.endswith(".L"):
            mask[:, j] &= x > -0.02
        if nm.endswith(".R"):
            mask[:, j] &= x < 0.02
        if nm.split(".")[0] in ("thigh", "shin", "foot", "toe"):
            mask[:, j] &= v[:, 2] < crotch + 0.16
            mask[:, j] &= np.abs(x) < 0.38
        if nm.split(".")[0] in ("upper_arm", "forearm", "hand", "fingers"):
            sh = J[f"shoulder.{nm[-1]}"]
            mask[:, j] &= (np.abs(x) > abs(sh.x) - 0.08) & (v[:, 2] > 0.5)
        if nm.split(".")[0] in ("forearm", "hand", "fingers"):
            mask[:, j] &= np.abs(x) > abs(J[f"shoulder.{nm[-1]}"].x) + 0.04
        if nm in ("head", "neck"):
            mask[:, j] &= v[:, 2] > J["neck"].z - 0.08
        if nm in ("hips", "spine", "spine1", "chest", "neck", "head", "clavicle.L", "clavicle.R"):
            mask[:, j] &= (np.abs(x) < 0.34) | (v[:, 2] > J["neck"].z - 0.1)
    Wt = np.where(mask, 1.0 / np.maximum(D, 0.01) ** 5, 0.0)
    bad = Wt.sum(1) == 0
    Wt[bad] = 1.0 / np.maximum(D[bad], 0.01) ** 5
    Wt /= Wt.sum(1, keepdims=True)
    # silliqlash: bir xil joydagi (UV chokidagi) nusxalarni birlashtirib, qo'shni uchlar bo'yicha
    key = np.round(v / 1e-4).astype(np.int64)
    _, uid, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    m = len(uid)
    Wu = np.zeros((m, k))
    np.add.at(Wu, inv, Wt)
    cnt = np.bincount(inv, minlength=m)[:, None]
    Wu /= cnt
    edges = np.array([e.vertices[:] for e in body.data.edges])
    ea, eb_ = inv[edges[:, 0]], inv[edges[:, 1]]
    for _ in range(4):
        acc = Wu.copy()
        deg = np.ones(m)
        np.add.at(acc, ea, Wu[eb_])
        np.add.at(acc, eb_, Wu[ea])
        np.add.at(deg, ea, 1)
        np.add.at(deg, eb_, 1)
        Wu = 0.5 * Wu + 0.5 * acc / deg[:, None]
    Wt = Wu[inv]
    # har uchga ko'pi bilan 4 ta suyak
    idx = np.argsort(-Wt, 1)[:, :4]
    top = np.take_along_axis(Wt, idx, 1)
    top[top < 0.02] = 0
    top /= top.sum(1, keepdims=True)
    groups = {nm: body.vertex_groups.new(name=nm) for nm in names}
    for i in range(n):
        for jj in range(4):
            if top[i, jj] > 0:
                groups[names[idx[i, jj]]].add([i], float(top[i, jj]), "REPLACE")
    body.parent = ob
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = ob
    return names, idx, top


# ------------------------------------------------------------------ 4) qurol modeli
def load_weapon(wname):
    W = WEAPONS[wname]
    o = import_glb(os.path.join(SRC, f"{wname}.glb"))
    o.name = wname
    v = verts_np(o)
    s = W["length"] / (v[:, 0].max() - v[:, 0].min())
    v *= s
    gx, gz = W["grip"]
    mx0, mx1, mz0, mz1 = W["mag_box"]
    inmag = (v[:, 0] > mx0) & (v[:, 0] < mx1) & (v[:, 2] < mz1)
    # dasta nuqtasi koordinata boshiga; og'iz −X dan −Y ga (Z atrofida +90°)
    v[:, 0] -= gx
    v[:, 2] -= gz
    x, y = v[:, 0].copy(), v[:, 1].copy()
    v[:, 0], v[:, 1] = -y, x
    set_verts(o, v)
    # o'q-dori qutisini alohida obyektga ajratamiz (qayta o'qlashda qo'l bilan chiqadi)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    mag_faces = [f for f in bm.faces if all(inmag[vv.index] for vv in f.verts)]
    mag = None
    if mag_faces:
        me2 = o.data.copy()
        mag = bpy.data.objects.new(wname + "_mag", me2)
        bpy.context.scene.collection.objects.link(mag)
        bm2 = bmesh.new()
        bm2.from_mesh(me2)
        bm2.faces.ensure_lookup_table()
        keep = {f.index for f in mag_faces}
        bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if f.index not in keep], context="FACES")
        bm2.to_mesh(me2)
        bm2.free()
        bmesh.ops.delete(bm, geom=mag_faces, context="FACES")
        bm.to_mesh(o.data)
    bm.free()
    return o, mag


# ------------------------------------------------------------------ 5) poza va animatsiya
class Poser:
    def __init__(self, ob, J, wname):
        self.ob, self.J, self.W = ob, J, WEAPONS[wname]
        self.pb = ob.pose.bones
        self.rest = {b.name: b.matrix_local.copy() for b in ob.data.bones}

    CURL = {"R": 72, "L": 58}

    def clear(self):
        for p in self.pb:
            p.rotation_mode = "QUATERNION"
            p.rotation_quaternion = (1, 0, 0, 0)
            p.location = (0, 0, 0)
        # barmoqlar dasta atrofida bukilgan (kaft tomonga, suyakning X o'qi atrofida)
        for s, a in self.CURL.items():
            self.pb[f"fingers.{s}"].rotation_quaternion = Quaternion((1, 0, 0), math.radians(a))

    def rot(self, name, axis, deg):
        """suyakni tinch holatdagi armatura o'qi atrofida burish (ota-suyak zanjiri bilan birga)"""
        R = Matrix.Rotation(math.radians(deg), 3, Vector(axis))
        B = self.rest[name].to_3x3().normalized()
        q = (B.inverted() @ R @ B).to_quaternion()
        p = self.pb[name]
        p.rotation_quaternion = q @ p.rotation_quaternion

    def move(self, name, delta):
        """suyakni armatura fazosida siljitish (ota burilmagan deb)"""
        B = self.rest[name].to_3x3().normalized()
        self.pb[name].location = self.pb[name].location + B.inverted() @ Vector(delta)

    def set_world(self, name, M):
        bpy.context.view_layer.update()
        self.pb[name].matrix = M
        bpy.context.view_layer.update()

    def key(self, frame, names=None):
        for p in self.pb:
            if names and p.name not in names:
                continue
            p.keyframe_insert("rotation_quaternion", frame=frame)
            p.keyframe_insert("location", frame=frame)


def weapon_base(J, W, crouch=0.0):
    """qurolning asosiy holati (armatura fazosida): qo'ndoq o'ng yelka chuqurchasida, og'iz oldinga"""
    sh = J["shoulder.R"]
    bx, bz = W["butt"]
    gx, gz = W["grip"]
    pocket = Vector((sh.x + 0.07, -0.02, sh.z - 0.07))
    grip = pocket - Vector((0, (bx - gx), (bz - gz)))
    return Matrix.Translation(grip)


def hand_targets(W):
    """weapon suyagi fazosida: o'ng va chap bilak nishonlari (bilak nuqtasi, qo'l yo'nalishi, kaft normali)"""
    gx, gz = W["grip"]
    fx, fz = W["fore"]
    fore = Vector((0, fx - gx, fz - gz))
    # o'ng qo'l: dasta atrofida, bilak dastaning orqa-yuqorisida, barmoqlar oldinga-pastga, kaft chapga (+X)
    r_dir = Vector((0.05, -0.55, -0.83)).normalized()
    r_palm = Vector((1, 0, 0))
    r_palm = (r_palm - r_dir * r_palm.dot(r_dir)).normalized()
    r_wrist = Vector((-0.035, 0.05, 0.035)) - r_dir * 0.0
    r_wrist = Vector((-0.03, 0.0, 0.0)) - r_dir * 0.075
    if W["fore_kind"] == "vertical":
        l_dir = Vector((-0.15, -0.45, -0.88)).normalized()
        l_palm = Vector((-1, 0, 0))
        l_wrist = fore + Vector((0.035, 0.0, 0.01)) - l_dir * 0.075
    else:
        l_dir = Vector((-0.45, -0.85, 0.28)).normalized()
        l_palm = Vector((-0.35, 0, 1))
        l_wrist = fore + Vector((0.04, 0.0, -0.035)) - l_dir * 0.07
    l_palm = (l_palm - l_dir * l_palm.dot(l_dir)).normalized()
    return (r_wrist, r_dir, r_palm), (l_wrist, l_dir, l_palm)


def place_ik_bones(ob, W):
    (rw, rd, rp), (lw, ld, lp) = hand_targets(W)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    eb = ob.data.edit_bones
    o = eb["weapon"].head.copy()
    for nm, w, d, p in (("ik_hand.R", rw, rd, rp), ("ik_hand.L", lw, ld, lp)):
        b = eb[nm]
        b.head = o + w
        b.tail = o + w + d * 0.08
        b.align_roll(p)
    bpy.ops.object.mode_set(mode="OBJECT")


def setup_constraints(ob):
    pb = ob.pose.bones
    for s in ("L", "R"):
        c = pb[f"forearm.{s}"].constraints.new("IK")
        c.target, c.subtarget = ob, f"ik_hand.{s}"
        c.pole_target, c.pole_subtarget = ob, f"pole_elbow.{s}"
        c.chain_count = 2
        c.use_tail = True
        cr = pb[f"hand.{s}"].constraints.new("COPY_ROTATION")
        cr.target, cr.subtarget = ob, f"ik_hand.{s}"
        c = pb[f"shin.{s}"].constraints.new("IK")
        c.target, c.subtarget = ob, f"ik_foot.{s}"
        c.pole_target, c.pole_subtarget = ob, f"pole_knee.{s}"
        c.chain_count = 2
        cr = pb[f"foot.{s}"].constraints.new("COPY_ROTATION")
        cr.target, cr.subtarget = ob, f"ik_foot.{s}"


def tune_poles(ob):
    """IK qutb burchagini tanlash: tirsak/tizza qutb nishoniga eng yaqin tushadigan burchak"""
    pb = ob.pose.bones
    for chain, pole in (("forearm.L", "pole_elbow.L"), ("forearm.R", "pole_elbow.R"), ("shin.L", "pole_knee.L"), ("shin.R", "pole_knee.R")):
        c = pb[chain].constraints[0]
        best = None
        for a in range(-180, 180, 15):
            c.pole_angle = math.radians(a)
            bpy.context.view_layer.update()
            mid = pb[chain].head                        # tirsak / tizza (armatura fazosi)
            root = pb[chain].parent.head
            tip = pb[chain].tail
            axis = (tip - root).normalized()
            pp = pb[pole].head
            to_mid = mid - root - axis * (mid - root).dot(axis)
            to_pole = pp - root - axis * (pp - root).dot(axis)
            sc = to_mid.normalized().dot(to_pole.normalized()) if to_mid.length > 1e-5 else -1
            if best is None or sc > best[0]:
                best = (sc, a)
        c.pole_angle = math.radians(best[1])


# ---- harakat parametrlari
PERIOD = 0.6   # hamma yurishlarda bir xil sikl (s): Godot'da yurish <-> yugurish aralashganda qadamlar mos tushadi
GAITS = {
    # nom: tezlik (m/s), tayanch ulushi, son balandligi, oyoq ko'tarilishi; yarim qadam E = tezlik*sikl*tayanch/2
    "walk": dict(speed=2.3, ds=0.60, hip=-0.035, lift=0.10, bob=0.020, lean=4),
    "run": dict(speed=4.5, ds=0.38, hip=-0.07, lift=0.20, bob=0.045, lean=9),
    "crouch": dict(speed=1.55, ds=0.62, hip=-0.36, lift=0.09, bob=0.012, lean=18),
}
for _g in GAITS.values():
    _g["E"] = _g["speed"] * PERIOD * _g["ds"] / 2
DIRS = {"f": (0, -1), "b": (0, 1), "l": (1, 0), "r": (-1, 0)}


def stance_pose(P, crouch=False, hip_drop=-0.02, lean=3, twist=32, breathe=0.0):
    """umumiy qurolli turish: tana chapga buralgan (chap yelka oldinda), bosh oldinga qaraydi"""
    J = P.J
    P.move("hips", (0, 0.0, hip_drop))
    P.rot("hips", (0, 0, 1), -twist * 0.25)
    P.rot("spine", (0, 0, 1), -twist * 0.25)
    P.rot("spine1", (0, 0, 1), -twist * 0.25)
    P.rot("chest", (0, 0, 1), -twist * 0.25)
    P.rot("spine", (1, 0, 0), lean * 0.4)
    P.rot("spine1", (1, 0, 0), lean * 0.3 + breathe * 0.6)
    P.rot("chest", (1, 0, 0), lean * 0.3 - breathe)
    P.rot("neck", (0, 0, 1), twist * 0.6)
    P.rot("head", (0, 0, 1), twist * 0.4)
    P.rot("neck", (1, 0, 0), -lean * 0.5)
    P.rot("clavicle.R", (1, 0, 0), -4)
    P.rot("clavicle.L", (0, 0, 1), -6)


def place_weapon(P, extra=Matrix.Identity(4), rigid=False):
    """qurol joyi ko'krakka ergashadi (yurganda tabiiy tebranadi), lekin yo'nalishi doim oldinga — nishonga
    (tana egilsa ham og'iz pastga tushmaydi). rigid=True — qurol tana bilan birga buriladi (o'lim)."""
    bpy.context.view_layer.update()
    chest = P.ob.pose.bones["chest"].matrix
    M = chest @ P.weapon_offset
    if not rigid:
        M = Matrix.Translation(M.translation) @ P.rest["weapon"].to_3x3().to_4x4()
    P.set_world("weapon", M @ extra)


def feet(P, frame_phase, gait, d, crouch_extra=0.0):
    """IK oyoq nishonlari: tayanchda oyoq yerda harakat yo'nalishiga teskari sirpanadi, siltanishda ko'tariladi"""
    J = P.J
    E, ds, lift = gait["E"], gait["ds"], gait["lift"]
    dv = Vector((d[0], d[1], 0))
    side = abs(d[0]) > 0
    out = {}
    for s, off in (("L", 0.0), ("R", 0.5)):
        p = (frame_phase + off) % 1.0
        base = Vector((J[f"ankle.{s}"].x * 0.7, J[f"ankle.{s}"].y + (-0.06 if s == "L" else 0.05), 0.0))
        if p < ds:                                   # tayanch: oldindan orqaga
            u = p / ds
            pos = base + dv * (E - 2 * E * u)
            h = 0.0
            pitch = (1 - u) * 6 - u * 10 if not side else 0
        else:                                        # siltanish: orqadan oldinga, ko'tarilib
            u = (p - ds) / (1 - ds)
            su = 0.5 - 0.5 * math.cos(math.pi * u)
            pos = base + dv * (-E + 2 * E * su)
            h = lift * math.sin(math.pi * u) ** 1.2
            pitch = (-18 * math.sin(math.pi * u) if not side else 0)
            if side:                                 # yonga yurganda oyoqlar kesishmasin: biri oldidan, biri orqadan o'tadi
                pos += Vector((0, (-0.12 if s == "L" else 0.12) * math.sin(math.pi * u), 0))
        out[s] = (pos, h, pitch, p)
    return out


def apply_feet(P, F):
    for s, (pos, h, pitch, _) in F.items():
        name = f"ik_foot.{s}"
        rest = P.rest[name]
        M = Matrix.Translation(Vector((pos.x, pos.y, 0.085 + h))) @ Matrix.Rotation(math.radians(pitch), 4, "X") @ rest.to_3x3().to_4x4()
        P.set_world(name, M)


def ik_feet_static(P, offsets=None):
    offsets = offsets or {}
    for s in ("L", "R"):
        o = offsets.get(s, (0, 0, 0, 0))
        a = P.J[f"ankle.{s}"]
        rest = P.rest[f"ik_foot.{s}"]
        M = Matrix.Translation(Vector((a.x * 0.7 + o[0], a.y + o[1] + (-0.06 if s == "L" else 0.05), 0.085 + o[2]))) \
            @ Matrix.Rotation(math.radians(o[3]), 4, "X") @ rest.to_3x3().to_4x4()
        P.set_world(f"ik_foot.{s}", M)


def new_action(ob, name):
    act = bpy.data.actions.new(name)
    ob.animation_data_create()
    ob.animation_data.action = act
    return act


def make_actions(P, info):
    ob = P.ob
    acts = {}
    steps = {}

    def frames_for(T):
        return max(8, int(round(T * FPS)))

    # --- turish (nafas)
    act = new_action(ob, "idle")
    n = 60
    for f in range(n + 1):
        P.clear()
        ph = f / n * 2 * math.pi
        stance_pose(P, hip_drop=-0.02 + 0.004 * math.sin(ph), breathe=1.2 * math.sin(ph))
        ik_feet_static(P, {"L": (0.02, -0.08, 0, 0), "R": (-0.02, 0.1, 0, 0)})
        place_weapon(P, Matrix.Rotation(math.radians(0.6 * math.sin(ph)), 4, "X"))
        P.key(f + 1)
    acts["idle"] = (act, n)
    # --- o'tirib turish
    act = new_action(ob, "crouch_idle")
    for f in range(n + 1):
        P.clear()
        ph = f / n * 2 * math.pi
        stance_pose(P, hip_drop=-0.36 + 0.004 * math.sin(ph), lean=16, breathe=1.0 * math.sin(ph))
        ik_feet_static(P, {"L": (0.03, -0.16, 0, 0), "R": (-0.04, 0.2, 0, 0)})
        place_weapon(P, Matrix.Rotation(math.radians(0.5 * math.sin(ph)), 4, "X"))
        P.key(f + 1)
    acts["crouch_idle"] = (act, n)
    # --- yurish / yugurish / o'tirib yurish, 4 yo'nalish
    for gname, g in GAITS.items():
        S = 2 * g["E"] / g["ds"]
        T = S / g["speed"]
        nf = frames_for(T)
        info["gaits"][gname] = dict(speed=g["speed"], period=nf / FPS, stride=S)
        for dn, d in DIRS.items():
            name = f"{gname}_{dn}"
            act = new_action(ob, name)
            for f in range(nf + 1):
                P.clear()
                ph = f / nf
                F = feet(P, ph, g, d)
                # son: ikki tayanchda pastroq, bitta oyoqda balandroq; tayanch oyog'i tomonga ozgina og'adi
                bob = -g["bob"] * math.cos(4 * math.pi * ph)
                sway = 0.025 * math.sin(2 * math.pi * ph) * (1 if gname != "run" else 0.6)
                lean_dir = g["lean"] * (1 if dn == "f" else (-0.4 if dn == "b" else 0.3))
                stance_pose(P, hip_drop=g["hip"] + bob, lean=lean_dir + (0 if gname != "crouch" else 0))
                P.move("hips", (sway, 0, 0))
                P.rot("hips", (0, 0, 1), 6 * math.sin(2 * math.pi * ph) * (d[1] != 0))
                P.rot("spine", (0, 0, 1), -6 * math.sin(2 * math.pi * ph) * (d[1] != 0))
                apply_feet(P, F)
                place_weapon(P, Matrix.Rotation(math.radians(1.2 * math.sin(4 * math.pi * ph)), 4, "X"))
                P.key(f + 1)
            acts[name] = (act, nf)
        # qadam fazalari (oyoq yerga tekkan payt): chap 0.0, o'ng 0.5
        steps[gname] = [0.0, 0.5]
    info["steps"] = steps
    # --- sakrash: ko'tarilish, havoda, qo'nish
    def jump_pose(hd, tuck, lean, spread=0.0):
        stance_pose(P, hip_drop=hd, lean=lean)
        ik_feet_static(P, {"L": (0.02, -0.12 - spread, max(0.0, tuck), 12 * (tuck > 0)),
                           "R": (-0.02, 0.12 + spread, max(0.0, tuck * 0.8), 18 * (tuck > 0))})
    act = new_action(ob, "jump_start")
    for f, (hd, tk, ln) in enumerate([(-0.03, 0, 4), (-0.14, 0, 12), (-0.08, 0, 8), (0.02, 0.05, 2), (0.06, 0.18, 2), (0.1, 0.30, 4)]):
        P.clear(); jump_pose(hd, tk, ln); place_weapon(P, Matrix.Rotation(math.radians(-2 * (f > 3)), 4, "X")); P.key(f * 2 + 1)
    acts["jump_start"] = (act, 11)
    act = new_action(ob, "jump_air")
    for f in range(21):
        ph = f / 20 * 2 * math.pi
        P.clear(); jump_pose(0.1 + 0.01 * math.sin(ph), 0.30 + 0.02 * math.sin(ph), 5); place_weapon(P, Matrix.Rotation(math.radians(-2), 4, "X")); P.key(f + 1)
    acts["jump_air"] = (act, 20)
    act = new_action(ob, "jump_land")
    for f, (hd, tk, ln) in enumerate([(0.06, 0.12, 6), (-0.08, 0, 10), (-0.2, 0, 16), (-0.14, 0, 12), (-0.07, 0, 7), (-0.03, 0, 3)]):
        P.clear(); jump_pose(hd, tk, ln); place_weapon(P, Matrix.Rotation(math.radians(2 * (f in (2, 3))), 4, "X")); P.key(f * 2 + 1)
    acts["jump_land"] = (act, 11)
    # --- o'q uzish (tepish): qurol orqaga va tepaga, ko'krak biroz orqaga
    act = new_action(ob, "fire")
    for f, (back, up, ch) in enumerate([(0, 0, 0), (0.045, 5, -2.5), (0.02, 2.5, -1.2), (0.006, 0.8, -0.4), (0, 0, 0)]):
        P.clear(); stance_pose(P, hip_drop=-0.02, lean=3 + ch)
        ik_feet_static(P, {"L": (0.02, -0.08, 0, 0), "R": (-0.02, 0.1, 0, 0)})
        place_weapon(P, Matrix.Translation((0, -back, 0)) @ Matrix.Rotation(math.radians(up), 4, "X"))
        P.key([1, 2, 4, 6, 8][f])
    acts["fire"] = (act, 8)
    # --- qayta o'qlash: qurol qiyshayadi, chap qo'l magazinni chiqaradi, kamardan yangisini oladi, kiritadi, dastaga qaytadi
    act = new_action(ob, "reload")
    W = P.W
    gx, gz = W["grip"]
    mx0, mx1, mz0, mz1 = W["mag_box"]
    # weapon suyagi fazosi: X — personajning o'ngi, Y — og'iz tomoni, Z — tepa
    mag_hold = Vector((-0.03, -((mx0 + mx1) / 2 - gx), (mz0 + mz1) / 2 - gz - 0.01))
    ikL0 = P.rest["ik_hand.L"].copy()
    wrest = P.rest["weapon"]
    ikL_local0 = wrest.inverted() @ ikL0
    pouch = Vector((0.16, -0.12, P.J["hips"].z + 0.08))
    keys = [  # kadr, qurol qiyshiqligi (°), qurol ko'tarilishi (°), chap qo'l holati: 'fore'|'mag'|'pouch', magazin: 'in'|'hand'|'hidden'
        (1, 0, 0, "fore", "in"), (10, 22, 8, "fore", "in"), (18, 28, 10, "mag", "in"), (24, 28, 10, "mag", "hand"),
        (34, 24, 8, "pouch", "hand"), (44, 24, 8, "pouch", "hand"), (54, 28, 10, "mag", "hand"), (60, 28, 12, "mag", "in"),
        (64, 30, 14, "mag", "in"), (72, 18, 6, "fore", "in"), (80, 0, 0, "fore", "in")]
    for fr, roll, pitch, hand, magst in keys:
        P.clear(); stance_pose(P, hip_drop=-0.03, lean=6)
        ik_feet_static(P, {"L": (0.02, -0.08, 0, 0), "R": (-0.02, 0.1, 0, 0)})
        place_weapon(P, Matrix.Rotation(math.radians(pitch), 4, "X") @ Matrix.Rotation(math.radians(-roll), 4, "Y"))
        bpy.context.view_layer.update()
        wM = P.ob.pose.bones["weapon"].matrix
        if hand == "fore":
            L = wM @ ikL_local0
        elif hand == "mag":
            L = wM @ Matrix.Translation(mag_hold) @ ikL_local0.to_3x3().to_4x4() @ Matrix.Rotation(math.radians(70), 4, "X")
        else:
            L = Matrix.Translation(pouch) @ (wM @ ikL_local0).to_3x3().to_4x4() @ Matrix.Rotation(math.radians(80), 4, "X")
        P.set_world("ik_hand.L", L)
        magM = P.ob.pose.bones["mag"].matrix.copy()
        if magst == "hand":
            # magazin qo'l bilan birga (qo'l nishoniga nisbatan o'sha joyda)
            rel = (wM @ Matrix.Translation(mag_hold) @ ikL_local0.to_3x3().to_4x4() @ Matrix.Rotation(math.radians(70), 4, "X")).inverted() @ (wM @ P.mag_rest_local)
            P.set_world("mag", L @ rel)
        P.key(fr)
    acts["reload"] = (act, 80)
    info["reload_time"] = 80 / FPS
    # --- bomba qo'yish / zararsizlantirish: tiz cho'kib, qurol pastga
    act = new_action(ob, "plant")
    for f in range(41):
        ph = f / 40 * 2 * math.pi
        P.clear(); stance_pose(P, hip_drop=-0.42, lean=30 + 3 * math.sin(ph), twist=10)
        ik_feet_static(P, {"L": (0.04, -0.28, 0, 0), "R": (-0.03, 0.32, 0.0, 60)})
        place_weapon(P, Matrix.Translation((0.02, -0.1, -0.06)) @ Matrix.Rotation(math.radians(-45), 4, "X"))
        P.key(f + 1)
    acts["plant"] = (act, 40)
    # --- o'lim: tizzalar bukiladi, orqaga yiqiladi
    act = new_action(ob, "death")
    seq = [(0, -0.02, 3, 0, 0), (6, -0.1, -6, 0.06, 0), (12, -0.35, -18, 0.12, 0), (18, -0.6, -40, 0.22, 0.2),
           (24, -0.72, -70, 0.30, 0.45), (30, -0.76, -82, 0.34, 0.55), (36, -0.76, -84, 0.34, 0.55)]
    for fr, hd, ln, back, legs in seq:
        P.clear(); stance_pose(P, hip_drop=hd, lean=ln * 0.35)
        P.move("hips", (0, back, 0))
        P.rot("hips", (1, 0, 0), ln * 0.65)
        ik_feet_static(P, {"L": (0.05, -0.1 - legs, 0, -legs * 60), "R": (-0.05, 0.05 - legs * 0.8, 0, -legs * 50)})
        place_weapon(P, Matrix.Rotation(math.radians(ln * 0.95), 4, "X"), rigid=True)
        P.key(fr + 1)
    acts["death"] = (act, 37)
    return acts


def bake_all(ob, acts):
    """IK va cheklovlarni kalit kadrlarga "pishirish" (Godot IK siz ham aynan shunday ko'rsatadi)"""
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    baked = {}
    for name, (act, n) in acts.items():
        ob.animation_data.action = act
        for p in ob.pose.bones:
            p.bone.select = True
        bpy.ops.nla.bake(frame_start=1, frame_end=n + 1 if name not in ("fire", "jump_start", "jump_land", "reload", "death") else n,
                         only_selected=False, visual_keying=True, clear_constraints=False, use_current_action=False,
                         bake_types={"POSE"})
        new = ob.animation_data.action
        new.name = name + "_baked"
        baked[name] = new
    for p in ob.pose.bones:
        for c in list(p.constraints):
            p.constraints.remove(c)
    bpy.ops.object.mode_set(mode="OBJECT")
    for name, (act, n) in acts.items():
        bpy.data.actions.remove(act)
    for name, a in baked.items():
        a.name = name
        a.use_fake_user = True
        # halqali animatsiyalarda oxirgi kadr birinchisining takrori — olib tashlaymiz (Godot silliq aylansin)
    ob.animation_data.action = None
    return baked


def push_to_nla(ob, baked):
    ob.animation_data_create()
    for name, a in baked.items():
        tr = ob.animation_data.nla_tracks.new()
        tr.name = name
        st = tr.strips.new(name, int(a.frame_range[0]), a)
        tr.mute = True


def export(path, objs, ob):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_animations=True,
                              export_animation_mode="ACTIONS", export_def_bones=True, export_force_sampling=True,
                              export_frame_step=1, export_optimize_animation_size=True, export_image_format="JPEG",
                              export_jpeg_quality=88, export_yup=True, export_skins=True, export_all_influences=False,
                              export_reset_pose_bones=True)


def preview(ob, name, baked):
    """tekshiruv uchun: har animatsiyadan kadrlar (old va yon), docs/characters/ ga"""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 6
    sc.cycles.device = "CPU"
    sc.render.resolution_x, sc.render.resolution_y = 360, 420
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.82, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 3.5; sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 2.1
    out = os.path.join(HERE, "..", "docs", "characters", "frames")
    os.makedirs(out, exist_ok=True)
    views = {"front": ((1.8, -4.2, 1.05), (86, 0, 23), 2.1), "side": ((4.5, 0, 1.05), (86, 0, 90), 2.1),
             "close": ((-3.0, -1.5, 1.35), (88, 0, -63), 0.9)}
    for an, fr in PREVIEW_FRAMES:
        if an not in baked:
            continue
        ob.animation_data.action = baked[an]
        sc.frame_set(fr)
        for vn, (loc, rot, osc) in views.items():
            if vn == "close" and an not in ("idle", "crouch_idle", "fire", "run_f"):
                continue
            cam.location = loc; cam.rotation_euler = [math.radians(a) for a in rot]; cam.data.ortho_scale = osc
            sc.render.filepath = os.path.join(out, f"{name}_{an}_{fr}_{vn}.png")
            bpy.ops.render.render(write_still=True)
    ob.animation_data.action = None


PREVIEW_FRAMES = [("idle", 1), ("run_f", 1), ("run_f", 5), ("walk_f", 6), ("crouch_idle", 1), ("crouch_f", 8), ("run_l", 4),
                  ("jump_air", 1), ("fire", 2), ("reload", 24), ("reload", 44), ("plant", 1), ("death", 37)]


# ------------------------------------------------------------------ asosiy
def build(name, wname, info_all):
    reset()
    body, v = load_character(name)
    J = joints_from_mesh(v)
    ob = build_armature(J, wname)
    W = WEAPONS[wname]
    # qurol holati: ko'krakka nisbatan (tinch holatdagi ko'krak bilan hisoblanadi)
    base = weapon_base(J, W)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    eb = ob.data.edit_bones
    wb = eb["weapon"]
    off = base.translation
    wb.head = off
    wb.tail = off + Vector((0, -0.2, 0))
    wb.align_roll(Vector((0, 0, 1)))
    mx0, mx1, mz0, mz1 = W["mag_box"]
    gx, gz = W["grip"]
    mc = off + Vector((0, (mx0 + mx1) / 2 - gx, mz1 - gz))
    eb["mag"].head = mc
    eb["mag"].tail = mc + Vector((0, 0, -0.12))
    eb["mag"].align_roll(Vector((0, -1, 0)))
    bpy.ops.object.mode_set(mode="OBJECT")
    place_ik_bones(ob, W)
    names, idx, top = skin(body, ob, J)
    # qurol modeli suyakka biriktiriladi
    gun, mag = load_weapon(wname)
    # qurol uchlari "weapon" fazosida (dasta — 0 nuqta); obyekt dunyoda shu suyak boshida turadi.
    # Blender'da BONE ota suyak dumiga bog'lanadi, shuning uchun asos matritsani dumga nisbatan hisoblaymiz.
    bpy.context.view_layer.update()
    for o, bn in ((gun, "weapon"), (mag, "mag")):
        if o is None:
            continue
        o.parent = ob
        o.parent_type = "BONE"
        o.parent_bone = bn
        o.matrix_parent_inverse = Matrix.Identity(4)
        b = ob.data.bones[bn]
        tail = b.matrix_local @ Matrix.Translation((0, b.length, 0))
        o.matrix_basis = tail.inverted() @ Matrix.Translation(ob.data.bones["weapon"].head_local)
    P = Poser(ob, J, wname)
    P.clear()
    bpy.context.view_layer.update()
    # tinch holatda ko'krak -> qurol ofseti (animatsiyalarda shu ofset saqlanadi, qurol ko'krak bilan yuradi)
    chest0 = ob.pose.bones["chest"].matrix.copy()
    stance_pose(P)
    bpy.context.view_layer.update()
    chest1 = ob.pose.bones["chest"].matrix.copy()
    # stance holatida qurol aniq oldinga qarasin, qo'ndoq buralgan o'ng yelka chuqurchasida: offset = chest1^-1 * W
    shR = ob.pose.bones["upper_arm.R"].head
    bx, bz = W["butt"]
    pocket = shR + Vector((0.065, -0.045, -0.07))
    grip = pocket - Vector((0, (bx - gx), (bz - gz)))
    Wm = Matrix.Translation(grip) @ ob.data.bones["weapon"].matrix_local.to_3x3().to_4x4()
    P.weapon_offset = chest1.inverted() @ Wm
    P.mag_rest_local = ob.data.bones["weapon"].matrix_local.inverted() @ ob.data.bones["mag"].matrix_local
    P.clear()
    setup_constraints(ob)
    stance_pose(P)
    place_weapon(P)
    ik_feet_static(P)
    tune_poles(ob)
    bpy.context.view_layer.update()
    pbs = ob.pose.bones
    for s_ in ("L", "R"):
        print(f"IK {s_}: bilak->nishon {(pbs[f'forearm.{s_}'].tail - pbs[f'ik_hand.{s_}'].head).length:.3f} m, "
              f"oyoq->nishon {(pbs[f'shin.{s_}'].tail - pbs[f'ik_foot.{s_}'].head).length:.3f} m, "
              f"yelka->nishon {(pbs[f'upper_arm.{s_}'].head - pbs[f'ik_hand.{s_}'].head).length:.3f}, qo'l uzunligi "
              f"{pbs[f'upper_arm.{s_}'].bone.length + pbs[f'forearm.{s_}'].bone.length:.3f}")
    P.clear()
    info = {"gaits": {}}
    acts = make_actions(P, info)
    baked = bake_all(ob, acts)
    if os.environ.get("PREVIEW"):
        preview(ob, name, baked)
    shrink_textures(body, 1024)
    for o in (gun, mag):
        if o:
            shrink_textures(o, 1024)
    os.makedirs(OUT, exist_ok=True)
    export(os.path.join(OUT, f"{name}.glb"), [body, gun] + ([mag] if mag else []), ob)
    # birinchi shaxs: faqat bilak va kaft (tirsakdan pastki qism) + qurol
    arm_bones = {"forearm.L", "forearm.R", "hand.L", "hand.R", "fingers.L", "fingers.R"}
    keep = np.array([names[idx[i, 0]] in arm_bones or (names[idx[i, 0]].startswith("upper_arm") and top[i, 0] < 0.75)
                     for i in range(len(idx))])
    arms = body.copy()
    arms.data = body.data.copy()
    arms.name = name + "_arms"
    bpy.context.scene.collection.objects.link(arms)
    bm = bmesh.new()
    bm.from_mesh(arms.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[vv for vv in bm.verts if not keep[vv.index]], context="VERTS")
    bm.to_mesh(arms.data)
    bm.free()
    body.hide_set(True)
    export(os.path.join(OUT, f"{name.split('_')[0]}_arms.glb"), [arms, gun] + ([mag] if mag else []), ob)
    # ko'z nuqtasi (birinchi shaxs kamerasi uchun), armatura fazosida
    eye = J["head"] + Vector((0, -0.09, 0.08))
    eye_local = ob.data.bones["head"].matrix_local.inverted() @ eye
    info.update(eye=list(eye), eye_head_local=list(eye_local), weapon=wname, grip=list(ob.data.bones["weapon"].head_local),
                sight_above_grip=W["sight"] - W["grip"][1], height=H)
    info_all[name] = info


if __name__ == "__main__":
    only = sys.argv[1:] or list(CHARS)
    info_all = {}
    for n in only:
        build(n, CHARS[n], info_all)
    p = os.path.join(OUT, "rig_info.json")
    old = json.load(open(p)) if os.path.exists(p) else {}
    old.update(info_all)
    json.dump(old, open(p, "w"), indent=1)
    print("tayyor:", ", ".join(only))
