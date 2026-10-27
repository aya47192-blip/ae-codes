require 'sketchup.rb'
require 'extensions.rb'
require_relative 'ayaa_lobby_builder_v141/refresh_compat'
module AyaaLobbyV141
  unless file_loaded?(__FILE__)
    extension = SketchupExtension.new('Ayaa Lobby 1.4.1 - Independent Components', 'ayaa_lobby_builder_v141/main')
    extension.description = 'Refresh compatibility fix for SketchUp Desktop; unchanged Bohemian V5 and Greek Coastal V4 designs, plus original Modern options.'
    extension.version = '1.4.1'
    extension.creator = 'Ayaa Lobby'
    Sketchup.register_extension(extension, true)
    file_loaded(__FILE__)
  end
end
