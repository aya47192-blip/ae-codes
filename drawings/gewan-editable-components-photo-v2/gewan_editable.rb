require 'sketchup.rb'
require 'extensions.rb'
module GewanEditable2026
 unless file_loaded?(__FILE__)
  ext=SketchupExtension.new('Gewan Editable Models', 'gewan_editable/main')
  ext.description='Independent furniture components and turtle photo-landmark concept models.'
  ext.version='2.0.0'
  ext.creator='Gewan Design Study'
  Sketchup.register_extension(ext,true)
  file_loaded(__FILE__)
 end
end
