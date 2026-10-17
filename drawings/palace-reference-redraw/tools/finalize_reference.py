from pathlib import Path
import sys,json,shutil
sys.path.insert(0,'/workspace/elevation/deps')
import cairocffi as cairo
import ezdxf,fitz,pypdfium2
BASE=Path('/workspace/palace_reference');OUT=BASE/'output';MM=14000/917
TITLE='Modern Islamic Commercial Elevation'
bounds=[-158*MM,-77*MM,1062*MM,787*MM]
title_point=[452*MM,-52*MM]
path=OUT/'palace_reference_redraw.dxf';d=ezdxf.readfile(path)
if not list(d.modelspace().query('DIMENSION')) and (OUT/'palace_reference_dimensions.dxf').exists():d=ezdxf.readfile(OUT/'palace_reference_dimensions.dxf')
ms=d.modelspace()
for old in list(ms.query('TEXT')):
 if old.dxf.text==TITLE:ms.delete_entity(old)
s=next(iter(ms.query('SOLID')))
a,b,c,e=bounds
s.dxf.vtx0=(a,b,0);s.dxf.vtx1=(c,b,0);s.dxf.vtx2=(a,e,0);s.dxf.vtx3=(c,e,0)
if '10_REFERENCE_TITLE' not in d.layers:d.layers.new('10_REFERENCE_TITLE',dxfattribs={'color':7,'true_color':0,'lineweight':18})
if 'REF_ARIAL' not in d.styles:d.styles.new('REF_ARIAL',dxfattribs={'font':'arial.ttf'})
ms.add_text(TITLE,dxfattribs={'insert':(*title_point,0),'align_point':(*title_point,0),'height':24*MM,'width':1.0,'halign':1,'valign':0,'style':'REF_ARIAL','layer':'10_REFERENCE_TITLE','true_color':0,'lineweight':18})
d.set_modelspace_vport((e-b)*1.03,center=((a+c)/2,(b+e)/2))
d.saveas(OUT/'palace_reference_dimensions.dxf')
for dim in list(ms.query('DIMENSION')):ms.delete_entity(dim)
d.saveas(path)
audit=ezdxf.readfile(path).audit();assert not audit.errors and not audit.fixes
pdf_path=OUT/'palace_reference_redraw.pdf'
if len(fitz.open(pdf_path))==2:shutil.copy2(pdf_path,OUT/'palace_reference_dimensions.pdf')
data=json.loads((OUT/'geometry_mm.json').read_text())
data['paper_bounds_mm']=bounds;data['reference_canvas']=[1220,864];data['reference_translation']=[133,7]
data['title']={'text':TITLE,'insert':title_point,'height_mm':24*MM,'font':'Arial','width_factor':1.0}
(OUT/'geometry_mm.json').write_text(json.dumps(data,separators=(',',':')))
PW=420*72/25.4;PH=297*72/25.4;sf=min(PW/1220,PH/864);tx=(PW-1220*sf)/2;ty=(PH-864*sf)/2
surface=cairo.PDFSurface(str(pdf_path),PW,PH);ctx=cairo.Context(surface)
ctx.set_source_rgb(1,1,1);ctx.paint();ctx.translate(tx,ty);ctx.scale(sf,sf)
ctx.set_source_rgb(0,0,0);ctx.set_line_width(.18*72/25.4/sf);ctx.set_line_cap(cairo.LINE_CAP_ROUND);ctx.set_line_join(cairo.LINE_JOIN_ROUND)
def pp(p):return (p[0]/MM+158,787-p[1]/MM)
for path in data['paths']:
 ctx.move_to(*pp(path['points'][0]))
 for p in path['points'][1:]:ctx.line_to(*pp(p))
 if path['closed']:ctx.close_path()
 ctx.stroke()
ctx.select_font_face('Arial',cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_NORMAL);ctx.set_font_size(32)
ex=ctx.text_extents(TITLE);fit=552/ex[2]
ctx.save();ctx.translate(610,839);ctx.scale(fit,1);ctx.move_to(-ex[0]-ex[2]/2,0);ctx.show_text(TITLE);ctx.restore();surface.finish()
p=fitz.open(pdf_path);assert len(p)==1 and not p[0].get_images(full=True)
widths={round(q['width'],5) for q in p[0].get_drawings() if q['type'] in ['s','fs']};assert widths=={round(.18*72/25.4,5)}
r=pypdfium2.PdfDocument(str(pdf_path));r[0].render(scale=1220/PW).to_pil().save(OUT/'palace_reference_preview.png')
im=r[0].render(scale=3/sf).to_pil();im.save(BASE/'review'/'reference_3x.png')
for name,bounds_src in {'upper_left':(240,370,470,555),'ground_roses':(268,610,448,749),'tower':(155,85,500,300),'upper_right':(850,370,1045,555)}.items():
 im.crop(tuple(round(v*3) for v in bounds_src)).save(BASE/'review'/(name+'.png'))
report=json.loads((OUT/'validation.json').read_text())
report.update({'reference_version':'clear 1220x864 inline reference','main_pdf_pages':1,'main_file_annotations':'Reference title only; estimated dimensions kept in separate files.',
 'reference_changes':['Ordered ashlar weave replaces random masonry','Three large rosettes in each upper leaf replace tiny daisy grids','Acanthus fans and scrolls replace top daisy rows','Continuous plinths meet the ground datum','Ground border spans full reference canvas','Original reference title and white margins retained'],
 'main_pdf_raster_images':0,'exact_reference_match':'Not established: manual visual reconstruction; source raster pixels unavailable for numerical overlay comparison.'})
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
print('Reference-layout PDF/DXF complete; dimensioned versions are separate.')
