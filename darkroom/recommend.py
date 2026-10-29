"""Which looks suit *this* photo?  Used to put the best options first."""
from __future__ import annotations

from . import geometry, styles
from .analysis import Analysis

_PORTRAIT = ["portrait_natural", "ph_mccurry", "ph_leibovitz", "portrait_warm_film", "portrait_bw", "ph_lindbergh",
             "portrait_moody", "portrait_airy"]
_LANDSCAPE = ["land_natural", "ph_adams", "land_golden", "land_vivid", "ph_salgado", "film_velvia", "land_moody", "ph_sugimoto"]
_ARCH = ["arch_clean", "ph_stoller", "arch_bw", "ph_shulman", "arch_dramatic", "ph_baan", "arch_minimal", "ph_binet"]
_NIGHT = ["street_neon_night", "night_city", "film_cinestill", "ph_hido", "bw_noir", "cine_teal_orange"]
_STREET = ["street_classic", "street_bw_trix", "ph_hcb", "ph_moriyama", "ph_herzog", "ph_leiter", "street_gritty", "ph_webb"]
_FILM = ["film_portra", "film_kodachrome", "film_ektar", "cine_teal_orange"]


def scene_kind(an: Analysis, rgb=None) -> str:
    if an.faces and max(f[2] * f[3] for f in an.faces) > 0.012:
        return "portrait"
    if an.night:
        return "night"
    if rgb is not None:
        est = geometry.estimate_upright(rgb, vertical=True, horizontal=False, min_len_frac=0.03)
        if est["n_v"] >= 14 and est["confidence"] > 0.35:
            return "architecture"
    if an.sky_frac > 0.18:
        return "landscape"
    return "street"


def recommend(an: Analysis, rgb=None, n: int = 8) -> tuple[str, list[str]]:
    kind = scene_kind(an, rgb)
    pools = {"portrait": [_PORTRAIT], "landscape": [_LANDSCAPE, _FILM], "architecture": [_ARCH],
             "night": [_NIGHT], "street": [_STREET, _FILM]}[kind]
    out: list[str] = ["natural"]
    # interleave so the shortlist mixes colour and black & white
    for pool in pools:
        for sid in pool:
            if sid not in out:
                out.append(sid)
    if an.is_mono:
        out = [s for s in out if styles.get(s).is_bw or s == "natural"] + [s.id for s in styles.STYLES if s.is_bw and s.id not in out]
    return kind, out[:n]
