"""BVH (CMU mocap) o'qish va forward kinematics — numpy, Blender'siz.

CMU BVH: Y — tepa, odam tinch holatda +Z ga qaraydi (T-poza). Ildiz: 6 kanal, qolganlar: 3 ta aylanish.
"""
import numpy as np
import re


class BVH:
    def __init__(self, path):
        txt = open(path).read().split("MOTION")
        self.names, self.parents, self.offsets, self.channels = [], [], [], []
        self.end_offsets = {}
        stack = []
        tok = re.findall(r"[^\s]+", txt[0])
        i = 0
        cur = -1
        while i < len(tok):
            t = tok[i]
            if t in ("ROOT", "JOINT"):
                self.names.append(tok[i + 1])
                self.parents.append(stack[-1] if stack else -1)
                cur = len(self.names) - 1
                i += 2
            elif t == "End":
                # End Site: offset'ni ota bo'g'imga yozamiz
                j = tok.index("OFFSET", i)
                self.end_offsets[stack[-1]] = np.array([float(x) for x in tok[j + 1:j + 4]])
                k = tok.index("}", j)
                i = k + 1
                continue
            elif t == "{":
                stack.append(cur)
                i += 1
            elif t == "}":
                stack.pop()
                i += 1
            elif t == "OFFSET":
                self.offsets.append(np.array([float(x) for x in tok[i + 1:i + 4]]))
                i += 4
            elif t == "CHANNELS":
                n = int(tok[i + 1])
                self.channels.append(tok[i + 2:i + 2 + n])
                i += 2 + n
            else:
                i += 1
        m = txt[1].split("\n")
        m = [l for l in m if l.strip()]
        self.nframes = int(m[0].split()[1])
        self.dt = float(m[1].split()[2])
        self.data = np.array([[float(x) for x in l.split()] for l in m[2:2 + self.nframes]])
        self.offsets = np.array(self.offsets)
        self.idx = {n: k for k, n in enumerate(self.names)}

    @staticmethod
    def _rot(axis, deg):
        a = np.radians(deg)
        c, s = np.cos(a), np.sin(a)
        n = len(a)
        R = np.zeros((n, 3, 3))
        if axis == "X":
            R[:, 0, 0] = 1; R[:, 1, 1] = c; R[:, 1, 2] = -s; R[:, 2, 1] = s; R[:, 2, 2] = c
        elif axis == "Y":
            R[:, 1, 1] = 1; R[:, 0, 0] = c; R[:, 0, 2] = s; R[:, 2, 0] = -s; R[:, 2, 2] = c
        else:
            R[:, 2, 2] = 1; R[:, 0, 0] = c; R[:, 0, 1] = -s; R[:, 1, 0] = s; R[:, 1, 1] = c
        return R

    def fk(self):
        """global aylanishlar (F, J, 3, 3) va joylar (F, J, 3)"""
        F, J = self.nframes, len(self.names)
        Rg = np.zeros((F, J, 3, 3))
        Pg = np.zeros((F, J, 3))
        col = 0
        for j in range(J):
            ch = self.channels[j]
            pos = self.offsets[j][None].repeat(F, 0)
            R = np.eye(3)[None].repeat(F, 0)
            for c in ch:
                v = self.data[:, col]
                col += 1
                if c.endswith("position"):
                    pos = pos.copy()
                    pos[:, "XYZ".index(c[0])] = v
                else:
                    R = R @ self._rot(c[0], v)
            p = self.parents[j]
            if p < 0:
                Rg[:, j] = R
                Pg[:, j] = pos
            else:
                Rg[:, j] = Rg[:, p] @ R
                Pg[:, j] = Pg[:, p] + np.einsum("fij,fj->fi", Rg[:, p], pos)
        self.Rg, self.Pg = Rg, Pg
        return Rg, Pg

    def rest_positions(self):
        J = len(self.names)
        P = np.zeros((J, 3))
        for j in range(J):
            p = self.parents[j]
            P[j] = self.offsets[j] + (P[p] if p >= 0 else 0)
        return P
