# Instance#bounds transforms the definition's bounding box, not each actual
# vertex. Rotated/curved furniture can therefore have much larger API boxes.
module AyaaLobbyGeometryBounds142
  def self.collect(entities, world_transform, result)
    seen = {}
    entities.each do |entity|
      case entity
      when Sketchup::Edge
        entity.vertices.each do |vertex|
          next if seen[vertex.entityID]
          seen[vertex.entityID] = true
          result.add(world_transform * vertex.position)
        end
      when Sketchup::Group
        collect(entity.entities, world_transform * entity.transformation, result)
      when Sketchup::ComponentInstance
        collect(entity.definition.entities, world_transform * entity.transformation, result)
      end
    end
    result
  end

  def self.for_instance(instance)
    collect(instance.definition.entities, instance.transformation, Geom::BoundingBox.new)
  end
end
