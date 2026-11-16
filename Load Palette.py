import os
import re
import bpy

# ==============================================================================
# CONFIGURATION
# ==============================================================================
EXPORT_FOLDER = r"G:\My Drive\3d objects\__Models\Vehicles\Real\__Full Size\STLs to process"

# ==============================================================================
# 1. BASE & UTILITY MATERIALS (Slots 01 - 10)
# Format: "Material_Name": ((R, G, B, Alpha), Metallic, Roughness)
# ==============================================================================
BASE_PALETTE = {
    "01_Body_White": ((235, 235, 235, 1.0), 0.0, 0.40),
    "02_Aluminum_Silver": ((195, 200, 205, 1.0), 0.85, 0.25),
    "03_Dark_Steel": ((70, 75, 80, 1.0), 0.80, 0.35),
    "04_Signal_Red": ((200, 30, 30, 1.0), 0.0, 0.35),
    "05_Navy_Blue": ((25, 55, 110, 1.0), 0.0, 0.35),
    "06_Olive_Drab": ((75, 85, 55, 1.0), 0.0, 0.65),
    "07_Safety_Yellow": ((235, 185, 20, 1.0), 0.0, 0.35),
    "08_Tire_Rubber": ((30, 30, 32, 1.0), 0.0, 0.85),
    "09_Wood_Brown": ((115, 70, 40, 1.0), 0.0, 0.70),
    # Opaque tinted & high-gloss canopy stand-in (hides hollow mesh interiors)
    "10_Canopy_Glass_StandIn": ((35, 65, 90, 1.0), 0.20, 0.06),
}

# ==============================================================================
# 2. NEUTRALS & 16-COLOR SPECTRUM (18 Colors x 3 Finishes = 54 Materials)
# Generates _Flat, _Gloss (non-metallic), and _Metallic for every entry.
# ==============================================================================
SPECTRUM_COLORS = [
    ("White", (240, 240, 240)),
    ("Black", (22, 22, 24)),
    ("Red", (235, 25, 25)),
    ("Red_Orange", (235, 95, 25)),
    ("Orange", (235, 160, 25)),
    ("Amber", (235, 200, 25)),
    ("Yellow", (235, 235, 25)),
    ("Chartreuse", (165, 235, 25)),
    ("Lime", (85, 235, 35)),
    ("Green", (25, 205, 65)),
    ("Mint", (25, 215, 145)),
    ("Cyan", (25, 215, 235)),
    ("Sky_Blue", (25, 150, 235)),
    ("Cobalt", (30, 85, 235)),
    ("Blue", (50, 35, 235)),
    ("Violet", (125, 30, 235)),
    ("Purple", (195, 30, 225)),
    ("Magenta", (235, 25, 135)),
]


def sanitize_name(raw_name):
  """Replaces spaces/invalid characters with clean underscores."""
  cleaned = re.sub(r"[^\w\-]+", "_", raw_name).strip("_")
  return cleaned or "Painted_Model"


def build_full_palette_dict():
  full_palette = dict(BASE_PALETTE)
  slot_num = len(full_palette) + 1

  for color_name, (r, g, b) in SPECTRUM_COLORS:
    rgba = (r, g, b, 1.0)

    # 1. Flat (matte non-metallic)
    full_palette[f"{slot_num:02d}_{color_name}_Flat"] = (rgba, 0.0, 0.62)
    slot_num += 1

    # 2. Gloss (high-shine non-metallic enamel/lacquer)
    full_palette[f"{slot_num:02d}_{color_name}_Gloss"] = (rgba, 0.0, 0.08)
    slot_num += 1

    # 3. Metallic (reflective anodized/metal)
    full_palette[f"{slot_num:02d}_{color_name}_Metallic"] = (rgba, 0.85, 0.22)
    slot_num += 1

  return full_palette


TOTAL_PALETTE_COUNT = len(build_full_palette_dict())


def srgb_to_linear(rgba):
  def convert(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

  r, g, b, a = rgba
  return (convert(r), convert(g), convert(b), a)


def get_or_create_palette():
  palette_defs = build_full_palette_dict()
  materials = []

  for name, (rgba, metallic, roughness) in palette_defs.items():
    mat = bpy.data.materials.get(name)
    if mat is None:
      mat = bpy.data.materials.new(name=name)
      mat.use_nodes = True

    bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.node_tree else None
    if bsdf:
      lin_color = srgb_to_linear(rgba)
      bsdf.inputs["Base Color"].default_value = lin_color
      bsdf.inputs["Metallic"].default_value = metallic
      bsdf.inputs["Roughness"].default_value = roughness
      bsdf.inputs["Alpha"].default_value = lin_color[3]

      # Boost specular sheen slightly on the opaque canopy glass stand-in
      if name == "10_Canopy_Glass_StandIn":
        if "Specular IOR Level" in bsdf.inputs:
          bsdf.inputs["Specular IOR Level"].default_value = 0.90
        elif "Specular" in bsdf.inputs:
          bsdf.inputs["Specular"].default_value = 0.90

    if hasattr(mat, "blend_method"):
      mat.blend_method = "BLEND" if rgba[3] < 1.0 else "OPAQUE"

    materials.append(mat)
  return materials


def load_palette_into_scene():
  meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
  if not meshes:
    print("[WARNING] No mesh objects found in the scene.")
    return False

  palette_mats = get_or_create_palette()
  base_mat = palette_mats[0]

  for obj in meshes:
    slots = obj.data.materials

    if "AR_Default_Gray" in slots:
      gray_idx = slots.find("AR_Default_Gray")
      slots[gray_idx] = base_mat
    elif len(slots) == 0:
      slots.append(base_mat)

    existing_names = {m.name for m in slots if m is not None}
    for mat in palette_mats:
      if mat.name not in existing_names:
        slots.append(mat)

  target_mesh = meshes[0]
  if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")

  bpy.ops.object.select_all(action="DESELECT")
  target_mesh.select_set(True)
  bpy.context.view_layer.objects.active = target_mesh

  # Auto-populate the sidebar filename box from the imported mesh name
  if hasattr(bpy.context.scene, "ar_museum_export_name"):
    bpy.context.scene.ar_museum_export_name = sanitize_name(target_mesh.name)

  bpy.ops.object.mode_set(mode="EDIT")
  bpy.ops.mesh.select_mode(type="FACE")
  print(f"Loaded {len(palette_mats)} palette colors onto '{target_mesh.name}'.")
  return True


# ==============================================================================
# BLENDER 3D VIEWPORT SIDEBAR UI ("AR Museum" Tab)
# ==============================================================================
class MUSEUM_OT_load_palette(bpy.types.Operator):
  bl_idname = "museum.load_palette"
  bl_label = f"Load / Reload {TOTAL_PALETTE_COUNT}-Color Palette"
  bl_description = (
      f"Loads all {TOTAL_PALETTE_COUNT} museum materials and enters Face Select"
      " mode"
  )

  def execute(self, context):
    if load_palette_into_scene():
      self.report(
          {"INFO"}, f"Loaded {TOTAL_PALETTE_COUNT} museum palette materials."
      )
      return {"FINISHED"}
    self.report({"WARNING"}, "No mesh found in scene.")
    return {"CANCELLED"}


class MUSEUM_OT_export_glb(bpy.types.Operator):
  bl_idname = "museum.export_glb"
  bl_label = "Export Painted .GLB to Batch Folder"
  bl_description = (
      "Removes unused material slots and saves a .glb directly to your batch"
      " folder"
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

    # Strip unused palette slots so the exported .glb stays lightweight
    try:
      bpy.ops.object.material_slot_remove_unused()
    except Exception:
      pass

    os.makedirs(EXPORT_FOLDER, exist_ok=True)
    clean_name = sanitize_name(context.scene.ar_museum_export_name)
    out_path = os.path.join(EXPORT_FOLDER, f"{clean_name}.glb")

    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format="GLB",
        use_selection=True,
    )

    self.report({"INFO"}, f"Saved: {clean_name}.glb")
    print(f"[AR Museum] Exported painted master GLB to: {out_path}")
    return {"FINISHED"}


class MUSEUM_PT_sidebar_panel(bpy.types.Panel):
  bl_label = "AR Museum Tools"
  bl_idname = "MUSEUM_PT_sidebar_panel"
  bl_space_type = "VIEW_3D"
  bl_region_type = "UI"
  bl_category = "AR Museum"

  def draw(self, context):
    layout = self.layout
    layout.operator("museum.load_palette", icon="MATERIAL")
    layout.separator()
    layout.prop(context.scene, "ar_museum_export_name", text="Filename")
    row = layout.row()
    row.scale_y = 1.5
    row.operator("museum.export_glb", icon="EXPORT")


CLASSES = (
    MUSEUM_OT_load_palette,
    MUSEUM_OT_export_glb,
    MUSEUM_PT_sidebar_panel,
)


def register():
  for cls in CLASSES:
    try:
      bpy.utils.unregister_class(cls)
    except Exception:
      pass
    bpy.utils.register_class(cls)

  bpy.types.Scene.ar_museum_export_name = bpy.props.StringProperty(
      name="Filename",
      description=(
          "Output .glb filename (spaces are automatically converted to"
          " underscores)"
      ),
      default="Painted_Model",
  )


register()
load_palette_into_scene()