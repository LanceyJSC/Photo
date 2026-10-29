"""The style library: how working photographers actually grade each genre.

Each Style is a partial recipe plus *targets* (where the histogram should land)
and *adapt* hints (which scene-aware behaviours the director should enable).
Scales: hsl h +-1 = +-30 deg, s +-1 = +-100 % chroma, l +-1 = +-0.22 L;
grade s ~ 0.3 is subtle, 0.6 strong; Oklab hues: red 29, orange 55, yellow 105,
green 142, teal 195, blue 264, magenta 340.
"""
from __future__ import annotations

from dataclasses import dataclass, field

BANDS = ["red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"]


def hsl(**kw):
    """hsl(red=(h, s, l), blue=(...))"""
    return {b: {"h": v[0], "s": v[1], "l": v[2]} for b, v in kw.items()}


def zone(h=0.0, s=0.0, l=0.0):
    return {"h": h, "s": s, "l": l}


def bwmix(**kw):
    return {b: kw.get(b, 0.0) for b in BANDS}


@dataclass
class Style:
    id: str
    name: str
    category: str
    description: str
    keywords: list
    recipe: dict
    targets: dict = field(default_factory=dict)
    adapt: dict = field(default_factory=dict)
    notes: str = ""

    @property
    def is_bw(self) -> bool:
        return self.recipe.get("color", {}).get("bw", {}).get("amount", 0) > 0.5


T = lambda median, lo=0.02, hi=0.96, **kw: {"median": median, "black": lo, "hi": hi, **kw}  # noqa: E731

STYLES: list[Style] = []


def add(*a, **k):
    STYLES.append(Style(*a, **k))


# ======================================================================= CLEAN
add("natural", "Natural – Pro Develop", "Everyday",
    "What a careful editor does before any 'look': accurate colour, protected highlights, open shadows, gentle contrast and crisp detail.",
    ["natural", "clean", "neutral", "realistic", "accurate", "basic", "default", "true to life", "faithful"],
    {"wb": {"auto": 0.2}, "tone": {"contrast": 1.08, "highlights": -20, "shadows": 18},
     "presence": {"clarity": 8, "texture": 6}, "color": {"vibrance": 10, "saturation": 2},
     "detail": {"sharpen": 0.55, "nr_luma": 0.0, "defringe": 0.4}},
    T(0.54), {"nr": 1.0},
    "Expose for the highlights, lift shadows, remove cast, add local contrast and sharpen once.")

# ======================================================================= STREET
add("street_classic", "Street – Classic Documentary", "Street",
    "Honest, contrasty reportage: deep blacks, a touch less colour, grit in the mid-tones, cool shadows and warm lights like a Leica-era colour print.",
    ["street", "documentary", "reportage", "urban", "classic street", "candid", "leica", "photojournalism"],
    {"tone": {"contrast": 1.2, "highlights": -18, "shadows": 6, "toe": 0.35, "shoulder": 0.6},
     "presence": {"clarity": 20, "texture": 14, "micro_contrast": 10},
     "color": {"saturation": -10, "vibrance": 6,
               "grade": {"shadows": zone(215, 0.22), "highlights": zone(70, 0.2), "blend": 0.5},
               "hsl": hsl(blue=(-0.05, -0.12, -0.1), green=(-0.1, -0.2, 0))},
     "detail": {"sharpen": 0.65, "defringe": 0.4},
     "effects": {"grain": {"amount": 0.22, "size": 1.0, "roughness": 0.5}, "vignette": {"amount": 0.18}},
     "wb": {"auto": 0.0}},
    T(0.48, 0.012, 0.95, preserve_key=0.4, lift_shadows=False),
    {"sky": {"exposure": -0.25, "blue_lum": -0.2}},
    "Street work keeps the scene's mood: little WB correction, protected blacks, local contrast over global lift.")

add("street_gritty", "Street – Gritty High Contrast", "Street",
    "Hard, punchy city look: crushed blacks, bite in every texture, desaturated colour, heavy grain.",
    ["gritty", "grit", "harsh", "hard", "punchy", "contrasty", "raw street", "dirty", "urban decay", "high contrast street"],
    {"tone": {"contrast": 1.38, "highlights": -25, "shadows": -5, "blacks": -15, "toe": 0.2, "shoulder": 0.7,
              "highlight_desat": 0.25},
     "presence": {"clarity": 38, "texture": 28, "micro_contrast": 25, "dehaze": 6},
     "color": {"saturation": -24, "vibrance": 4,
               "grade": {"shadows": zone(230, 0.25), "highlights": zone(85, 0.18)}},
     "detail": {"sharpen": 0.8, "defringe": 0.4},
     "effects": {"grain": {"amount": 0.45, "size": 1.15, "roughness": 0.65}, "vignette": {"amount": 0.3}}},
    T(0.44, 0.005, 0.95, preserve_key=0.5, lift_shadows=False),
    {"sky": {"exposure": -0.4, "blue_lum": -0.3}},
    "Contrast comes from a steep curve plus clarity; blacks are deliberately clipped.")

add("street_bw_trix", "Street – Black & White (Tri-X)", "Street",
    "Classic photojournalism monochrome: rich blacks, luminous highlights, punchy mid-tone contrast and Tri-X style grain.",
    ["street black and white", "street bw", "tri-x", "trix", "photojournalism bw", "bw street", "monochrome street",
     "black and white street", "b&w street", "noir street"],
    {"tone": {"contrast": 1.3, "highlights": -15, "shadows": 8, "blacks": -10, "toe": 0.3, "shoulder": 0.6},
     "presence": {"clarity": 28, "texture": 18, "micro_contrast": 15},
     "color": {"bw": {"amount": 1.0, "mix": bwmix(red=0.25, orange=0.22, yellow=0.12, green=0.0, aqua=-0.1, blue=-0.2),
                      "tone": {"h": 60, "s": 0.04}}},
     "detail": {"sharpen": 0.7},
     "effects": {"grain": {"amount": 0.55, "size": 1.2, "roughness": 0.6}, "vignette": {"amount": 0.28}}},
    T(0.46, 0.008, 0.95, preserve_key=0.35, lift_shadows=False),
    {"sky": {"exposure": -0.3, "blue_lum": -0.3}},
    "Tri-X is a mid-contrast, red-sensitive pan film pushed for grit; the mix darkens blue skies a little.")

add("street_bw_extreme", "Street – Ultra-Grain Black & White", "Street",
    "Provoke-era 'are-bure-boke': extreme contrast, blown highlights, huge grain, raw and emotional.",
    ["moriyama", "provoke", "are bure boke", "extreme", "ultra grain", "grainy black and white", "very grainy", "raw bw",
     "high contrast black and white", "daido"],
    {"tone": {"contrast": 1.65, "highlights": 10, "whites": 25, "blacks": -30, "toe": 0.1, "shoulder": 0.9},
     "presence": {"clarity": 45, "texture": 30},
     "color": {"bw": {"amount": 1.0, "mix": bwmix(red=0.3, orange=0.25, yellow=0.15, blue=-0.25)}},
     "detail": {"sharpen": 0.5},
     "effects": {"grain": {"amount": 0.95, "size": 1.8, "roughness": 0.75}, "vignette": {"amount": 0.2}}},
    T(0.5, 0.0, 0.99, preserve_key=0.4, max_clip=0.05, lift_shadows=False),
    {"nr": 0.0},
    "Pushed and over-developed look: let the highlights burn and the blacks fill in.")

add("street_neon_night", "Street – Neon Night (Cinestill)", "Street",
    "After-dark city: halated neon, teal shadows, warm-magenta lights, soft film glow.",
    ["neon", "night street", "cyberpunk", "cinestill", "tokyo night", "rainy night", "blade runner", "night city", "urban night"],
    {"tone": {"contrast": 1.14, "highlights": -35, "shadows": 15, "blacks": -6, "fade": 0.012},
     "presence": {"clarity": 10, "texture": 8},
     "color": {"vibrance": 18, "saturation": 4,
               "grade": {"shadows": zone(205, 0.5), "mids": zone(300, 0.12), "highlights": zone(20, 0.38), "blend": 0.6},
               "hsl": hsl(blue=(-0.15, 0.1, 0), magenta=(0, 0.15, 0), aqua=(0, 0.1, 0))},
     "detail": {"sharpen": 0.5, "nr_luma": 0.2},
     "effects": {"halation": {"amount": 0.55, "radius": 0.012, "threshold": 0.8, "hue": 22},
                 "glow": {"amount": 0.15, "radius": 0.02},
                 "grain": {"amount": 0.32, "size": 1.25, "roughness": 0.5}, "vignette": {"amount": 0.25}}},
    T(0.38, 0.01, 0.96, preserve_key=0.65, lift_shadows=False),
    {"nr": 1.3},
    "Night street is graded for mood, not exposure: protect the lights, keep the dark, split-tone teal/orange.")

add("street_muted_urban", "Street – Muted Urban (Classic Chrome)", "Street",
    "Fuji Classic-Chrome-like: subdued colour, hard shadow contrast, cool teal blues and a quiet, editorial mood.",
    ["classic chrome", "muted", "editorial", "subdued", "desaturated", "quiet", "fuji street", "washed", "cinematic street"],
    {"tone": {"contrast": 1.22, "highlights": -22, "shadows": 5, "toe": 0.3, "fade": 0.008},
     "presence": {"clarity": 14, "texture": 10},
     "color": {"saturation": -20, "vibrance": 6,
               "grade": {"shadows": zone(250, 0.22), "highlights": zone(95, 0.18)},
               "hsl": hsl(blue=(-0.2, -0.15, -0.1), red=(0.04, -0.15, 0), green=(-0.15, -0.3, 0), yellow=(0, -0.2, 0))},
     "detail": {"sharpen": 0.6},
     "effects": {"grain": {"amount": 0.28, "size": 1.0}, "vignette": {"amount": 0.12}}},
    T(0.47, 0.015, 0.95, preserve_key=0.4, lift_shadows=False),
    {}, "Classic Chrome: low saturation, strong contrast, blues pushed toward teal.")

# ======================================================================= ARCHITECTURE
_ARCH_COMMON = {"geometry": {"auto_upright": 1.0}, "detail": {"sharpen": 0.75, "defringe": 0.7}}

add("arch_clean", "Architecture – Clean & Accurate", "Architecture",
    "Straight verticals, neutral colour, controlled highlights, crisp micro-contrast and deep clean skies: the magazine standard.",
    ["architecture", "architectural", "building", "buildings", "clean", "accurate", "exterior", "facade", "modern",
     "straight lines", "commercial architecture", "neutral architecture", "cityscape"],
    {**_ARCH_COMMON,
     "wb": {"auto": 0.7},
     "tone": {"contrast": 1.14, "highlights": -38, "shadows": 30, "whites": 6, "blacks": -10},
     "presence": {"clarity": 20, "texture": 14, "micro_contrast": 22, "dehaze": 10},
     "color": {"vibrance": 8, "saturation": -4,
               "hsl": hsl(blue=(0, 0.05, -0.15), orange=(0, -0.08, 0), yellow=(0, -0.1, 0))},
     "local": {"sky": {"exposure": -0.3, "blue_lum": -0.25, "saturation": 0.1}}},
    T(0.55, 0.015, 0.96, preserve_key=0.15),
    {"nr": 1.0, "sky": True},
    "Architectural pros correct perspective first, neutralise WB, pull windows/sky back and add micro-contrast for texture.")

add("arch_interior", "Architecture – Bright Interior / Real Estate", "Architecture",
    "Airy, evenly lit interiors: neutral whites, lifted shadows, tamed windows and warm bulbs, verticals straightened.",
    ["interior", "real estate", "property", "room", "home", "airy interior", "bright interior", "hdr", "listing", "hotel", "kitchen"],
    {**_ARCH_COMMON,
     "wb": {"auto": 0.9},
     "tone": {"contrast": 1.05, "highlights": -50, "shadows": 55, "whites": 18, "blacks": -6},
     "presence": {"clarity": 12, "texture": 8, "micro_contrast": 14},
     "color": {"vibrance": 10, "saturation": -3,
               "hsl": hsl(orange=(0, -0.12, 0.04), yellow=(0, -0.2, 0.04), red=(0, -0.06, 0))},
     "detail": {"sharpen": 0.7, "defringe": 0.6}},
    T(0.64, 0.03, 0.97, preserve_key=0.1),
    {"nr": 1.1},
    "Interiors are balanced toward even light: heavy shadow lift, window pull-down, and tungsten saturation reduced.")

add("arch_dramatic", "Architecture – Dramatic Fine Art", "Architecture",
    "Moody, graphic and sculptural: deep contrast, darkened sky, steely cool shadows, strong vignette.",
    ["dramatic architecture", "fine art architecture", "moody architecture", "sculptural", "graphic", "brutalist", "dark architecture"],
    {**_ARCH_COMMON,
     "wb": {"auto": 0.4},
     "tone": {"contrast": 1.32, "highlights": -30, "shadows": 0, "blacks": -14, "toe": 0.3},
     "presence": {"clarity": 34, "texture": 22, "micro_contrast": 24, "dehaze": 16},
     "color": {"saturation": -20, "vibrance": 4,
               "grade": {"shadows": zone(235, 0.3), "highlights": zone(75, 0.12)},
               "hsl": hsl(blue=(0, 0.1, -0.25))},
     "local": {"sky": {"exposure": -0.6, "blue_lum": -0.4}, "gradient_top": {"exposure": -0.3}},
     "effects": {"vignette": {"amount": 0.3}, "grain": {"amount": 0.12}}},
    T(0.42, 0.008, 0.95, preserve_key=0.3, lift_shadows=False),
    {"sky": True}, "Darker key, steeper curve and a burned-down sky give architecture a graphic, cinematic weight.")

add("arch_bw", "Architecture – Fine-Art Black & White", "Architecture",
    "Crisp monochrome with sculpted tones: dark dramatic skies, luminous concrete and glass, selenium-cool tone.",
    ["architecture black and white", "architectural bw", "fine art bw", "bw architecture", "monochrome architecture", "black and white building"],
    {**_ARCH_COMMON,
     "tone": {"contrast": 1.34, "highlights": -28, "shadows": 18, "blacks": -10, "toe": 0.35},
     "presence": {"clarity": 32, "texture": 18, "micro_contrast": 26, "dehaze": 14},
     "color": {"bw": {"amount": 1.0, "mix": bwmix(red=0.5, orange=0.4, yellow=0.2, green=0.05, aqua=-0.3, blue=-0.55),
                      "tone": {"h": 250, "s": 0.12}}},
     "local": {"sky": {"exposure": -0.35}},
     "effects": {"grain": {"amount": 0.1, "size": 0.8}, "vignette": {"amount": 0.16}}},
    T(0.46, 0.008, 0.96, preserve_key=0.3, lift_shadows=False),
    {"sky": True}, "Red/orange filtration darkens sky, a cool selenium tint gives a gallery-print feel.")

add("arch_minimal", "Architecture – Minimal High-Key", "Architecture",
    "Bright, quiet, desaturated minimalism: pale shadows, soft contrast, clean whites.",
    ["minimal", "minimalist", "high key architecture", "white", "pale", "scandinavian", "quiet architecture"],
    {**_ARCH_COMMON,
     "wb": {"auto": 0.8},
     "tone": {"contrast": 1.0, "highlights": -10, "shadows": 40, "whites": 18, "fade": 0.02},
     "presence": {"clarity": 10, "micro_contrast": 10},
     "color": {"saturation": -32, "vibrance": -4, "grade": {"shadows": zone(235, 0.12)}},
     "effects": {"grain": {"amount": 0.05}}},
    T(0.68, 0.04, 0.98, preserve_key=0.1, auto_black=False),
    {}, "High-key minimalism relies on lifted exposure, low saturation and almost no vignette.")

# ======================================================================= LANDSCAPE
add("land_natural", "Landscape – Natural Pro", "Landscape",
    "Rich yet believable scenery: recovered skies, open shadows, dehazed distance, lush greens and clean blues.",
    ["landscape", "nature", "scenery", "outdoor", "mountains", "forest", "natural landscape", "hiking", "national park", "scenic"],
    {"geometry": {"auto_horizon": 1.0},
     "wb": {"auto": 0.12},
     "tone": {"contrast": 1.16, "highlights": -45, "shadows": 35, "blacks": -6, "whites": 6},
     "presence": {"clarity": 22, "texture": 16, "dehaze": 14, "micro_contrast": 10},
     "color": {"vibrance": 26, "saturation": 4,
               "hsl": hsl(green=(-0.12, 0.05, -0.04), yellow=(-0.05, 0.05, 0), blue=(0, 0.12, -0.12), aqua=(0, 0.05, -0.05))},
     "local": {"sky": {"exposure": -0.35, "saturation": 0.15, "blue_lum": -0.25}, "gradient_top": {"exposure": -0.25}},
     "detail": {"sharpen": 0.7, "defringe": 0.6}},
    T(0.52, 0.015, 0.96, preserve_key=0.25), {"sky": True},
    "Landscape pros level the horizon, darken skies with graduated filters, dehaze and push vibrance not saturation.")

add("land_golden", "Landscape – Golden Hour Glow", "Landscape",
    "Warm low sun: amber highlights, cool blue shadows, soft glow, saturated but luminous.",
    ["golden hour", "sunset", "sunrise", "warm landscape", "glow", "magic hour", "amber", "warm light", "dusk"],
    {"geometry": {"auto_horizon": 1.0},
     "wb": {"mired": 12},
     "tone": {"contrast": 1.2, "highlights": -42, "shadows": 30, "blacks": -4},
     "presence": {"clarity": 16, "texture": 12, "dehaze": 8},
     "color": {"vibrance": 28, "saturation": 6,
               "grade": {"shadows": zone(255, 0.3), "highlights": zone(72, 0.45), "balance": 0.1},
               "hsl": hsl(orange=(0, 0.12, 0.05), yellow=(-0.05, 0.1, 0.03), blue=(0, 0.1, -0.1), green=(-0.15, -0.05, 0))},
     "local": {"sky": {"exposure": -0.25, "saturation": 0.1, "warmth": 0.3}},
     "effects": {"glow": {"amount": 0.2, "radius": 0.025}, "vignette": {"amount": 0.15}, "grain": {"amount": 0.05}}},
    T(0.5, 0.015, 0.96, preserve_key=0.35), {"sky": True},
    "Golden-hour grading splits cool shadows from amber highlights and adds a soft Orton-style glow.")

add("land_moody", "Landscape – Moody Muted Earth", "Landscape",
    "Overcast, brooding scenery: muted olive greens, teal shadows, matte blacks, soft vignette.",
    ["moody landscape", "moody", "misty", "fog", "foggy", "overcast", "scottish", "highlands", "brooding", "dark and moody landscape", "earthy"],
    {"tone": {"contrast": 1.2, "highlights": -30, "shadows": 20, "fade": 0.03},
     "presence": {"clarity": 16, "dehaze": 6},
     "color": {"saturation": -26, "vibrance": 6,
               "grade": {"shadows": zone(195, 0.3), "highlights": zone(85, 0.14)},
               "hsl": hsl(green=(-0.25, -0.2, -0.08), yellow=(-0.1, -0.15, -0.05), blue=(-0.1, -0.1, -0.1))},
     "effects": {"vignette": {"amount": 0.32}, "grain": {"amount": 0.15}}},
    T(0.4, 0.02, 0.95, preserve_key=0.4, auto_black=False), {"sky": True},
    "Desaturate, shift greens toward olive, tint shadows teal, matte the blacks.")

add("land_vivid", "Travel – Vivid & Punchy", "Landscape",
    "Postcard colour: saturated skies and foliage, strong contrast, crisp detail, Instagram-ready pop.",
    ["vivid", "travel", "punchy color", "colourful", "colorful", "vibrant", "saturated", "pop", "postcard", "holiday", "tropical"],
    {"tone": {"contrast": 1.24, "highlights": -40, "shadows": 30, "whites": 8},
     "presence": {"clarity": 28, "texture": 20, "dehaze": 16, "micro_contrast": 12},
     "color": {"vibrance": 38, "saturation": 12,
               "hsl": hsl(blue=(0, 0.15, -0.14), aqua=(0, 0.15, -0.05), green=(-0.1, 0.1, 0), orange=(0, 0.06, 0.03))},
     "local": {"sky": {"exposure": -0.3, "saturation": 0.2, "blue_lum": -0.3}},
     "detail": {"sharpen": 0.8}},
    T(0.54, 0.015, 0.96), {"sky": True}, "Vibrance first (protects skin), then targeted HSL on blues and greens.")

# ======================================================================= PORTRAIT
add("portrait_natural", "Portrait – Natural Skin", "Portrait",
    "Flattering and true: smooth but textured skin, protected skin hue, gentle contrast, subject brightened.",
    ["portrait", "people", "headshot", "natural portrait", "skin", "family", "face", "model", "lifestyle"],
    {"wb": {"auto": 0.25},
     "tone": {"contrast": 1.06, "highlights": -22, "shadows": 16},
     "presence": {"clarity": -4, "texture": -6},
     "color": {"vibrance": 8, "skin_protect": 1.0,
               "hsl": hsl(orange=(0, -0.04, 0.07), red=(0, -0.08, 0.03), green=(0, -0.2, 0), yellow=(0, -0.1, 0))},
     "local": {"subject": {"exposure": 0.2}, "skin_smooth": 0.4},
     "detail": {"sharpen": 0.45, "nr_luma": 0.1},
     "effects": {"vignette": {"amount": 0.14}}},
    T(0.58, 0.02, 0.96, preserve_key=0.2), {"nr": 1.2, "faces": True},
    "Portraits favour smooth tones: negative texture/clarity, skin hue protected, eyes/face dodged.")

add("portrait_warm_film", "Portrait – Warm Pastel Film (Portra)", "Portrait",
    "Kodak Portra 400 feel: creamy pastel skin, soft contrast, gentle shadow lift, olive greens, fine grain.",
    ["portra", "kodak portra", "pastel", "creamy", "soft film", "wedding film", "film portrait", "warm film", "peach"],
    {"wb": {"mired": 7},
     "tone": {"contrast": 0.98, "highlights": -20, "shadows": 22, "toe": 0.75, "shoulder": 0.75, "fade": 0.015,
              "chroma_follow": 0.4},
     "presence": {"clarity": -4, "texture": -4},
     "color": {"saturation": -6, "vibrance": 10, "skin_protect": 1.0,
               "grade": {"shadows": zone(175, 0.14), "highlights": zone(72, 0.2)},
               "hsl": hsl(green=(-0.2, -0.18, 0.04), blue=(0.05, -0.15, 0), orange=(0, 0, 0.05), red=(0.05, -0.05, 0.02))},
     "local": {"skin_smooth": 0.25},
     "effects": {"grain": {"amount": 0.28, "size": 1.0, "roughness": 0.4}, "halation": {"amount": 0.07}}},
    T(0.58, 0.03, 0.96, preserve_key=0.2, auto_black=False), {"faces": True},
    "Portra: wide latitude, soft shoulder, warm skin, slightly yellow-green foliage.")

add("portrait_moody", "Portrait – Dark & Moody", "Portrait",
    "Low-key, painterly: deep shadows, glowing skin, desaturated surroundings, strong vignette.",
    ["dark portrait", "moody portrait", "low key portrait", "brooding", "chiaroscuro", "rembrandt", "dramatic portrait", "dark and moody"],
    {"tone": {"contrast": 1.24, "highlights": -20, "shadows": -8, "blacks": -10, "fade": 0.012},
     "presence": {"clarity": 6, "texture": -4},
     "color": {"saturation": -18, "skin_protect": 1.0,
               "grade": {"shadows": zone(200, 0.22), "highlights": zone(60, 0.2)},
               "hsl": hsl(orange=(0, 0.06, 0.05), green=(-0.1, -0.35, -0.05), blue=(0, -0.2, -0.1))},
     "local": {"subject": {"exposure": 0.3}, "skin_smooth": 0.25},
     "effects": {"vignette": {"amount": 0.48}, "grain": {"amount": 0.2}}},
    T(0.36, 0.01, 0.95, preserve_key=0.5, lift_shadows=False), {"faces": True},
    "Dark/moody portraits bring the key down but keep the face luminous with a local dodge.")

add("portrait_airy", "Portrait – Light & Airy", "Portrait",
    "Bright, soft, optimistic: lifted shadows, low contrast, pastel colour, warm creamy highlights.",
    ["light and airy", "bright portrait", "airy", "wedding", "bridal", "soft and bright", "newborn", "bright and airy", "high key portrait"],
    {"wb": {"mired": 6},
     "tone": {"contrast": 0.92, "highlights": -20, "shadows": 38, "whites": 10, "fade": 0.04, "toe": 0.8},
     "presence": {"clarity": -8, "texture": -6},
     "color": {"saturation": -12, "vibrance": 6, "skin_protect": 1.0,
               "grade": {"highlights": zone(65, 0.15)},
               "hsl": hsl(green=(-0.1, -0.35, 0.1), blue=(0, -0.25, 0.08), orange=(0, -0.03, 0.08))},
     "local": {"skin_smooth": 0.4},
     "effects": {"grain": {"amount": 0.08}, "glow": {"amount": 0.1, "radius": 0.02}}},
    T(0.68, 0.045, 0.98, preserve_key=0.1, auto_black=False), {"faces": True},
    "Light & airy: expose bright, flatten contrast, mute greens/blues so skin glows.")

add("portrait_bw", "Portrait – Black & White", "Portrait",
    "Timeless monochrome portraiture: soft-contrast skin tones, glowing highlights, subtle grain.",
    ["portrait black and white", "bw portrait", "monochrome portrait", "black and white portrait", "classic portrait bw"],
    {"tone": {"contrast": 1.16, "highlights": -18, "shadows": 12, "blacks": -6},
     "presence": {"clarity": 8, "texture": -2},
     "color": {"bw": {"amount": 1.0, "mix": bwmix(red=0.35, orange=0.3, yellow=0.12, blue=-0.2),
                      "tone": {"h": 60, "s": 0.04}}},
     "local": {"skin_smooth": 0.3, "subject": {"exposure": 0.15}},
     "effects": {"grain": {"amount": 0.28, "size": 1.0}, "vignette": {"amount": 0.2}}},
    T(0.5, 0.012, 0.96, preserve_key=0.25), {"faces": True},
    "Orange/red mix lightens skin and softens blemishes in monochrome.")

# ======================================================================= FILM
add("film_kodachrome", "Film – Kodachrome 64", "Film",
    "Saturated reds and yellows, deep blues, punchy contrast and a warm 1970s National-Geographic glow.",
    ["kodachrome", "70s", "national geographic", "slide film", "vintage color", "retro color", "warm vintage"],
    {"wb": {"mired": 8},
     "tone": {"contrast": 1.28, "highlights": -28, "shadows": 12, "blacks": -8, "chroma_follow": 0.45},
     "presence": {"clarity": 12},
     "color": {"saturation": 4, "vibrance": 14,
               "grade": {"shadows": zone(240, 0.18), "highlights": zone(70, 0.22)},
               "hsl": hsl(red=(-0.04, 0.22, -0.02), orange=(0, 0.06, 0), yellow=(-0.05, 0.16, 0), green=(-0.2, -0.1, -0.05),
                          blue=(-0.05, 0.12, -0.18), aqua=(0, -0.05, 0))},
     "effects": {"grain": {"amount": 0.32, "size": 1.0, "roughness": 0.5}, "vignette": {"amount": 0.2}}},
    T(0.5, 0.012, 0.95, preserve_key=0.3), {},
    "Kodachrome: strong reds/yellows, cyan-leaning blues, olive greens, high contrast.")

add("film_velvia", "Film – Fuji Velvia", "Film",
    "Landscape slide film: intense saturation, rich greens and magentas, high contrast, ultra-fine grain.",
    ["velvia", "fuji velvia", "slide", "intense", "super saturated", "fuji film"],
    {"tone": {"contrast": 1.34, "highlights": -35, "shadows": 18, "blacks": -10, "chroma_follow": 0.4},
     "presence": {"clarity": 14, "dehaze": 6},
     "color": {"saturation": 18, "vibrance": 14,
               "hsl": hsl(green=(0.04, 0.22, -0.06), blue=(0, 0.2, -0.2), red=(0, 0.2, 0), magenta=(0, 0.15, 0), yellow=(0, 0.1, 0))},
     "effects": {"grain": {"amount": 0.1, "size": 0.8}}},
    T(0.5, 0.01, 0.95, preserve_key=0.3), {"sky": True},
    "Velvia = contrast + saturation, with blues darkened and greens made emerald.")

add("film_ektar", "Film – Kodak Ektar 100", "Film",
    "Vivid but clean colour negative: fine grain, strong reds, punchy contrast, crisp.",
    ["ektar", "kodak ektar", "fine grain color", "vivid film", "crisp film"],
    {"wb": {"mired": 3},
     "tone": {"contrast": 1.2, "highlights": -28, "shadows": 15, "blacks": -6},
     "presence": {"clarity": 10},
     "color": {"saturation": 8, "vibrance": 14,
               "hsl": hsl(red=(0, 0.16, 0), orange=(0, 0.06, 0.02), blue=(0, 0.1, -0.1), green=(-0.1, 0.0, 0))},
     "effects": {"grain": {"amount": 0.12, "size": 0.85}}},
    T(0.52, 0.012, 0.95, preserve_key=0.3), {}, "Ektar: ultra-fine grain, saturated reds, clean highlights.")

add("film_cinestill", "Film – CineStill 800T", "Film",
    "Tungsten cinema stock: teal shadows, orange-red halation around lights, soft contrast, visible grain.",
    ["cinestill 800t", "800t", "tungsten film", "halation", "cine film", "film night", "red halation"],
    {"tone": {"contrast": 1.1, "highlights": -30, "shadows": 20, "fade": 0.02, "toe": 0.6},
     "color": {"saturation": 2, "vibrance": 10,
               "grade": {"shadows": zone(200, 0.4), "highlights": zone(35, 0.3), "mids": zone(180, 0.08)},
               "hsl": hsl(blue=(-0.1, 0.0, 0), orange=(0, 0.05, 0))},
     "effects": {"halation": {"amount": 0.7, "radius": 0.014, "threshold": 0.78, "hue": 25},
                 "grain": {"amount": 0.45, "size": 1.3, "roughness": 0.55}, "vignette": {"amount": 0.15}}},
    T(0.44, 0.02, 0.96, preserve_key=0.5, auto_black=False), {"nr": 1.1},
    "Removing the remjet layer is what makes lights bleed red; we simulate with threshold-glow tinted red.")

add("film_vintage_fade", "Film – Faded Vintage", "Film",
    "Sun-bleached memory: lifted blacks, warm yellow highlights, green-cyan shadows, soft grain.",
    ["vintage", "faded", "retro", "nostalgic", "old photo", "polaroid", "sun faded", "matte", "analog", "analogue"],
    {"wb": {"mired": 8},
     "tone": {"contrast": 0.98, "highlights": -18, "shadows": 22, "fade": 0.075, "toe": 0.8, "chroma_follow": 0.4},
     "color": {"saturation": -14, "vibrance": 8,
               "grade": {"shadows": zone(180, 0.28), "highlights": zone(95, 0.35), "mids": zone(60, 0.08)},
               "hsl": hsl(blue=(0.05, -0.2, 0), green=(-0.15, -0.15, 0), red=(0.05, -0.1, 0))},
     "effects": {"grain": {"amount": 0.42, "size": 1.2, "roughness": 0.55}, "vignette": {"amount": 0.3},
                 "halation": {"amount": 0.12}}},
    T(0.54, 0.05, 0.96, preserve_key=0.35, auto_black=False), {}, "Matte blacks and split-tone give the faded print feel.")

# ======================================================================= B&W
add("bw_hp5", "B&W – Ilford HP5 (balanced)", "Black & White",
    "Versatile, softer-contrast monochrome with full tonal range and moderate grain.",
    ["hp5", "ilford", "balanced black and white", "soft black and white", "black and white", "bw", "b&w", "monochrome", "mono"],
    {"tone": {"contrast": 1.18, "highlights": -22, "shadows": 18, "blacks": -6},
     "presence": {"clarity": 14, "texture": 8},
     "color": {"bw": {"amount": 1.0, "mix": bwmix(red=0.18, orange=0.15, yellow=0.08, blue=-0.1)}},
     "detail": {"sharpen": 0.6},
     "effects": {"grain": {"amount": 0.3, "size": 1.05}, "vignette": {"amount": 0.15}}},
    T(0.5, 0.012, 0.96, preserve_key=0.25), {"sky": True},
    "General-purpose mono: honest tonal separation without extremes.")

add("bw_delta", "B&W – Fine-Grain Silver (Delta 100)", "Black & White",
    "Smooth, detailed fine-art monochrome: wide tonal scale, minimal grain, crisp.",
    ["delta 100", "fine grain", "silver gelatin", "fine art black and white", "gallery print", "tonal", "zone system"],
    {"tone": {"contrast": 1.22, "highlights": -28, "shadows": 22, "blacks": -8, "whites": 6},
     "presence": {"clarity": 20, "texture": 14, "micro_contrast": 16},
     "color": {"bw": {"amount": 1.0, "mix": bwmix(red=0.3, orange=0.25, yellow=0.12, aqua=-0.1, blue=-0.3),
                      "tone": {"h": 255, "s": 0.06}}},
     "detail": {"sharpen": 0.75},
     "effects": {"grain": {"amount": 0.08, "size": 0.7}, "vignette": {"amount": 0.12}}},
    T(0.5, 0.01, 0.96, preserve_key=0.2), {"sky": True},
    "Zone-system thinking: place blacks and whites precisely, keep texture, mild selenium cool.")

add("bw_high_key", "B&W – High-Key", "Black & White",
    "Bright airy monochrome: luminous whites, soft shadows, low-contrast elegance.",
    ["high key", "bright black and white", "airy black and white", "white background", "fashion bw"],
    {"tone": {"contrast": 1.0, "highlights": -8, "shadows": 40, "whites": 20, "fade": 0.02},
     "presence": {"clarity": 8},
     "color": {"bw": {"amount": 1.0, "mix": bwmix(red=0.25, orange=0.2, yellow=0.1)}},
     "effects": {"grain": {"amount": 0.12}}},
    T(0.7, 0.03, 0.99, preserve_key=0.1, auto_black=False, max_clip=0.03), {}, "Overexpose the key and compress the shadows toward mid-grey.")

add("bw_noir", "B&W – Film Noir / Low-Key", "Black & White",
    "Hard, shadow-dominated cinema noir: deep blacks swallowing the frame, spotlit subject, glowing highlights.",
    ["noir", "film noir", "low key", "dark black and white", "shadowy", "detective", "cinematic black and white", "dramatic black and white"],
    {"tone": {"contrast": 1.5, "highlights": -10, "shadows": -12, "blacks": -22, "toe": 0.1, "shoulder": 0.8},
     "presence": {"clarity": 30, "texture": 14},
     "color": {"bw": {"amount": 1.0, "mix": bwmix(red=0.4, orange=0.3, yellow=0.2, blue=-0.4)}},
     "local": {"subject": {"exposure": 0.35}},
     "effects": {"vignette": {"amount": 0.55}, "grain": {"amount": 0.38, "size": 1.1}, "glow": {"amount": 0.12}}},
    T(0.3, 0.0, 0.96, preserve_key=0.55, lift_shadows=False, max_clip=0.02), {},
    "Low-key: underexpose on purpose, steep curve, spotlight the subject.")

# ======================================================================= CINEMATIC
add("cine_teal_orange", "Cinematic – Teal & Orange", "Cinematic",
    "Blockbuster grade: teal shadows against warm skin and highlights, contrasty, slight bloom.",
    ["cinematic", "teal and orange", "teal orange", "movie", "film look", "hollywood", "blockbuster", "cine"],
    {"tone": {"contrast": 1.2, "highlights": -28, "shadows": 12, "blacks": -4, "fade": 0.018},
     "presence": {"clarity": 14, "texture": 6},
     "color": {"saturation": -4, "vibrance": 10, "skin_protect": 0.8,
               "grade": {"shadows": zone(198, 0.5), "mids": zone(190, 0.1), "highlights": zone(58, 0.45), "blend": 0.55},
               "hsl": hsl(blue=(-0.28, -0.1, -0.1), green=(-0.2, -0.35, -0.06), orange=(0, 0.1, 0.02), yellow=(0, -0.2, 0))},
     "effects": {"vignette": {"amount": 0.3}, "halation": {"amount": 0.12}, "glow": {"amount": 0.08}, "grain": {"amount": 0.15}}},
    T(0.46, 0.02, 0.95, preserve_key=0.4, auto_black=False), {"faces": True},
    "Blues are pulled toward teal, greens muted, orange kept for skin – complementary colour contrast.")

add("cine_bleach", "Cinematic – Bleach Bypass", "Cinematic",
    "Gritty war-film desaturation: silvery highlights, crushed contrast, hard texture.",
    ["bleach bypass", "saving private ryan", "silver", "war", "desaturated cinematic", "metallic", "harsh cinematic"],
    {"tone": {"contrast": 1.38, "highlights": -20, "shadows": 5, "blacks": -14, "highlight_desat": 0.2},
     "presence": {"clarity": 34, "texture": 22, "micro_contrast": 14},
     "color": {"saturation": -42, "vibrance": -4,
               "grade": {"shadows": zone(220, 0.15), "highlights": zone(85, 0.1)}},
     "effects": {"grain": {"amount": 0.38, "size": 1.1}, "vignette": {"amount": 0.28}}},
    T(0.44, 0.005, 0.95, preserve_key=0.4, lift_shadows=False), {},
    "Retained silver halves colour saturation and doubles contrast.")

# ======================================================================= COMMERCIAL
add("product_clean", "Product – Clean Commercial", "Commercial",
    "E-commerce-ready: neutral white balance, bright clean background, even tone, maximum crispness.",
    ["product", "ecommerce", "e-commerce", "catalog", "catalogue", "commercial", "packshot", "studio", "still life", "objects"],
    {"wb": {"auto": 1.0},
     "tone": {"contrast": 1.1, "highlights": -18, "shadows": 25, "whites": 14, "blacks": -6},
     "presence": {"clarity": 12, "micro_contrast": 22, "texture": 10},
     "color": {"vibrance": 6, "saturation": 2},
     "detail": {"sharpen": 0.85, "defringe": 0.6}},
    T(0.62, 0.02, 0.97, preserve_key=0.1, max_clip=0.02), {"nr": 1.1},
    "Neutral whites and dense sharpening, no stylisation.")

add("food_warm", "Food – Warm & Appetising", "Commercial",
    "Inviting warm tones, rich reds/oranges, soft contrast, bright natural look.",
    ["food", "restaurant", "cuisine", "meal", "dish", "appetising", "appetizing", "recipe", "culinary", "drink", "coffee"],
    {"wb": {"mired": 7},
     "tone": {"contrast": 1.12, "highlights": -24, "shadows": 24},
     "presence": {"clarity": 16, "texture": 14},
     "color": {"saturation": 4, "vibrance": 20,
               "hsl": hsl(orange=(0, 0.12, 0.03), red=(0, 0.1, 0), yellow=(0, 0.1, 0.02), green=(-0.1, -0.05, 0))},
     "effects": {"vignette": {"amount": 0.16}}},
    T(0.56, 0.02, 0.96, preserve_key=0.2), {}, "Warm, saturated reds/oranges and gentle vignette draw the eye in.")

add("night_city", "Night – Clean Cityscape", "Night",
    "Balanced night skylines: tamed lights, clean shadows, rich colour, low noise.",
    ["night", "night photography", "skyline", "blue hour", "long exposure night", "city lights", "after dark", "astro", "evening"],
    {"geometry": {"auto_upright": 0.6},
     "tone": {"contrast": 1.15, "highlights": -45, "shadows": 25, "blacks": -6},
     "presence": {"clarity": 12, "dehaze": 4},
     "color": {"vibrance": 16, "saturation": 2,
               "grade": {"shadows": zone(240, 0.3), "highlights": zone(70, 0.15)}},
     "detail": {"nr_luma": 0.3, "sharpen": 0.55},
     "effects": {"halation": {"amount": 0.2, "threshold": 0.85}, "vignette": {"amount": 0.15}}},
    T(0.36, 0.01, 0.95, preserve_key=0.7, lift_shadows=False), {"nr": 1.4},
    "Night images keep their darkness; the work is noise control and light-source management.")

DEFAULT_STYLE = "natural"
_BY_ID = {s.id: s for s in STYLES}


def get(style_id: str) -> Style:
    try:
        return _BY_ID[style_id]
    except KeyError:
        raise KeyError(f"unknown style '{style_id}'. Try one of: {', '.join(_BY_ID)}") from None


def catalog() -> list[dict]:
    return [{"id": s.id, "name": s.name, "category": s.category, "description": s.description,
             "bw": s.is_bw} for s in STYLES]


# --------------------------------------------------------------------------
# free-text -> style (+ modifiers)
# --------------------------------------------------------------------------
_MOD_WORDS = [
    (("dark", "darker", "moody", "low key", "underexposed"), {"brightness": -0.4}),
    (("bright", "brighter", "airy", "light"), {"brightness": 0.4}),
    (("contrast", "contrasty", "punchy", "harsh", "hard", "gritty"), {"contrast": 0.4}),
    (("soft", "flat", "low contrast", "gentle"), {"contrast": -0.4}),
    (("warm", "warmer", "golden", "sunny"), {"warmth": 0.5}),
    (("cool", "cooler", "cold", "blue", "icy"), {"warmth": -0.5}),
    (("vivid", "saturated", "colourful", "colorful", "vibrant"), {"saturation": 0.4}),
    (("muted", "desaturated", "subdued", "pastel", "faded"), {"saturation": -0.4}),
    (("grain", "grainy", "gritty", "film"), {"grain": 0.5}),
    (("matte", "faded", "washed"), {"fade": 0.6}),
    (("vignette", "vignetted"), {"vignette": 0.5}),
    (("sharp", "crisp", "detailed", "clarity"), {"clarity": 0.4}),
]


def match(text: str) -> tuple[Style, dict, list]:
    """Pick the best style (and slider modifiers) for a free-text description."""
    t = " " + " ".join(text.lower().replace("&", " and ").replace("-", " ").replace(",", " ").split()) + " "
    best, best_score = None, 0.0
    scores = []
    for s in STYLES:
        score = 0.0
        for kw in s.keywords + [s.name.lower(), s.category.lower()]:
            k = kw.lower().replace("&", "and").replace("–", " ").replace("-", " ")
            if f" {k} " in t:
                score += 1.0 + 0.5 * len(k.split())
            elif len(k) > 4 and k in t:
                score += 0.5
        cat_word = s.category.lower().split()[0]
        cat_hit = cat_word not in ("black", "everyday") and f" {cat_word} " in t
        if cat_hit:
            score += 2.5
        if " black and white " in t or " bw " in t or " monochrome " in t or " b and w " in t or " mono " in t:
            score += (2.0 + (2.0 if cat_hit else 0.0)) if s.is_bw else -1.5
        elif s.is_bw:
            score -= 0.5
        scores.append((score, s))
        if score > best_score:
            best, best_score = s, score
    if best is None:
        best = _BY_ID[DEFAULT_STYLE]
    mods: dict = {}
    for words, m in _MOD_WORDS:
        if any(f" {w} " in t for w in words):
            for k, v in m.items():
                mods[k] = mods.get(k, 0) + v
    mods = {k: max(-1.0, min(1.0, v)) for k, v in mods.items()}
    ranked = [s.id for sc, s in sorted(scores, key=lambda x: -x[0])[:3] if sc > 0]
    return best, mods, ranked
