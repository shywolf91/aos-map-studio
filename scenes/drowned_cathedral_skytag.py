"""Test variant of Drowned Cathedral: map info on a sky plate (z 4) over the bottom-right corner, ground NOT cleared.
Same seed and geometry otherwise. Run: python scenes/drowned_cathedral_skytag.py out/drowned_cathedral_skytag"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scenes.drowned_cathedral as D                                          # noqa: E402

D.SPEC['signature'].update({'mode': 'sky', 'clear': False, 'sky_z': 4})

if __name__ == '__main__':
    from aosmap.vxl import write_vxl
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/drowned_cathedral_skytag'
    os.makedirs(out, exist_ok=True)
    s, L = D.build()
    data = write_vxl(s.to_voxelmap())
    name = 'drowned_cathedral_skytag'
    open(os.path.join(out, name + '.vxl'), 'wb').write(data)
    open(os.path.join(out, name + '.txt'), 'w').write(D.metadata_txt())
    json.dump(D.SPEC, open(os.path.join(out, 'spec.json'), 'w'), indent=1, default=list)
    print('written', len(data), 'bytes', 'pruned', s.markers['pruned'])
