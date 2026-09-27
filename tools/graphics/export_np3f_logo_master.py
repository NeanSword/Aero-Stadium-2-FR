"""Fit transparent title artwork to the NP3F logo's 376x196 layout at 6x."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageCms


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise SystemExit('Use a new versioned output directory.')
    source=Image.open(a.source).convert('RGBA')
    alpha=source.getchannel('A')
    if alpha.getextrema() != (0,255):raise SystemExit('A real transparent background and opaque lettering are required.')
    target=(2256,1176)
    scale=min(target[0]/source.width,target[1]/source.height)
    size=tuple(round(v*scale) for v in source.size)
    # Premultiplied-alpha interpolation avoids dark color fringes.
    resized=source.convert('RGBa').resize(size,Image.Resampling.LANCZOS).convert('RGBA')
    master=Image.new('RGBA',target,(0,0,0,0))
    offset=((target[0]-size[0])//2,(target[1]-size[1])//2)
    master.paste(resized,offset)
    pixels=np.array(master)
    pixels[pixels[:,:,3]==0,:3]=0
    master=Image.fromarray(pixels)
    a.output.mkdir(parents=True)
    shutil.copy2(a.source,a.output/'generated-logo-original.png')
    path=a.output/'aerostadium-2-logo-2256x1176.png'
    profile=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    master.save(path,icc_profile=profile)
    report={'source_size':list(source.size),'master_size':list(target),'fit_size':list(size),
            'offset':list(offset),'resize':'premultiplied-alpha Lanczos; no crop or stretch',
            'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),
            'master_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'transparent_rgb_zeroed':True,'alpha_extrema':list(master.getchannel('A').getextrema())}
    (a.output/'export-manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
