"""Spawn exposure: an open spawn is fully visible from the platform; a tall wall between them hides it."""
import numpy as np

from aosmap.sightline import spawn_exposure


def _flat(z=40):
    s = np.zeros((512, 512, 64), bool)
    s[:, :, z:] = True
    return s


def test_open_spawn_is_exposed():
    r = spawn_exposure(_flat(), (118, 256), viewer_step=16, spawn_step=8)
    assert r['exposed_pct'] == 100.0


def test_wall_hides_spawn():
    s = _flat()
    s[150:153, 200:312, 0:40] = True          # wall from the sky down to the ground between spawn and platform
    r = spawn_exposure(s, (118, 256), viewer_step=16, spawn_step=8)
    assert r['exposed_pct'] == 0.0
