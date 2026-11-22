
require 'sketchup.rb'
require 'json'
module GewanEditable2026
 ROOT=File.dirname(__FILE__) unless const_defined?(:ROOT)
 def self.load_data
  @data ||= JSON.parse(File.read(File.join(ROOT,'models.json'),encoding:'UTF-8'))
 end
 def self.transform(values)
  m=values.map(&:to_f)
  [12,13,14].each { |i| m[i] = m[i].m }
  Geom::Transformation.new(m)
 end
 def self.build(families)
  model=Sketchup.active_model
  data=load_data
  index=data['nodes'].map { |n| [n['id'],n] }.to_h
  defs={};materials={}
  model.start_operation('Build editable Gewan models',true)
  begin
  data['mats'].each do |key,col|
   mat=model.materials.add("GEWAN_#{key}")
   mat.color=Sketchup::Color.new(*col[0,3].map { |c| (c*255).round })
   mat.alpha=col[3] if col.length>3
   spec=data['material_info'][key] || {}
   if spec['texture']
    path=File.join(ROOT,spec['texture'])
    if File.file?(path)
     mat.texture=path
     begin
      tile=(spec['tile_m'] || 1).to_f.m
      mat.texture.size=[tile,tile]
     rescue StandardError
     end
    end
   end
   materials[key]=mat
  end
   build_def=nil
   build_def=lambda do |id|
    return defs[id] if defs.key?(id)
    n=index.fetch(id)
    childdefs=n['ch'].map { |ch| [ch,build_def.call(ch['n'])] }
    definition=model.definitions.add(n['name'])
    defs[id]=definition
    n['t'].group_by { |t| t[0] }.each do |key,tris|
     mesh=Geom::PolygonMesh.new(tris.length*2,tris.length)
     tris.each do |t|
      pts=t[1,3].map { |i| p=n['v'][i]; Geom::Point3d.new(p[0].to_f.m,p[1].to_f.m,p[2].to_f.m) }
      mesh.add_polygon(pts)
     end
     definition.entities.add_faces_from_mesh(mesh,0,materials.fetch(key),materials.fetch(key))
    end
    definition.entities.grep(Sketchup::Edge).each do |edge|
     next unless edge.faces.length==2
     dot=edge.faces[0].normal.dot(edge.faces[1].normal)
     if dot>0.99999
      edge.soft=true;edge.smooth=false
     elsif dot>0.91
      edge.soft=true;edge.smooth=true
     end
    end
    childdefs.each { |ch,child| definition.entities.add_instance(child,transform(ch['matrix'])) }
    definition.set_attribute('GEWAN','source_id',id)
    definition.set_attribute('GEWAN','geometry','Editable 3D mesh, not a picture plane')
    definition
   end
   instances=[]
   families.each_with_index do |family,fi|
    container=model.definitions.add("GEWAN_#{family}_Independent_Units")
    ids=data['roots'].fetch(family)
    ids.each_with_index do |id,i|
     record=data['records'].find { |r| r['id']==id }
     xyz=record ? record['at'] : [0,0,0]
     xyz ||= [0,0,0]
     tr=Geom::Transformation.translation(xyz.map { |x| x.to_f.m })
     unit=container.entities.add_instance(build_def.call(id),tr)
     unit.name=index[id]['name']
    end
    raise 'Unexpected loose geometry in collection' unless container.entities.all? { |e| e.is_a?(Sketchup::ComponentInstance) }
    if family!='Photo'
     ids.each do |id|
      raise 'Furniture was flattened' unless defs[id].entities.all? { |e| e.is_a?(Sketchup::ComponentInstance) }
     end
    end
    offset=families.length>1 ? (family=='Fish' ? [155,0,0] : family=='Photo' ? [0,-165,0] : [0,0,0]) : [0,0,0]
    instance=model.active_entities.add_instance(container,Geom::Transformation.translation(offset.map { |x| x.to_f.m }))
    instance.name="GEWAN #{family} - #{ids.length} editable units"
    instances << instance
   end
   model.commit_operation
   box=Geom::BoundingBox.new
   instances.each { |instance| box.add(instance.bounds) }
   model.active_view.zoom(instances)
   model.active_view.invalidate
   UI.messagebox("Created #{families.sum { |f| data['roots'][f].length }} editable units.\nDouble-click the collection to select a unit. Double-click a building to select independent chairs, tables, cups and plates.\nExplode only the container level when needed. Exploding an individual cup or chair naturally exposes its own geometry.\nUse File > Save As to save SKP.\nPhoto artworks are interpretations of the approved images, not exact dimensioned replicas.")
  rescue Exception => e
   model.abort_operation
   UI.messagebox("Gewan build stopped; the operation was undone.\n#{e.class}: #{e.message}")
   puts e.full_message
  end
 end
 unless file_loaded?(__FILE__)
  menu=UI.menu('Extensions').add_submenu('Gewan Editable Models')
  menu.add_item('Build Star - 16 editable units') { build(['Star']) }
  menu.add_item('Build Fish Scale - 16 editable units') { build(['Fish']) }
  menu.add_item('Build Turtle Photo Art - 15 units') { build(['Photo']) }
  menu.add_item('Build ALL - 47 editable units') { build(['Star','Fish','Photo']) }
  file_loaded(__FILE__)
 end
end
