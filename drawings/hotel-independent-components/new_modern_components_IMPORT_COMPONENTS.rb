# Imports each whole asset separately; does not depend on COLLADA group retention.
require 'sketchup.rb'
require 'json'
module AyaaIndependentComponents2026
  def self.run(base)
    manifest = JSON.parse(File.read(File.join(base, 'parts.json'), :encoding => 'UTF-8'))
    model = Sketchup.active_model
    unless model.active_path.nil? && model.entities.empty?
      UI.messagebox('Open a NEW EMPTY SketchUp model first, then run this file again. Existing work will not be replaced.')
      return
    end
    parts = manifest.fetch('parts')
    parts.each do |part|
      path = File.join(base, part.fetch('file'))
      raise "Missing asset: #{path}. Extract the entire ZIP first." unless File.file?(path)
    end
    model.start_operation('Import independent whole-piece components', true)
    operation_open = true
    begin
      parts.each_with_index do |part, i|
        Sketchup.status_text = "#{manifest['title']}: #{i + 1}/#{parts.length} - #{part['name']}"
        before = model.entities.to_a
        raise "Import failed: #{part['name']}" unless model.import(File.join(base, part.fetch('file')), false)
        added = model.entities.to_a - before
        raise "No imported geometry: #{part['name']}" if added.empty?
        # Whatever the importer does internally, ONLY this complete asset is wrapped.
        instance = model.entities.add_group(added).to_component
        instance.definition.name = part.fetch('name')
        instance.name = part.fetch('name')
        instance.transform!(Geom::Transformation.new(part.fetch('transform_inches')))
        instance.set_attribute('AyaaParts', 'asset_id', part.fetch('id'))
        instance.set_attribute('AyaaParts', 'category', part.fetch('category'))
        raise "Empty component: #{part['name']}" if instance.definition.entities.empty?
      end
      actual = model.entities.to_a
      unless actual.length == parts.length && actual.all? { |e| e.is_a?(Sketchup::ComponentInstance) }
        raise 'Component check failed: unexpected top-level geometry.'
      end
      ids = actual.map { |e| e.get_attribute('AyaaParts', 'asset_id') }
      raise 'Component ID check failed.' unless ids.sort == parts.map { |p| p.fetch('id') }.sort
      model.rendering_options['RenderMode'] = 4 # Shaded with Textures
      model.active_view.zoom_extents
      model.commit_operation
      operation_open = false
      target = File.join(base, manifest.fetch('output_skp'))
      index = 1
      while File.exist?(target)
        target = File.join(base, File.basename(manifest.fetch('output_skp'), '.skp') + "_#{index}.skp")
        index += 1
      end
      saved = model.save(target)
      report = { 'independent_components' => actual.length, 'furniture' => parts.count { |p| p['category'] == 'furniture' }, 'loose_top_level_edges_or_faces' => 0, 'saved_skp' => saved ? target : nil }
      begin
        File.write(File.join(base, 'sketchup_import_report.json'), JSON.pretty_generate(report))
      rescue StandardError
        # A read-only folder must not discard the assembled model.
      end
      if saved
        UI.messagebox("Saved #{actual.length} independent components.\nEach complete chair/table/counter is selectable directly. Do NOT Explode.\n#{target}")
      else
        UI.messagebox('Components assembled. Use File > Save As to save the SKP in a writable folder.')
      end
    rescue StandardError => error
      model.abort_operation if operation_open
      UI.messagebox(error.message)
      raise
    ensure
      Sketchup.status_text = ''
    end
  end
end
AyaaIndependentComponents2026.run(File.dirname(__FILE__))
