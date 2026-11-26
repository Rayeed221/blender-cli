"""Materials matched to the design photos: warm cream/beige paint, white marble floor,
walnut slatted doors, black slim frames, taupe/beige kitchen with black granite, beige
fabrics, warm 2700K LED coves."""
import bpy

M = {}


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)


class NT:
    """Tiny node-tree builder."""

    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        self.nt.nodes.clear()
        self.out = self.node("ShaderNodeOutputMaterial")
        self.x = 0

    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            if k in n.inputs:
                n.inputs[k].default_value = v
            else:
                setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def principled(self, color, rough=0.5, metal=0.0, **kw):
        p = self.node("ShaderNodeBsdfPrincipled")
        p.inputs["Base Color"].default_value = srgb(color) if isinstance(color, str) else color
        p.inputs["Roughness"].default_value = rough
        p.inputs["Metallic"].default_value = metal
        for k, v in kw.items():
            p.inputs[k].default_value = v
        self.link(p.outputs[0], self.out.inputs["Surface"])
        self.mat.diffuse_color = srgb(color) if isinstance(color, str) else color
        return p

    def coords(self, kind="Object"):
        tc = self.node("ShaderNodeTexCoord")
        return tc.outputs[kind]

    def ramp(self, fac, stops):
        r = self.node("ShaderNodeValToRGB")
        el = r.color_ramp.elements
        el[0].position, el[0].color = stops[0][0], srgb(stops[0][1])
        el[1].position, el[1].color = stops[-1][0], srgb(stops[-1][1])
        for pos, col in stops[1:-1]:
            e = el.new(pos)
            e.color = srgb(col)
        self.link(fac, r.inputs["Fac"])
        return r.outputs["Color"]


def plain(name, color, rough=0.5, metal=0.0, **kw):
    t = NT(name)
    t.principled(color, rough, metal, **kw)
    return t.mat


def marble(name="Marble", base="#f4f0ea", vein="#d2c9be", scale=1.1, rough=0.12):
    """Polished marble: near-uniform base, thin meandering veins from a noise iso-line."""
    t = NT(name)
    p = t.principled(base, rough)
    co = t.coords()
    n = t.node("ShaderNodeTexNoise", noise_dimensions="3D")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = 9
    n.inputs["Roughness"].default_value = 0.6
    n.inputs["Distortion"].default_value = 0.6
    t.link(co, n.inputs["Vector"])
    mr = t.node("ShaderNodeMath", operation="SUBTRACT")
    mr.inputs[1].default_value = 0.5
    t.link(n.outputs["Fac"], mr.inputs[0])
    ab = t.node("ShaderNodeMath", operation="ABSOLUTE")
    t.link(mr.outputs[0], ab.inputs[0])
    col = t.ramp(ab.outputs[0], [(0.0, vein), (0.008, base), (1.0, base)])
    # faint cloudy variation
    n2 = t.node("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = scale * 3
    t.link(co, n2.inputs["Vector"])
    cl = t.ramp(n2.outputs["Fac"], [(0.35, "#ffffff"), (0.75, "#eee9e2")])
    mix = t.node("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    mix.inputs[0].default_value = 1.0
    t.link(col, mix.inputs[6])
    t.link(cl, mix.inputs[7])
    t.link(mix.outputs[2], p.inputs["Base Color"])
    return t.mat


def tiles(name, base, grout, size=0.6, rough=0.3):
    t = NT(name)
    p = t.principled(base, rough)
    co = t.coords()
    br = t.node("ShaderNodeTexBrick", offset=0.0)
    br.inputs["Color1"].default_value = srgb(base)
    br.inputs["Color2"].default_value = srgb(base)
    br.inputs["Mortar"].default_value = srgb(grout)
    br.inputs["Scale"].default_value = 1 / size
    br.inputs["Mortar Size"].default_value = 0.003
    br.inputs["Row Height"].default_value = 0.5
    br.inputs["Brick Width"].default_value = 0.5
    t.link(co, br.inputs["Vector"])
    t.link(br.outputs["Color"], p.inputs["Base Color"])
    return t.mat


def wood(name, base, dark, grooves=None, scale=8.0, rough=0.45, axis="Z"):
    """Wood grain (noise-stretched waves). grooves: spacing (m) of horizontal slat lines."""
    t = NT(name)
    p = t.principled(base, rough)
    co = t.coords()
    mp = t.node("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1, 1, 12) if axis == "Z" else (12, 1, 1)
    t.link(co, mp.inputs["Vector"])
    n = t.node("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = 8
    n.inputs["Distortion"].default_value = 2
    t.link(mp.outputs[0], n.inputs["Vector"])
    col = t.ramp(n.outputs["Fac"], [(0.3, dark), (0.7, base)])
    if grooves:
        w = t.node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Z", wave_profile="SAW")
        w.inputs["Scale"].default_value = 1.0 / grooves / 6.2832 * 6.2832
        t.link(co, w.inputs["Vector"])
        mr = t.node("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.0
        mr.inputs["From Max"].default_value = 0.06
        t.link(w.outputs["Fac"], mr.inputs["Value"])
        mul = t.node("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
        mul.inputs[0].default_value = 1.0
        t.link(col, mul.inputs[6])
        t.link(mr.outputs[0], mul.inputs[7])
        sub = t.node("ShaderNodeMix", data_type="RGBA", blend_type="MIX")
        sub.inputs[6].default_value = srgb("#2b1a10")
        t.link(mr.outputs[0], sub.inputs[0])
        sub.inputs[6].default_value = srgb("#2b1a10")
        t.link(col, sub.inputs[7])
        t.link(sub.outputs[2], p.inputs["Base Color"])
        bump = t.node("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.4
        t.link(mr.outputs[0], bump.inputs["Height"])
        t.link(bump.outputs[0], p.inputs["Normal"])
    else:
        t.link(col, p.inputs["Base Color"])
    return t.mat


def fabric(name, color, rough=0.9, bump=0.15):
    t = NT(name)
    p = t.principled(color, rough, **{"Sheen Weight": 0.4})
    co = t.coords()
    n = t.node("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 180
    t.link(co, n.inputs["Vector"])
    b = t.node("ShaderNodeBump")
    b.inputs["Strength"].default_value = bump
    t.link(n.outputs["Fac"], b.inputs["Height"])
    t.link(b.outputs[0], p.inputs["Normal"])
    return t.mat


def emission(name, color, strength):
    t = NT(name)
    e = t.node("ShaderNodeEmission")
    e.inputs["Color"].default_value = color if isinstance(color, tuple) else srgb(color)
    e.inputs["Strength"].default_value = strength
    t.link(e.outputs[0], t.out.inputs["Surface"])
    t.mat.diffuse_color = e.inputs["Color"].default_value
    return t.mat


def thin_glass(name, tint="#f4f8f8", frosted=False):
    """Architectural glass: Fresnel reflection over a clear see-through layer, so sun and
    sky pass straight through windows without caustic noise."""
    t = NT(name)
    tr = t.node("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = srgb(tint)
    gl = t.node("ShaderNodeBsdfAnisotropic")  # "Glossy BSDF" in 4.0+
    gl.inputs["Roughness"].default_value = 0.35 if frosted else 0.02
    fr = t.node("ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.5
    # reflection only on front faces of camera/indirect rays: back faces of the thin pane
    # would otherwise hit total internal reflection (Fresnel = 1) and block the sun
    lp = t.node("ShaderNodeLightPath")
    geo = t.node("ShaderNodeNewGeometry")
    nb = t.node("ShaderNodeMath", operation="SUBTRACT")
    nb.inputs[0].default_value = 1.0
    t.link(geo.outputs["Backfacing"], nb.inputs[1])
    ns = t.node("ShaderNodeMath", operation="SUBTRACT")
    ns.inputs[0].default_value = 1.0
    t.link(lp.outputs["Is Shadow Ray"], ns.inputs[1])
    f1 = t.node("ShaderNodeMath", operation="MULTIPLY")
    t.link(fr.outputs[0], f1.inputs[0])
    t.link(nb.outputs[0], f1.inputs[1])
    f2 = t.node("ShaderNodeMath", operation="MULTIPLY")
    t.link(f1.outputs[0], f2.inputs[0])
    t.link(ns.outputs[0], f2.inputs[1])
    mix = t.node("ShaderNodeMixShader")
    t.link(f2.outputs[0], mix.inputs[0])
    t.link(tr.outputs[0], mix.inputs[1])
    t.link(gl.outputs[0], mix.inputs[2])
    if frosted:
        df = t.node("ShaderNodeBsdfTranslucent")
        df.inputs["Color"].default_value = srgb("#f2efe9")
        m2 = t.node("ShaderNodeMixShader")
        m2.inputs[0].default_value = 0.6
        t.link(mix.outputs[0], m2.inputs[1])
        t.link(df.outputs[0], m2.inputs[2])
        mix = m2
    t.link(mix.outputs[0], t.out.inputs["Surface"])
    t.mat.diffuse_color = srgb(tint)[:3] + (0.15,)
    t.mat.blend_method = "BLEND" if hasattr(t.mat, "blend_method") else None
    return t.mat


def exterior_render(name, base="#ddd5ca", joint="#b9b0a4", course=0.6):
    """Smooth render with horizontal panel joints every `course` metres."""
    t = NT(name)
    p = t.principled(base, 0.85)
    sep = t.node("ShaderNodeSeparateXYZ")
    t.link(t.coords(), sep.inputs[0])
    d = t.node("ShaderNodeMath", operation="DIVIDE")
    d.inputs[1].default_value = course
    t.link(sep.outputs["Z"], d.inputs[0])
    fr = t.node("ShaderNodeMath", operation="FRACT")
    t.link(d.outputs[0], fr.inputs[0])
    lt = t.node("ShaderNodeMath", operation="LESS_THAN")
    lt.inputs[1].default_value = 0.025
    t.link(fr.outputs[0], lt.inputs[0])
    mix = t.node("ShaderNodeMix", data_type="RGBA")
    mix.inputs[6].default_value = srgb(base)
    mix.inputs[7].default_value = srgb(joint)
    t.link(lt.outputs[0], mix.inputs[0])
    t.link(mix.outputs[2], p.inputs["Base Color"])
    return t.mat


def blackbody(k):
    # approximate sRGB->linear warm white for LED colour temperatures
    return {2700: (1.0, 0.62, 0.32, 1), 3000: (1.0, 0.70, 0.42, 1), 4000: (1.0, 0.82, 0.64, 1)}[k]


def make():
    M["wall"] = plain("Wall paint", "#ece3d7", 0.85)
    M["exterior"] = exterior_render("Exterior render")
    M["wall_top"] = plain("Wall top", "#bdb6ac", 0.9)
    M["ceiling"] = plain("Ceiling", "#f7f3ee", 0.9)
    M["roof"] = tiles("Roof tiles", "#b4aea5", "#8e877d", 0.4, 0.8)
    M["marble"] = marble()
    M["bath_tile"] = tiles("Bath tile", "#d8cdbf", "#b9ad9e", 0.6, 0.25)
    M["utility_tile"] = tiles("Utility tile", "#bdb7ae", "#8f897f", 0.3, 0.6)
    M["deck"] = wood("Teak deck", "#a46f45", "#7a4b2b", scale=5, rough=0.6, axis="X")
    M["frame"] = plain("Black aluminium", "#252322", 0.35, 0.8)
    M["glass"] = thin_glass("Glass")
    M["glass_frosted"] = thin_glass("Frosted glass", frosted=True)
    M["door_wood"] = wood("Walnut", "#8a5b3d", "#5e3a24", rough=0.4)
    M["door_leaf"] = wood("Walnut slatted", "#8a5b3d", "#5e3a24", grooves=0.11, rough=0.4)
    M["brass"] = plain("Satin brass", "#c9a46b", 0.3, 1.0)
    M["chrome"] = plain("Chrome", "#d9d9d9", 0.08, 1.0)
    M["planter"] = plain("Planter render", "#cfc6ba", 0.85)
    M["soil"] = plain("Soil", "#3b2a1e", 1.0)
    M["led"] = emission("LED cove 2700K", blackbody(2700), 12.0)
    M["led_panel"] = emission("LED linear 3000K", blackbody(3000), 6.0)
    # furniture palette (from the photos)
    M["sofa"] = fabric("Sofa beige", "#d8c8b3")
    M["cushion_cream"] = fabric("Cushion cream", "#ece4d6")
    M["cushion_rust"] = fabric("Cushion terracotta", "#b8735a")
    M["rug"] = fabric("Rug grey-beige", "#a9a196", rough=1.0, bump=0.5)
    M["panel_beige"] = plain("Beige panel", "#d6c3aa", 0.6)
    M["panel_cream"] = plain("Cream lacquer", "#efe8dc", 0.3)
    M["black_metal"] = plain("Black metal", "#1c1b1a", 0.35, 0.9)
    M["black_glass"] = plain("TV glass", "#0c0c0d", 0.05)
    M["granite"] = marble("Black granite", "#141414", "#3a3a3a", 3.0, 0.18)
    M["cabinet_taupe"] = plain("Taupe lacquer", "#bfae9b", 0.35)
    M["cabinet_cream"] = plain("Cream matt", "#e4dbcf", 0.55)
    M["backsplash"] = marble("Backsplash marble", "#e3d8c9", "#bba993", 1.2, 0.2)
    M["steel"] = plain("Dark steel", "#3a3a3c", 0.3, 0.9)
    M["leather_rose"] = fabric("Chair leather", "#a77b67", rough=0.55, bump=0.05)
    M["white_marble_top"] = marble("Table marble", "#f4f1ec", "#cfc8c0", 1.5, 0.08)
    M["wood_light"] = wood("Light oak", "#b88c62", "#97704c", rough=0.5)
    M["rattan"] = fabric("Rattan charcoal", "#3d3934", rough=0.8, bump=0.6)
    M["terracotta"] = plain("Terracotta pot", "#b06a4a", 0.8)
    M["plant"] = fabric("Leaf green", "#4b6b37", rough=0.6, bump=0.2)
    M["plant_dark"] = fabric("Leaf dark", "#34502a", rough=0.6, bump=0.2)
    M["sheer"] = plain("Sheer curtain", "#f3efe8", 0.9, **{"Transmission Weight": 0.6, "Thin Wall": True})
    M["drape"] = fabric("Drape taupe", "#a89078")
    M["ceramic"] = plain("Ceramic white", "#f4f2ee", 0.15)
    M["bed_linen"] = fabric("Bed linen", "#eee8de")
    M["throw"] = fabric("Throw taupe", "#9e8670")
    M["lamp_glow"] = emission("Lamp glow", blackbody(2700), 8.0)
    M["art"] = plain("Art print", "#c7a98a", 0.7)
    M["teal"] = plain("Teal panel", "#3f6870", 0.6)
    M["teal_fabric"] = fabric("Teal velvet", "#3c6a72", rough=0.7)
    M["art_abstract"] = marble("Abstract art", "#cdbba1", "#2c4f57", 0.8, 0.5)
    return M
