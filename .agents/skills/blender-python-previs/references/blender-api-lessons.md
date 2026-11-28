# Blender 4.x / 5.x API Lessons & Headless Verification Rules

> Source: [starryark/3d-assisted-illustration — docs/LESSONS.md](https://github.com/starryark/3d-assisted-illustration/blob/main/docs/LESSONS.md) (MIT License)

## Compositor & Render Output (Blender 5.x)
- No `scene.node_tree` / Composite node in 5.2+: create a `CompositorNodeTree` group, add an interface output socket, end in `NodeGroupOutput`, and assign `scene.compositing_node_group`.
- File Output / PNG render: set `image_settings.media_type = 'IMAGE'` (when present) **before** `file_format = 'PNG'`, otherwise multilayer EXR may be enforced.
- Never combine `item.override_node_format` with mutating `item.format` (crash risk); use one node-level format per output node.
- `CompositorNodeMixRGB` is removed in 5.x; use `ShaderNodeMix` (`data_type = 'RGBA'`).

## Geometry, Placement & Measuring
- **Fresh objects have a stale `matrix_world`**: call `bpy.context.view_layer.update()` or aim cameras from `obj.location`, never from un-updated `matrix_world.translation`.
- **Bounding boxes lie for rotated objects**: `obj.bound_box` transformed to world space inflates AABBs. Always inspect evaluated vertices (`depsgraph` + `eo.to_mesh()` + `eo.to_mesh_clear()`).
- **Ray-casting past resting objects**: temporarily hide ignored objects before casting `scene.ray_cast` rather than offsetting past coplanar bases.
- **Scatter after ray-cast placement**: `scene.ray_cast` hits geometry-nodes instances.
- `bmesh.ops.subdivide_edges` invalidates references to original vertices.

## Checkpoint & Clay Render Discipline
- Clear or replace Blender's default near-black world with a calibrated neutral/scene world before evaluating silhouettes.
- Never write fake assertions (`ok or True`); print measured values (`u, v, height_share, contact_z`) in every QA report.

## Headless Operation & GPU
- Always run headless scripts with:
  ```bash
  blender --background --factory-startup --python-exit-code 1 --python script.py -- [args]
  ```
- Cycles GPU discovery: iterate `METAL`, `OPTIX`, `CUDA`, `HIP`, `ONEAPI` via `prefs.get_devices()`, falling back cleanly to `CPU`.
