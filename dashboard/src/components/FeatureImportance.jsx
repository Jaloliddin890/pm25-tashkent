import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'

export default function FeatureImportance({ data }) {
  if (!data || data.length === 0) return null

  const chartData = [...data]
    .sort((a, b) => a.importance - b.importance)
    .map(d => ({ name: d.feature, value: +d.importance.toFixed(4) }))

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h2 className="text-white font-semibold mb-4">Top 15 Feature Importance (XGBoost)</h2>
      <ResponsiveContainer width="100%" height={380}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={130} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' }}
            formatter={v => [v.toFixed(4), 'Importance']}
          />
          <Bar dataKey="value" fill="#fb923c" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
