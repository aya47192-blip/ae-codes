require 'sketchup.rb'
require 'json'
require 'zlib'
require 'tmpdir'
require_relative 'refresh_compat'
require_relative 'geometry_bounds'
module AyaaBohoCounterLibrary
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
  # Merge the planar faces themselves, so diagonals do not return while editing.
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
        container.set_attribute('AyaaBohoCounters', 'curved_surface', true) if surface['curve_smoothing']
        container.set_attribute('AyaaBohoCounters', 'foliage_surface', true) if surface['name'].to_s.include?('Foliage')
        containers[key] = container
      end
      # UV charts are temporary build groups, not separate finished geometry.
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
      clean_surface(container.entities, container.get_attribute('AyaaBohoCounters', 'curved_surface', false) ? 0.499999 : 0.819152)
      if container.get_attribute('AyaaBohoCounters', 'foliage_surface', false)
        hide_foliage_edges(container.entities)
      end
    end
    if part['category'] == 'floor' && part['expected_floor_area_in2']
      area = native_surface_area(definition.entities) / (LARGE * LARGE)
      expected_area = part['expected_floor_area_in2']
      tolerance = [expected_area * 0.00001, 0.05].max
      raise "Floor area check failed: #{part['name']}" if (area - expected_area).abs > tolerance
    end
    # Build large to avoid SketchUp's small-face tolerance, then restore original size.
    root_values = part.fetch('transform_inches').map(&:to_f)
    [0, 1, 2, 4, 5, 6, 8, 9, 10].each { |i| root_values[i] /= LARGE }
    instance = model.entities.add_instance(definition, Geom::Transformation.new(root_values))
    instance.name = part.fetch('name')
    if part['category'] == 'Rug'
      name = 'Coastal - Separate Rugs'
      instance.layer = model.layers[name] || model.layers.add(name)
    end
    instance.set_attribute('AyaaBohoCounters', 'asset_id', part.fetch('id'))
    instance.set_attribute('AyaaBohoCounters', 'category', part.fetch('category'))
    raise "No visible geometry in #{part['name']}" if instance.bounds.empty?
    if part['bounds_inches']
      b = AyaaBohoCounterBounds.for_instance(instance)
      raise "No vertex geometry in #{part['name']}" if b.empty?
      actual = [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z]
      error = actual.zip(part['bounds_inches']).map { |a, e| (a - e).abs }.max
      raise "Size/position check failed for #{part['name']} (#{error} inches)" if error > 0.004
    end
    instance
  end
  VERSION = '1.0.0'
  def self.manifest
    @manifest ||= read_json(File.join(File.dirname(__FILE__), 'payload', 'manifest.json'))
  end
  def self.assert_dimensions(instance, part)
    b = AyaaBohoCounterBounds.for_instance(instance)
    expected = part.fetch('bounds_inches')
    actual = [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z]
    error = actual.zip(expected).map { |a, e| (a - e).abs }.max
    raise "Dimensions changed: #{part['id']} (#{error} inches)" if error > 0.004
  end
  def self.get_piece(model, part, materials, prefix)
    definition = model.definitions.find do |d|
      d.get_attribute('AyaaBohoCounters', 'id') == part['id'] && d.get_attribute('AyaaBohoCounters', 'version') == VERSION
    end
    if definition
      instance = model.entities.add_instance(definition, Geom::Transformation.new)
    else
      base = File.join(File.dirname(__FILE__), 'payload')
      instance = make_part(model, base, part, materials, prefix)
      definition = instance.definition
      # Restore a true-size definition so native Place Component has the right scale.
      definition.entities.transform_entities(Geom::Transformation.scaling(1.0 / LARGE), definition.entities.to_a)
      instance.transformation = Geom::Transformation.new
      definition.name = "#{part['id']} - #{part['title']}"
      definition.description = "#{part['style']}: #{part['description']}"
      definition.set_attribute('AyaaBohoCounters', 'id', part['id'])
      definition.set_attribute('AyaaBohoCounters', 'version', VERSION)
      definition.set_attribute('AyaaBohoCounters', 'style', part['style'])
      definition.set_attribute('AyaaBohoCounters', 'dimensions_m', part['dimensions_m'])
    end
    assert_dimensions(instance, part)
    instance.name = "#{part['id']} - #{part['title']}"
    tag = "Ayaa Boho Counters - #{part['style']}"
    instance.layer = model.layers[tag] || model.layers.add(tag)
    instance.set_attribute('AyaaBohoCounters', 'id', part['id'])
    instance.set_attribute('AyaaBohoCounters', 'style', part['style'])
    instance
  end
  def self.prepare(model)
    if model.active_path
      UI.messagebox('Close component/group editing first. Existing model objects will not be changed.')
      return false
    end
    true
  end
  def self.report_error(error, code)
    puts error.full_message if error.respond_to?(:full_message)
    log_path = File.join(Dir.tmpdir, 'Ayaa_Boho_Counters_error.log')
    begin
      File.write(log_path, (["Ayaa Boho Counters #{VERSION}", code, "#{error.class}: #{error.message}"] + Array(error.backtrace)).join("\n"))
    rescue StandardError
      log_path = '(log could not be written)'
    end
    UI.messagebox("Ayaa Boho Counters Blocks: #{error.class}: #{error.message}\nPiece: #{code}\n#{log_path}")
  end
  def self.gallery(style = nil)
    model = Sketchup.active_model
    return unless prepare(model)
    operation_open = false
    current = 'catalogue'
    begin
      rows = manifest.fetch('parts').select { |p| style.nil? || p['style'] == style }
      # Add the library beside existing geometry; never clear or rebuild the lobby.
      if model.entities.length > 5
        UI.messagebox('Open File > New to build the complete library. Use Place ONE to insert a counter into your existing lobby.')
        return
      end
      nonempty = false
      offset = nonempty ? [model.bounds.max.x + 4.m, model.bounds.min.y, 0.0] : [0.0, 0.0, 0.0]
      model.start_operation('Add independent iconic pieces', true)
      operation_open = true
      materials = make_materials(model, File.join(File.dirname(__FILE__), 'payload'), manifest.fetch('materials'), 'AYAA_BOHO_COUNTERS_V100')
      pieces = []
      rows.each_with_index do |part, i|
        current = part['id']
        Sketchup.status_text = "Ayaa Boho Counters: #{i + 1}/#{rows.length} - #{part['title']}"
        instance = get_piece(model, part, materials, 'AYAA_BOHO_COUNTERS')
        instance.transformation = Geom::Transformation.translation([offset[0] + (i % 5) * 5.5.m, offset[1] + (i / 5) * 4.m, 0])
        pieces << instance
        refresh_view(model) if i % 3 == 0
      end
      raise 'Incomplete gallery' unless pieces.length == rows.length && pieces.all?(&:valid?)
      model.commit_operation
      operation_open = false
      model.selection.clear
      model.selection.add(pieces)
      begin
        model.rendering_options['RenderMode'] = 4
        keys = []
        model.rendering_options.each { |key, _value| keys << key }
        model.rendering_options['DrawProfiles'] = false if keys.include?('DrawProfiles')
        bounds = Geom::BoundingBox.new
        pieces.each { |piece| bounds.add(piece.bounds) }
        center = bounds.center
        span = [bounds.width, bounds.depth, 3.m].max
        eye = center.offset(Geom::Vector3d.new(span * 0.52, -span * 0.95, span * 0.72))
        model.active_view.camera = Sketchup::Camera.new(eye, center, Geom::Vector3d.new(0, 0, 1), false)
        model.active_view.zoom(pieces)
        refresh_view(model)
      rescue StandardError => display_error
        warn "Ayaa Boho Counters: optional camera skipped: #{display_error.message}"
      end
      save_library(model)
      UI.messagebox("#{pieces.length} complete independent components created.\nBK01-BK20: BOHEMIAN LOBBY RECEPTION COUNTERS.\nEach full arrangement selects as ONE piece. No Explode needed.\nCopy/Paste or Move a piece into your lobby reception; File > Save As to save this library.\nExisting lobby objects were preserved.")
    rescue StandardError => error
      model.abort_operation if operation_open
      report_error(error, current)
    ensure
      Sketchup.status_text = ''
    end
  end
  def self.insert_piece(code)
    model = Sketchup.active_model
    return unless prepare(model)
    operation_open = false
    begin
      part = manifest.fetch('parts').find { |p| p['id'] == code }
      raise "Unknown piece: #{code}" unless part
      model.start_operation("Load #{code}", true)
      operation_open = true
      materials = make_materials(model, File.join(File.dirname(__FILE__), 'payload'), manifest.fetch('materials'), 'AYAA_BOHO_COUNTERS_V100')
      instance = get_piece(model, part, materials, 'AYAA_BOHO_COUNTERS')
      definition = instance.definition
      # Only this temporary loading instance is removed; nothing in the model is selected/deleted.
      instance.erase!
      model.commit_operation
      operation_open = false
      model.place_component(definition, false)
    rescue StandardError => error
      model.abort_operation if operation_open
      report_error(error, code)
    end
  end
  def self.catalogue
    if @catalogue && @catalogue.visible?
      @catalogue.bring_to_front
      return
    end
    @catalogue = UI::HtmlDialog.new(:dialog_title => 'Ayaa Boho Counters - 20 complete pieces', :preferences_key => 'AyaaBohoCountersBlocks', :scrollable => true, :resizable => true, :width => 1040, :height => 760, :style => UI::HtmlDialog::STYLE_DIALOG)
    @catalogue.set_file(File.join(File.dirname(__FILE__), 'catalogue.html'))
    @catalogue.add_action_callback('place') do |_context, code|
      @catalogue.close
      insert_piece(code.to_s)
    end
    @catalogue.add_action_callback('gallery') do |_context, _unused|
      @catalogue.close
      gallery
    end
    @catalogue.show
  rescue StandardError => error
    report_error(error, 'catalogue')
  end
  def self.save_library(model = Sketchup.active_model)
    path = UI.savepanel('Save 20 Bohemian counters as SketchUp', nil, 'Ayaa_Bohemian_20_Reception_Counters.skp')
    return unless path
    path += '.skp' unless File.extname(path).downcase == '.skp'
    unless model.save(path)
      UI.messagebox('The components were built, but saving failed. Preserve your last saved file and try File > Save As with a NEW name.')
    end
  rescue StandardError => error
    UI.messagebox("Components remain in the model. Save failed: #{error.message}. Use File > Save As with a new name.")
  end
  unless file_loaded?(__FILE__)
    menu = UI.menu('Extensions').add_submenu('Ayaa Boho Counters 1.0')
    menu.add_item('Browse 20 reception counters') { catalogue }
    menu.add_item('Build ALL 20 and save SKP') { gallery }
    menu.add_item('Save model as SKP') { save_library }
    sub = menu.add_submenu('Place ONE reception counter')
    manifest.fetch('parts').each do |part|
      code = part['id']
      sub.add_item("#{code} - #{part['title']}") { insert_piece(code) }
    end
    file_loaded(__FILE__)
  end
end
