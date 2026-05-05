import type { AttackGraph, TopologyNode, TopologyEdge } from '../types/pentest'

const LAYER_X: Record<string, number> = {
  attacker: 72,
  host: 232,
  service: 392,
  vulnerability: 552,
  data: 552,
}

const NODE_W = 136
const NODE_H = 40
const NODE_RX = 8
const SVG_W = 720
const PAD_Y = 28
const ROW_GAP = 16

function nodeColors(node: TopologyNode): { fill: string; stroke: string; text: string } {
  if (node.status === 'compromised') return { fill: '#1f0808', stroke: '#ef4444', text: '#fca5a5' }
  if (node.status === 'vulnerable') return { fill: '#1a1200', stroke: '#f59e0b', text: '#fcd34d' }
  switch (node.node_type) {
    case 'attacker':     return { fill: '#071a24', stroke: '#22d3ee', text: '#67e8f9' }
    case 'host':         return { fill: '#070f24', stroke: '#3b82f6', text: '#93c5fd' }
    case 'service':      return { fill: '#0e0724', stroke: '#8b5cf6', text: '#c4b5fd' }
    case 'vulnerability':return { fill: '#1a0808', stroke: '#ef4444', text: '#fca5a5' }
    case 'data':         return { fill: '#071a10', stroke: '#10b981', text: '#6ee7b7' }
    default:             return { fill: '#0d1117', stroke: '#334155', text: '#94a3b8' }
  }
}

function nodeIcon(type: string): string {
  switch (type) {
    case 'attacker':      return '⌖'
    case 'host':          return '◈'
    case 'service':       return '◉'
    case 'vulnerability': return '⚠'
    case 'data':          return '◆'
    default:              return '●'
  }
}

function buildPositions(nodes: TopologyNode[]): Map<string, { x: number; y: number }> {
  const layers: Record<string, TopologyNode[]> = {}
  for (const n of nodes) {
    const key = n.node_type === 'data' ? 'data' : n.node_type
    ;(layers[key] ??= []).push(n)
  }

  const positions = new Map<string, { x: number; y: number }>()
  for (const [layerType, layerNodes] of Object.entries(layers)) {
    const x = LAYER_X[layerType] ?? 552
    const startY = PAD_Y
    layerNodes.forEach((node, i) => {
      positions.set(node.id, { x, y: startY + i * (NODE_H + ROW_GAP) })
    })
  }
  return positions
}

function calcSvgHeight(positions: Map<string, { x: number; y: number }>): number {
  let maxY = 0
  for (const { y } of positions.values()) {
    if (y + NODE_H > maxY) maxY = y + NODE_H
  }
  return maxY + PAD_Y
}

function edgeColor(edgeType: string): string {
  if (edgeType === 'exploit') return '#ef4444'
  if (edgeType === 'vulnerability') return '#f59e0b'
  return '#22d3ee'
}

function EdgePath({
  edge,
  positions,
}: {
  edge: TopologyEdge
  positions: Map<string, { x: number; y: number }>
}) {
  const src = positions.get(edge.source)
  const tgt = positions.get(edge.target)
  if (!src || !tgt) return null

  const x1 = src.x + NODE_W
  const y1 = src.y + NODE_H / 2
  const x2 = tgt.x
  const y2 = tgt.y + NODE_H / 2
  const cx = (x1 + x2) / 2

  const color = edgeColor(edge.edge_type)
  const pathId = `path-${edge.source}-${edge.target}`
  const dashLen = Math.hypot(x2 - x1, y2 - y1) + 60

  return (
    <g>
      <defs>
        <marker
          id={`arrow-${edge.source}-${edge.target}`}
          markerWidth="8"
          markerHeight="8"
          refX="6"
          refY="3"
          orient="auto"
        >
          <path d="M0,0 L0,6 L8,3 z" fill={color} opacity="0.7" />
        </marker>
      </defs>
      <path
        id={pathId}
        d={`M${x1},${y1} C${cx},${y1} ${cx},${y2} ${x2},${y2}`}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeOpacity="0.5"
        strokeDasharray={dashLen}
        strokeDashoffset={dashLen}
        markerEnd={`url(#arrow-${edge.source}-${edge.target})`}
        style={{ animation: `dash-draw 0.8s ease forwards` }}
      />
      {edge.label && (
        <text fontSize="9" fill={color} opacity="0.7">
          <textPath href={`#${pathId}`} startOffset="40%">
            {edge.label}
          </textPath>
        </text>
      )}
    </g>
  )
}

function NodeRect({
  node,
  pos,
}: {
  node: TopologyNode
  pos: { x: number; y: number }
}) {
  const { fill, stroke, text } = nodeColors(node)
  const pulse = node.status === 'compromised' || node.status === 'vulnerable'

  return (
    <g
      style={{
        animation: 'node-appear 0.4s ease forwards',
        opacity: 0,
      }}
    >
      {pulse && (
        <rect
          x={pos.x - 3}
          y={pos.y - 3}
          width={NODE_W + 6}
          height={NODE_H + 6}
          rx={NODE_RX + 2}
          fill="none"
          stroke={stroke}
          strokeWidth="1"
          strokeOpacity="0.3"
          style={{ animation: 'pulse-ring 2s ease-in-out infinite' }}
        />
      )}
      <rect
        x={pos.x}
        y={pos.y}
        width={NODE_W}
        height={NODE_H}
        rx={NODE_RX}
        fill={fill}
        stroke={stroke}
        strokeWidth="1.5"
      />
      <text
        x={pos.x + 14}
        y={pos.y + NODE_H / 2 + 1}
        dominantBaseline="middle"
        fontSize="12"
        fill={stroke}
      >
        {nodeIcon(node.node_type)}
      </text>
      <text
        x={pos.x + 28}
        y={pos.y + NODE_H / 2}
        dominantBaseline="middle"
        fontSize="10"
        fill={text}
        style={{ fontFamily: 'monospace' }}
      >
        {node.label.length > 14 ? node.label.slice(0, 13) + '…' : node.label}
      </text>
      {node.detail && (
        <text
          x={pos.x + 28}
          y={pos.y + NODE_H / 2 + 12}
          dominantBaseline="middle"
          fontSize="8"
          fill={stroke}
          opacity="0.6"
          style={{ fontFamily: 'monospace' }}
        >
          {node.detail}
        </text>
      )}
    </g>
  )
}

export function AttackGraphView({ graph }: { graph: AttackGraph }) {
  if (!graph.nodes.length) {
    return (
      <div className="attack-graph-empty">
        <span className="attack-graph-empty-icon">◈</span>
        <p>Graph builds as steps complete…</p>
      </div>
    )
  }

  const positions = buildPositions(graph.nodes)
  const svgH = calcSvgHeight(positions)

  return (
    <div className="attack-graph-wrap">
      <svg
        width="100%"
        viewBox={`0 0 ${SVG_W} ${svgH}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ display: 'block' }}
      >
        {/* Layer labels */}
        {(['attacker', 'host', 'service', 'vulnerability'] as const).map((layer) => {
          const hasNodes = graph.nodes.some(
            (n) => n.node_type === layer || (layer === 'vulnerability' && (n.node_type === 'vulnerability' || n.node_type === 'data')),
          )
          if (!hasNodes) return null
          return (
            <text
              key={layer}
              x={(LAYER_X[layer] ?? 552) + NODE_W / 2}
              y="12"
              textAnchor="middle"
              fontSize="9"
              fill="#334155"
              style={{ fontFamily: 'monospace', textTransform: 'uppercase', letterSpacing: '0.05em' }}
            >
              {layer === 'vulnerability' ? 'vulns / data' : layer}
            </text>
          )
        })}

        {/* Edges drawn first (below nodes) */}
        {graph.edges.map((edge) => (
          <EdgePath
            key={`${edge.source}-${edge.target}`}
            edge={edge}
            positions={positions}
          />
        ))}

        {/* Nodes */}
        {graph.nodes.map((node) => {
          const pos = positions.get(node.id)
          if (!pos) return null
          return <NodeRect key={node.id} node={node} pos={pos} />
        })}
      </svg>
    </div>
  )
}
