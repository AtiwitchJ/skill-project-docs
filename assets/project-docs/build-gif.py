"""Rebuild the English workflow GIF on macOS: python3 assets/project-docs/build-gif.py.

Requires Swift/AppKit and Pillow. No project documentation or user settings are
modified. Frames are original code-drawn graphics, not edits of the infographic.
"""
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

folder = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="project-docs-demo-") as temp:
    subprocess.run(["swift", str(folder / "render-demo.swift"), temp], check=True)
    paths = sorted(Path(temp).glob("*.png"))
    frames = []
    for path in paths:
        with Image.open(path) as image:
            frames.append(image.convert("RGB").quantize(colors=128))
    durations = [2800 if i % 12 == 0 else 100 for i in range(len(frames))]
    frames[0].save(folder / "project-docs-workflow.gif", save_all=True,
                   append_images=frames[1:], duration=durations, loop=0,
                   optimize=True, disposal=1)
    for scene in range(6):
        with Image.open(paths[scene * 12]) as image:
            if scene == 2:
                image.save(folder / "project-docs-workflow-poster.png")
    # A contact sheet allows every scene to be inspected without playing the GIF.
    sheet = Image.new("RGB", (1280, 1200), "white")
    for scene in range(6):
        with Image.open(paths[scene * 12]) as image:
            sheet.paste(image.resize((640, 400)), ((scene % 2) * 640, (scene // 2) * 400))
    sheet.save(folder / "project-docs-workflow-storyboard.png")
print(folder / "project-docs-workflow.gif")
