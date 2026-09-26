# ---------------- v2 prop placement (cover planned for gameplay)
# --- A site: x -23..-7, z -1..13  (open, long sightlines from Long)
decal(-15.0, 8.0, "A")
stack(-17.6, 4.6, [(0, 0, 0, 1.2, False), (1.2, 0, 0, 1.2, False), (0.6, 0, 1.2, 1.2, False)])   # default
stack(-11.6, 9.6, [(0, 0, 0, 1.2, True), (0, 1.25, 0, 1.2, False)], 0.15)                        # plant cover
platform(-23.0, 7.5, -20.5, 12.8, 1.3, "+x")                                                     # A back platform
stack(-19.6, 1.3, [(0, 0, 0, 1.1, False)])                                                        # long exit cover
barrel(-8.0, 0.4); sandbags(-11.8, 2.8, -9.2, 2.8)                                                # short exit cover
stack(-9.4, 11.0, [(0, 0, 0, 1.0, False), (1.05, 0, 0, 1.0, False)], -0.1)                        # CT side
palm(-22.4, 0.3, 8.5, (0.5, -0.2)); palm(-7.9, 12.3, 7.0, (-0.3, -0.4))
# --- Long + long doors
stack(-18.2, -9.0, [(0, 0, 0, 1.1, True)]); urn(-22.3, -14.0); palm(-22.3, -6.5, 8.0, (0.4, 0.1))
stack(-20.3, -22.2, [(0, 0, 0, 1.1, False)]); barrel(-8.3, -22.3)
# --- Top mid: x -7..7, z -15..-7
stack(-5.2, -9.2, [(0, 0, 0, 1.2, False), (0, 0, 1.2, 1.0, False)])
stack(5.4, -13.2, [(0, 0, 0, 1.2, True)]); barrel(6.2, -8.2); urn(-6.3, -14.3)
palm(-6.1, -7.9, 7.5, (0.2, 0.3))
# --- Mid corridor + CT mid
crate(-4.2, -4.0, 0.9, yaw=0.2); urn(-4.4, 2.3)
stack(4.2, 9.9, [(0, 0, 0, 1.1, False), (0, 0, 1.1, 0.9, True)])                                 # CT mid pocket
barrel(-2.3, 12.3); urn(2.3, 5.8); palm(-2.2, 6.0, 7.5, (0.3, 0.2))
# --- B site: x 7..23, z -1..13 (tight, lots of close cover)
decal(16.0, 7.0, "B")
stack(12.2, 4.6, [(0, 0, 0, 1.2, False), (0, 1.25, 0, 1.2, False), (0, 0.6, 1.2, 1.2, False)], -0.1)
stack(17.8, 9.6, [(0, 0, 0, 1.3, True)])
stack(16.2, 1.4, [(0, 0, 0, 1.1, False), (1.1, 0, 0, 1.1, False)], 0.1)                          # tunnel exit cover
platform(20.8, 3.5, 23.0, 9.5, 1.3, "-x")                                                          # B back platform
barrel(8.3, 3.8); urn(8.3, 8.4, 1.1)                                                               # B doors flanks
sandbags(19.5, 11.9, 22.5, 11.9); barrel(22.3, 0.3, "green")
palm(8.0, 0.0, 8.5, (0.4, 0.3)); palm(22.2, 12.2, 7.2, (-0.4, -0.3))
# --- Tunnels
barrel(8.4, -22.3); crate(15.6, -22.2, 0.9, yaw=0.3); crate(18.2, -16.0, 0.9, yaw=0.3)
urn(11.7, -5.5); barrel(14.3, -3.2)
# --- Spawns and CT connectors
stack(-5.8, -21.9, [(0, 0, 0, 1.1, False), (1.1, 0, 0, 1.1, False)]); stack(5.9, -21.8, [(0, 0, 0, 1.2, True)])
barrel(-6.3, -17.8); barrel(6.3, -17.8); urn(0.0, -22.4, 1.2)
stack(-7.6, 19.9, [(0, 0, 0, 1.2, True)]); stack(7.4, 20.0, [(0, 0, 0, 1.1, False), (0, -1.1, 0, 1.1, False)])
barrel(-3.9, 20.3); urn(3.9, 20.4)
urn(-16.3, 18.3); crate(-10.0, 18.4, 0.9, yaw=0.2); barrel(16.3, 18.3); crate(10.0, 18.4, 0.9, yaw=-0.2)
