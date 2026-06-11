export default function Navbar({ generated_at }) {
  const time = generated_at ? new Date(generated_at).toLocaleString() : '—'
  return (
    <nav className="bg-slate-900 border-b border-slate-700 px-6 py-4 flex items-center justify-between">
      <div>
        <h1 className="text-xl font-bold text-white">PM2.5 Tashkent</h1>
        <p className="text-xs text-slate-400">Air Quality Forecast Dashboard</p>
      </div>
      <div className="text-right">
        <p className="text-xs text-slate-400">Last updated</p>
        <p className="text-sm text-slate-300">{time}</p>
      </div>
    </nav>
  )
}
