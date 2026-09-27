"""Prepare metadata and four identity-control replacements from catalog previews.

No art is retouched: the four files are exact nearest-neighbor previews. They
validate the loading mechanism before any HD production. Never ship as HD art.
"""
import argparse
import json
from pathlib import Path
import shutil
from PIL import Image

PILOTS = [
    ('text','02f9b8d67777bf16','Glyphe L','ui/text','menus / texte'),
    ('rgba','82dbc094ea0f8ac0','Icône Pikachu','ui/icons','sélection Pokémon, à confirmer'),
    ('intensity','951448e72cb575fc','Bande COMBAT!','ui/labels','menu principal'),
    ('repeat','369e34f9da3e0131','Motif Poké Ball répétable','unknown','menu de combat, à confirmer'),
]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    rows=json.loads((a.catalog/'catalog.json').read_text(encoding='utf-8'));by_hash={r['hash']:r for r in rows}
    labels={}
    # Reviewed visually on the contact sheets, not classified by dimensions alone.
    for r in rows:
        if r['review_group']=='24x20':
            labels[r['hash']]={'category':'ui/text','priority':'phase1','label':'Glyphe IA8 (identité à transcrire)',
                               'classification_evidence':'Visually reviewed glyph sheets 24x20-01/02; scene hash confirmation pending'}
        elif r['review_group']=='40x40':
            labels[r['hash']]={'category':'ui/icons','priority':'phase2','label':'Icône Pokémon / élément 2D',
                               'classification_evidence':'Visually reviewed all five 40x40 contact sheets; exact usage pending'}
    entries=[];manifest=[]
    for role,h,label,category,scene in PILOTS:
        r=by_hash[h];im=Image.open(a.catalog/r['nearest']).convert('RGBA')
        raw=Image.open(a.catalog/r['preview']).convert('RGBA')
        scale=r['nearest_scale']
        if im.size!=(raw.width*scale,raw.height*scale) or im.tobytes()!=raw.resize(im.size,Image.Resampling.NEAREST).tobytes():
            raise ValueError(f'Preview is not an identity upscale: {h}')
        relative=f'Pilots/{role}_{h}'
        target=a.output/'control-pack'/f'{relative}.png';target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(a.catalog/r['nearest'],target)
        entries.append({'hashes':{'rt64':h},'path':relative,'operation':'preload'})
        manifest.append({'role':role,'hash':h,'label':label,'source_size':[r['width'],r['height']],
                         'export_size':list(im.size),'scale':scale,'format':r['format'],
                         'wrap_s':r['wrap_s'],'wrap_t':r['wrap_t'],'candidate_scene':scene,
                         'art_status':'identity control, not HD production','in_game_status':'pending',
                         'checks':{'hash_match':False,'orientation':False,'alpha':False,'uv':False,'wrap_clamp':False,'1440p':False,'1080p':False}})
        labels[h]={'category':category,'priority':'pilot','label':label,
                   'classification_evidence':'Source preview visually reviewed; scene use must be verified'}
    db={'configuration':{'autoPath':'rt64','configurationVersion':3,'hashVersion':5,
                        'defaultOperation':'stream','defaultShift':'half'},'textures':entries}
    (a.output/'control-pack'/'rt64.json').write_text(json.dumps(db,indent=2)+'\n',encoding='utf-8')
    (a.output/'pilots.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (a.output/'labels.json').write_text(json.dumps(labels,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    phases={
       'phase1':{'category':'ui/text + ui/labels','status':'blocked on pilot validation','master_scale':8,'export_scales':[4,8],
                 'hashes':[r['hash'] for r in rows if r['review_group']=='24x20'],
                 'deferred_groups':{'56x26 + 56x28':'Rendered Pokemon portrait strips with multiple states; not text labels. Reconstruct and map before editing.'}},
       'phase2':{'category':'ui/icons','status':'blocked on pilot validation','master_scale':8,'export_scales':[4,8],
                 'hashes':[r['hash'] for r in rows if r['review_group']=='40x40']},
       'phase3':{'category':'pokemon','status':'mapping required','master_scale':4,'export_scales':[2,4],'hashes':[],
                 'required_mapping':['hash','scene','pokemon','model_part']},
       'phase4':{'category':'stadium','status':'mapping required','master_scale':4,'export_scales':[2,4],'hashes':[],
                 'required_mapping':['hash','stadium','surface','wrap_clamp','importance']},
       'phase5':{'category':'microtiles','status':'deferred until usage and visual benefit are demonstrated',
                 'unclassified_16x16_hashes':[r['hash'] for r in rows if r['review_group']=='16x16']}}
    for name,phase in phases.items():
        phase['production_allowed']=False
        (a.output/f'{name}.json').write_text(json.dumps(phase,indent=2)+'\n',encoding='utf-8')
    print(f'Prepared {len(entries)} identity pilots, {len(labels)} reviewed classifications; production remains gated.')

if __name__=='__main__':main()
