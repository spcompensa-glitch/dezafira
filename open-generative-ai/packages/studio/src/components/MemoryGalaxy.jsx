import React, { useRef, useEffect, useState, useCallback } from 'react';
import * as d3 from 'd3';

// ============================================================================
// Types
// ============================================================================

interface GraphNode {
  id: string;
  label: string;
  content: string;
  type: 'memory' | 'skill' | 'project' | 'note' | 'training' | 'session';
  tags: string[];
  createdAt: string;
  updatedAt: string;
  connections: string[];
  index?: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  strength: number;
  type: 'link' | 'reference' | 'contribution';
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ============================================================================
// Constants
// ============================================================================

const NODE_COLORS: Record<string, string> = {
  memory: '#cba6f7',
  skill: '#a6e3a1',
  project: '#fab387',
  note: '#89b4fa',
  training: '#f9e2af',
  session: '#f38ba8',
};

const NODE_GLOW: Record<string, string> = {
  memory: 'rgba(203,166,247,0.5)',
  skill: 'rgba(166,227,161,0.5)',
  project: 'rgba(250,179,135,0.5)',
  note: 'rgba(137,180,250,0.5)',
  training: 'rgba(249,226,175,0.5)',
  session: 'rgba(243,139,168,0.5)',
};

const NODE_ICONS: Record<string, string> = {
  memory: '🧠',
  skill: '🔧',
  project: '📁',
  note: '📝',
  training: '📊',
  session: '💬',
};

const BASE_RADIUS: Record<string, number> = {
  memory: 10,
  skill: 9,
  project: 13,
  note: 8,
  training: 11,
  session: 8,
};

function getNodeRadius(node: GraphNode): number {
  const base = BASE_RADIUS[node.type] || 9;
  const connCount = node.connections?.length || 0;
  return base + Math.sqrt(connCount) * 2;
}

// ============================================================================
// ForceGraph Component
// ============================================================================

interface ForceGraphProps {
  data: GraphData;
  onNodeClick: (node: GraphNode) => void;
  selectedNodeId?: string;
  searchQuery?: string;
}

function ForceGraph({ data, onNodeClick, selectedNodeId, searchQuery }: ForceGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null);
  const zoomRef = useRef<any>(null);
  const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null);
  const nodesSelRef = useRef<d3.Selection<SVGGElement, GraphNode, SVGGElement, unknown> | null>(null);
  const linksSelRef = useRef<any>(null);
  const initializedRef = useRef(false);
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, title: '', preview: '', type: '' });
  const particleAnimRef = useRef<number | null>(null);
  const particleLayerRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null);

  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setDimensions({ width, height });
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (!svgRef.current || data.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const { width, height } = dimensions;
    const defs = svg.append('defs');

    Object.entries(NODE_GLOW).forEach(([type, glowColor]) => {
      const filter = defs.append('filter')
        .attr('id', `glow-${type}`)
        .attr('x', '-50%').attr('y', '-50%')
        .attr('width', '200%').attr('height', '200%');
      filter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'coloredBlur');
      const feMerge = filter.append('feMerge');
      feMerge.append('feMergeNode').attr('in', 'coloredBlur');
      feMerge.append('feMergeNode').attr('in', 'SourceGraphic');
    });

    const selFilter = defs.append('filter')
      .attr('id', 'glow-selected')
      .attr('x', '-50%').attr('y', '-50%')
      .attr('width', '200%').attr('height', '200%');
    selFilter.append('feGaussianBlur').attr('stdDeviation', '6').attr('result', 'coloredBlur');
    const selMerge = selFilter.append('feMerge');
    selMerge.append('feMergeNode').attr('in', 'coloredBlur');
    selMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => { g.attr('transform', event.transform.toString()); });

    svg.call(zoom as any);
    zoomRef.current = zoom;

    svg.append('rect')
      .attr('width', width).attr('height', height)
      .attr('fill', 'transparent').style('cursor', 'grab');

    const g = svg.append('g');
    gRef.current = g;

    const particleLayer = g.append('g').attr('class', 'particles');
    particleLayerRef.current = particleLayer;

    const simulation = d3.forceSimulation<GraphNode>(data.nodes)
      .force('link', d3.forceLink<GraphNode, GraphEdge>(data.edges)
        .id(d => d.id).distance(90).strength(d => d.strength * 0.6))
      .force('charge', d3.forceManyBody().strength(-350))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius((d: any) => getNodeRadius(d) + 8));

    simulationRef.current = simulation;

    const links = g.append('g')
      .attr('stroke', '#585b70').attr('stroke-opacity', 0.25)
      .selectAll('line').data(data.edges).join('line')
      .attr('stroke-width', d => Math.max(0.5, Math.sqrt(d.strength) * 1.5));
    linksSelRef.current = links;

    const nodes = g.append('g')
      .selectAll<SVGGElement, GraphNode>('g').data(data.nodes).join('g')
      .attr('cursor', 'pointer')
      .call((d3.drag() as any)
        .on('start', (event: any, d: any) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event: any, d: any) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event: any, d: any) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      );
    nodesSelRef.current = nodes;

    nodes.append('circle')
      .attr('class', 'node-halo')
      .attr('r', d => getNodeRadius(d) + 4)
      .attr('fill', 'none')
      .attr('stroke', d => NODE_COLORS[d.type] || '#cba6f7')
      .attr('stroke-opacity', 0.15).attr('stroke-width', 2);

    nodes.append('circle')
      .attr('class', 'node-main')
      .attr('r', d => getNodeRadius(d))
      .attr('fill', d => NODE_COLORS[d.type] || '#cba6f7')
      .attr('fill-opacity', 0.85).attr('stroke', 'none').attr('stroke-width', 0)
      .style('filter', d => `url(#glow-${d.type})`)
      .style('transition', 'r 0.2s ease, fill-opacity 0.2s ease');

    nodes.append('text')
      .attr('class', 'node-label')
      .attr('dy', d => getNodeRadius(d) + 14)
      .attr('text-anchor', 'middle')
      .style('font-size', '11px').style('fill', '#a6adc8')
      .style('pointer-events', 'none')
      .style('opacity', d => getNodeRadius(d) > 16 ? 0.8 : 0)
      .text(d => d.label.length <= 18 ? d.label : d.label.slice(0, 18) + '…');

    nodes
      .on('mouseenter', function (event, d) {
        d3.select(this).select('.node-main')
          .transition().duration(200)
          .attr('r', getNodeRadius(d) * 1.15).attr('fill-opacity', 1);
        d3.select(this).select('.node-label')
          .transition().duration(150).style('opacity', 1);

        const preview = d.content ? d.content.slice(0, 150) + (d.content.length > 150 ? '…' : '') : 'Sem conteúdo';
        const rect = containerRef.current?.getBoundingClientRect();
        if (rect) {
          setTooltip({
            visible: true, x: event.clientX - rect.left + 16, y: event.clientY - rect.top + 16,
            title: d.label, preview, type: d.type,
          });
        }

        if (!selectedNodeId) {
          const connectedIds = new Set(d.connections || []);
          connectedIds.add(d.id);
          nodes.transition().duration(200)
            .style('opacity', (n: GraphNode) => connectedIds.has(n.id) ? 1 : 0.15);
          links.transition().duration(200)
            .style('opacity', (e: any) => {
              const src = typeof e.source === 'string' ? e.source : e.source.id;
              const tgt = typeof e.target === 'string' ? e.target : e.target.id;
              return (src === d.id || tgt === d.id) ? 0.7 : 0.05;
            });
        }
      })
      .on('mousemove', function (event) {
        const rect = containerRef.current?.getBoundingClientRect();
        if (rect && tooltip.visible) {
          setTooltip(prev => ({ ...prev, x: event.clientX - rect.left + 16, y: event.clientY - rect.top + 16 }));
        }
      })
      .on('mouseleave', function (event, d) {
        d3.select(this).select('.node-main')
          .transition().duration(200)
          .attr('r', getNodeRadius(d)).attr('fill-opacity', 0.85);
        d3.select(this).select('.node-label')
          .transition().duration(150)
          .style('opacity', function (this: any) {
            const n = d3.select(this.parentNode).datum() as GraphNode;
            return selectedNodeId === n.id ? 1 : getNodeRadius(n) > 16 ? 0.8 : 0;
          });
        setTooltip(prev => ({ ...prev, visible: false }));
        if (!selectedNodeId) {
          nodes.transition().duration(200).style('opacity', 1);
          links.transition().duration(200).style('opacity', 0.25);
        }
      })
      .on('click', (event, d) => { event.stopPropagation(); onNodeClick(d); })
      .on('dblclick', (event, d) => {
        event.preventDefault(); event.stopPropagation();
        if (svgRef.current && zoomRef.current && d.x != null && d.y != null) {
          const scale = 2;
          const transform = d3.zoomIdentity
            .translate(dimensions.width / 2 - d.x * scale, dimensions.height / 2 - d.y * scale)
            .scale(scale);
          d3.select(svgRef.current).transition().duration(750).call(zoomRef.current.transform, transform);
        }
      });

    simulation.on('tick', () => {
      links
        .attr('x1', d => (d.source as GraphNode).x!)
        .attr('y1', d => (d.source as GraphNode).y!)
        .attr('x2', d => (d.target as GraphNode).x!)
        .attr('y2', d => (d.target as GraphNode).y!);
      nodes.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    initializedRef.current = true;

    return () => {
      simulation.stop();
      initializedRef.current = false;
      if (particleAnimRef.current) { cancelAnimationFrame(particleAnimRef.current); particleAnimRef.current = null; }
    };
  }, [data, dimensions]);

  useEffect(() => {
    if (!initializedRef.current || !nodesSelRef.current || !linksSelRef.current) return;
    const nodes = nodesSelRef.current;
    const links = linksSelRef.current;

    if (particleAnimRef.current) { cancelAnimationFrame(particleAnimRef.current); particleAnimRef.current = null; }

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      nodes.select('.node-main').transition().duration(200)
        .attr('fill-opacity', d => {
          const match = d.label.toLowerCase().includes(q) || d.content.toLowerCase().includes(q) || d.tags.some(t => t.toLowerCase().includes(q));
          return match ? 1 : 0.12;
        });
      nodes.transition().duration(200).style('opacity', 1);
      links.transition().duration(200).style('opacity', 0.05);
      return;
    }

    if (selectedNodeId) {
      const selectedNode = data.nodes.find(n => n.id === selectedNodeId);
      const connectedIds = new Set(selectedNode?.connections || []);
      connectedIds.add(selectedNodeId);

      nodes.select('.node-main').transition().duration(300)
        .attr('fill-opacity', (n: GraphNode) => connectedIds.has(n.id) ? 1 : 0.15)
        .attr('stroke', (n: GraphNode) => n.id === selectedNodeId ? '#cdd6f4' : 'none')
        .attr('stroke-width', (n: GraphNode) => n.id === selectedNodeId ? 2.5 : 0)
        .style('filter', (n: GraphNode) => {
          if (n.id === selectedNodeId) return 'url(#glow-selected)';
          return connectedIds.has(n.id) ? `url(#glow-${n.type})` : 'none';
        });

      nodes.select('.node-halo').transition().duration(300)
        .attr('stroke-opacity', (n: GraphNode) => {
          if (n.id === selectedNodeId) return 0.6;
          return connectedIds.has(n.id) ? 0.25 : 0.05;
        });

      nodes.select('.node-label').transition().duration(200)
        .style('opacity', (n: GraphNode) => {
          if (n.id === selectedNodeId) return 1;
          return connectedIds.has(n.id) ? 0.9 : 0;
        });

      links.transition().duration(300)
        .attr('stroke-width', (e: any) => {
          const src = typeof e.source === 'string' ? e.source : e.source.id;
          const tgt = typeof e.target === 'string' ? e.target : e.target.id;
          return (src === selectedNodeId || tgt === selectedNodeId) ? 2 : 0.5;
        })
        .style('opacity', (e: any) => {
          const src = typeof e.source === 'string' ? e.source : e.source.id;
          const tgt = typeof e.target === 'string' ? e.target : e.target.id;
          return (src === selectedNodeId || tgt === selectedNodeId) ? 0.8 : 0.05;
        })
        .attr('stroke', (e: any) => {
          const src = typeof e.source === 'string' ? e.source : e.source.id;
          const tgt = typeof e.target === 'string' ? e.target : e.target.id;
          return (src === selectedNodeId || tgt === selectedNodeId) ? NODE_COLORS[selectedNode?.type || 'note'] : '#585b70';
        });
    } else {
      nodes.select('.node-main').transition().duration(300)
        .attr('fill-opacity', 0.85).attr('stroke', 'none').attr('stroke-width', 0)
        .style('filter', (n: GraphNode) => `url(#glow-${n.type})`);
      nodes.select('.node-halo').transition().duration(300).attr('stroke-opacity', 0.15);
      nodes.select('.node-label').transition().duration(200)
        .style('opacity', (n: GraphNode) => getNodeRadius(n) > 16 ? 0.8 : 0);
      nodes.transition().duration(200).style('opacity', 1);
      links.transition().duration(300)
        .attr('stroke-width', (d: GraphEdge) => Math.max(0.5, Math.sqrt(d.strength) * 1.5))
        .style('opacity', 0.25).attr('stroke', '#585b70');
    }
  }, [selectedNodeId, searchQuery, data.nodes]);

  const handleZoomIn = useCallback(() => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 1.4);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 0.7);
    }
  }, []);

  const handleZoomReset = useCallback(() => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current).transition().duration(500).call(zoomRef.current.transform, d3.zoomIdentity);
    }
  }, []);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative', background: '#1e1e2e' }}>
      <svg ref={svgRef} style={{ width: '100%', height: '100%', background: '#1e1e2e' }} />

      {tooltip.visible && (
        <div style={{
          position: 'absolute', left: Math.min(tooltip.x, (dimensions.width || 800) - 280),
          top: Math.min(tooltip.y, (dimensions.height || 600) - 150),
          maxWidth: 280, background: '#1e1e2e', border: '1px solid #45475a',
          borderRadius: 8, padding: '10px 14px', zIndex: 50,
          pointerEvents: 'none', boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: NODE_COLORS[tooltip.type] || '#cba6f7',
              boxShadow: `0 0 6px ${NODE_COLORS[tooltip.type] || '#cba6f7'}`,
            }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: '#cdd6f4' }}>{tooltip.title}</span>
          </div>
          <div style={{ fontSize: 11, color: '#a6adc8', lineHeight: 1.5 }}>{tooltip.preview}</div>
        </div>
      )}

      <div style={{ position: 'absolute', bottom: 16, right: 16, display: 'flex', flexDirection: 'column', gap: 4, zIndex: 10 }}>
        <button onClick={handleZoomIn} style={zoomBtnStyle}>+</button>
        <button onClick={handleZoomOut} style={zoomBtnStyle}>−</button>
        <button onClick={handleZoomReset} style={{ ...zoomBtnStyle, fontSize: 14 }}>⌂</button>
      </div>

      <div style={{
        position: 'absolute', bottom: 16, left: 16,
        background: 'rgba(24,24,37,0.9)', borderRadius: 10,
        padding: '12px 16px', border: '1px solid #313244', zIndex: 10,
        backdropFilter: 'blur(12px)',
      }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Tipos de Node
        </div>
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, boxShadow: `0 0 6px ${color}` }} />
            <span style={{ fontSize: 12, color: '#a6adc8' }}>{NODE_ICONS[type]} {type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const zoomBtnStyle: React.CSSProperties = {
  width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: 'rgba(24,24,37,0.9)', border: '1px solid #313244', borderRadius: 8,
  color: '#cdd6f4', fontSize: 18, fontWeight: 500, cursor: 'pointer', backdropFilter: 'blur(12px)',
};

// ============================================================================
// Sidebar Component
// ============================================================================

interface SidebarProps {
  nodes: GraphNode[];
  selectedNodeId?: string;
  onNodeSelect: (node: GraphNode) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

function Sidebar({ nodes, selectedNodeId, onNodeSelect, searchQuery, onSearchChange }: SidebarProps) {
  const grouped = nodes.reduce((acc, node) => {
    if (!acc[node.type]) acc[node.type] = [];
    acc[node.type].push(node);
    return acc;
  }, {} as Record<string, GraphNode[]>);

  return (
    <div style={{
      width: 260, background: '#181825', borderRight: '1px solid #313244',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #313244' }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#cdd6f4', marginBottom: 8 }}>
          🧠 Memória Galáxia
        </div>
        <input
          type="text"
          placeholder="🔍 Buscar memórias..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          style={{
            width: '100%', padding: '8px 12px', background: '#1e1e2e',
            border: '1px solid #45475a', borderRadius: 6, color: '#cdd6f4',
            fontSize: 12, outline: 'none',
          }}
        />
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '8px 0' }}>
        {Object.entries(grouped).map(([type, typeNodes]) => (
          <div key={type} style={{ marginBottom: 8 }}>
            <div style={{
              padding: '4px 16px', fontSize: 11, fontWeight: 600,
              color: '#a6adc8', textTransform: 'uppercase', letterSpacing: '0.05em',
            }}>
              {NODE_ICONS[type]} {type} ({typeNodes.length})
            </div>
            {typeNodes.map(node => (
              <div
                key={node.id}
                onClick={() => onNodeSelect(node)}
                style={{
                  padding: '6px 16px 6px 24px', cursor: 'pointer',
                  background: selectedNodeId === node.id ? '#313244' : 'transparent',
                  color: selectedNodeId === node.id ? '#cdd6f4' : '#a6adc8',
                  fontSize: 12, borderBottom: '1px solid #1e1e2e',
                  display: 'flex', alignItems: 'center', gap: 8,
                }}
              >
                <div style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: NODE_COLORS[node.type], flexShrink: 0,
                }} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {node.label}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>

      <div style={{
        padding: '8px 16px', borderTop: '1px solid #313244',
        fontSize: 11, color: '#585b70', display: 'flex', justifyContent: 'space-between',
      }}>
        <span>{nodes.length} nodes</span>
        <span>{Object.keys(grouped).length} tipos</span>
      </div>
    </div>
  );
}

// ============================================================================
// Content Panel Component
// ============================================================================

interface ContentPanelProps {
  node: GraphNode | null;
  onClose: () => void;
}

function ContentPanel({ node, onClose }: ContentPanelProps) {
  if (!node) return null;

  return (
    <div style={{
      width: 320, background: '#181825', borderLeft: '1px solid #313244',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #313244',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            background: NODE_COLORS[node.type], boxShadow: `0 0 8px ${NODE_COLORS[node.type]}`,
          }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: '#cdd6f4' }}>{node.label}</span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none', border: 'none', color: '#585b70',
            cursor: 'pointer', fontSize: 18,
          }}
        >×</button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 4, textTransform: 'uppercase' }}>Tipo</div>
          <div style={{ fontSize: 13, color: '#cdd6f4' }}>{NODE_ICONS[node.type]} {node.type}</div>
        </div>

        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 4, textTransform: 'uppercase' }}>Tags</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {node.tags.map(tag => (
              <span key={tag} style={{
                padding: '2px 8px', background: '#313244', borderRadius: 4,
                fontSize: 11, color: '#a6adc8',
              }}>{tag}</span>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 4, textTransform: 'uppercase' }}>Conteúdo</div>
          <div style={{ fontSize: 13, color: '#cdd6f4', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            {node.content}
          </div>
        </div>

        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 4, textTransform: 'uppercase' }}>Conexões</div>
          <div style={{ fontSize: 13, color: '#cdd6f4' }}>
            {node.connections.length} node(s) conectado(s)
          </div>
        </div>

        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#a6adc8', marginBottom: 4, textTransform: 'uppercase' }}>Criado em</div>
          <div style={{ fontSize: 12, color: '#585b70' }}>
            {new Date(node.createdAt).toLocaleDateString('pt-BR')}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main MemoryGalaxy Component
// ============================================================================

export default function MemoryGalaxy() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ nodes: 0, edges: 0, types: 0 });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      // Try to load from API first, fallback to static data
      const res = await fetch('/api/memory/sync');
      if (res.ok) {
        const data = await res.json();
        setGraphData({ nodes: data.nodes || [], edges: data.edges || [] });
        setStats({
          nodes: data.nodes?.length || 0,
          edges: data.edges?.length || 0,
          types: new Set(data.nodes?.map((n: GraphNode) => n.type) || []).size,
        });
      } else {
        // Fallback: load from static JSON
        const nodesRes = await fetch('/data/memory/nodes.json');
        const edgesRes = await fetch('/data/memory/edges.json');
        if (nodesRes.ok && edgesRes.ok) {
          const nodes = await nodesRes.json();
          const edges = await edgesRes.json();
          setGraphData({ nodes, edges });
          setStats({ nodes: nodes.length, edges: edges.length, types: new Set(nodes.map((n: GraphNode) => n.type)).size });
        }
      }
    } catch (err) {
      console.error('Failed to load graph data:', err);
      // Load empty state
      setGraphData({ nodes: [], edges: [] });
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (node: GraphNode) => {
    setSelectedNode(node);
  };

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
  };

  if (loading) {
    return (
      <div style={{
        width: '100%', height: '100%', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        background: '#1e1e2e', color: '#cdd6f4',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🌌</div>
          <div style={{ fontSize: 16, marginBottom: 8 }}>Carregando Memória Galáxia...</div>
          <div style={{ fontSize: 12, color: '#585b70' }}>Conectando com Nous Hermes Agent</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', background: '#1e1e2e' }}>
      <Sidebar
        nodes={graphData.nodes}
        selectedNodeId={selectedNode?.id}
        onNodeSelect={handleNodeClick}
        searchQuery={searchQuery}
        onSearchChange={handleSearch}
      />

      <div style={{ flex: 1, position: 'relative' }}>
        <ForceGraph
          data={graphData}
          onNodeClick={handleNodeClick}
          selectedNodeId={selectedNode?.id}
          searchQuery={searchQuery}
        />

        {/* Stats bar */}
        <div style={{
          position: 'absolute', top: 12, left: 12,
          background: 'rgba(24,24,37,0.9)', borderRadius: 8,
          padding: '8px 14px', border: '1px solid #313244',
          display: 'flex', gap: 16, fontSize: 11, color: '#a6adc8',
          backdropFilter: 'blur(12px)',
        }}>
          <span>Nodes: <strong style={{ color: '#cdd6f4' }}>{stats.nodes}</strong></span>
          <span>Conexões: <strong style={{ color: '#cdd6f4' }}>{stats.edges}</strong></span>
          <span>Tipos: <strong style={{ color: '#cdd6f4' }}>{stats.types}</strong></span>
          <span style={{ color: '#a6e3a1' }}>● Conectado</span>
        </div>
      </div>

      <ContentPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
    </div>
  );
}
