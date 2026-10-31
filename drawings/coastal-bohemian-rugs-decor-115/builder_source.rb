require 'sketchup.rb'
require 'json'
require 'zlib'
require 'tmpdir'
require_relative 'refresh_compat'
require_relative 'geometry_bounds'
module AyaaRugsDecorLibrary115
  LARGE = 1000.0
  INCHES_PER_M = 1.0 / 0.0254
  def self.refresh_view(model)
    AyaaLobbyRefreshCompat141.refresh_view(model)
  end
  def self.read_json(path)
    if path.end_with?('.gz')
      Zlib::GzipReader.open(path) { |f| JSON.parse(f.read) }
    else
      JSON.parse(File.read(path, :encoding => 'UTF-8'))
    end
  end
  def self.large_matrix(values)
    a = values.map(&:to_f)
    [12, 13, 14].each { |i| a[i] *= INCHES_PER_M * LARGE }
    Geom::Transformation.new(a)
  end
  def self.make_materials(model, base, rows, prefix)
    rows.each_with_object({}) do |row, materials|
      name = "#{prefix}_#{row['id']}_#{row['name']}"
      m = model.materials[name]
      if m
        materials[row['id']] = m
        next
      end
      m = model.materials.add(name)
      c = row.fetch('color').first(3).map { |v| [[(v * 255).round, 0].max, 255].min }
      if row['texture']
        texture = File.join(base, row['texture'])
        raise "Missing texture: #{texture}" unless File.file?(texture)
        m.texture = texture
      else
        m.color = Sketchup::Color.new(*c)
      end
      m.alpha = row['alpha'] if row['alpha']
      materials[row['id']] = m
    end
  end

  # Curved surfaces retain their geometry with softened facet edges; sharp corners remain.
  # Hide coplanar/smooth facet edges without erasing topology or welding separate meshes.
  def self.clean_surface(entities, soften_cosine = 0.819152)
    entities.grep(Sketchup::Group).each { |group| clean_surface(group.entities, soften_cosine) }
    entities.grep(Sketchup::Edge).each do |edge|
      faces = edge.faces
      next unless faces.length == 2
      next unless faces[0].normal.dot(faces[1].normal) > soften_cosine
      edge.soft = true
      edge.smooth = true
      edge.hidden = true
    end
    0
  end
  def self.native_surface_area(entities, transformation = Geom::Transformation.new)
    entities.inject(0.0) do |area, entity|
      if entity.is_a?(Sketchup::Face)
        area + entity.area(transformation)
      elsif entity.is_a?(Sketchup::Group)
        area + native_surface_area(entity.entities, transformation * entity.transformation)
      else
        area
      end
    end
  end
  def self.hide_foliage_edges(entities)
    entities.grep(Sketchup::Edge).each { |e| e.hidden = true; e.soft = true; e.smooth = true }
    entities.grep(Sketchup::Group).each { |g| hide_foliage_edges(g.entities) }
  end
  def self.make_part(model, base, part, materials, prefix)
    cache_key = part.fetch('file')
    definition = @definition_cache[cache_key]
    unless definition
      data = read_json(File.join(base, part.fetch('file')))
      definition = model.definitions.add("#{prefix}_#{part.fetch('name')}")
      containers = {}
      data.fetch('meshes').each_with_index do |surface, surface_index|
        key = [surface['geometry'] || surface['name'], surface['material'], surface['matrix_m']]
        container = containers[key]
        unless container
          container = definition.entities.add_group
          container.name = surface['name']
          container.transformation = large_matrix(surface.fetch('matrix_m'))
          container.set_attribute('AyaaRugsDecor115', 'curved_surface', true) if surface['curve_smoothing']
          container.set_attribute('AyaaRugsDecor115', 'foliage_surface', true) if surface['name'].to_s.include?('Foliage')
          containers[key] = container
        end
        # Keep UV charts in separate geometry contexts.
        group = container.entities.add_group
        group.name = "UV_chart_#{surface_index}"
        points = surface.fetch('points')
        triangles = surface.fetch('faces')
        polygon_mesh = Geom::PolygonMesh.new(points.length, triangles.length)
        remap = [nil]
        points.each do |point|
          index = polygon_mesh.add_point(Geom::Point3d.new(point[0] * INCHES_PER_M * LARGE, point[1] * INCHES_PER_M * LARGE, point[2] * INCHES_PER_M * LARGE))
          uv = Geom::Point3d.new(point[3], point[4], 1.0)
          polygon_mesh.set_uv(index, uv, true)
          polygon_mesh.set_uv(index, uv, false)
          remap << index
        end
        triangles.each do |triangle|
          polygon_mesh.add_polygon(triangle.map { |i| i < 0 ? -remap[-i] : remap[i] })
        end
        material = materials.fetch(surface.fetch('material'))
        flags = Geom::PolygonMesh::HIDE_BASED_ON_INDEX | Geom::PolygonMesh::SOFTEN_BASED_ON_INDEX | Geom::PolygonMesh::SMOOTH_SOFT_EDGES
        success = group.entities.fill_from_mesh(polygon_mesh, true, flags, material, material)
        raise "Mesh could not be built: #{surface['name']}" unless success
        # Keep independent UV charts in independent contexts: no explode/merge with coincident faces.
      end
      containers.each_value do |container|
        clean_surface(container.entities, container.get_attribute('AyaaRugsDecor115', 'curved_surface', false) ? 0.499999 : 0.819152)
        if container.get_attribute('AyaaRugsDecor115', 'foliage_surface', false)
          hide_foliage_edges(container.entities)
        end
      end
      if part['category'] == 'floor' && part['expected_floor_area_in2']
        area = native_surface_area(definition.entities) / (LARGE * LARGE)
        expected_area = part['expected_floor_area_in2']
        tolerance = [expected_area * 0.00001, 0.05].max
        raise "Floor area check failed: #{part['name']}" if (area - expected_area).abs > tolerance
      end
      @definition_cache[cache_key] = definition
    end
    # Build large to avoid SketchUp's small-face tolerance, then restore original size.
    root_values = part.fetch('transform_inches').map(&:to_f)
    [0, 1, 2, 4, 5, 6, 8, 9, 10].each { |i| root_values[i] /= LARGE }
    instance = model.entities.add_instance(definition, Geom::Transformation.new(root_values))
    instance.name = part.fetch('name')
    tag = "Ayaa Rugs Decor - #{part['style']} #{part['category']=='rug' ? 'Rugs' : 'Decor'}"
    instance.layer = model.layers[tag] || model.layers.add(tag)
    instance.set_attribute('AyaaRugsDecor115', 'asset_id', part.fetch('id'))
    instance.set_attribute('AyaaRugsDecor115', 'category', part.fetch('category'))
    raise "No visible geometry in #{part['name']}" if instance.bounds.empty?
    if part['bounds_inches']
      b = AyaaRugsDecorBounds115.for_instance(instance)
      raise "No vertex geometry in #{part['name']}" if b.empty?
      actual = [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z]
      error = actual.zip(part['bounds_inches']).map { |a, e| (a - e).abs }.max
      raise "Size/position check failed for #{part['name']} (#{error} inches)" if error > 0.004
    end
    instance
  end
  VERSION = '1.0.0'
  def self.manifest
    @manifest ||= read_json(File.join(File.dirname(__FILE__),'payload','manifest.json'))
  end
  def self.prepare
    if Sketchup.active_model.active_path
      UI.messagebox('Close component editing before adding a library piece.'); return false
    end
    @definition_cache={}
    true
  end
  def self.get_piece(model,part,materials)
    definition=model.definitions.find { |d| d.get_attribute('AyaaRugsDecor115','id')==part['id'] && d.get_attribute('AyaaRugsDecor115','version')==VERSION }
    if definition
      instance=model.entities.add_instance(definition,Geom::Transformation.new)
    else
      instance=make_part(model,File.join(File.dirname(__FILE__),'payload'),part,materials,'AYAA_RUGS_DECOR_115')
      definition=instance.definition
      definition.entities.transform_entities(Geom::Transformation.scaling(1.0/LARGE),definition.entities.to_a)
      instance.transformation=Geom::Transformation.new
      definition.name="#{part['id']} - #{part['title']}"
      definition.description="#{part['style']} / #{part['category']} / Complete independent component"
      definition.set_attribute('AyaaRugsDecor115','id',part['id'])
      definition.set_attribute('AyaaRugsDecor115','version',VERSION)
      definition.set_attribute('AyaaRugsDecor115','dimensions_m',part['dimensions_m'])
    end
    instance.name="#{part['id']} - #{part['title']}"
    instance.set_attribute('AyaaRugsDecor115','asset_id',part['id'])
    instance.set_attribute('AyaaRugsDecor115','style',part['style'])
    instance.set_attribute('AyaaRugsDecor115','category',part['category'])
    tag="Ayaa Rugs Decor - #{part['style']} #{part['category']=='rug' ? 'Rugs' : 'Decor'}"
    instance.layer=model.layers[tag] || model.layers.add(tag)
    b=AyaaRugsDecorBounds115.for_instance(instance);actual=[b.min.x,b.min.y,b.min.z,b.max.x,b.max.y,b.max.z]
    error=actual.zip(part['bounds_inches']).map { |a,e| (a-e).abs }.max
    raise "Dimensions changed for #{part['id']}: #{error} inches" if error>0.004
    instance
  end
  def self.materials(model)
    make_materials(model,File.join(File.dirname(__FILE__),'payload'),manifest.fetch('materials'),'AYAA_RUGS_DECOR_115')
  end
  def self.show_view(parts,plan=false)
    return if parts.empty?
    model=Sketchup.active_model;b=Geom::BoundingBox.new;parts.each { |p| b.add(p.bounds) };c=b.center;s=[b.width,b.depth,2.m].max
    eye=plan ? c.offset(Geom::Vector3d.new(0,0,s*2)) : c.offset(Geom::Vector3d.new(s*0.3,-s*0.7,s*0.7))
    model.active_view.camera=Sketchup::Camera.new(eye,c,Geom::Vector3d.new(0,1,plan ? 0 : 1),false)
    model.active_view.zoom(parts);refresh_view(model)
  end
  def self.report_error(error,current)
    path=File.join(Dir.tmpdir,'Ayaa_Rugs_Decor_115_error.log')
    begin;File.write(path,([current,"#{error.class}: #{error.message}"]+Array(error.backtrace)).join("\n"));rescue StandardError;end
    UI.messagebox("Ayaa Rugs & Decor: #{error.class}: #{error.message}\nPiece: #{current}\n#{path}")
  end
  def self.gallery(style=nil,rugs=nil)
    return unless prepare
    model=Sketchup.active_model;operation_open=false;current='manifest'
    begin
      rows=manifest.fetch('parts').select { |p| (style.nil? || p['style']==style) && (rugs.nil? || (p['category']=='rug')==rugs) }
      offset=model.entities.length>0 ? [model.bounds.max.x+3.m,model.bounds.min.y,0] : [0,0,0]
      model.start_operation('Add complete rugs and decor library',true);operation_open=true
      mm=materials(model);pieces=[]
      rows.each_with_index do |part,i|
        current=part['id'];Sketchup.status_text="Ayaa Rugs & Decor #{i+1}/#{rows.length} - #{part['id']}"
        instance=get_piece(model,part,mm);p=part['gallery_position_m'];instance.transformation=Geom::Transformation.translation([offset[0]+p[0].m,offset[1]+p[1].m,p[2].m]);pieces<<instance
        refresh_view(model) if i%4==0
      end
      raise 'Incomplete gallery' unless pieces.length==rows.length && pieces.all?(&:valid?)
      model.commit_operation;operation_open=false
      begin
        model.rendering_options['RenderMode']=4
        keys=[];model.rendering_options.each { |key,_value| keys<<key };%w[DrawProfiles DrawHidden DrawHiddenGeometry DrawHiddenObjects DrawBackEdges].each { |key| model.rendering_options[key]=false if keys.include?(key) }
        show_view(pieces,rugs==true)
      rescue StandardError => e;warn "Optional display: #{e.message}";end
      model.selection.clear;model.selection.add(pieces)
      UI.messagebox("#{pieces.length} complete independent components added.\nR01-R25: Coastal rugs; A01-A50: Coastal decor.\nB01-B20: Bohemian rugs; D01-D20: Bohemian decor.\nUse Copy/Paste or Move without Explode.\nUse this menu > Save model as SKP to save the library.")
    rescue StandardError => e
      model.abort_operation if operation_open;report_error(e,current)
    ensure;@definition_cache={};Sketchup.status_text='';end
  end
  def self.insert_piece(code)
    return unless prepare
    model=Sketchup.active_model;operation_open=false
    begin
      part=manifest.fetch('parts').find { |p| p['id']==code };raise 'Unknown piece' unless part
      model.start_operation("Insert #{code}",true);operation_open=true
      instance=get_piece(model,part,materials(model));definition=instance.definition;instance.erase!
      model.commit_operation;operation_open=false
      model.place_component(definition,false)
    rescue StandardError => e;model.abort_operation if operation_open;report_error(e,code)
    ensure;@definition_cache={};end
  end
  def self.catalogue
    @dialog ||= begin
      dialog=UI::HtmlDialog.new(dialog_title:'Ayaa Rugs & Decor - 115 independent blocks',preferences_key:'AyaaRugsDecor115',scrollable:true,resizable:true,width:1120,height:760,style:UI::HtmlDialog::STYLE_DIALOG)
      dialog.set_file(File.join(File.dirname(__FILE__),'catalogue.html'))
      dialog.add_action_callback('insert_piece') { |_context,code| insert_piece(code.to_s) }
      dialog
    end
    @dialog.show
  end
  def self.save_skp
    path=UI.savepanel('Save complete rugs and decor library',nil,'Ayaa_Coastal_Bohemian_Rugs_Decor.skp');return unless path
    path+='.skp' unless File.extname(path).downcase=='.skp'
    UI.messagebox('Save failed. Use File > Save As with a new name.') unless Sketchup.active_model.save(path)
  rescue StandardError => e;report_error(e,'save');end
  def self.export_selected
    model=Sketchup.active_model;rows=model.selection.grep(Sketchup::ComponentInstance).select { |e| e.get_attribute('AyaaRugsDecor115','asset_id') }
    if rows.empty?;UI.messagebox('Select one or more complete library components first.');return;end
    folder=UI.select_directory(title:'Save selected pieces as individual SKP files');return unless folder
    rows.each do |instance|
      name=instance.name.gsub(/[^A-Za-z0-9 _-]/,'_')
      raise "Save failed: #{name}" unless instance.definition.save_as(File.join(folder,name+'.skp'))
    end
    UI.messagebox("#{rows.length} independent SKP files saved.")
  rescue StandardError => e;report_error(e,'export selected');end
  unless file_loaded?(__FILE__)
    menu=UI.menu('Extensions').add_submenu('Ayaa Rugs + Decor 115')
    menu.add_item('Browse and INSERT one complete block') { catalogue }
    menu.add_separator
    menu.add_item('Add COASTAL RUGS - 25') { gallery('Coastal',true) }
    menu.add_item('Add COASTAL DECOR - 50') { gallery('Coastal',false) }
    menu.add_item('Add BOHEMIAN RUGS - 20') { gallery('Bohemian',true) }
    menu.add_item('Add BOHEMIAN DECOR - 20') { gallery('Bohemian',false) }
    menu.add_item('Add ALL 115 as a library') { gallery }
    menu.add_separator
    menu.add_item('Save model as SKP') { save_skp }
    menu.add_item('Export selected blocks as individual SKP') { export_selected }
    file_loaded(__FILE__)
  end
end
