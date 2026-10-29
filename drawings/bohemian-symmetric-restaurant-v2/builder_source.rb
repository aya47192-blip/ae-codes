require 'sketchup.rb'
require 'json'
require 'zlib'
require 'tmpdir'
require_relative 'refresh_compat'
require_relative 'geometry_bounds'
module AyaaBohoSymRestaurantV200
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
      m = model.materials.add("#{prefix}_#{row['id']}_#{row['name']}")
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
          container.set_attribute('AyaaSymRestaurantV200', 'curved_surface', true) if surface['curve_smoothing']
          container.set_attribute('AyaaSymRestaurantV200', 'foliage_surface', true) if surface['name'].to_s.include?('Foliage')
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
        clean_surface(container.entities, container.get_attribute('AyaaSymRestaurantV200', 'curved_surface', false) ? 0.499999 : 0.819152)
        if container.get_attribute('AyaaSymRestaurantV200', 'foliage_surface', false)
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
    category = part.fetch('category')
    tag = case category
    when 'ceiling' then 'Ayaa Symmetric Restaurant 2 - Roof'
    when 'wall', 'floor', 'column' then 'Ayaa Symmetric Restaurant 2 - Architecture'
    when 'wall_decor' then 'Ayaa Symmetric Restaurant 2 - Wall Decor'
    when 'ceiling_light', 'wall_light' then 'Ayaa Symmetric Restaurant 2 - Lighting'
    else 'Ayaa Symmetric Restaurant 2 - Furnishings'
    end
    instance.layer = model.layers[tag] || model.layers.add(tag)
    instance.set_attribute('AyaaSymRestaurantV200', 'asset_id', part.fetch('id'))
    instance.set_attribute('AyaaSymRestaurantV200', 'category', part.fetch('category'))
    instance.set_attribute('AyaaSymRestaurantV200', 'seating_capacity', part.fetch('capacity',0))
    raise "No visible geometry in #{part['name']}" if instance.bounds.empty?
    if part['bounds_inches']
      b = AyaaSymRestaurantBounds200.for_instance(instance)
      raise "No vertex geometry in #{part['name']}" if b.empty?
      actual = [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z]
      error = actual.zip(part['bounds_inches']).map { |a, e| (a - e).abs }.max
      raise "Size/position check failed for #{part['name']} (#{error} inches)" if error > 0.004
    end
    instance
  end
  def self.model_parts
    Sketchup.active_model.entities.grep(Sketchup::ComponentInstance).select { |e| e.get_attribute('AyaaSymRestaurantV200','asset_id') }
  end
  def self.view(kind, parts=nil)
    model=Sketchup.active_model;parts ||= model_parts;return if parts.empty?
    bounds=Geom::BoundingBox.new;parts.each { |p| bounds.add(p.bounds) };c=bounds.center;span=[bounds.width,bounds.depth,1.0].max
    if kind==:plan
      eye=c.offset(Geom::Vector3d.new(0,0,span*2));up=Geom::Vector3d.new(0,1,0)
    else
      eye=c.offset(Geom::Vector3d.new(span*0.75,-span*0.90,span*0.80));up=Geom::Vector3d.new(0,0,1)
    end
    model.active_view.camera=Sketchup::Camera.new(eye,c,up,false);model.active_view.zoom(parts);refresh_view(model)
  end
  def self.save_as_skp
    path=UI.savepanel('Save furnished Bohemian restaurant',nil,'Ayaa_Symmetric_Bohemian_Restaurant_v2.skp');return unless path
    path += '.skp' unless File.extname(path).downcase=='.skp'
    UI.messagebox('Model is built. Save failed; keep your previous file and use File > Save As with a new name.') unless Sketchup.active_model.save(path)
  rescue StandardError => error
    UI.messagebox("Model remains built. Saving failed: #{error.message}. Use File > Save As with a new name.")
  end
  def self.build
    model=Sketchup.active_model
    if model.active_path || model.entities.length>5
      UI.messagebox('Open File > New before building this standalone restaurant. Existing lobby/hotel models will not be replaced.');return
    end
    operation_open=false;created=[];current_part='manifest'
    begin
      base=File.join(File.dirname(__FILE__),'payload');manifest=read_json(File.join(base,'manifest.json'))
      model.start_operation('Build independent symmetric Bohemian restaurant v2',true);operation_open=true
      AyaaLobbyRefreshCompat141.install_legacy_bridge;@definition_cache={}
      prefix="AYAA_SYM_RESTAURANT_V2_#{Time.now.to_i}";materials=make_materials(model,base,manifest.fetch('materials'),prefix)
      manifest.fetch('parts').each_with_index do |part,i|
        current_part=part['name'];Sketchup.status_text="Restaurant: #{i+1}/#{manifest['parts'].length} - #{current_part}"
        created << make_part(model,base,part,materials,prefix)
        refresh_view(model) if i%20==0
      end
      raise 'Incomplete restaurant components' unless created.length==manifest['parts'].length && created.all?(&:valid?)
      roof=model.layers['Ayaa Symmetric Restaurant 2 - Roof'];roof.visible=false if roof
      model.set_attribute('AyaaSymRestaurantV200','source_dwg','lobby aya elshamy 3.dwg')
      model.set_attribute('AyaaSymRestaurantV200','dwg_origin_m',manifest['coordinate_origin_dwg'])
      model.set_attribute('AyaaSymRestaurantV200','seat_count',manifest['seat_count'])
      model.set_attribute('AyaaSymRestaurantV200','table_count',manifest['table_count'])
      model.set_attribute('AyaaSymRestaurantV200','capacity_basis','whole restaurant; 310 adopted seats after circulation checks')
      model.commit_operation;operation_open=false
      begin
        model.rendering_options['RenderMode']=4;keys=[];model.rendering_options.each { |key,_v| keys << key }
        %w[DrawProfiles DrawHidden DrawHiddenGeometry DrawHiddenObjects DrawBackEdges].each { |key| model.rendering_options[key]=false if keys.include?(key) }
        view(:plan,created);page=model.pages.add('01 - RESTAURANT PLAN');page.update
        view(:three_d,created);page3=model.pages.add('02 - BOHEMIAN DINING 3D');page3.update
        model.pages.selected_page=page;view(:plan,created)
      rescue StandardError => display_error
        warn "Optional review views skipped: #{display_error.message}"
      end
      puts "Ayaa Restaurant: #{created.length} independent complete pieces, #{manifest['table_count']} tables, #{manifest['seat_count']} seats"
      save_as_skp
      UI.messagebox("Restaurant built: #{manifest['table_count']} tables / #{manifest['seat_count']} seats.\nEach chair, table, banquette, service cabinet, planter and fixture is a complete independent component.\nThe roof is hidden for review. Use the menu for PLAN / 3D, roof, architecture, or furnishing selection.\nUse File > Save As if you skipped saving.")
    rescue StandardError => error
      model.abort_operation if operation_open
      path=File.join(Dir.tmpdir,'Ayaa_Symmetric_Restaurant_v2_error.log')
      begin;File.write(path,([current_part,"#{error.class}: #{error.message}"]+Array(error.backtrace)).join("\n"));rescue StandardError;end
      UI.messagebox("Restaurant build failed: #{error.class}: #{error.message}\nPart: #{current_part}\nDetails: #{path}")
    ensure
      @definition_cache={};Sketchup.status_text=''
    end
  end
  def self.toggle_tag(name)
    tag=Sketchup.active_model.layers[name];tag.visible=!tag.visible? if tag
  end
  def self.select_furnishings
    model=Sketchup.active_model;parts=model_parts.select { |e| %w[chair banquette table perimeter_banquette sideboard host planter].include?(e.get_attribute('AyaaSymRestaurantV200','category')) }
    model.selection.clear;model.selection.add(parts)
  end
  unless file_loaded?(__FILE__)
    menu=UI.menu('Extensions').add_submenu('Ayaa Symmetric Boho Restaurant 2.0')
    menu.add_item('Build SYMMETRIC restaurant v2 and save SKP') { build }
    menu.add_separator
    menu.add_item('View PLAN') { view(:plan) }
    menu.add_item('View 3D') { view(:three_d) }
    menu.add_item('Show / hide ROOF') { toggle_tag('Ayaa Symmetric Restaurant 2 - Roof') }
    menu.add_item('Show / hide ARCHITECTURE') { toggle_tag('Ayaa Symmetric Restaurant 2 - Architecture') }
    menu.add_item('Select complete furnishings') { select_furnishings }
    menu.add_item('Save model as SKP') { save_as_skp }
    file_loaded(__FILE__)
  end
end
