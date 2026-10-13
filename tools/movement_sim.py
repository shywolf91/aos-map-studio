"""Re-implements the vertical part of pyspades 1.4.2 world_c.cpp move_player()/boxclipmove()
to derive jump apex and fall-damage heights. Derived numbers, NOT playtested."""
FALL_SLOW_DOWN, FALL_DAMAGE_VELOCITY, FALL_DAMAGE_SCALAR = 0.24, 0.58, 4096

def jump_apex(dt):
    vz, z, apex = -0.36, 0.0, 0.0
    for _ in range(100000):
        vz += dt; vz /= (dt + 1)
        z += vz * dt * 32
        apex = min(apex, z)
        if z > 0: break
    return -apex  # voxels risen (z grows downward)

def fall(height, dt):
    vz, z = 0.0, 0.0
    while z < height:
        vz += dt; vz /= (dt + 1); z += vz * dt * 32
    f2 = vz
    if f2 > FALL_DAMAGE_VELOCITY:
        return int((f2 - FALL_DAMAGE_VELOCITY) ** 2 * FALL_DAMAGE_SCALAR)
    return 0

for dt in (1/60, 1/120):
    print(f"dt={dt:.4f}: jump apex = {jump_apex(dt):.3f} voxels")
    first_dmg = next(h for h in range(1, 64) if fall(h, dt) > 0)
    lethal = next((h for h in range(1, 64) if fall(h, dt) >= 100), None)
    print(f"   first damaging drop = {first_dmg} voxels, lethal (>=100) drop = {lethal} voxels")
    print("   damage by drop:", {h: fall(h, dt) for h in range(first_dmg, first_dmg + 12)})
