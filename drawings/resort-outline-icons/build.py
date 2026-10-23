from pathlib import Path
import json, shutil, zipfile, html
import fitz
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'drawings/resort-outline-all'
manifest=json.loads((SOURCE/'manifest.json').read_text())
assert len(manifest)==21
assets=OUT/'assets';assets.mkdir(exist_ok=True)
board_path=Path('/tmp/concept_icon_boards.json')
board_map=json.loads(board_path.read_text()) if board_path.exists() else {}
atlas=fitz.open()
for key in ['a','b','c']:
 target=assets/f'icons_{key}.png'
 if not target.exists():shutil.copyfile(board_map[key],target)
 image=fitz.Pixmap(target)
 p=atlas.new_page(width=image.width,height=image.height)
 p.insert_image(p.rect,filename=str(target))

CARD=fitz.Rect(900,25,1045,175)
def icon(page,number,target):
 board,index=divmod(number-1,7)
 row,col=divmod(index,4)
 sheet=atlas[board].rect;cw=sheet.width/4;ch=sheet.height/2
 clip=fitz.Rect((col+.04)*cw,(row+.04)*ch,(col+.96)*cw,(row+.96)*ch)
 page.show_pdf_page(target,atlas,board,clip=clip,keep_proportion=True)

def add_card(page,entry):
 n=entry['option']
 page.insert_text((947,32),f'CONCEPT {n:02}',fontsize=8,color=(0,0,0))
 icon(page,n,fitz.Rect(908,38,1037,130))
 text=html.escape(entry['name_ar'])
 result=page.insert_htmlbox(fitz.Rect(900,132,1045,154),f'<div dir="rtl" style="font-family:sans-serif;font-size:11pt;text-align:center">{text}</div>')
 assert result[0]>=0
 page.insert_textbox(fitz.Rect(900,156,1045,173),entry['name_en'],fontsize=8,align=1,color=(0,0,0))

combined=fitz.open()
with fitz.open(SOURCE/'all_21_concepts_outline.pdf') as src:
 for i,entry in enumerate(manifest):
  rect=src[i].rect
  page=combined.new_page(width=rect.width,height=rect.height)
  page.show_pdf_page(page.rect,src,i)
  add_card(page,entry)
  base=entry['outline_png'].removesuffix('.png')
  with fitz.open(SOURCE/(base+'.pdf')) as original:
   one=fitz.open();p=one.new_page(width=rect.width,height=rect.height)
   p.show_pdf_page(p.rect,original,0);add_card(p,entry)
   one.save(OUT/(base+'_with_icon.pdf'),garbage=4,deflate=True)
   one.close()
combined.save(OUT/'all_21_outline_with_icons.pdf',garbage=4,deflate=True)
combined.close()

legend=fitz.open();page=legend.new_page(width=1190.55,height=841.89)
page.insert_text((28,29),'CONCEPT ICONS | OPTIONS 01-21',fontsize=18)
for i,entry in enumerate(manifest):
 row,col=divmod(i,3);x=22+col*384;y=49+row*110
 icon(page,entry['option'],fitz.Rect(x,y,x+90,y+96))
 page.insert_text((x+103,y+22),f"{entry['option']:02} | {entry['name_en']}",fontsize=11)
 page.insert_htmlbox(fitz.Rect(x+102,y+36,x+365,y+73),f'<div dir="rtl" style="font-size:13pt;text-align:left">{html.escape(entry["name_ar"])}</div>')
legend.save(OUT/'concept_icon_legend.pdf',garbage=4,deflate=True);legend.close()

# Check that additions are confined to the formerly blank card, preserving all plan pixels.
checks=[]
with fitz.open(SOURCE/'all_21_concepts_outline.pdf') as before, fitz.open(OUT/'all_21_outline_with_icons.pdf') as after:
 assert len(after)==21
 for i in range(21):
  assert before[i].rect==after[i].rect
  p=before[i].get_pixmap(colorspace=fitz.csRGB)
  q=after[i].get_pixmap(colorspace=fitz.csRGB)
  a=np.frombuffer(p.samples,dtype=np.uint8).reshape(p.height,p.width,3)
  b=np.frombuffer(q.samples,dtype=np.uint8).reshape(q.height,q.width,3)
  changed=np.any(a!=b,axis=2)
  outside=changed.copy();outside[24:177,899:1047]=False
  assert not outside.any(),(i+1,int(outside.sum()))
  assert changed.sum()>100
  checks.append({'option':i+1,'page_size_unchanged':True,'plan_pixels_outside_icon_area_unchanged':True})
 for i in [0,13,16,17,20]:
  after[i].get_pixmap(matrix=fitz.Matrix(1,1)).save(OUT/f'preview_{i+1:02}.png')
(OUT/'validation.json').write_text(json.dumps({'pages':21,'icon_area_pt':list(CARD),'page_checks':checks},indent=2))

with zipfile.ZipFile(OUT/'individual_outline_with_icons.zip','w',zipfile.ZIP_DEFLATED) as z:
 z.write(OUT/'README_AR.md','README_AR.md')
 z.write(OUT/'concept_icon_legend.pdf','concept_icon_legend.pdf')
 for entry in manifest:
  name=entry['outline_png'].removesuffix('.png')+'_with_icon.pdf'
  with fitz.open(OUT/name) as d:assert len(d)==1
  z.write(OUT/name,name)
with zipfile.ZipFile(OUT/'individual_outline_with_icons.zip') as z:
 assert z.testzip() is None and len(z.namelist())==23
for name in ['all_21_outline_with_icons.pdf','individual_outline_with_icons.zip','concept_icon_legend.pdf']:
 print(name,(OUT/name).stat().st_size,'bytes')
print('Verified all 21 plans unchanged outside their concept icon cards.')
