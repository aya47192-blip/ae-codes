require 'sketchup.rb'
require 'json'
require 'zlib'
module AyaaLobbyV140
  LARGE = 1000.0
  INCHES_PER_M = 1.0 / 0.0254
  def self.refresh_view(model)
    view = model.active_view
    view.invalidate if view.respond_to?(:invalidate)
    view.refresh if view.respond_to?(:refresh)
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
  # Merge the planar faces themselves, so diagonals do not return while editing.
  # Curved surfaces retain their geometry with softened facet edges; sharp corners remain.
  def self.clean_surface(entities, soften_cosine = 0.819152)
    planar = entities.grep(Sketchup::Edge).select do |edge|
      faces = edge.faces
      next false unless faces.length == 2
      a, b = faces
      next false unless a.material == b.material && a.back_material == b.back_material
      next false unless a.normal.dot(b.normal) > 0.99999999
      b.vertices.all? { |v| v.position.distance_to_plane(a.plane).abs < 0.002 }
    end
    entities.erase_entities(planar) unless planar.empty?
    entities.grep(Sketchup::Edge).each do |edge|
      faces = edge.faces
      next unless faces.length == 2
      next unless faces[0].normal.dot(faces[1].normal) > soften_cosine
      edge.soft = true
      edge.smooth = true
      edge.hidden = true
    end
    planar.length
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
        container.set_attribute('AyaaLobby', 'curved_surface', true) if surface['curve_smoothing']
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
      group.entities.fill_from_mesh(polygon_mesh, true, flags, material, material)
      group.explode
    end
    containers.each_value do |container|
      clean_surface(container.entities, container.get_attribute('AyaaLobby', 'curved_surface', false) ? 0.499999 : 0.819152)
    end
    if part['category'] == 'floor'
      # One editable face context for all finish regions: rectangles split faces
      # rather than creating a second face above a nested surface group.
      containers.each_value { |container| container.explode }
      clean_surface(definition.entities)
      floor_faces = definition.entities.grep(Sketchup::Face)
      raise "No editable floor faces: #{part['name']}" if floor_faces.empty?
      if part['expected_floor_area_in2']
        area = floor_faces.inject(0.0) { |sum, face| sum + face.area } / (LARGE * LARGE)
        expected_area = part['expected_floor_area_in2']
        tolerance = [expected_area * 0.00001, 0.05].max
        raise "Floor area check failed: #{part['name']}" if (area - expected_area).abs > tolerance
      end
    end
    # Build large to avoid SketchUp's small-face tolerance, then restore original size.
    root_values = part.fetch('transform_inches').map(&:to_f)
    [0, 1, 2, 4, 5, 6, 8, 9, 10].each { |i| root_values[i] /= LARGE }
    instance = model.entities.add_instance(definition, Geom::Transformation.new(root_values))
    instance.name = part.fetch('name')
    instance.set_attribute('AyaaLobby', 'asset_id', part.fetch('id'))
    instance.set_attribute('AyaaLobby', 'category', part.fetch('category'))
    raise "No visible geometry in #{part['name']}" if instance.bounds.empty?
    if part['bounds_inches']
      b = instance.bounds
      actual = [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z]
      error = actual.zip(part['bounds_inches']).map { |a, e| (a - e).abs }.max
      raise "Size/position check failed for #{part['name']} (#{error} inches)" if error > 0.004
    end
    instance
  end
  def self.build(slug)
    model = Sketchup.active_model
    if model.active_path
      UI.messagebox('Close component editing first, then choose the lobby again.')
      return
    end
    if model.entities.length > 5
      UI.messagebox('Open a NEW SketchUp model first. The default person is allowed. Your existing design will not be replaced.')
      return
    end
    base = File.join(File.dirname(__FILE__), slug)
    manifest = read_json(File.join(base, 'manifest.json'))
    operation_open = false
    created = []
    begin
      model.start_operation('Build independent lobby components', true)
      operation_open = true
      prefix = "AYAA_#{Time.now.to_i}"
      materials = make_materials(model, base, manifest.fetch('materials'), prefix)
      total = manifest.fetch('parts').length
      manifest.fetch('parts').each_with_index do |part, i|
        Sketchup.status_text = "Ayaa Lobby - #{manifest['title']} - #{i + 1}/#{total}: #{part['name']}"
        created << make_part(model, base, part, materials, prefix)
        refresh_view(model) if i % 4 == 0
      end
      raise 'Some components were not created.' unless created.length == total
      raise 'Some components are empty.' unless created.all? { |e| e.valid? && !e.bounds.empty? }
      model.rendering_options['RenderMode'] = 4
      available_render_options = []
      model.rendering_options.each { |key, value| available_render_options << key }
      ['DrawHidden', 'DrawHiddenGeometry', 'DrawHiddenObjects', 'DrawBackEdges', 'DrawProfiles'].each do |key|
        model.rendering_options[key] = false if available_render_options.include?(key)
      end
      bounds = Geom::BoundingBox.new
      created.each { |e| bounds.add(e.bounds) }
      center = bounds.center
      span = [bounds.width, bounds.depth, bounds.height].max
      eye = center.offset(Geom::Vector3d.new(-span * 0.8, span * 0.8, span))
      model.active_view.camera = Sketchup::Camera.new(eye, center, Geom::Vector3d.new(0, 0, 1))
      model.active_view.zoom(created)
      model.commit_operation
      operation_open = false
      report = { 'components_created' => created.length, 'whole_furniture_components' => manifest['parts'].count { |p| p['category'] == 'furniture' }, 'build_method' => 'native SketchUp geometry; no DAE import', 'version' => '1.4.0' }
      puts JSON.pretty_generate(report)
      path = UI.savepanel('Save lobby as SketchUp', nil, manifest.fetch('output_skp'))
      if path
        path += '.skp' unless File.extname(path).downcase == '.skp'
        raise 'The model was built, but SketchUp could not save it. Use File > Save As.' unless model.save(path)
        begin
          File.write(path + '.build-report.json', JSON.pretty_generate(report))
        rescue StandardError
        end
      end
      UI.messagebox("Ayaa Lobby: #{created.length} complete, independent components CREATED.\n#{report['whole_furniture_components']} complete furniture pieces. Select any piece with one click; do not Explode.\nUse File > Save As if you did not save yet.")
    rescue StandardError => error
      model.abort_operation if operation_open
      puts error.full_message if error.respond_to?(:full_message)
      UI.messagebox("Ayaa Lobby BUILD FAILED; no success has been reported.\n#{error.class}: #{error.message}\nPlease send a screenshot of this error.")
    ensure
      Sketchup.status_text = ''
    end
  end
  unless file_loaded?(__FILE__)
    menu = UI.menu('Extensions').add_submenu('Ayaa Lobby 1.4')
    menu.add_item('Build NEW MODERN - original layout') { build('new_modern_components') }
    menu.add_item('Build MODERN ALTERNATIVE V2 - new floor and layout') { build('modern_alternative_v2') }
    menu.add_item('Build BOHEMIAN V5 - family lounges and library') { build('bohemian_distinct_v5') }
    menu.add_item('Build GREEK COASTAL V4 - new stone reception and full walls') { build('greek_coastal_distinct_v4') }
    file_loaded(__FILE__)
  end
end
