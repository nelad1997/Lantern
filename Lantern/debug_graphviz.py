import graphviz
import re

def check_graph():
    graph = graphviz.Digraph()
    graph.node('A', 'Large Node Name That Should Expand Naturally')
    graph.node('B', 'Another Node')
    graph.edge('A', 'B')
    
    svg = graph.pipe(format='svg').decode('utf-8')
    
    # Extract the <svg> tag attributes
    svg_tag = re.search(r'<svg.*?>', svg, re.DOTALL)
    if svg_tag:
        print(f"SVG TAG: {svg_tag.group(0)}")
    
    # Check if width/height are present
    width = re.search(r'width="([^"]*)"', svg)
    height = re.search(r'height="([^"]*)"', svg)
    viewbox = re.search(r'viewBox="([^"]*)"', svg)
    
    print(f"Width: {width.group(1) if width else 'None'}")
    print(f"Height: {height.group(1) if height else 'None'}")
    print(f"ViewBox: {viewbox.group(1) if viewbox else 'None'}")

if __name__ == "__main__":
    check_graph()
