require 'sketchup.rb'
require 'extensions.rb'
module AyaaLobbyDirect2026
  unless file_loaded?(__FILE__)
    extension = SketchupExtension.new('Ayaa Lobby - Independent Components', 'ayaa_lobby_builder/main')
    extension.description = 'Rich Bohemian V4 and Greek Coastal V3 with complete seating groups, designed walls, equipped bars and independent components. Original Modern choices included.'
    extension.version = '1.3.0'
    extension.creator = 'Ayaa Lobby'
    Sketchup.register_extension(extension, true)
    file_loaded(__FILE__)
  end
end
