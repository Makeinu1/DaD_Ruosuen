import bpy, math, sys
from mathutils import Vector, Euler
A=sys.argv[-2]; OUT=sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene; sc.render.engine="CYCLES"; sc.cycles.device="CPU"; sc.cycles.samples=32; sc.cycles.use_denoising=True
sc.render.resolution_x, sc.render.resolution_y = 800, 450
sc.view_settings.view_transform="AgX"
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs["Color"].default_value=(0.36,0.37,0.39,1); w.node_tree.nodes["Background"].inputs["Strength"].default_value=1.0
bpy.ops.import_scene.gltf(filepath=A+"/wh01_v20_hero.glb")
wh=next(o for o in bpy.data.objects if o.type=='MESH')
n_local=Vector((0.09,0.94,0.34)).normalized()
ids={vi for p in wh.data.polygons if p.material_index==1 for vi in p.vertices}
# push both eyes out (left eye +Y, right eye mirrored -Y)
for vi in ids:
    v=wh.data.vertices[vi]; nl=Vector((n_local.x, n_local.y if v.co.y>0 else -n_local.y, n_local.z))
    v.co+=nl*0.20
wh.data.update()
body=bpy.data.materials.new("skin"); body.use_nodes=True; b=body.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value=(0.10,0.15,0.22,1); b.inputs["Roughness"].default_value=0.33
if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value=0.5
eye=bpy.data.materials.new("eye"); eye.use_nodes=True; e=eye.node_tree.nodes["Principled BSDF"]
e.inputs["Base Color"].default_value=(0.003,0.004,0.008,1); e.inputs["Roughness"].default_value=0.05
for i,s in enumerate(wh.material_slots): s.material = eye if i==1 else body
def light(name,loc,energy,size):
    d=bpy.data.lights.new(name,"AREA"); d.energy=energy; d.size=size
    o=bpy.data.objects.new(name,d); sc.collection.objects.link(o); o.location=loc
    o.rotation_euler=(Vector((0,0,0))-Vector(loc)).to_track_quat("-Z","Y").to_euler()
light("key",(10,-25,18),90000,14); light("fill",(-20,20,8),30000,20); light("rim",(-5,30,-10),25000,16)
camd=bpy.data.cameras.new("c"); camd.sensor_width=36; cam=bpy.data.objects.new("c",camd); sc.collection.objects.link(cam); sc.camera=cam
views=[("side",(0,-46,0),(0,0,0),40),("front34",(34,-16,7),(1,0,0),36),("belly",(0,-6,-40),(0,0,0),40),("top",(0,0,64),(0,0,0),40)]
for name,loc,tgt,lens in views:
    camd.lens=lens; cam.location=loc
    up="Y" if name!="top" else "Y"
    cam.rotation_euler=(Vector(tgt)-Vector(loc)).to_track_quat("-Z","Y").to_euler()
    if name=="top": cam.rotation_euler=Euler((0,0,math.radians(90)))
    sc.render.filepath=f"{OUT}/sheet_{name}.png"; bpy.ops.render.render(write_still=True); print("rendered",name)
