import React from 'react'
import { ResponsiveBar } from '@nivo/bar'
import { ResponsiveLine } from '@nivo/line'
import { ResponsivePie } from '@nivo/pie'

const NIVO_THEME = {
  background: 'transparent',
  text: { fontFamily: "'DM Mono', monospace", fontSize: 11, fill: '#a0aec0' },
  axis: {
    domain: { line: { stroke: 'rgba(99, 102, 241, 0.2)', strokeWidth: 1 } },
    ticks: {
      line: { stroke: 'rgba(99, 102, 241, 0.2)', strokeWidth: 1 },
      text: { fill: '#a0aec0', fontSize: 11 },
    },
    legend: { text: { fill: '#a0aec0', fontSize: 12 } },
  },
  grid: { line: { stroke: 'rgba(99, 102, 241, 0.1)', strokeWidth: 1 } },
  legends: { text: { fill: '#a0aec0', fontSize: 11 } },
  tooltip: {
    container: {
      background: 'rgba(15, 15, 30, 0.95)',
      border: '1px solid rgba(99, 102, 241, 0.3)',
      borderRadius: '8px',
      color: '#f5f7fb',
      fontFamily: "'DM Mono', monospace",
      fontSize: 12,
      padding: '10px 14px',
      backdropFilter: 'blur(10px)',
    },
  },
}

// ── Bar Chart ─────────────────────────────────────────────────────────────────

function BarChart({ data, xKey, yKey, title }) {
  const chartData = data.rows?.map((row) => ({
    [xKey]: String(row[xKey]),
    [yKey]: Number(row[yKey]),
  })) ?? []

  if (!chartData.length) return null

  return (
    <div style={{ height: 320 }}>
      <ResponsiveBar
        data={chartData}
        keys={[yKey]}
        indexBy={xKey}
        theme={NIVO_THEME}
        colors={['#6366f1']}
        borderRadius={4}
        borderWidth={0}
        padding={0.35}
        margin={{ top: 20, right: 20, bottom: 60, left: 70 }}
        axisBottom={{
          tickRotation: chartData.length > 5 ? -35 : 0,
          tickSize: 4,
        }}
        axisLeft={{ tickSize: 4 }}
        enableLabel={false}
        enableGridX={false}
        enableGridY={true}
        animate={true}
        motionConfig="gentle"
        tooltip={({ id, value, indexValue }) => (
          <div style={{ padding: '8px 12px' }}>
            <span style={{ color: '#a0aec0' }}>{indexValue}: </span>
            <strong style={{ color: '#6366f1' }}>{value.toLocaleString()}</strong>
          </div>
        )}
      />
    </div>
  )
}

// ── Line Chart ────────────────────────────────────────────────────────────────

function LineChart({ data, xKey, yKey, title }) {
  const points = data.rows?.map((row) => ({
    x: String(row[xKey]),
    y: Number(row[yKey]),
  })) ?? []

  if (!points.length) return null

  const lineData = [{ id: yKey, color: '#14b8a6', data: points }]

  return (
    <div style={{ height: 320 }}>
      <ResponsiveLine
        data={lineData}
        theme={NIVO_THEME}
        colors={['#14b8a6']}
        margin={{ top: 20, right: 20, bottom: 60, left: 70 }}
        xScale={{ type: 'point' }}
        yScale={{ type: 'linear', nice: true }}
        axisBottom={{
          tickRotation: points.length > 6 ? -35 : 0,
          tickSize: 4,
        }}
        axisLeft={{ tickSize: 4 }}
        pointSize={7}
        pointColor="#0a0a0f"
        pointBorderWidth={2}
        pointBorderColor="#14b8a6"
        enableArea={true}
        areaOpacity={0.12}
        enableGridX={false}
        curve="monotoneX"
        animate={true}
        motionConfig="gentle"
        tooltip={({ point }) => (
          <div style={{ padding: '8px 12px' }}>
            <span style={{ color: '#a0aec0' }}>{point.data.xFormatted}: </span>
            <strong style={{ color: '#14b8a6' }}>{Number(point.data.y).toLocaleString()}</strong>
          </div>
        )}
      />
    </div>
  )
}

// ── Pie Chart ─────────────────────────────────────────────────────────────────

const PIE_COLORS = ['#6366f1', '#14b8a6', '#ec4899', '#f59e0b', '#10b981', '#8b5cf6']

function PieChart({ data, xKey, yKey, title }) {
  const chartData = data.rows?.map((row, i) => ({
    id: String(row[xKey]),
    label: String(row[xKey]),
    value: Number(row[yKey]),
    color: PIE_COLORS[i % PIE_COLORS.length],
  })) ?? []

  if (!chartData.length) return null

  return (
    <div style={{ height: 320 }}>
      <ResponsivePie
        data={chartData}
        theme={NIVO_THEME}
        colors={PIE_COLORS}
        margin={{ top: 20, right: 80, bottom: 40, left: 80 }}
        innerRadius={0.55}
        padAngle={2}
        cornerRadius={4}
        activeOuterRadiusOffset={6}
        borderWidth={0}
        enableArcLinkLabels={true}
        arcLinkLabelsColor={{ from: 'color' }}
        arcLinkLabelsTextColor="#a0aec0"
        arcLinkLabelsThickness={1}
        arcLabelsTextColor="#1e1e2e"
        animate={true}
        motionConfig="gentle"
        tooltip={({ datum }) => (
          <div style={{ padding: '8px 12px' }}>
            <span style={{ color: '#a0aec0' }}>{datum.label}: </span>
            <strong style={{ color: datum.color }}>{datum.value.toLocaleString()}</strong>
          </div>
        )}
      />
    </div>
  )
}

// ── Export ────────────────────────────────────────────────────────────────────

export default function ChartBlock({ chart }) {
  if (!chart) return null

  const { chart_type, x_key, y_key, title, data } = chart

  const inner =
    chart_type === 'bar' ? <BarChart data={data} xKey={x_key} yKey={y_key} title={title} /> :
    chart_type === 'line' ? <LineChart data={data} xKey={x_key} yKey={y_key} title={title} /> :
    chart_type === 'pie' ? <PieChart data={data} xKey={x_key} yKey={y_key} title={title} /> :
    <p style={{ color: 'var(--text-sec)' }}>Unsupported chart type: {chart_type}</p>

  return (
    <div style={{
      marginTop: 16,
      background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(236, 72, 153, 0.05))',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: '24px 20px 16px',
      backdropFilter: 'blur(4px)',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
    }}>
      {title && (
        <p style={{
          fontFamily: 'var(--font-display)',
          fontSize: 13,
          fontWeight: 700,
          color: 'var(--accent)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginBottom: 16,
        }}>
          📊 {title}
        </p>
      )}
      {inner}
    </div>
  )
}
