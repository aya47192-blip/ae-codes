# SketchUp 2023 has no UI.refresh. Some already-loaded Ayaa releases call it.
# Supply that missing entry point without replacing a native/third-party method.
module AyaaLobbyRefreshCompat141
  def self.refresh_view(model = nil)
    model ||= Sketchup.active_model if defined?(Sketchup) && Sketchup.respond_to?(:active_model)
    return nil unless model && model.respond_to?(:active_view)
    view = model.active_view
    return nil unless view
    if view.respond_to?(:invalidate)
      view.invalidate
    elsif view.respond_to?(:refresh)
      view.refresh
    end
    nil
  rescue StandardError => error
    # A redraw failure must never abort the geometry-building transaction.
    warn "Ayaa Lobby: optional redraw skipped (#{error.class}: #{error.message})"
    nil
  end

  def self.install_legacy_bridge
    return false unless defined?(UI)
    return false if UI.respond_to?(:refresh)
    UI.define_singleton_method(:refresh) do |*_args|
      AyaaLobbyRefreshCompat141.refresh_view
    end
    true
  end
end
AyaaLobbyRefreshCompat141.install_legacy_bridge
