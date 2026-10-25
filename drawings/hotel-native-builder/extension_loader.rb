require 'sketchup.rb'
require 'extensions.rb'
module AyaaLobbyDirect2026
  unless file_loaded?(__FILE__)
    extension = SketchupExtension.new('Ayaa Lobby - Independent Components', 'ayaa_lobby_builder/main')
    extension.description = 'Build the New Modern or latest Bohemian lobby as independent complete components, including materials. No COLLADA import.'
    extension.version = '1.0.0'
    extension.creator = 'Ayaa Lobby'
    Sketchup.register_extension(extension, true)
    file_loaded(__FILE__)
  end
end
