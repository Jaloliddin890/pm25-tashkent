import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine, Cell,
} from 'recharts'

const WHO_GUIDELINE = 15

function barColor(pm25) {
  if (pm25 <= 15)  return '#4ade80'  // good
  if (pm25 <= 35)  return '#facc15'  // moderate
  if (pm25 <= 55)  return '#fb923c'  // unhealthy sensitive
  return '#f87171'                   // unhealthy
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const val = payload[0].value
  return (
    <div style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: '8px 12px' }}>
      <p style={{ color: '#94a3b8', marginBottom: 4 }}>{label}</p>
      <p style={{ color: '#f1f5f9', fontWeight: 600 }}>{val} µg/m³</p>
    </div>
  )
}

export default function MonthlyChart({ data }) {
  if (!data || data.length === 0) return null

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-white font-semibold">Monthly Average PM2.5</h2>
        <span className="text-xs text-slate-400">WHO guideline: {WHO_GUIDELINE} µg/m³</span>
      </div>
      <p className="text-slate-500 text-xs mb-4">
        Green ≤15 · Yellow ≤35 · Orange ≤55 · Red &gt;55
      </p>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 11 }} angle={-30} textAnchor="end" height={48} />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            unit=" µg"
            width={52}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#334155' }} />
          <ReferenceLine
            y={WHO_GUIDELINE}
            stroke="#38bdf8"
            strokeDasharray="4 3"
            label={{ value: 'WHO', position: 'insideTopRight', fill: '#38bdf8', fontSize: 11 }}
          />
          <Bar dataKey="pm25" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={barColor(entry.pm25)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
