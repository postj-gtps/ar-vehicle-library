import os
import re
import bpy
import mathutils

# ==============================================================================
# CONFIGURATION
# ==============================================================================
EXPORT_FOLDER = r"G:\My Drive\3d objects\__Models\Vehicles\Real\__Full Size\STLs to process"

_updating_ui = False


def sanitize_name(raw_name):
  """Replaces spaces/invalid characters with clean underscores."""
  cleaned = re.sub(r"[^\w\-]+", "_", raw_name).strip("_")
  return cleaned or "Scaled_Model"


def enforce_meter_units(context):
  """Forces Blender's scene units to Metric -> Meters (1 Blender unit = 1 meter)."""
  units = context.scene.unit_settings
  units.system = "METRIC"
  units.scale_length = 1.0
  units.length_unit = "METERS"


def get_target_mesh(context):
  """Returns the active mesh, or the first mesh in the scene if an Empty is selected."""
  obj = context.active_object
  if obj and obj.type == "MESH":
    return obj
  meshes = [o for o in context.scene.objects if o.type == "MESH"]
  return meshes[0] if meshes else None


def sync_target_field_from_mesh(context):
  """Updates the Target Size input box to match the selected axis's current meter size."""
  global _updating_ui
  mesh = get_target_mesh(context)
  if not mesh or not hasattr(context.scene, "ar_target_dimension"):
    return
  axis_idx = {"X": 0, "Y": 1, "Z": 2}[context.scene.ar_scale_axis]
  _updating_ui = True
  try:
    context.scene.ar_target_dimension = mesh.dimensions[axis_idx]
  finally:
    _updating_ui = False


def apply_proportional_target_scale(context):
  """Scales the entire model uniformly so the chosen axis matches Target Size (m)."""
  enforce_meter_units(context)
  mesh = get_target_mesh(context)
  if not mesh:
    return False, "No mesh found in scene."

  axis_label = context.scene.ar_scale_axis
  axis_idx = {"X": 0, "Y": 1, "Z": 2}[axis_label]
  current_val = mesh.dimensions[axis_idx]
  target_val = context.scene.ar_target_dimension

  if current_val <= 1e-6 or target_val <= 1e-6:
    return False, "Current or target dimension must be greater than 0."

  ratio = target_val / current_val

  if context.object and context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")

  # Scale all root objects uniformly around world origin
  for obj in context.scene.objects:
    if obj.parent is None:
      obj.scale = (
          obj.scale.x * ratio,
          obj.scale.y * ratio,
          obj.scale.z * ratio,
      )

  context.view_layer.update()

  # Unparent any USDZ wrapper Empties while preserving world transform, then bake scale
  meshes = [o for o in context.scene.objects if o.type == "MESH"]
  bpy.ops.object.select_all(action="DESELECT")
  for m in meshes:
    m.select_set(True)
  context.view_layer.objects.active = mesh

  bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
  bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

  # Clean up leftover empty parent containers
  for obj in list(context.scene.objects):
    if obj.type == "EMPTY" and len(obj.children) == 0:
      bpy.data.objects.remove(obj, do_unlink=True)

  return (
      True,
      f"Scaled uniformly to {axis_label} = {mesh.dimensions[axis_idx]:.3f} m",
  )


def on_axis_changed(self, context):
  if not _updating_ui:
    sync_target_field_from_mesh(context)


def on_target_dimension_changed(self, context):
  if not _updating_ui:
    apply_proportional_target_scale(context)


def prepare_mesh_for_scaling(context):
  """Enforces meters, joins multi-part meshes, centers at (0,0,0), and rests base on Z=0."""
  enforce_meter_units(context)

  meshes = [obj for obj in context.scene.objects if obj.type == "MESH"]
  if not meshes:
    return None

  if context.object and context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")

  bpy.ops.object.select_all(action="DESELECT")
  for obj in meshes:
    obj.select_set(True)
  context.view_layer.objects.active = meshes[0]

  bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")

  if len(meshes) > 1:
    bpy.ops.object.join()

  target = context.active_object

  # Bake any existing import scale/rotation so meter dimensions read accurately
  bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

  # Center X/Y at 0 and place the bottom of the model flat on the floor (Z=0)
  bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
  target.location = (0.0, 0.0, 0.0)

  bbox = [
      target.matrix_world @ mathutils.Vector(corner)
      for corner in target.bound_box
  ]
  min_z = min(corner.z for corner in bbox)
  target.location.z -= min_z
  bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

  if hasattr(context.scene, "ar_scale_export_name"):
    context.scene.ar_scale_export_name = sanitize_name(target.name)

  sync_target_field_from_mesh(context)
  return target


# ==============================================================================
# BLENDER 3D VIEWPORT SIDEBAR UI ("Scale & Export" Tab)
# ==============================================================================
class SCALE_OT_prepare_meters(bpy.types.Operator):
  bl_idname = "museum.prepare_meters"
  bl_label = "Set Units to Meters & Center"
  bl_description = (
      "Forces scene units to Meters and centers the imported model at (0,0,0)"
  )

  def execute(self, context):
    target = prepare_mesh_for_scaling(context)
    if target:
      self.report(
          {"INFO"}, f"Units set to Meters. Ready to scale '{target.name}'."
      )
      return {"FINISHED"}
    enforce_meter_units(context)
    self.report({"WARNING"}, "Units set to Meters (no mesh in scene yet).")
    return {"FINISHED"}


class SCALE_OT_apply_uniform_target(bpy.types.Operator):
  bl_idname = "museum.apply_uniform_target"
  bl_label = "Apply Uniform Scale"
  bl_description = (
      "Scales X, Y, and Z proportionally so the chosen axis equals Target Size"
  )

  def execute(self, context):
    ok, msg = apply_proportional_target_scale(context)
    self.report({"INFO"} if ok else {"ERROR"}, msg)
    return {"FINISHED"} if ok else {"CANCELLED"}


class SCALE_OT_export_stl(bpy.types.Operator):
  bl_idname = "museum.export_scaled_stl"
  bl_label = "Apply Scale & Export .STL"
  bl_description = (
      "Bakes the new meter scale into the mesh and exports a clean .STL"
  )

  def execute(self, context):
    meshes = [obj for obj in context.scene.objects if obj.type == "MESH"]
    if not meshes:
      self.report({"ERROR"}, "No mesh found to export.")
      return {"CANCELLED"}

    if context.object and context.object.mode != "OBJECT":
      bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
      obj.select_set(True)
    context.view_layer.objects.active = meshes[0]

    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    os.makedirs(EXPORT_FOLDER, exist_ok=True)
    clean_name = sanitize_name(context.scene.ar_scale_export_name)
    out_path = os.path.join(EXPORT_FOLDER, f"{clean_name}.stl")

    if hasattr(bpy.ops.wm, "stl_export"):
      bpy.ops.wm.stl_export(
          filepath=out_path,
          export_selected_objects=True,
          global_scale=1.0,
      )
    else:
      bpy.ops.export_mesh.stl(
          filepath=out_path,
          use_selection=True,
          global_scale=1.0,
      )

    self.report({"INFO"}, f"Exported: {clean_name}.stl")
    print(f"[Scale Tool] Exported meter-scaled STL to: {out_path}")
    return {"FINISHED"}


class SCALE_OT_export_usdz_direct(bpy.types.Operator):
  bl_idname = "museum.export_direct_usdz"
  bl_label = "Export Direct .USDZ (Skip Batch)"
  bl_description = (
      "Exports an already-colored/anchored .USDZ directly without re-running"
      " batch_convert.py"
  )

  def execute(self, context):
    meshes = [obj for obj in context.scene.objects if obj.type == "MESH"]
    if not meshes:
      self.report({"ERROR"}, "No mesh found to export.")
      return {"CANCELLED"}

    if context.object and context.object.mode != "OBJECT":
      bpy.ops.object.mode_set(mode="OBJECT")

    clean_name = sanitize_name(context.scene.ar_scale_export_name)
    default_path = os.path.join(EXPORT_FOLDER, f"{clean_name}.usdz")
    bpy.ops.wm.usd_export("INVOKE_DEFAULT", filepath=default_path)
    return {"FINISHED"}


class SCALE_PT_sidebar_panel(bpy.types.Panel):
  bl_label = "Scale & Export (Meters)"
  bl_idname = "SCALE_PT_sidebar_panel"
  bl_space_type = "VIEW_3D"
  bl_region_type = "UI"
  bl_category = "Scale & Export"

  def draw(self, context):
    layout = self.layout
    layout.operator("museum.prepare_meters", icon="FULLSCREEN_ENTER")

    mesh = get_target_mesh(context)
    if mesh:
      box = layout.box()
      box.label(text="Current Size (Meters):", icon="DRIVER_DISTANCE")
      col = box.column(align=True)
      col.enabled = False
      col.prop(mesh, "dimensions", index=0, text="X (Width)")
      col.prop(mesh, "dimensions", index=1, text="Y (Length)")
      col.prop(mesh, "dimensions", index=2, text="Z (Height)")

      sbox = layout.box()
      sbox.label(text="Proportional Scale (Lock Ratio):", icon="CON_SIZELIKE")
      sbox.prop(context.scene, "ar_scale_axis", text="Axis")
      sbox.prop(context.scene, "ar_target_dimension", text="Target (m)")
      sbox.operator("museum.apply_uniform_target", icon="CHECKMARK")

    layout.separator()
    layout.prop(context.scene, "ar_scale_export_name", text="Filename")
    row = layout.row()
    row.scale_y = 1.4
    row.operator("museum.export_scaled_stl", icon="EXPORT")

    row2 = layout.row()
    row2.operator("museum.export_direct_usdz", icon="FILE_3D")


CLASSES = (
    SCALE_OT_prepare_meters,
    SCALE_OT_apply_uniform_target,
    SCALE_OT_export_stl,
    SCALE_OT_export_usdz_direct,
    SCALE_PT_sidebar_panel,
)


def register():
  for cls in CLASSES:
    try:
      bpy.utils.unregister_class(cls)
    except Exception:
      pass
    bpy.utils.register_class(cls)

  bpy.types.Scene.ar_scale_axis = bpy.props.EnumProperty(
      name="Reference Axis",
      description="Choose which axis to set; the other two scale proportionally",
      items=[
          ("X", "X (Width / Wingspan)", "Scale uniformly based on X dimension"),
          ("Y", "Y (Length)", "Scale uniformly based on Y dimension"),
          ("Z", "Z (Height)", "Scale uniformly based on Z dimension"),
      ],
      default="X",
      update=on_axis_changed,
  )

  bpy.types.Scene.ar_target_dimension = bpy.props.FloatProperty(
      name="Target Size (m)",
      description="Desired meter size for the selected axis (scales all axes uniformly)",
      default=1.0,
      min=0.0001,
      soft_max=500.0,
      unit="LENGTH",
      update=on_target_dimension_changed,
  )

  bpy.types.Scene.ar_scale_export_name = bpy.props.StringProperty(
      name="Filename",
      description="Output filename (spaces are converted to underscores)",
      default="Scaled_Model",
  )


register()
prepare_mesh_for_scaling(bpy.context)