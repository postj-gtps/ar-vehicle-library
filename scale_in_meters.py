import os
import re
import bpy
import mathutils

# ==============================================================================
# CONFIGURATION
# ==============================================================================
EXPORT_FOLDER = r"G:\My Drive\3d objects\__Models\Vehicles\Real\__Full Size\STLs to process"


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

    # Bake the scaled dimensions directly into the mesh vertices before export
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


class SCALE_PT_sidebar_panel(bpy.types.Panel):
  bl_label = "Scale & Export (Meters)"
  bl_idname = "SCALE_PT_sidebar_panel"
  bl_space_type = "VIEW_3D"
  bl_region_type = "UI"
  bl_category = "Scale & Export"

  def draw(self, context):
    layout = self.layout
    layout.operator("museum.prepare_meters", icon="FULLSCREEN_ENTER")

    obj = context.active_object
    if obj and obj.type == "MESH":
      box = layout.box()
      box.label(text="Current Size (Meters):", icon="DRIVER_DISTANCE")
      col = box.column(align=True)
      col.prop(obj, "dimensions", index=0, text="X (Width)")
      col.prop(obj, "dimensions", index=1, text="Y (Length)")
      col.prop(obj, "dimensions", index=2, text="Z (Height)")

    layout.separator()
    layout.prop(context.scene, "ar_scale_export_name", text="Filename")
    row = layout.row()
    row.scale_y = 1.5
    row.operator("museum.export_scaled_stl", icon="EXPORT")


CLASSES = (
    SCALE_OT_prepare_meters,
    SCALE_OT_export_stl,
    SCALE_PT_sidebar_panel,
)


def register():
  for cls in CLASSES:
    try:
      bpy.utils.unregister_class(cls)
    except Exception:
      pass
    bpy.utils.register_class(cls)

  bpy.types.Scene.ar_scale_export_name = bpy.props.StringProperty(
      name="Filename",
      description="Output .stl filename (spaces are converted to underscores)",
      default="Scaled_Model",
  )


register()
prepare_mesh_for_scaling(bpy.context)