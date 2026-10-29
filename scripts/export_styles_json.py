"""Export the style library (merged with neutral defaults) as JSON for the browser-only build."""
import json
import sys

from darkroom import recipe, styles


def export() -> dict:
    out = []
    for s in styles.STYLES:
        out.append({"id": s.id, "name": s.name, "category": s.category, "description": s.description,
                    "keywords": s.keywords, "photographer": s.photographer, "bw": s.is_bw,
                    "recipe": recipe.merge(recipe.DEFAULT, s.recipe), "targets": s.targets, "adapt": s.adapt})
    return {"styles": out, "default": recipe.default(), "default_style": styles.DEFAULT_STYLE}


if __name__ == "__main__":
    json.dump(export(), sys.stdout, separators=(",", ":"))
