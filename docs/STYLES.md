# Style library

Every look is a *recipe* (what to change) plus *targets* (where the histogram should land) and *adaptive hints* (what the director should detect and react to). Run `darkroom styles` for the same list in a terminal.

The **Photographers** group is built from research into how well-known photographers worked. Each entry separates what was *documented* in the sources consulted from my *interpretation* of it — web sources on exact editing settings were thin, so these are informed approximations of a look, not reproductions of anyone's actual workflow.


## Everyday

### Natural – Pro Develop  
`natural`

What a careful editor does before any 'look': accurate colour, protected highlights, open shadows, gentle contrast and crisp detail.

*Basis:* Expose for the highlights, lift shadows, remove cast, add local contrast and sharpen once.

*Targets:* median lightness 0.54, black 0.02, highlights 0.96  
*Say:* natural, clean, neutral, realistic, accurate, basic  

## Street

### Street – Classic Documentary  
`street_classic`

Honest, contrasty reportage: deep blacks, a touch less colour, grit in the mid-tones, cool shadows and warm lights like a Leica-era colour print.

*Basis:* Street work keeps the scene's mood: little WB correction, protected blacks, local contrast over global lift.

*Targets:* median lightness 0.48, black 0.012, highlights 0.95, preserves 40% of the original key  
*Say:* street, documentary, reportage, urban, classic street, candid  
### Street – Gritty High Contrast  
`street_gritty`

Hard, punchy city look: crushed blacks, bite in every texture, desaturated colour, heavy grain.

*Basis:* Contrast comes from a steep curve plus clarity; blacks are deliberately clipped.

*Targets:* median lightness 0.44, black 0.005, highlights 0.95, preserves 50% of the original key  
*Say:* gritty, grit, harsh, hard, punchy, contrasty  
### Street – Black & White (Tri-X)  
`street_bw_trix`

Classic photojournalism monochrome: rich blacks, luminous highlights, punchy mid-tone contrast and Tri-X style grain.

*Basis:* Tri-X is a mid-contrast, red-sensitive pan film pushed for grit; the mix darkens blue skies a little.

*Targets:* median lightness 0.46, black 0.008, highlights 0.95, preserves 35% of the original key  
*Say:* street black and white, street bw, tri-x, trix, photojournalism bw, bw street  
### Street – Ultra-Grain Black & White  
`street_bw_extreme`

Provoke-era 'are-bure-boke': extreme contrast, blown highlights, huge grain, raw and emotional.

*Basis:* Pushed and over-developed look: let the highlights burn and the blacks fill in.

*Targets:* median lightness 0.5, black 0.0, highlights 0.99, preserves 40% of the original key  
*Say:* extreme, ultra grain, grainy black and white, very grainy, raw bw, high contrast black and white  
### Street – Neon Night (Cinestill)  
`street_neon_night`

After-dark city: halated neon, teal shadows, warm-magenta lights, soft film glow.

*Basis:* Night street is graded for mood, not exposure: protect the lights, keep the dark, split-tone teal/orange.

*Targets:* median lightness 0.38, black 0.01, highlights 0.96, preserves 65% of the original key  
*Say:* neon, night street, cyberpunk, cinestill, tokyo night, rainy night  
### Street – Muted Urban (Classic Chrome)  
`street_muted_urban`

Fuji Classic-Chrome-like: subdued colour, hard shadow contrast, cool teal blues and a quiet, editorial mood.

*Basis:* Classic Chrome: low saturation, strong contrast, blues pushed toward teal.

*Targets:* median lightness 0.47, black 0.015, highlights 0.95, preserves 40% of the original key  
*Say:* classic chrome, muted, editorial, subdued, desaturated, quiet  

## Architecture

### Architecture – Clean & Accurate  
`arch_clean`

Straight verticals, neutral colour, controlled highlights, crisp micro-contrast and deep clean skies: the magazine standard.

*Basis:* Architectural pros correct perspective first, neutralise WB, pull windows/sky back and add micro-contrast for texture.

*Targets:* median lightness 0.55, black 0.015, highlights 0.96, preserves 15% of the original key  
*Say:* architecture, architectural, building, buildings, clean, accurate  
### Architecture – Bright Interior / Real Estate  
`arch_interior`

Airy, evenly lit interiors: neutral whites, lifted shadows, tamed windows and warm bulbs, verticals straightened.

*Basis:* Interiors are balanced toward even light: heavy shadow lift, window pull-down, and tungsten saturation reduced.

*Targets:* median lightness 0.64, black 0.03, highlights 0.97, preserves 10% of the original key  
*Say:* interior, real estate, property, room, home, airy interior  
### Architecture – Dramatic Fine Art  
`arch_dramatic`

Moody, graphic and sculptural: deep contrast, darkened sky, steely cool shadows, strong vignette.

*Basis:* Darker key, steeper curve and a burned-down sky give architecture a graphic, cinematic weight.

*Targets:* median lightness 0.42, black 0.008, highlights 0.95, preserves 30% of the original key  
*Say:* dramatic architecture, fine art architecture, moody architecture, sculptural, graphic, brutalist  
### Architecture – Fine-Art Black & White  
`arch_bw`

Crisp monochrome with sculpted tones: dark dramatic skies, luminous concrete and glass, selenium-cool tone.

*Basis:* Red/orange filtration darkens sky, a cool selenium tint gives a gallery-print feel.

*Targets:* median lightness 0.46, black 0.008, highlights 0.96, preserves 30% of the original key  
*Say:* architecture black and white, architectural bw, fine art bw, bw architecture, monochrome architecture, black and white building  
### Architecture – Minimal High-Key  
`arch_minimal`

Bright, quiet, desaturated minimalism: pale shadows, soft contrast, clean whites.

*Basis:* High-key minimalism relies on lifted exposure, low saturation and almost no vignette.

*Targets:* median lightness 0.68, black 0.04, highlights 0.98, preserves 10% of the original key  
*Say:* minimal, minimalist, high key architecture, white, pale, scandinavian  

## Landscape

### Landscape – Natural Pro  
`land_natural`

Rich yet believable scenery: recovered skies, open shadows, dehazed distance, lush greens and clean blues.

*Basis:* Landscape pros level the horizon, darken skies with graduated filters, dehaze and push vibrance not saturation.

*Targets:* median lightness 0.52, black 0.015, highlights 0.96, preserves 25% of the original key  
*Say:* landscape, nature, scenery, outdoor, mountains, forest  
### Landscape – Golden Hour Glow  
`land_golden`

Warm low sun: amber highlights, cool blue shadows, soft glow, saturated but luminous.

*Basis:* Golden-hour grading splits cool shadows from amber highlights and adds a soft Orton-style glow.

*Targets:* median lightness 0.5, black 0.015, highlights 0.96, preserves 35% of the original key  
*Say:* golden hour, sunset, sunrise, warm landscape, glow, magic hour  
### Landscape – Moody Muted Earth  
`land_moody`

Overcast, brooding scenery: muted olive greens, teal shadows, matte blacks, soft vignette.

*Basis:* Desaturate, shift greens toward olive, tint shadows teal, matte the blacks.

*Targets:* median lightness 0.4, black 0.02, highlights 0.95, preserves 40% of the original key  
*Say:* moody landscape, moody, misty, fog, foggy, overcast  
### Travel – Vivid & Punchy  
`land_vivid`

Postcard colour: saturated skies and foliage, strong contrast, crisp detail, Instagram-ready pop.

*Basis:* Vibrance first (protects skin), then targeted HSL on blues and greens.

*Targets:* median lightness 0.54, black 0.015, highlights 0.96  
*Say:* vivid, travel, punchy color, colourful, colorful, vibrant  

## Portrait

### Portrait – Natural Skin  
`portrait_natural`

Flattering and true: smooth but textured skin, protected skin hue, gentle contrast, subject brightened.

*Basis:* Portraits favour smooth tones: negative texture/clarity, skin hue protected, eyes/face dodged.

*Targets:* median lightness 0.58, black 0.02, highlights 0.96, preserves 20% of the original key  
*Say:* portrait, people, headshot, natural portrait, skin, family  
### Portrait – Warm Pastel Film (Portra)  
`portrait_warm_film`

Kodak Portra 400 feel: creamy pastel skin, soft contrast, gentle shadow lift, olive greens, fine grain.

*Basis:* Portra: wide latitude, soft shoulder, warm skin, slightly yellow-green foliage.

*Targets:* median lightness 0.58, black 0.03, highlights 0.96, preserves 20% of the original key  
*Say:* portra, kodak portra, pastel, creamy, soft film, wedding film  
### Portrait – Dark & Moody  
`portrait_moody`

Low-key, painterly: deep shadows, glowing skin, desaturated surroundings, strong vignette.

*Basis:* Dark/moody portraits bring the key down but keep the face luminous with a local dodge.

*Targets:* median lightness 0.36, black 0.01, highlights 0.95, preserves 50% of the original key  
*Say:* dark portrait, moody portrait, low key portrait, brooding, chiaroscuro, rembrandt  
### Portrait – Light & Airy  
`portrait_airy`

Bright, soft, optimistic: lifted shadows, low contrast, pastel colour, warm creamy highlights.

*Basis:* Light & airy: expose bright, flatten contrast, mute greens/blues so skin glows.

*Targets:* median lightness 0.68, black 0.045, highlights 0.98, preserves 10% of the original key  
*Say:* light and airy, bright portrait, airy, wedding, bridal, soft and bright  
### Portrait – Black & White  
`portrait_bw`

Timeless monochrome portraiture: soft-contrast skin tones, glowing highlights, subtle grain.

*Basis:* Orange/red mix lightens skin and softens blemishes in monochrome.

*Targets:* median lightness 0.5, black 0.012, highlights 0.96, preserves 25% of the original key  
*Say:* portrait black and white, bw portrait, monochrome portrait, black and white portrait, classic portrait bw  

## Film

### Film – Kodachrome 64  
`film_kodachrome`

Saturated reds and yellows, deep blues, punchy contrast and a warm 1970s National-Geographic glow.

*Basis:* Kodachrome: strong reds/yellows, cyan-leaning blues, olive greens, high contrast.

*Targets:* median lightness 0.5, black 0.012, highlights 0.95, preserves 30% of the original key  
*Say:* kodachrome, 70s, national geographic, slide film, vintage color, retro color  
### Film – Fuji Velvia  
`film_velvia`

Landscape slide film: intense saturation, rich greens and magentas, high contrast, ultra-fine grain.

*Basis:* Velvia = contrast + saturation, with blues darkened and greens made emerald.

*Targets:* median lightness 0.5, black 0.01, highlights 0.95, preserves 30% of the original key  
*Say:* velvia, fuji velvia, slide, intense, super saturated, fuji film  
### Film – Kodak Ektar 100  
`film_ektar`

Vivid but clean colour negative: fine grain, strong reds, punchy contrast, crisp.

*Basis:* Ektar: ultra-fine grain, saturated reds, clean highlights.

*Targets:* median lightness 0.52, black 0.012, highlights 0.95, preserves 30% of the original key  
*Say:* ektar, kodak ektar, fine grain color, vivid film, crisp film  
### Film – CineStill 800T  
`film_cinestill`

Tungsten cinema stock: teal shadows, orange-red halation around lights, soft contrast, visible grain.

*Basis:* Removing the remjet layer is what makes lights bleed red; we simulate with threshold-glow tinted red.

*Targets:* median lightness 0.44, black 0.02, highlights 0.96, preserves 50% of the original key  
*Say:* cinestill 800t, 800t, tungsten film, halation, cine film, film night  
### Film – Faded Vintage  
`film_vintage_fade`

Sun-bleached memory: lifted blacks, warm yellow highlights, green-cyan shadows, soft grain.

*Basis:* Matte blacks and split-tone give the faded print feel.

*Targets:* median lightness 0.54, black 0.05, highlights 0.96, preserves 35% of the original key  
*Say:* vintage, faded, retro, nostalgic, old photo, polaroid  

## Black & White

### B&W – Ilford HP5 (balanced)  
`bw_hp5`

Versatile, softer-contrast monochrome with full tonal range and moderate grain.

*Basis:* General-purpose mono: honest tonal separation without extremes.

*Targets:* median lightness 0.5, black 0.012, highlights 0.96, preserves 25% of the original key  
*Say:* hp5, ilford, balanced black and white, soft black and white, black and white, bw  
### B&W – Fine-Grain Silver (Delta 100)  
`bw_delta`

Smooth, detailed fine-art monochrome: wide tonal scale, minimal grain, crisp.

*Basis:* Zone-system thinking: place blacks and whites precisely, keep texture, mild selenium cool.

*Targets:* median lightness 0.5, black 0.01, highlights 0.96, preserves 20% of the original key  
*Say:* delta 100, fine grain, silver gelatin, fine art black and white, gallery print, tonal  
### B&W – High-Key  
`bw_high_key`

Bright airy monochrome: luminous whites, soft shadows, low-contrast elegance.

*Basis:* Overexpose the key and compress the shadows toward mid-grey.

*Targets:* median lightness 0.7, black 0.03, highlights 0.99, preserves 10% of the original key  
*Say:* high key, bright black and white, airy black and white, white background, fashion bw  
### B&W – Film Noir / Low-Key  
`bw_noir`

Hard, shadow-dominated cinema noir: deep blacks swallowing the frame, spotlit subject, glowing highlights.

*Basis:* Low-key: underexpose on purpose, steep curve, spotlight the subject.

*Targets:* median lightness 0.3, black 0.0, highlights 0.96, preserves 55% of the original key  
*Say:* noir, film noir, low key, dark black and white, shadowy, detective  

## Cinematic

### Cinematic – Teal & Orange  
`cine_teal_orange`

Blockbuster grade: teal shadows against warm skin and highlights, contrasty, slight bloom.

*Basis:* Blues are pulled toward teal, greens muted, orange kept for skin – complementary colour contrast.

*Targets:* median lightness 0.46, black 0.02, highlights 0.95, preserves 40% of the original key  
*Say:* cinematic, teal and orange, teal orange, movie, film look, hollywood  
### Cinematic – Bleach Bypass  
`cine_bleach`

Gritty war-film desaturation: silvery highlights, crushed contrast, hard texture.

*Basis:* Retained silver halves colour saturation and doubles contrast.

*Targets:* median lightness 0.44, black 0.005, highlights 0.95, preserves 40% of the original key  
*Say:* bleach bypass, saving private ryan, silver, war, desaturated cinematic, metallic  

## Commercial

### Product – Clean Commercial  
`product_clean`

E-commerce-ready: neutral white balance, bright clean background, even tone, maximum crispness.

*Basis:* Neutral whites and dense sharpening, no stylisation.

*Targets:* median lightness 0.62, black 0.02, highlights 0.97, preserves 10% of the original key  
*Say:* product, ecommerce, e-commerce, catalog, catalogue, commercial  
### Food – Warm & Appetising  
`food_warm`

Inviting warm tones, rich reds/oranges, soft contrast, bright natural look.

*Basis:* Warm, saturated reds/oranges and gentle vignette draw the eye in.

*Targets:* median lightness 0.56, black 0.02, highlights 0.96, preserves 20% of the original key  
*Say:* food, restaurant, cuisine, meal, dish, appetising  

## Night

### Night – Clean Cityscape  
`night_city`

Balanced night skylines: tamed lights, clean shadows, rich colour, low noise.

*Basis:* Night images keep their darkness; the work is noise control and light-source management.

*Targets:* median lightness 0.36, black 0.01, highlights 0.95, preserves 70% of the original key  
*Say:* night, night photography, skyline, blue hour, long exposure night, city lights  

## Photographers

### Ansel Adams – Zone System Print  
`ph_adams`

Full tonal scale from true black to paper white, dark red-filtered skies, glowing clouds, crisp edge-to-edge detail, burned corners and dodged shadows.

*Basis:* Documented: the Zone System (expose for the shadows, develop for the highlights so the scene fits ten zones) and heavy dodging & burning at the print stage. Interpretation: red/yellow filtration for dark skies, the steep-but-open curve and the burned-in corners/sky gradient.

*Targets:* median lightness 0.46, black 0.006, highlights 0.98, preserves 20% of the original key  
*Say:* ansel adams, adams, zone system, yosemite, half dome, grand landscape  
*Sources:* [1](https://en.wikipedia.org/wiki/Dodging_and_burning); [2](https://photo-facts.com/zone-system)

### Daido Moriyama – Are-Bure-Boke  
`ph_moriyama`

Provoke-era Tokyo: pushed-Tri-X contrast, coarse grain, crushed blacks and burnt highlights. Rough, raw and immediate.

*Basis:* Documented: 'are, bure, boke' = grainy, blurry, out-of-focus, with grain treated as an expressive tool; he pushed contrast to extremes in the darkroom; Ricoh's 'High Contrast B&W' imitates this push-processed film look. Interpretation: exact curve, grain size and the blown-highlight bias.

*Targets:* median lightness 0.5, black 0.0, highlights 0.99, preserves 40% of the original key  
*Say:* daido moriyama, moriyama, are bure boke, provoke, ricoh gr, high contrast bw  
*Sources:* [1](https://thephotographersgallery.org.uk/node/2317); [2](https://digitalcameraworld.com/cameras/compact-cameras/did-you-know-the-ricoh-gr-iii-has-a-daido-moriyama-mode)

### Henri Cartier-Bresson – The Decisive Moment  
`ph_hcb`

Leica-and-Tri-X reportage: rich mid-grey tonality, restrained contrast, gentle lens vignette, warm bromide-paper feel, straight horizon.

*Basis:* Documented: his prints were made by master printers (e.g. Pierre Gassmann/Picto) on bromide papers prized for their tonality. Interpretation: moderate contrast with a long, even grey scale, warm-neutral tone, light vignetting typical of fast Leica lenses.

*Targets:* median lightness 0.5, black 0.015, highlights 0.96, preserves 30% of the original key  
*Say:* cartier bresson, cartier-bresson, hcb, decisive moment, magnum, leica street  
*Sources:* [1](https://www.photrio.com/forum/threads/hcb-appreciation.138841/page-5?amp=1)

### Fan Ho – Shadow & Smoke (Hong Kong)  
`ph_fanho`

Low-sun chiaroscuro: deep shadows cut by shafts of light, hazy glowing highlights, graphic geometry, a small figure in a pool of light.

*Basis:* Documented: style defined by shadow and light, often shot with the sun low; the tonality was shaped in the darkroom, taming wildly varying light. Interpretation: low-key target, burnt shadows, atmospheric glow for haze/smoke.

*Targets:* median lightness 0.36, black 0.0, highlights 0.98, preserves 50% of the original key  
*Say:* fan ho, ho fan, hong kong, shadows and light, chiaroscuro street, light shafts  
*Sources:* [1](https://www.mplus.org.hk/en/magazine/ho-fan-on-the-decisive-moment/)

### Vivian Maier – Rolleiflex Street  
`ph_maier`

Medium-format street tonality: soft, wide-ranging greys, fine grain, deep but open shadows, quiet and observational.

*Basis:* Documented: she shot Rolleiflex and Leica for decades and printed very little, so her 'look' is mostly the negatives as later printed. Interpretation: a gentle, medium-format-like scale with fine grain; for a true square frame, crop 1:1 afterwards.

*Targets:* median lightness 0.5, black 0.02, highlights 0.96, preserves 30% of the original key  
*Say:* vivian maier, maier, rolleiflex, nanny, medium format street, chicago street  
*Sources:* [1](https://www.rousette.org.uk/archives/vivian-maier/); [2](https://www.artforum.com/columns/vivian-maier-out-of-the-shadows-216711/)

### Sebastião Salgado – Epic Monochrome  
`ph_salgado`

Monumental black & white: velvety deep blacks, luminous silver mid-tones, brooding skies and a dramatic glow of light on faces and land.

*Basis:* Documented (secondary sources): Tri-X rated 400–1600, exposure for the shadows with wide tonal range; later work digital but styled to match. Interpretation: dark sky burn, subject dodge, rich blacks with retained shadow detail.

*Targets:* median lightness 0.43, black 0.008, highlights 0.97, preserves 35% of the original key  
*Say:* salgado, sebastiao salgado, genesis, workers, epic black and white, humanist documentary  
*Sources:* [1](https://luminous-landscape.com/sebastiao-salgado-master-of-light-shadow-and-human-dignity); [2](https://www.photrio.com/forum/threads/sebasti%C3%A3o-salgados-genesis-how-did-he-do-it.104571/)

### Josef Koudelka – Dark & Heavy  
`ph_koudelka`

Brooding, raw and heavy: thick blacks, gritty grain, harsh contrast, low-key frames that feel like a cold wind.

*Basis:* Documented (forum, anecdotal): high-contrast lighting, raw grain, and a look attributed mainly to heavy darkroom work. Interpretation: low key, crushed blacks, coarse grain, strong vignette.

*Targets:* median lightness 0.34, black 0.0, highlights 0.96, preserves 55% of the original key  
*Say:* koudelka, josef koudelka, gypsies, exiles, heavy blacks, dark gritty bw  
*Sources:* [1](https://www.photrio.com/forum/threads/how-josef-koudelka-achieved-this-style.184548/?amp=1)

### Robert Frank – The Americans  
`ph_frank`

Rough, off-hand, grainy: uneven light, smoky greys, deep muddy shadows, a sad, honest roadside America.

*Basis:* Interpretation from the look of the published book (35 mm Tri-X, uneven printing): not a documented recipe.

*Targets:* median lightness 0.42, black 0.01, highlights 0.95, preserves 45% of the original key  
*Say:* robert frank, the americans, roadside, beat, grainy documentary, americana bw  
### Saul Leiter – Painterly Kodachrome  
`ph_leiter`

Soft, abstract, painterly colour: glowing reds and ambers against muted surroundings, low contrast, a veil of rain and reflection.

*Basis:* Documented: Kodachrome in 1940s–60s New York, rain-streaked glass and reflections breaking the scene into painterly blocks; Kodachrome's rich reds. Interpretation: soft veil (negative clarity + glow), red emphasis with the rest muted.

*Targets:* median lightness 0.5, black 0.025, highlights 0.95, preserves 40% of the original key  
*Say:* saul leiter, leiter, painterly, rainy window, abstract street color, new york 1950s  
*Sources:* [1](https://www.internazionale.it/foto/2017/05/30/colori-vancouver-fred-herzog); [2](https://www.equinoxgallery.com/wp-content/uploads/2024/02/When-Master-Photographers-Spin-the-Color-Wheel-The-New-York-Times.pdf)

### William Eggleston – Dye-Transfer Colour  
`ph_eggleston`

Saturated, deadpan colour of the everyday: lurid reds, deep cyan-greens, smooth rich surfaces, nothing dramatised.

*Basis:* Documented: ordinary subjects (gas stations, suburban streets, interiors) in vivid colour, the 1976 MoMA show that legitimised colour. Interpretation: dye-transfer-like density — strong reds/cyans, smooth, no vignette or grain.

*Targets:* median lightness 0.52, black 0.015, highlights 0.96, preserves 30% of the original key  
*Say:* eggleston, william eggleston, dye transfer, new color, deadpan, suburban color  
*Sources:* [1](https://www.internazionale.it/foto/2017/05/30/colori-vancouver-fred-herzog); [2](https://kirkville.com/photo-book-review-modern-color-by-fred-herzog/)

### Fred Herzog – Kodachrome Vancouver  
`ph_herzog`

Gritty 1950s–60s city colour: warm Kodachrome density, saturated signage, cool shadow edges, working-class streets.

*Basis:* Documented: ~50 years almost exclusively on Kodachrome slide film; prints matched the slide's colour and intensity (the 'Kodachrome look'). Interpretation: warm density, strong reds/yellows, cooler shadow edges.

*Targets:* median lightness 0.46, black 0.012, highlights 0.95, preserves 40% of the original key  
*Say:* fred herzog, herzog, vancouver, modern color, kodachrome street, signage  
*Sources:* [1](https://www.internazionale.it/foto/2017/05/30/colori-vancouver-fred-herzog); [2](https://kirkville.com/photo-book-review-modern-color-by-fred-herzog/)

### Alex Webb – Layered Light  
`ph_webb`

Hot, layered colour: radiant reds, yellows and deep blues, silhouettes in dense shadow, searing light.

*Basis:* Documented: layered compositions of gesture, light and colour; vivid reds, deep blues and radiant yellows; light that shaped his move to colour. Interpretation: dense shadows with saturated primaries.

*Targets:* median lightness 0.42, black 0.006, highlights 0.95, preserves 50% of the original key  
*Say:* alex webb, webb, layered, silhouette color, haiti, istanbul  
*Sources:* [1](https://www.shutterbug.com/node/371923); [2](https://theclick.us/2024/07/25/alex-webb-on-how-color-photography-changes-his-way-of-seeing)

### Steve McCurry – Saturated Portraiture  
`ph_mccurry`

Rich, saturated travel portraiture: glowing reds, oranges and deep blues, luminous eyes and skin, warm Kodachrome heritage.

*Basis:* Documented: heavily saturated colour is central to his work (and a PetaPixel tutorial describes his muted film tone plus added saturation). Interpretation: vibrance-led push, eyes/face dodge, blues deepened.

*Targets:* median lightness 0.5, black 0.012, highlights 0.96, preserves 30% of the original key  
*Say:* mccurry, steve mccurry, afghan girl, national geographic portrait, saturated portrait, travel portrait  
*Sources:* [1](https://petapixel.com/2018/05/12/how-to-edit-photos-like-steve-mccurry-the-art-of-removing-distractions)

### Annie Leibovitz – Editorial Drama  
`ph_leibovitz`

Staged and painterly: rich colour, deliberate dramatic light, dense shadows and glowing skin, a confident, cinematic presence.

*Basis:* Described in sources as dramatic lighting, rich colour, careful staging and strong sense of character. Interpretation: darker key, saturated but skin-safe grade.

*Targets:* median lightness 0.44, black 0.01, highlights 0.95, preserves 45% of the original key  
*Say:* leibovitz, annie leibovitz, vanity fair, editorial, rolling stone, staged  
*Sources:* [1](https://retouchinglabs.com/famous-portrait-photographers-of-the-21st-century/)

### Peter Lindbergh – Raw Cinematic B&W  
`ph_lindbergh`

Natural, barely retouched black & white: honest skin texture, silvery cinematic tones, soft light and a hint of grain.

*Basis:* Documented: believed retouching should be minimal, often black & white for drama. Interpretation: silvery neutral-cool grade, skin texture deliberately preserved (no smoothing).

*Targets:* median lightness 0.52, black 0.02, highlights 0.97, preserves 25% of the original key  
*Say:* lindbergh, peter lindbergh, supermodels, natural black and white portrait, unretouched, cinematic bw portrait  
*Sources:* [1](https://retouchinglabs.com/famous-portrait-photographers-of-the-21st-century/)

### Todd Hido – Suburban Night  
`ph_hido`

Moody twilight suburbia: fluorescent teal-green shadows, amber windows, long-exposure softness and film grain.

*Basis:* Documented only that he has a signature palette conveying unease beneath suburban uniformity. Interpretation: green-teal shadows vs warm window light, as a mood study.

*Targets:* median lightness 0.34, black 0.02, highlights 0.95, preserves 65% of the original key  
*Say:* todd hido, hido, suburban night, house hunting, twilight windows, lonely house  
*Sources:* [1](https://juxtapoz.com/news/photography/todd-hido-makes-a-series-of-small-decisions-at-leica-gallery/)

### Ezra Stoller – Modernist Clarity  
`ph_stoller`

Rational, precise architectural monochrome: plumb verticals, hard geometry, crisp tonal separation, light studied until shadows describe the form.

*Basis:* Documented: mostly black & white, clean geometric precision, hours spent tracking sun until shadows described the form. Interpretation: red-filter skies, steep clean curve, perfect verticals.

*Targets:* median lightness 0.46, black 0.008, highlights 0.97, preserves 20% of the original key  
*Say:* ezra stoller, stoller, modernist architecture, mid century architecture bw, rational, geometry bw  
*Sources:* [1](https://illustrarch.com/architectural-photography/65449-famous-architectural-photographers.html)

### Julius Shulman – Case Study Glow  
`ph_shulman`

Mid-century modern glamour: luminous interior against a deep dusk or sky, controlled reflections, warm lamps balanced with daylight.

*Basis:* Documented: staged interiors, controlled reflections in glass, and balancing daylight against interior lamps. Interpretation: dusk-sky darkening with warm interior glow.

*Targets:* median lightness 0.46, black 0.012, highlights 0.96, preserves 40% of the original key  
*Say:* shulman, julius shulman, case study house, mid century modern, california modernism, stahl house  
*Sources:* [1](https://illustrarch.com/architectural-photography/65449-famous-architectural-photographers.html)

### Iwan Baan – Lived-In Architecture  
`ph_baan`

Documentary architecture: natural, honest colour, soft ambient light, buildings in context with weather and life.

*Basis:* Documented: documentary approach including people, weather and the 'messiness of actual inhabitation'. Interpretation: light-touch, natural grade with mild correction.

*Targets:* median lightness 0.52, black 0.015, highlights 0.96, preserves 35% of the original key  
*Say:* iwan baan, baan, lived in architecture, documentary architecture, context, people in architecture  
*Sources:* [1](https://illustrarch.com/architectural-photography/65449-famous-architectural-photographers.html)

### Hélène Binet – Light on Form  
`ph_binet`

Analogue-feeling architectural abstraction: raking light, deep tones, textured surfaces, quiet graphic composition.

*Basis:* Documented: repeated site visits studying how light meets structure; analogue practice. Interpretation: raking-light contrast, textured grain, deep blacks.

*Targets:* median lightness 0.4, black 0.005, highlights 0.96, preserves 45% of the original key  
*Say:* helene binet, binet, raking light, texture architecture, abstract architecture, analogue architecture  
*Sources:* [1](https://illustrarch.com/architectural-photography/65449-famous-architectural-photographers.html)

### Hiroshi Sugimoto – Seascape  
`ph_sugimoto`

Meditative long-exposure minimalism: silk-smooth water and sky as even grey planes, a precise horizon, timeless stillness.

*Basis:* Documented: Seascapes since 1980, large-format, exposures up to hours; B&W planes of water and sky split by a centred horizon. Interpretation: heavy noise smoothing, no grain, soft cool-selenium tone.

*Targets:* median lightness 0.52, black 0.04, highlights 0.95, preserves 45% of the original key  
*Say:* sugimoto, hiroshi sugimoto, seascape, long exposure, michael kenna, kenna  
*Sources:* [1](https://wizardgallery.com/blog/49-hiroshi-sugimoto-master-of-minimalist-photography); [2](https://www.whitecube.com/gallery-exhibitions/seascapes-theatres-dioramas-and-drive-ins)
