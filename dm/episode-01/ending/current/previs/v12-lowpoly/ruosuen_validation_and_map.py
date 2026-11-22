#!/usr/bin/env python3
import sys,json,math,argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from trimesh.triangles import closest_point
from ruosuen_story_previs import *

arg=argparse.ArgumentParser(description='Validate low-poly proxy and create top-down scene map')
arg.add_argument('--out',default='./previs-output')
out=Path(arg.parse_args().out);out.mkdir(parents=True,exist_ok=True)
# Comparative 3D-proxy checks. NOT clearance certification of WH-01 or thick ceiling geometry.
def world_mesh(t):
 cp,f,sd,up=pose(t)
 return np.array([[cp+f*q[0]+sd*q[1]+up*q[2] for q in [a,b,c]] for a,b,c,kind in MESH])

def fissure_margin(x,y):
 if not FISSURE[0][0]<=y<=FISSURE[-1][0]:return None
 for a,b in zip(FISSURE,FISSURE[1:]):
  if a[0]<=y<=b[0]:
   v=(y-a[0])/(b[0]-a[0]);x1=a[1]+v*(b[1]-a[1]);x2=a[2]+v*(b[2]-a[2]);return min(x-x1,x2-x)
 return None

cases=[]
for t in [14.5,15,15.5,16,16.5,17,17.8,18,20.8,21.4,23.2,25.5,35.7,58,60,62,63.8,64]:
 tris=world_mesh(t);verts=tris.reshape((-1,3));cam_eye=N([-58,-84,4.1]);closest=closest_point(tris,np.repeat(cam_eye[None,:],len(tris),axis=0));min_eye=float(np.linalg.norm(closest-cam_eye,axis=1).min());
 mc=[fissure_margin(p[0],p[1]) for p in verts];mc=[a for a in mc if a is not None];
 cases.append({'t':t,'min_vertex_z_m':round(float(verts[:,2].min()),2),'min_mesh_eye_distance_m':round(min_eye,2),
               'min_fissure_margin_xy_m':None if not mc else round(float(min(mc)),2),
               'all_proxy_vertices_above_thin_roof_z190':bool(np.all(verts[:,2]>190)),
               'all_proxy_vertices_inside_2d_aperture':bool(mc and len(mc)==len(verts) and min(mc)>0)})
checks={'scope':'Low-poly PROXY ONLY; not WH-01 3D full mesh or 3D roof collision approval',
 'camera_B_initial':{'xyz_m':[-58,-84,4.1],'lens_mm':16,'yaw_deg':-60,'pitch_deg':50},
 'N06':{'lowest_sample_mesh_to_eye_m':min((x['min_mesh_eye_distance_m'] for x in cases if 14<=x['t']<=18)),
        'compared_v04_spherical_head_proxy':'v0.4 reports 1.4m possible eye proximity and 2.99m above representative ground, geometry differs; DO NOT infer human-safe clearance',
        'result':'INCONCLUSIVE: WH01 anatomical mesh, PC body and fin sweep not inspected'},
 'N08':{'head_contact_reference_s':20.93,'nose_midpoint_reference_s':21.17,'model_self_emission_starts_s':21.17,'status':'PROVISIONAL: 3D thick roof shadow path not tested'},
 'N10':{'S1_a_bloom_reference_s':25.5,'S1_tip_bloom_reference_s':35.7,'candidate_shot_end_s':36.5},
 'N13_N14':{'wide_mm':24,'tele_mm':70,'tele_tilt_deg':1.5,'status':'PROVISIONAL'},
 'N16':{'thin_roof_z_m':190,'thick_roof_geometry':'NOT INCLUDED', 'rim_intersection_and_tail_clearance':'NOT VERIFIED; vertical apex and 2D opening tests are insufficient'},
 'N01_N17':{'camera_initial_xyz_identical':True,'yaw_pitch_lens_identical':True,'background':'same scene function; N17 retains only one final petal'},
 'samples':cases}
(out/'qa-proxy.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False))

W,H=1500,1000
img=Image.new('RGB',(W,H),(24,49,66));d=ImageDraw.Draw(img)
# World overview covers S1 and rear lake; +Y at top.
minx,maxx=-165,165;miny,maxy=-133,260
p=lambda x,y:(int((x-minx)/(maxx-minx)*W),int((maxy-y)/(maxy-miny)*H))
# Coast, land and lake
coast=[p(x,y) for x,y in SHORE];d.polygon(coast+[p(165,-133),p(-165,-133)],fill=(78,80,68))
d.line(coast,fill=(128,171,182),width=5)
# Fissure elongated unique shape
left=[p(xl,y) for y,xl,xr in FISSURE];right=[p(xr,y)for y,xl,xr in reversed(FISSURE)]
d.polygon(left+right,fill=(55,88,107),outline=(150,190,202),width=4)
# subtle grid
reg=ImageFont.truetype(FONTPATH,21);small=ImageFont.truetype(FONTPATH,17);head=ImageFont.truetype(FONTPATH,31)
for x in range(-160,166,40):
 d.line([p(x,miny),p(x,maxy)],fill=(48,78,90),width=1);d.text((p(x,miny)[0]+5,H-29),f'X {x}',font=small,fill=(185,208,212))
for y in range(-120,261,40):
 d.line([p(minx,y),p(maxx,y)],fill=(48,78,90),width=1);d.text((7,p(minx,y)[1]-17),f'Y {y}',font=small,fill=(185,208,212))
# 3d proxy track
track=[p(*interp(t)[0][:2])for t in np.arange(6.5,64.001,.15)]
d.line(track,fill=(233,199,151),width=9,joint='curve');d.line(track,fill=(53,56,53),width=3,joint='curve')
for t in [6.5,12.5,14.5,16.5,18,21.16,25.5,35.7,47,51,58,62,64]:
 xyz=interp(t)[0];x,y=p(*xyz[:2]);c=(152,207,223) if t<20 else ((243,203,142) if t<=40 else (162,206,173))
 d.ellipse((x-10,y-10,x+10,y+10),fill=c,outline=(11,31,45),width=2)
 d.text((x+12,y-16),f'{t:g}s',font=small,fill=(235,235,218))
# camera stations (distinct ground camera points; never teleport PC)
for name in ['A','B','C','D','FLOWERWIDE','MACRO','E-WIDE','E-TELE','F']:
 cam=camera(name,49.2);x,y=p(*cam[0][:2]);d.regular_polygon((x,y,10),3,rotation=180,fill=(248,217,160))
 d.text((x+12,y+3),name,font=small,fill=(247,234,211))
# flower sites and P0
for idx,(x,y,z,lab,st) in enumerate(S1):
 a,b=p(x,y);d.ellipse((a-6,b-6,a+6,b+6),fill=(235,216,150));d.text((a+9,b-21),f'S1 {lab}',font=small,fill=(238,226,188))
a,b=p(-18,-83);d.ellipse((a-7,b-7,a+7,b+7),fill=(241,229,200));d.text((a+12,b-12),'P0',font=small,fill=(247,239,220))
a,b=p(-58,-84);d.ellipse((a-8,b-8,a+8,b+8),fill=(207,131,112));d.text((a-27,b+17),'PC',font=small,fill=(255,200,180))
# Header/footer
d.rounded_rectangle((32,26,790,125),radius=16,fill=(10,26,38),outline=(90,129,144),width=2)
d.text((54,34),'RUOSUEN / OVERLAND SPATIAL PREVIS',font=head,fill=(230,236,228))
d.text((54,82),'v12.1 candidate · metric map · NOT author-approved XYZ',font=reg,fill=(188,205,210))
d.rounded_rectangle((1070,30,1462,125),radius=12,fill=(10,26,38))
d.text((1090,44),'+Y → lake interior / north in diagram',font=small,fill=(211,224,227))
d.text((1090,72),'Whale 24m / camera dots schematic',font=small,fill=(211,224,227))
img.save(out/'scene-plan.png',optimize=True)
print('wrote proxy qa and plan')
