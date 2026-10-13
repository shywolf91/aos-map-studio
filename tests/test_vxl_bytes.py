"""Byte-level tests of the VXL writer/reader against hand-derived spec examples and pyspades 1.4.2.

Every test map uses identical columns everywhere, so horizontal neighbours never expose a voxel
(map edges count as solid) and the expected per-column bytes can be derived by hand.
"""
import io
import numpy as np
import pytest

from aosmap.vxl import VoxelMap, rgb, read_vxl, write_vxl, MissingColorError

C30, C31, C35, C40 = rgb(200, 30, 30), rgb(30, 200, 30), rgb(30, 30, 200), rgb(90, 80, 70)


def le(c):
    return c.to_bytes(4, 'little')


def uniform(build):
    m = VoxelMap()
    build(m)
    return m


def ground40(m):
    m.solid[:, :, 40:] = True
    m.set(slice(None), slice(None), 40, C40)


def test_column_A_flat_ground():
    m = uniform(ground40)
    data = write_vxl(m)
    col = bytes([0, 40, 40, 0]) + le(C40)
    assert data == col * (512 * 512)


def test_column_B_two_thick_overhang():
    def b(m):
        ground40(m)
        m.set(slice(None), slice(None), 30, C30)
        m.set(slice(None), slice(None), 31, C31)
    data = write_vxl(uniform(b))
    col = bytes([3, 30, 31, 0]) + le(C30) + le(C31) + bytes([0, 40, 40, 32]) + le(C40)
    assert data[:20] == col and len(data) == 20 * 512 * 512


def test_column_C_thick_slab_hidden_interior():
    def c(m):
        ground40(m)
        m.solid[:, :, 30:36] = True
        m.set(slice(None), slice(None), 30, C30)
        m.set(slice(None), slice(None), 35, C35)   # interior 31-34 left uncoloured (hidden)
    data = write_vxl(uniform(c))
    col = bytes([3, 30, 30, 0]) + le(C30) + le(C35) + bytes([0, 40, 40, 36]) + le(C40)
    assert data[:20] == col


def test_missing_surface_colour_is_an_error():
    m = VoxelMap()
    m.solid[:, :, 40:] = True                       # no colours at all
    with pytest.raises(MissingColorError):
        write_vxl(m)


def test_cave_column_emits_zero_length_top_run_like_pyspades():
    """A buried cave exposes side voxels inside a solid run -> pyspades emits a span with E = S-1."""
    def cave(m):
        ground40(m)
        m.solid[:, :, 41:] = True
        m.color[:, :, 41:] = rgb(10, 10, 10)
        m.colored[:, :, 41:] = True
        m.set(200, 200, slice(55, 58), None)        # 1x1x3 cave next to column (201,200)
    m = uniform(cave)
    data = write_vxl(m)
    back, rep = read_vxl(data)
    assert rep.ok and rep.empty_top_runs > 0
    assert np.array_equal(back.solid, m.solid)
    assert back.colored[201, 200, 55:58].all()          # exposed cave wall kept its colours
    ours, theirs, _ = roundtrip_with_pyspades(m)
    assert ours == theirs                               # pyspades emits the same E = S-1 spans


def roundtrip_with_pyspades(m):
    from pyspades.vxl import VXLData
    ours = write_vxl(m)
    pys = VXLData(io.BytesIO(ours))
    theirs = pys.generate()
    return ours, theirs, pys


@pytest.mark.parametrize('builder', [ground40])
def test_pyspades_regenerates_identical_bytes(builder):
    ours, theirs, pys = roundtrip_with_pyspades(uniform(builder))
    assert ours == theirs
    assert pys.get_solid(10, 10, 40) and not pys.get_solid(10, 10, 39)
    assert pys.get_color(10, 10, 40) == (90, 80, 70)


def test_reader_matches_writer_inverse():
    def b(m):
        ground40(m)
        m.set(slice(100, 110), slice(100, 110), slice(20, 25), rgb(1, 2, 3))
        m.solid[100:110, 100:110, 21:24] = True
    m = uniform(b)
    data = write_vxl(m, missing='default')
    back, rep = read_vxl(data)
    assert rep.ok
    assert write_vxl(back, missing='default') == data


def test_paint_bottom_plane_roundtrips_through_pyspades():
    from aosmap.scene import Scene, Material
    s = Scene('t', seed=1)
    rock = s.material(Material('rock', (100, 100, 100)))
    s.box(250, 260, 250, 260, 50, 62, rock)
    xs, ys = np.indices((512, 512))
    img = np.stack([xs // 2, ys // 2, (xs + ys) // 4], -1).astype(np.uint8)
    s.paint_bottom(img)
    vm = s.to_voxelmap()
    ours, theirs, pys = roundtrip_with_pyspades(vm)
    assert ours == theirs
    assert pys.get_color(10, 20, 63) == (5, 10, 7)          # painted, read back by pyspades
    assert pys.get_color(255, 255, 50) == (100, 100, 100)   # structure unaffected
