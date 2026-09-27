"""Read an RT64 v5 ZIP without extraction; preserve raw previews and evidence.

TMEM addressing follows RT64's TextureDecoder.hlsli and Format conversions.
This is a decoder/catalog, not an upscale or an automatic asset classifier.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile
from PIL import Image, ImageDraw, ImageFont

FORMATS = {(0,2): 'RGBA16', (0,3): 'RGBA32', (3,0): 'IA4',
           (3,1): 'IA8', (3,2): 'IA16', (4,0): 'I4', (4,1): 'I8'}
CATEGORIES = ['ui/text','ui/labels','ui/icons','pokemon','stadium','effects',
              'backgrounds','microtiles','unknown']

def rgba16(v):
    return tuple(((v >> s & 31) << 3) | (v >> s & 31) >> 2
                 for s in (11,6,1)) + (255 if v & 1 else 0,)

def pixel(fmt, siz, values):
    a = values[0]
    if (fmt,siz) == (0,2): return rgba16((a << 8) | values[1])
    if (fmt,siz) == (0,3): return tuple(values)
    if (fmt,siz) == (3,0):
        i = a & 14
        i = (i << 4) | (i << 1) | (i >> 2)
        return (i,i,i,255 if a & 1 else 0)
    if (fmt,siz) == (3,1): return (a >> 4 << 4 | a >> 4,)*3 + ((a & 15)*17,)
    if (fmt,siz) == (3,2): return (a,a,a,values[1])
    if (fmt,siz) == (4,0): return (a*17,)*4
    if (fmt,siz) == (4,1): return (a,)*4
    raise ValueError(f'Unsupported format {fmt}/{siz}')

def decode_tmem(meta, data):
    t = meta['tile']; fmt,siz = t['fmt'],t['siz']
    if meta['tlut'] != 'None' or (fmt,siz) not in FORMATS:
        raise ValueError('Unsupported palette/format; do not guess')
    if len(data) != 4096 or t['line'] == 0: raise ValueError('Invalid TMEM/stride')
    start,stride = t['tmem']*8,t['line']*8
    rgba32 = (fmt,siz) == (0,3)
    mask = 2047 if rgba32 else 4095
    out = bytearray()
    for y in range(meta['height']):
        def read(rel, bank=0):
            row = rel//stride*stride
            offset = row + (((rel-row)//4 ^ 1)*4) + (rel & 3) if y & 1 else rel
            return data[(((start+offset) & mask) | bank) & 4095]
        for x in range(meta['width']):
            at = y*stride + ((x << (2 if rgba32 else siz)) >> 1)
            if siz == 0: vals = [(read(at) >> (0 if x & 1 else 4)) & 15]
            elif rgba32: vals = [read(at),read(at+1),read(at,2048),read(at+1,2048)]
            else: vals = [read(at+i) for i in range(1 << (siz-1))]
            out.extend(pixel(fmt,siz,vals))
    return Image.frombytes('RGBA',(meta['width'],meta['height']),bytes(out))

def check_rdram(meta, rice, raw, image):
    # Independent check only for contiguous, origin-zero, full block loads.
    t = meta['tile']; w,h = image.size; siz = t['siz']
    if (rice['type'] != 'Block' or rice['tile']['lrt'] == 0 or
        rice['texture']['address'] % 4 or siz == 3 or t['uls'] or t['ult'] or
        (w*(4 << siz)) % 64 or t['line']*8 != w*(4 << siz)//8 or
        len(raw) != w*h*(4 << siz)//8 or len(raw)%4): return 'not_applicable'
    # RDRAM dumps are host word-swapped; TMEM dumps are already byte ordered.
    raw = b''.join(raw[i:i+4][::-1] for i in range(0,len(raw),4))
    out = bytearray()
    for i in range(w*h):
        if siz == 0: values = [(raw[i//2] >> (0 if i & 1 else 4)) & 15]
        else:
            step = 1 << (siz-1); values = raw[i*step:(i+1)*step]
        out.extend(pixel(t['fmt'],siz,values))
    return 'match' if bytes(out) == image.tobytes() else 'mismatch'

def preserve_png(path, image):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        with Image.open(path) as old:
            if old.size != image.size or old.convert('RGBA').tobytes() != image.convert('RGBA').tobytes():
                raise ValueError(f'Immutable preview differs: {path}')
        return
    buffer = io.BytesIO(); image.save(buffer,format='PNG')
    with path.open('xb') as f: f.write(buffer.getvalue())

def contact_sheet(records, output, name, font):
    for page in range((len(records)+59)//60):
        batch = records[page*60:(page+1)*60]
        sheet = Image.new('RGB',(1200,((len(batch)+5)//6)*150),(32,35,42))
        d = ImageDraw.Draw(sheet)
        for i,r in enumerate(batch):
            x,y = (i%6)*200,(i//6)*150
            im = Image.open(output/r['preview']).convert('RGBA')
            scale = max(1,min(4,184//im.width,106//im.height))
            im = im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
            if im.width>184 or im.height>106:
                # Wide strips are intentionally cropped, never resampled down.
                im = im.crop((0,0,min(im.width,184),min(im.height,106)))
            sheet.paste(im,(x+8,y+4),im)
            d.text((x+6,y+111),r['hash'],font=font,fill='white')
            d.text((x+6,y+129),f"{r['width']}x{r['height']} {r['format']}",font=font,fill='#aabbd0')
        preserve_png(output/'sheets'/f'{name}-{page+1:02d}.png',sheet)

def write_html(output, records):
    data = json.dumps(records,ensure_ascii=False).replace('<','\\u003c')
    html = '''<!doctype html><html lang="fr"><meta charset="utf-8"><title>NP3F · Catalogue textures</title>
<style>body{font:15px system-ui;background:#11151c;color:#eef2f7;margin:24px}h1{font-size:25px}header{position:sticky;top:0;background:#11151cf0;padding:12px;z-index:1}input,select,button{font:inherit;padding:9px;margin:4px;background:#232c38;color:white;border:1px solid #526070;border-radius:5px}#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(265px,1fr));gap:12px}.card{padding:12px;background:#202833;border-radius:8px}.art{height:155px;overflow:auto;background:repeating-conic-gradient(#5c6168 0 25%,#777c83 0 50%) 0/16px 16px;display:flex;align-items:center;justify-content:center}.art img{image-rendering:pixelated;max-width:none}small{color:#b8c9db}code{user-select:all}p{line-height:1.5}a{color:#a6d1ff}</style>
<header><h1>AeroStadium2 · Catalogue local des textures</h1><p>Sources intactes · Aperçus nearest-neighbor · Une dimension suggère une piste, jamais une catégorie validée.</p>
<input id="q" placeholder="Hash, dimensions, libellé…"><select id="fmt"><option value="">Tous les formats</option></select><select id="cat"><option value="">Toutes les catégories</option></select><select id="group"><option value="">Tous les groupes à examiner</option></select><button id="prev">Précédent</button><button id="next">Suivant</button><p id="count"></p></header><div id="grid"></div>
<script>const records=DATA;let page=0;const $=id=>document.getElementById(id);for(const [id,key] of [['fmt','format'],['cat','category'],['group','review_group']]){for(const v of [...new Set(records.map(r=>r[key]))].sort()){const o=document.createElement('option');o.value=v;o.textContent=v;$(id).append(o)}}
function render(){const q=$('q').value.toLowerCase();const rows=records.filter(r=>(!$('fmt').value||r.format===$('fmt').value)&&(!$('cat').value||r.category===$('cat').value)&&(!$('group').value||r.review_group===$('group').value)&&JSON.stringify(r).toLowerCase().includes(q));page=Math.max(0,Math.min(page,Math.ceil(rows.length/60)-1));$('count').textContent=rows.length+' textures · page '+(page+1)+' / '+Math.max(1,Math.ceil(rows.length/60));$('grid').replaceChildren();for(const r of rows.slice(page*60,(page+1)*60)){const card=document.createElement('article');card.className='card';const art=document.createElement('div');art.className='art';const img=document.createElement('img');img.src=r.nearest;img.loading='lazy';art.append(img);const title=document.createElement('p');title.textContent=r.label||r.hash;const meta=document.createElement('small');meta.textContent=r.width+'×'+r.height+' · '+r.format+' · '+r.category+' · '+r.wrap_s+'/'+r.wrap_t;const hash=document.createElement('p');const code=document.createElement('code');code.textContent=r.hash;hash.append(code);const link=document.createElement('a');link.href=r.preview;link.textContent='Source décodée 1×';card.append(art,title,meta,hash,link);$('grid').append(card)}}
for(const id of ['q','fmt','cat','group'])$(id).oninput=()=>{page=0;render()};$('prev').onclick=()=>{page--;render()};$('next').onclick=()=>{page++;render()};render();</script></html>'''
    (output/'index.html').write_text(html.replace('DATA',data),encoding='utf-8')

def run(args):
    out = args.output; out.mkdir(parents=True,exist_ok=True)
    labels = json.loads(args.labels.read_text(encoding='utf-8')) if args.labels else {}
    source_sha = hashlib.sha256(args.dump_zip.read_bytes()).hexdigest()
    source_file = out/'source.json'
    if source_file.exists() and json.loads(source_file.read_text())['sha256'] != source_sha:
        raise ValueError('Different source ZIP; use a separate output directory')
    records = []; errors = []; names = []
    with zipfile.ZipFile(args.dump_zip) as z:
        names=z.namelist()
        for n in sorted(names):
            if not n.endswith('.v5.tile.json'): continue
            h = Path(n).name.split('.')[0]
            try:
                meta=json.loads(z.read(n)); rice=json.loads(z.read(n.replace('.tile.json','.rice.json')))
                raw=z.read(n.replace('.tile.json','.rice.rdram')); tmem=z.read(n.replace('.tile.json','.tmem'))
                im=decode_tmem(meta,tmem); t=meta['tile']; w,ht=im.size
                rel=f'raw/{h}.png'; near=f'nearest/{h}.png'
                preserve_png(out/rel,im)
                scale=max(1,min(4,1024//w,512//ht))
                preserve_png(out/near,im.resize((w*scale,ht*scale),Image.Resampling.NEAREST))
                wrap=lambda c,m: 'clamp' if c&2 else ('mirror' if c&1 and m else 'repeat' if m else 'unbounded')
                r={'hash':h,'hash_version':5,'width':w,'height':ht,'format':FORMATS[(t['fmt'],t['siz'])],
                   'category':'unknown','priority':'unassigned','label':'','observed_scenes':[],
                   'review_group':f'{w}x{ht}','preview':rel,'nearest':near,'nearest_scale':scale,
                   'wrap_s':wrap(t['cms'],t['masks']),'wrap_t':wrap(t['cmt'],t['maskt']),
                   'tile':t,'tlut':meta['tlut'],'rdram_address':rice['texture']['address'],
                   'load_type':rice['type'],'timestamp':list(z.getinfo(n).date_time),
                   'rgba_sha256':hashlib.sha256(im.tobytes()).hexdigest(),
                   'tmem_sha256':hashlib.sha256(tmem).hexdigest(),
                   'rdram_crosscheck':check_rdram(meta,rice,raw,im)}
                r.update(labels.get(h,{}))
                if r['category'] not in CATEGORIES: raise ValueError('Invalid category')
                records.append(r)
            except (ValueError,KeyError) as exc: errors.append({'file':n,'error':str(exc)})
    if errors:
        (out/'errors.json').write_text(json.dumps(errors,indent=2),encoding='utf-8')
        raise ValueError(f'{len(errors)} decode failures; no complete catalog produced')
    source={'file':args.dump_zip.name,'sha256':source_sha,'entries':len(names),
            'textures':len(records),'formats':dict(Counter(r['format'] for r in records)),
            'sizes':dict(Counter(r['review_group'] for r in records).most_common()),
            'rdram_crosscheck':dict(Counter(r['rdram_crosscheck'] for r in records)),
            'method':'RT64 TMEM addressing; no creative edits; original ZIP unchanged'}
    source_file.write_text(json.dumps(source,indent=2)+'\n',encoding='utf-8')
    (out/'catalog.json').write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    fields=['hash','width','height','format','category','priority','label','review_group','wrap_s','wrap_t','preview','rdram_crosscheck']
    with (out/'catalog.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(records)
    font=ImageFont.load_default(size=12)
    for group in ('24x20','56x26','56x28','40x40','112x36','136x14','144x28'):
        contact_sheet([r for r in records if r['review_group']==group],out,group,font)
    contact_sheet([r for r in records if r['wrap_s']=='repeat' or r['wrap_t']=='repeat'],out,'repeat',font)
    write_html(out,records)
    print(json.dumps(source,indent=2))

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dump-zip',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--labels',type=Path)
    run(p.parse_args())
