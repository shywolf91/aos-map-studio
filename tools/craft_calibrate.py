"""Calibration of aosmap.kit.craft_checks building gates on exemplar boxes (paths are local; H:/maps is the owner's collection)."""
import sys, json; sys.path.insert(0,'.')
from aosmap.kit import craft_checks as C
SP='D:/Ace of Spades/Aos_Map/_updates/silverpine_hunt_v2_2/maps/silverpine_hunt_v2_2/silverpine_hunt.vxl'
jobs=[(SP,[('SP lodge',(90,131,193,232),'main'),('SP watch',(176,200,184,202),'ruin')]),
 ('H:/maps/wicker_kings_harvest.vxl',[('WK barn',(82,117,186,217),'main'),('WK farm',(80,102,285,305),'main'),('WK shed',(82,96,307,318),'small')]),
 ('H:/maps/normandie.vxl',[('NO block',(195,232,217,275),'main'),('NO block2',(169,214,329,368),'main'),('NO church',(264,282,264,296),'main'),('NO house',(201,217,240,247),'small')]),
 ('maps/floebreaker_v1/floebreaker_day.vxl',[('FB hut',(144,156,184,194),'small'),('FB tower',(182,194,202,214),'tower'),('FB basehut',(78,90,225,235),'small'),('FB super',(243,268,124,160),'vessel'),('FB fishhut',(212,222,214,223),'small')])]
keys=['area','height','roof_pitched','roof_rise_share','roof_eave','colours','wall_colours','wall_value_range','base_course','roof_wall_contrast','openings_per_10_perim','indoor_share','massing','yard_props']
print('%-11s'%'bldg'+''.join('%9s'%k[:9] for k in keys))
for path,boxes in jobs:
    R=C.run(path,'babel',[b for _,b,_r in boxes],[r for _,_b,r in boxes])
    for (n,_,r),b in zip(boxes,R['buildings']):
        fails=[k for k,v in b['gates'].items() if not v]
        print('%-11s %-6s %s  fails: %s'%(n,r,'PASS' if b['pass'] else 'FAIL',', '.join(f'{k}={b[k]}' for k in fails)))
