require 'sketchup.rb'
require 'extensions.rb'
module AyaaLobbyDirect2026
  unless file_loaded?(__FILE__)
    extension = SketchupExtension.new('Ayaa Lobby - Independent Components', 'ayaa_lobby_builder/main')
    extension.description = 'Complete furnished New Modern, Modern Alternative, Bohemian V3 and Greek Coastal V2 options with editable independent pieces and cleaned surface topology.'
    extension.version = '1.2.0'
    extension.creator = 'Ayaa Lobby'
    Sketchup.register_extension(extension, true)
    file_loaded(__FILE__)
  end
end
