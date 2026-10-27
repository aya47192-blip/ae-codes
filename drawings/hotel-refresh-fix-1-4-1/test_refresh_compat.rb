module UI; end
module Sketchup
  class << self
    attr_accessor :active_model
  end
end
class ModelStub
  attr_accessor :active_view
  def initialize(view); @active_view = view; end
end
class ViewStub
  attr_reader :invalidates
  def initialize; @invalidates = 0; end
  def invalidate; @invalidates += 1; end
end
path = ARGV.fetch(0)
view = ViewStub.new
Sketchup.active_model = ModelStub.new(view)
# Reproduce the actual missing-method failure before loading the bridge.
begin
  UI.refresh
  raise 'Expected legacy UI.refresh failure was not reproduced'
rescue NoMethodError => error
  raise unless error.name == :refresh
end
load path
raise 'Legacy call must return nil' unless UI.refresh.nil?
raise 'The active view did not receive the redraw' unless view.invalidates == 1
UI.refresh(true)
raise 'Optional legacy arguments failed' unless view.invalidates == 2
raise 'Double install replaced an existing method' if AyaaLobbyRefreshCompat141.install_legacy_bridge
UI.singleton_class.send(:remove_method, :refresh)
UI.define_singleton_method(:refresh) { :existing_implementation }
raise 'Existing UI implementation was replaced' if AyaaLobbyRefreshCompat141.install_legacy_bridge
raise 'Existing UI implementation changed' unless UI.refresh == :existing_implementation
UI.singleton_class.send(:remove_method, :refresh)
AyaaLobbyRefreshCompat141.install_legacy_bridge
Sketchup.active_model = nil
raise unless UI.refresh.nil?
Sketchup.active_model = ModelStub.new(nil)
raise unless UI.refresh.nil?
refresh_only = Object.new
refresh_only.define_singleton_method(:refresh) { @refreshed = true }
Sketchup.active_model = ModelStub.new(refresh_only)
UI.refresh
raise 'Fallback View.refresh did not run' unless refresh_only.instance_variable_get(:@refreshed)
broken = Object.new
broken.define_singleton_method(:invalidate) { raise 'Simulated redraw failure' }
Sketchup.active_model = ModelStub.new(broken)
raise 'Redraw error escaped into the build transaction' unless UI.refresh.nil?
Sketchup.active_model = ModelStub.new(Object.new)
raise unless UI.refresh.nil?
puts 'PASS: missing-method reproduced; legacy calls, existing-method preservation, idempotence, nil models/views, refresh fallback and redraw failure isolation verified.'
