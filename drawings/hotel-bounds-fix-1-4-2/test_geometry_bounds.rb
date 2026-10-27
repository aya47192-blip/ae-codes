# Native API shape mocks isolate the bounds calculation, not SketchUp geometry creation.
module Geom
  class Point3d
    attr_reader :x, :y, :z
    def initialize(x,y,z); @x,@y,@z=x,y,z; end
    def to_a; [@x,@y,@z]; end
  end
  class Transformation
    attr_reader :values
    def initialize(a=nil); @values=a || [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]; end
    def *(other)
      a=@values
      if other.is_a?(Transformation)
        b=other.values
        Transformation.new((0...16).map { |i| row=i%4; col=i/4; (0...4).inject(0.0) { |s,k| s+a[k*4+row]*b[col*4+k] } })
      else
        p=other.to_a+[1.0]
        q=(0...3).map { |r| (0...4).inject(0.0) { |s,k| s+a[k*4+r]*p[k] } }
        Point3d.new(*q)
      end
    end
  end
  class BoundingBox
    def initialize; @lo=[Float::INFINITY]*3; @hi=[-Float::INFINITY]*3; end
    def add(point)
      point.to_a.each_with_index { |v,i| @lo[i]=[@lo[i],v].min; @hi[i]=[@hi[i],v].max };self
    end
    def min; Point3d.new(*@lo); end
    def max; Point3d.new(*@hi); end
  end
end
module Sketchup
  class Vertex
    attr_reader :position
    def initialize(p); @position=Geom::Point3d.new(*p); end
    def entityID; object_id; end
  end
  class Edge
    attr_reader :vertices
    def initialize(a,b); @vertices=[a,b]; end
  end
  class Group
    attr_reader :entities,:transformation
    def initialize(entities,t);@entities,@transformation=entities,t;end
  end
  class ComponentInstance
    attr_reader :definition,:transformation
    def initialize(entities,t);@definition=Struct.new(:entities).new(entities);@transformation=t;end
  end
end
load ARGV.fetch(0)
load ARGV.fetch(1)
max_error=0.0
CASES.each_with_index do |row,index|
  name,root,surfaces,expected=row
  groups=surfaces.map.with_index do |s,j|
    matrix,points=s
    vertices=points.map { |p| Sketchup::Vertex.new(p) }
    # A shared vertex appears on adjacent edges, matching native mesh topology.
    edges=vertices.each_with_index.map { |v,k| Sketchup::Edge.new(v,vertices[(k+1)%vertices.length]) }
    klass=j.even? ? Sketchup::Group : Sketchup::ComponentInstance
    klass.new(edges,Geom::Transformation.new(matrix))
  end
  instance=Sketchup::ComponentInstance.new(groups,Geom::Transformation.new(root))
  b=AyaaLobbyGeometryBounds142.for_instance(instance)
  actual=b.min.to_a+b.max.to_a
  err=actual.zip(expected).map { |a,e| (a-e).abs }.max
  max_error=[max_error,err].max
  raise "#{name}: #{err} inches" if err>0.004
end
puts "PASS: #{CASES.length} actual component payloads, nested groups and component instances; max exact-geometry bounds error #{max_error} inches."
