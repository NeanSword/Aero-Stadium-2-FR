"""Preserve an opaque 4:3 artwork and export the NP3F title master at 1920x1440."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image, ImageCms


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise SystemExit('Choose a versioned output directory; existing assets are preserved.')
    with Image.open(a.source) as im:
        image = im.convert('RGBA')
    if image.width * 3 != image.height * 4:
        raise SystemExit('Expected 4:3 art; choose composition explicitly instead of cropping.')
    if image.getchannel('A').getextrema() != (255, 255):
        raise SystemExit('The title background must be fully opaque.')
    a.output.mkdir(parents=True)
    shutil.copy2(a.source, a.output / ('original-artwork' + a.source.suffix))
    master = image.resize((1920, 1440), Image.Resampling.LANCZOS)
    path = a.output / 'title-background-1920x1440.png'
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    master.save(path, icc_profile=profile)
    report = {'source_size': list(image.size), 'master_size': list(master.size),
              'resize': 'Lanczos; full frame; no crop; no neural upscale',
              'source_sha256': hashlib.sha256(a.source.read_bytes()).hexdigest(),
              'master_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'color_space': 'sRGB', 'alpha': 'fully opaque', 'runtime_modified': False}
    (a.output / 'export-manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
