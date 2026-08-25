from pathlib import Path
from PIL import Image


BASE = Path("/Users/kang-yumin/Documents/GitHub/new 3d/Art/Animations")
FPS = 30


def make_gif(action_name, hold_last=0):
    frame_paths = sorted((BASE / action_name).glob("frame_*.png"))
    frames = [Image.open(path).convert("P", palette=Image.Palette.ADAPTIVE) for path in frame_paths]
    if hold_last and frames:
        frames.extend([frames[-1].copy() for _ in range(hold_last)])
    output = BASE / f"char_baker_cat_{action_name.lower()}.gif"
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        disposal=2,
        optimize=False,
    )
    return output


outputs = [
    make_gif("Idle"),
    make_gif("Run"),
    make_gif("Attack", hold_last=6),
    make_gif("Defend", hold_last=6),
]
print("\n".join(str(path) for path in outputs))
