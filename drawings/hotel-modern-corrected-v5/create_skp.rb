# Import the DAE next to this file and turn each complete NEW_ assembly into a component.
require 'sketchup.rb'
module AyaaModernV5
  def self.label(entity)
    name = entity.name.to_s
    name = entity.definition.name.to_s if name.empty? && entity.respond_to?(:definition)
    name
  end
  def self.visit(entities)
    entities.to_a.each do |entity|
      next unless entity.is_a?(Sketchup::Group) || entity.is_a?(Sketchup::ComponentInstance)
      children = entity.is_a?(Sketchup::Group) ? entity.entities : entity.definition.entities
      name = label(entity)
      if name.start_with?('NEW_')
        component = entity.is_a?(Sketchup::Group) ? entity.to_component : entity
        component.definition.name = name
        component.name = name
      else
        visit(children)
      end
    end
  end
  def self.unpack_containers(entities)
    entities.to_a.each do |entity|
      next unless entity.is_a?(Sketchup::Group) || entity.is_a?(Sketchup::ComponentInstance)
      name = label(entity)
      children = entity.is_a?(Sketchup::Group) ? entity.entities : entity.definition.entities
      if name =~ /^(Collection_|01_ORIGINAL_|10_NEW_FLOOR_|11_NEW_MODERN_|12_NEW_LIGHTING|AYAA_HOTEL|LobbyScene|hotel_modern|hotel_bohemian|ayaa_hotel_new_modern)/i
        entity.explode
        unpack_containers(entities)
        return
      else
        unpack_containers(children) unless name.start_with?('NEW_')
      end
    end
  end
  def self.run
    file = File.join(File.dirname(__FILE__), 'hotel_modern_corrected_v5.dae')
    raise 'Keep this script beside the supplied DAE and textures folder.' unless File.exist?(file)
    model = Sketchup.active_model
    model.start_operation('NEW MODERN / CORRECTED V5', true)
    begin
      raise 'DAE import failed.' unless model.import(file, false)
      visit(model.entities)
      unpack_containers(model.entities)
      model.active_view.zoom_extents
      model.commit_operation
      target = File.join(File.dirname(__FILE__), 'hotel_modern_corrected_v5.skp')
      index = 1
      while File.exist?(target)
        target = File.join(File.dirname(__FILE__), 'hotel_modern_corrected_v5_' + index.to_s + '.skp')
        index += 1
      end
      raise 'The model imported, but SketchUp could not save the SKP.' unless model.save(target)
      UI.messagebox('Imported with textures and saved as SKP beside the DAE. NEW_ assemblies are independent components.')
    rescue => error
      model.abort_operation
      UI.messagebox(error.message)
      raise
    end
  end
end
AyaaModernV5.run
