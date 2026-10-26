require 'sketchup.rb'
require 'extensions.rb'
module AyaaLobbyDirect2026
  unless file_loaded?(__FILE__)
    extension = SketchupExtension.new('Ayaa Lobby - Independent Components', 'ayaa_lobby_builder/main')
    extension.description = 'Build complete New Modern, Bohemian V2 or Greek Coastal lobbies, each with independent whole-piece components and materials.'
    extension.version = '1.1.0'
    extension.creator = 'Ayaa Lobby'
    Sketchup.register_extension(extension, true)
    file_loaded(__FILE__)
  end
end
