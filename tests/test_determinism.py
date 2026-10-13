"""Shaders must give identical colours in every process (no reliance on Python's randomised hash())."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNIPPET = r'''
import sys, hashlib
sys.path.insert(0, %r)
from aosmap.scene import Scene, Material
from aosmap.art import SurfaceShader, StrataShader
s = Scene('det', seed=5)
a = s.material(Material('rock', (1, 1, 1), shader=SurfaceShader(top=['#c0a080', '#806040'], side=['#604030'])))
b = s.material(Material('band', (1, 1, 1), shader=StrataShader(['#d0a070', '#a06040'])))
s.box(10, 40, 10, 40, 50, 62, a)
s.box(20, 30, 20, 30, 40, 49, b)
vm = s.to_voxelmap()
print(hashlib.sha256(vm.color.tobytes()).hexdigest())
''' % ROOT


def _run(seed):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    return subprocess.run([sys.executable, '-c', SNIPPET], env=env, capture_output=True, text=True,
                          check=True).stdout.strip()


def test_colours_identical_across_hash_seeds():
    assert _run(1) == _run(2) == _run(12345)
