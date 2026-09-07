"""Regenerates `pvechallenge/icon.ico` from `assets/logo.png`.

The icon is versioned, so this script only runs when the logo changes. It
exists to keep the `.ico` reproducible: without it, nobody would know how the
six sizes were obtained, nor why the two smallest are treated apart.
"""

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "assets" / "logo.png"
CIBLE = ROOT / "pvechallenge" / "icon.ico"

#: Sizes embedded. No 256: the source is 128 wide, and enlarging it would
#: fabricate detail that does not exist.
TAILLES = (16, 24, 32, 48, 64, 128)

#: Below 32 px the dark shield dissolves into a dark taskbar. These sizes get a
#: one-pixel rim and livelier colours.
RENFORCEES = (16, 24)

#: Light steel: invisible on a light background, where the dark shield already
#: contrasts on its own, and the only defence on a dark one.
LISERE = (185, 190, 198)

SATURATION = 1.45
CONTRASTE = 1.15


def rendu(source: Image.Image, taille: int) -> Image.Image:
    """Produce one size. The smallest are reinforced, the others merely scaled."""
    if taille not in RENFORCEES:
        return source.resize((taille, taille), Image.LANCZOS)

    # Scaling to size-2 leaves the border pixel free for the rim.
    base = source.resize((taille - 2, taille - 2), Image.LANCZOS)
    base = ImageEnhance.Color(base).enhance(SATURATION)
    base = ImageEnhance.Contrast(base).enhance(CONTRASTE)

    toile = Image.new("RGBA", (taille, taille), (0, 0, 0, 0))
    toile.paste(base, (1, 1))

    # The ring is the difference between the dilated silhouette and the original.
    alpha = toile.getchannel("A")
    couronne = ImageChops.subtract(alpha.filter(ImageFilter.MaxFilter(3)), alpha)

    bord = Image.new("RGBA", (taille, taille), LISERE)
    bord.putalpha(couronne)
    bord.alpha_composite(toile)
    return bord


def main() -> int:
    if not SOURCE.is_file():
        print(f"Source introuvable : {SOURCE}", file=sys.stderr)
        return 1

    source = Image.open(SOURCE).convert("RGBA")
    if source.size != (128, 128):
        print(f"{SOURCE} : 128x128 attendu, {source.size[0]}x{source.size[1]} trouve.", file=sys.stderr)
        return 1

    images = [rendu(source, taille) for taille in TAILLES]
    images[-1].save(
        CIBLE,
        format="ICO",
        append_images=images[:-1],
        sizes=[(taille, taille) for taille in TAILLES],
    )

    with Image.open(CIBLE) as ecrit:
        tailles = sorted(largeur for largeur, _hauteur in ecrit.ico.sizes())
    print(f"{CIBLE} : {CIBLE.stat().st_size} octets, tailles {tailles}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
