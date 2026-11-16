"""VXL core: C encoder (pyspades algorithm) + independent pure-Python reader."""
import ctypes, os, numpy as np
_lib = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libvxlenc.so'))
_lib.encode.restype = ctypes.c_size_t

def encode(S, C):
    S = np.ascontiguousarray(S, dtype=np.uint8); C = np.ascontiguousarray(C, dtype=np.uint8)
    assert S.shape == (512, 512, 64) and C.shape == (512, 512, 64, 3)
    out = np.zeros(48 * 1024 * 1024, np.uint8)
    n = _lib.encode(S.ctypes.data_as(ctypes.c_void_p), C.ctypes.data_as(ctypes.c_void_p), out.ctypes.data_as(ctypes.c_void_p))
    return out[:n].tobytes()

def decode(data):
    """Independent reader (written from the Voxlap spec, not from the encoder). Returns S[x,y,z], C[x,y,z,3] (surface colours)."""
    S = np.ones((512, 512, 64), bool); C = np.zeros((512, 512, 64, 3), np.uint8)
    b = memoryview(data); p = 0
    for y in range(512):
        for x in range(512):
            z = 0
            while True:
                N, s, e, a = b[p], b[p+1], b[p+2], b[p+3]
                S[x, y, z:s] = False  # air from z to s-1 (a == z in canonical files)
                for i in range(s, e + 1):
                    q = p + 4 + (i - s) * 4
                    C[x, y, i] = (b[q+2], b[q+1], b[q])
                if N == 0:
                    p += 4 * (e - s + 2)
                    break
                ntop = e - s + 1
                nbot = (N - 1) - ntop
                p += N * 4
                na = b[p+3]
                for k in range(nbot):
                    q = p - nbot * 4 + k * 4
                    C[x, y, na - nbot + k] = (b[q+2], b[q+1], b[q])
                z = na
    assert p == len(data), (p, len(data))
    return S, C
