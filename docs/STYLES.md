# Style library

Every look is a *recipe* (what to change) plus *targets* (where the histogram should land) and *adaptive hints* (what the director should detect and react to). The professional reasoning for each is below. Run `darkroom styles` for the same list in a terminal.


## Everyday

### Natural – Pro Develop  
`natural`

What a careful editor does before any 'look': accurate colour, protected highlights, open shadows, gentle contrast and crisp detail.

*Why:* Expose for the highlights, lift shadows, remove cast, add local contrast and sharpen once.

*Targets:* median lightness 0.54, black 0.02, highlights 0.96  
*Keywords:* natural, clean, neutral, realistic, accurate, basic, default, true to life


## Street

### Street – Classic Documentary  
`street_classic`

Honest, contrasty reportage: deep blacks, a touch less colour, grit in the mid-tones, cool shadows and warm lights like a Leica-era colour print.

*Why:* Street work keeps the scene's mood: little WB correction, protected blacks, local contrast over global lift.

*Targets:* median lightness 0.48, black 0.012, highlights 0.95, preserves 40% of the original key  
*Keywords:* street, documentary, reportage, urban, classic street, candid, leica, photojournalism

### Street – Gritty High Contrast  
`street_gritty`

Hard, punchy city look: crushed blacks, bite in every texture, desaturated colour, heavy grain.

*Why:* Contrast comes from a steep curve plus clarity; blacks are deliberately clipped.

*Targets:* median lightness 0.44, black 0.005, highlights 0.95, preserves 50% of the original key  
*Keywords:* gritty, grit, harsh, hard, punchy, contrasty, raw street, dirty

### Street – Black & White (Tri-X)  
`street_bw_trix`

Classic photojournalism monochrome: rich blacks, luminous highlights, punchy mid-tone contrast and Tri-X style grain.

*Why:* Tri-X is a mid-contrast, red-sensitive pan film pushed for grit; the mix darkens blue skies a little.

*Targets:* median lightness 0.46, black 0.008, highlights 0.95, preserves 35% of the original key  
*Keywords:* street black and white, street bw, tri-x, trix, photojournalism bw, bw street, monochrome street, black and white street

### Street – Ultra-Grain Black & White  
`street_bw_extreme`

Provoke-era 'are-bure-boke': extreme contrast, blown highlights, huge grain, raw and emotional.

*Why:* Pushed and over-developed look: let the highlights burn and the blacks fill in.

*Targets:* median lightness 0.5, black 0.0, highlights 0.99, preserves 40% of the original key  
*Keywords:* moriyama, provoke, are bure boke, extreme, ultra grain, grainy black and white, very grainy, raw bw

### Street – Neon Night (Cinestill)  
`street_neon_night`

After-dark city: halated neon, teal shadows, warm-magenta lights, soft film glow.

*Why:* Night street is graded for mood, not exposure: protect the lights, keep the dark, split-tone teal/orange.

*Targets:* median lightness 0.38, black 0.01, highlights 0.96, preserves 65% of the original key  
*Keywords:* neon, night street, cyberpunk, cinestill, tokyo night, rainy night, blade runner, night city

### Street – Muted Urban (Classic Chrome)  
`street_muted_urban`

Fuji Classic-Chrome-like: subdued colour, hard shadow contrast, cool teal blues and a quiet, editorial mood.

*Why:* Classic Chrome: low saturation, strong contrast, blues pushed toward teal.

*Targets:* median lightness 0.47, black 0.015, highlights 0.95, preserves 40% of the original key  
*Keywords:* classic chrome, muted, editorial, subdued, desaturated, quiet, fuji street, washed


## Architecture

### Architecture – Clean & Accurate  
`arch_clean`

Straight verticals, neutral colour, controlled highlights, crisp micro-contrast and deep clean skies: the magazine standard.

*Why:* Architectural pros correct perspective first, neutralise WB, pull windows/sky back and add micro-contrast for texture.

*Targets:* median lightness 0.55, black 0.015, highlights 0.96, preserves 15% of the original key  
*Keywords:* architecture, architectural, building, buildings, clean, accurate, exterior, facade

### Architecture – Bright Interior / Real Estate  
`arch_interior`

Airy, evenly lit interiors: neutral whites, lifted shadows, tamed windows and warm bulbs, verticals straightened.

*Why:* Interiors are balanced toward even light: heavy shadow lift, window pull-down, and tungsten saturation reduced.

*Targets:* median lightness 0.64, black 0.03, highlights 0.97, preserves 10% of the original key  
*Keywords:* interior, real estate, property, room, home, airy interior, bright interior, hdr

### Architecture – Dramatic Fine Art  
`arch_dramatic`

Moody, graphic and sculptural: deep contrast, darkened sky, steely cool shadows, strong vignette.

*Why:* Darker key, steeper curve and a burned-down sky give architecture a graphic, cinematic weight.

*Targets:* median lightness 0.42, black 0.008, highlights 0.95, preserves 30% of the original key  
*Keywords:* dramatic architecture, fine art architecture, moody architecture, sculptural, graphic, brutalist, dark architecture

### Architecture – Fine-Art Black & White  
`arch_bw`

Crisp monochrome with sculpted tones: dark dramatic skies, luminous concrete and glass, selenium-cool tone.

*Why:* Red/orange filtration darkens sky, a cool selenium tint gives a gallery-print feel.

*Targets:* median lightness 0.46, black 0.008, highlights 0.96, preserves 30% of the original key  
*Keywords:* architecture black and white, architectural bw, fine art bw, bw architecture, monochrome architecture, black and white building

### Architecture – Minimal High-Key  
`arch_minimal`

Bright, quiet, desaturated minimalism: pale shadows, soft contrast, clean whites.

*Why:* High-key minimalism relies on lifted exposure, low saturation and almost no vignette.

*Targets:* median lightness 0.68, black 0.04, highlights 0.98, preserves 10% of the original key  
*Keywords:* minimal, minimalist, high key architecture, white, pale, scandinavian, quiet architecture


## Landscape

### Landscape – Natural Pro  
`land_natural`

Rich yet believable scenery: recovered skies, open shadows, dehazed distance, lush greens and clean blues.

*Why:* Landscape pros level the horizon, darken skies with graduated filters, dehaze and push vibrance not saturation.

*Targets:* median lightness 0.52, black 0.015, highlights 0.96, preserves 25% of the original key  
*Keywords:* landscape, nature, scenery, outdoor, mountains, forest, natural landscape, hiking

### Landscape – Golden Hour Glow  
`land_golden`

Warm low sun: amber highlights, cool blue shadows, soft glow, saturated but luminous.

*Why:* Golden-hour grading splits cool shadows from amber highlights and adds a soft Orton-style glow.

*Targets:* median lightness 0.5, black 0.015, highlights 0.96, preserves 35% of the original key  
*Keywords:* golden hour, sunset, sunrise, warm landscape, glow, magic hour, amber, warm light

### Landscape – Moody Muted Earth  
`land_moody`

Overcast, brooding scenery: muted olive greens, teal shadows, matte blacks, soft vignette.

*Why:* Desaturate, shift greens toward olive, tint shadows teal, matte the blacks.

*Targets:* median lightness 0.4, black 0.02, highlights 0.95, preserves 40% of the original key  
*Keywords:* moody landscape, moody, misty, fog, foggy, overcast, scottish, highlands

### Travel – Vivid & Punchy  
`land_vivid`

Postcard colour: saturated skies and foliage, strong contrast, crisp detail, Instagram-ready pop.

*Why:* Vibrance first (protects skin), then targeted HSL on blues and greens.

*Targets:* median lightness 0.54, black 0.015, highlights 0.96  
*Keywords:* vivid, travel, punchy color, colourful, colorful, vibrant, saturated, pop


## Portrait

### Portrait – Natural Skin  
`portrait_natural`

Flattering and true: smooth but textured skin, protected skin hue, gentle contrast, subject brightened.

*Why:* Portraits favour smooth tones: negative texture/clarity, skin hue protected, eyes/face dodged.

*Targets:* median lightness 0.58, black 0.02, highlights 0.96, preserves 20% of the original key  
*Keywords:* portrait, people, headshot, natural portrait, skin, family, face, model

### Portrait – Warm Pastel Film (Portra)  
`portrait_warm_film`

Kodak Portra 400 feel: creamy pastel skin, soft contrast, gentle shadow lift, olive greens, fine grain.

*Why:* Portra: wide latitude, soft shoulder, warm skin, slightly yellow-green foliage.

*Targets:* median lightness 0.58, black 0.03, highlights 0.96, preserves 20% of the original key  
*Keywords:* portra, kodak portra, pastel, creamy, soft film, wedding film, film portrait, warm film

### Portrait – Dark & Moody  
`portrait_moody`

Low-key, painterly: deep shadows, glowing skin, desaturated surroundings, strong vignette.

*Why:* Dark/moody portraits bring the key down but keep the face luminous with a local dodge.

*Targets:* median lightness 0.36, black 0.01, highlights 0.95, preserves 50% of the original key  
*Keywords:* dark portrait, moody portrait, low key portrait, brooding, chiaroscuro, rembrandt, dramatic portrait, dark and moody

### Portrait – Light & Airy  
`portrait_airy`

Bright, soft, optimistic: lifted shadows, low contrast, pastel colour, warm creamy highlights.

*Why:* Light & airy: expose bright, flatten contrast, mute greens/blues so skin glows.

*Targets:* median lightness 0.68, black 0.045, highlights 0.98, preserves 10% of the original key  
*Keywords:* light and airy, bright portrait, airy, wedding, bridal, soft and bright, newborn, bright and airy

### Portrait – Black & White  
`portrait_bw`

Timeless monochrome portraiture: soft-contrast skin tones, glowing highlights, subtle grain.

*Why:* Orange/red mix lightens skin and softens blemishes in monochrome.

*Targets:* median lightness 0.5, black 0.012, highlights 0.96, preserves 25% of the original key  
*Keywords:* portrait black and white, bw portrait, monochrome portrait, black and white portrait, classic portrait bw


## Film

### Film – Kodachrome 64  
`film_kodachrome`

Saturated reds and yellows, deep blues, punchy contrast and a warm 1970s National-Geographic glow.

*Why:* Kodachrome: strong reds/yellows, cyan-leaning blues, olive greens, high contrast.

*Targets:* median lightness 0.5, black 0.012, highlights 0.95, preserves 30% of the original key  
*Keywords:* kodachrome, 70s, national geographic, slide film, vintage color, retro color, warm vintage

### Film – Fuji Velvia  
`film_velvia`

Landscape slide film: intense saturation, rich greens and magentas, high contrast, ultra-fine grain.

*Why:* Velvia = contrast + saturation, with blues darkened and greens made emerald.

*Targets:* median lightness 0.5, black 0.01, highlights 0.95, preserves 30% of the original key  
*Keywords:* velvia, fuji velvia, slide, intense, super saturated, fuji film

### Film – Kodak Ektar 100  
`film_ektar`

Vivid but clean colour negative: fine grain, strong reds, punchy contrast, crisp.

*Why:* Ektar: ultra-fine grain, saturated reds, clean highlights.

*Targets:* median lightness 0.52, black 0.012, highlights 0.95, preserves 30% of the original key  
*Keywords:* ektar, kodak ektar, fine grain color, vivid film, crisp film

### Film – CineStill 800T  
`film_cinestill`

Tungsten cinema stock: teal shadows, orange-red halation around lights, soft contrast, visible grain.

*Why:* Removing the remjet layer is what makes lights bleed red; we simulate with threshold-glow tinted red.

*Targets:* median lightness 0.44, black 0.02, highlights 0.96, preserves 50% of the original key  
*Keywords:* cinestill 800t, 800t, tungsten film, halation, cine film, film night, red halation

### Film – Faded Vintage  
`film_vintage_fade`

Sun-bleached memory: lifted blacks, warm yellow highlights, green-cyan shadows, soft grain.

*Why:* Matte blacks and split-tone give the faded print feel.

*Targets:* median lightness 0.54, black 0.05, highlights 0.96, preserves 35% of the original key  
*Keywords:* vintage, faded, retro, nostalgic, old photo, polaroid, sun faded, matte


## Black & White

### B&W – Ilford HP5 (balanced)  
`bw_hp5`

Versatile, softer-contrast monochrome with full tonal range and moderate grain.

*Why:* General-purpose mono: honest tonal separation without extremes.

*Targets:* median lightness 0.5, black 0.012, highlights 0.96, preserves 25% of the original key  
*Keywords:* hp5, ilford, balanced black and white, soft black and white, black and white, bw, b&w, monochrome

### B&W – Fine-Grain Silver (Delta 100)  
`bw_delta`

Smooth, detailed fine-art monochrome: wide tonal scale, minimal grain, crisp.

*Why:* Zone-system thinking: place blacks and whites precisely, keep texture, mild selenium cool.

*Targets:* median lightness 0.5, black 0.01, highlights 0.96, preserves 20% of the original key  
*Keywords:* delta 100, fine grain, silver gelatin, fine art black and white, gallery print, tonal, zone system

### B&W – High-Key  
`bw_high_key`

Bright airy monochrome: luminous whites, soft shadows, low-contrast elegance.

*Why:* Overexpose the key and compress the shadows toward mid-grey.

*Targets:* median lightness 0.7, black 0.03, highlights 0.99, preserves 10% of the original key  
*Keywords:* high key, bright black and white, airy black and white, white background, fashion bw

### B&W – Film Noir / Low-Key  
`bw_noir`

Hard, shadow-dominated cinema noir: deep blacks swallowing the frame, spotlit subject, glowing highlights.

*Why:* Low-key: underexpose on purpose, steep curve, spotlight the subject.

*Targets:* median lightness 0.3, black 0.0, highlights 0.96, preserves 55% of the original key  
*Keywords:* noir, film noir, low key, dark black and white, shadowy, detective, cinematic black and white, dramatic black and white


## Cinematic

### Cinematic – Teal & Orange  
`cine_teal_orange`

Blockbuster grade: teal shadows against warm skin and highlights, contrasty, slight bloom.

*Why:* Blues are pulled toward teal, greens muted, orange kept for skin – complementary colour contrast.

*Targets:* median lightness 0.46, black 0.02, highlights 0.95, preserves 40% of the original key  
*Keywords:* cinematic, teal and orange, teal orange, movie, film look, hollywood, blockbuster, cine

### Cinematic – Bleach Bypass  
`cine_bleach`

Gritty war-film desaturation: silvery highlights, crushed contrast, hard texture.

*Why:* Retained silver halves colour saturation and doubles contrast.

*Targets:* median lightness 0.44, black 0.005, highlights 0.95, preserves 40% of the original key  
*Keywords:* bleach bypass, saving private ryan, silver, war, desaturated cinematic, metallic, harsh cinematic


## Commercial

### Product – Clean Commercial  
`product_clean`

E-commerce-ready: neutral white balance, bright clean background, even tone, maximum crispness.

*Why:* Neutral whites and dense sharpening, no stylisation.

*Targets:* median lightness 0.62, black 0.02, highlights 0.97, preserves 10% of the original key  
*Keywords:* product, ecommerce, e-commerce, catalog, catalogue, commercial, packshot, studio

### Food – Warm & Appetising  
`food_warm`

Inviting warm tones, rich reds/oranges, soft contrast, bright natural look.

*Why:* Warm, saturated reds/oranges and gentle vignette draw the eye in.

*Targets:* median lightness 0.56, black 0.02, highlights 0.96, preserves 20% of the original key  
*Keywords:* food, restaurant, cuisine, meal, dish, appetising, appetizing, recipe


## Night

### Night – Clean Cityscape  
`night_city`

Balanced night skylines: tamed lights, clean shadows, rich colour, low noise.

*Why:* Night images keep their darkness; the work is noise control and light-source management.

*Targets:* median lightness 0.36, black 0.01, highlights 0.95, preserves 70% of the original key  
*Keywords:* night, night photography, skyline, blue hour, long exposure night, city lights, after dark, astro
