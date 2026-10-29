"""Regenerate docs/STYLES.md from darkroom/styles.py."""
from pathlib import Path

from darkroom import styles

out = ["# Style library\n",
       "Every look is a *recipe* (what to change) plus *targets* (where the histogram should land) and *adaptive hints* "
       "(what the director should detect and react to). Run `darkroom styles` for the same list in a terminal.\n",
       "The **Photographers** group is built from research into how well-known photographers worked. Each entry separates what was "
       "*documented* in the sources consulted from my *interpretation* of it — web sources on exact editing settings were thin, so "
       "these are informed approximations of a look, not reproductions of anyone's actual workflow.\n"]
cat = None
for s in styles.STYLES:
    if s.category != cat:
        cat = s.category
        out.append(f"\n## {cat}\n")
    t = s.targets
    out.append(f"### {s.name}  \n`{s.id}`\n\n{s.description}\n")
    if s.notes:
        out.append(f"*Basis:* {s.notes}\n")
    out.append(f"*Targets:* median lightness {t.get('median')}, black {t.get('black')}, highlights {t.get('hi')}"
               + (f", preserves {int(100 * t['preserve_key'])}% of the original key" if "preserve_key" in t else "") + "  ")
    out.append(f"*Say:* {', '.join(s.keywords[:6])}  ")
    if s.refs:
        out.append("*Sources:* " + "; ".join(f"[{i + 1}]({u})" for i, u in enumerate(s.refs)) + "\n")
Path(__file__).resolve().parents[1].joinpath("docs/STYLES.md").write_text("\n".join(out))
print(len(styles.STYLES), "styles documented")
