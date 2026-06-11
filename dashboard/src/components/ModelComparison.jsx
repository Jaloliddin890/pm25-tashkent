import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'

export default function ModelComparison({ metrics }) {
  if (!metrics || metrics.length === 0) return null

  const rmseData = metrics.map(m => ({ name: m.model, RMSE: m.rmse ? +m.rmse.toFixed(2) : null }))
  const r2Data   = metrics.map(m => ({ name: m.model, R2:   m.r2   ? +m.r2.toFixed(4)   : null }))

  return (
    <div className="bg-slate-800 rounded-xl p-6">
      <h2 className="text-white font-semibold mb-4">Model Comparison</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <p className="text-slate-400 text-sm mb-2">RMSE (lower is better)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={rmseData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' }} />
              <Bar dataKey="RMSE" fill="#38bdf8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div>
          <p className="text-slate-400 text-sm mb-2">R² Score (higher is better)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={r2Data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} domain={[0.75, 1]} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' }} />
              <Bar dataKey="R2" fill="#4ade80" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm text-slate-300">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="text-left py-2 text-slate-400">Model</th>
              <th className="text-right py-2 text-slate-400">RMSE</th>
              <th className="text-right py-2 text-slate-400">MAE</th>
              <th className="text-right py-2 text-slate-400">R²</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map(m => (
              <tr key={m.model} className="border-b border-slate-700/50">
                <td className="py-2 font-medium">{m.model}</td>
                <td className="text-right py-2">{m.rmse?.toFixed(3) ?? '—'}</td>
                <td className="text-right py-2">{m.mae?.toFixed(3)  ?? '—'}</td>
                <td className="text-right py-2">{m.r2?.toFixed(4)   ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
