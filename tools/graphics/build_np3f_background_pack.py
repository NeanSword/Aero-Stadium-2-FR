"""Slice the verified NP3F title background and optional logo into an RT64 pack.

No UI text, ROM, game code or runtime configuration is modified here.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image
from build_np3f_title_pack_from_dump import (
    discover_dump, select_layout_records, LAYOUT, TITLE_ANCHOR_HASH,
    load_scaled_master, split_master,
)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dump-zip',type=Path,required=True)
    p.add_argument('--master',type=Path,required=True)
    p.add_argument('--logo',type=Path,help='Optional transparent 376x196 integer-scale logo master.')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--shift',choices=['half','none'],default='none',
                   help='RT64 replacement sampling shift; verify in-game for this asset.')
    a=p.parse_args()
    if a.output.exists():
        raise SystemExit('Output exists; choose a versioned sibling to preserve the previous pack.')
    image,scale=load_scaled_master(a.master,(320,240))
    if image.getchannel('A').getextrema() != (255,255):
        raise SystemExit('The title background master must be fully opaque.')
    by_address,by_hash=discover_dump(a.dump_zip)
    anchor=by_hash.get(TITLE_ANCHOR_HASH)
    if anchor is None:raise SystemExit('Verified title anchor missing from this dump.')
    records=select_layout_records(by_address,LAYOUT['background'],anchor_time=anchor['timestamp'])
    if len({r['hash'] for r in records})!=300:
        raise SystemExit('Expected 300 unique background hashes.')
    entries=[]
    split_master(a.master,(320,240),records,20,a.output,'Title/Background',entries)
    background_entries=list(entries)
    logo_manifest=None
    if a.logo:
        logo,logo_scale=load_scaled_master(a.logo,(376,196))
        if logo.getchannel('A').getextrema() != (0,255):
            raise SystemExit('Logo must have both transparency and opaque lettering.')
        logo_records=select_layout_records(by_address,LAYOUT['logo'])
        split_master(a.logo,(376,196),logo_records,1,a.output,'Title/Logo',entries)
        logo_entries=entries[len(background_entries):]
        joined=Image.new('RGBA',logo.size)
        for i,entry in enumerate(logo_entries):
            strip=Image.open(a.output/(entry['path']+'.png')).convert('RGBA')
            if strip.size!=(376*logo_scale,4*logo_scale):raise SystemExit('Invalid logo strip size.')
            joined.paste(strip,(0,i*4*logo_scale))
        if joined.tobytes()!=logo.tobytes():raise SystemExit('Logo reassembly mismatch.')
        logo_manifest={'master':a.logo.name,'size':list(logo.size),'strips':len(logo_entries),
                       'master_sha256':hashlib.sha256(a.logo.read_bytes()).hexdigest(),
                       'reassembly_pixel_identical':True}
    if len({e['hashes']['rt64'] for e in entries}) != len(entries):
        raise SystemExit('Duplicate replacement hashes are not permitted.')
    db={'configuration':{'autoPath':'rt64','configurationVersion':3,'hashVersion':5,
                        'defaultOperation':'stream','defaultShift':a.shift},
        'textures':entries}
    (a.output/'rt64.json').write_text(json.dumps(db,indent=2)+'\n',encoding='utf-8')
    # Prove tile boundaries neither crop nor duplicate master pixels.
    stitched=Image.new('RGBA',image.size)
    for i,entry in enumerate(background_entries):
        tile=Image.open(a.output/(entry['path']+'.png')).convert('RGBA')
        if tile.size!=(16*scale,16*scale):raise SystemExit('Unexpected export size.')
        stitched.paste(tile,((i%20)*16*scale,(i//20)*16*scale))
    if stitched.tobytes()!=image.tobytes():raise SystemExit('Master reassembly mismatch.')
    manifest={'asset':'NP3F title background only','master':a.master.name,
              'master_size':list(image.size),'scale':scale,'tiles':len(background_entries),
              'tile_size':[16*scale,16*scale],
              'master_file_sha256':hashlib.sha256(a.master.read_bytes()).hexdigest(),
              'source_zip_sha256':hashlib.sha256(a.dump_zip.read_bytes()).hexdigest(),
              'reassembly_pixel_identical':True,'sampling_shift':a.shift,'runtime_modified':False,
              'runtime_validation':'pending'}
    manifest['asset']='NP3F title background and logo' if a.logo else manifest['asset']
    manifest['logo']=logo_manifest
    manifest['total_entries']=len(entries)
    (a.output/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
