const toTashkent = (dtStr) => {
  if (!dtStr) return ''
  const d = new Date(dtStr)
  const t = new Date(d.getTime() + 5 * 60 * 60 * 1000)
  const hh  = String(t.getUTCHours()).padStart(2, '0')
  const min = String(t.getUTCMinutes()).padStart(2, '0')
  const dd  = String(t.getUTCDate()).padStart(2, '0')
  const mm  = String(t.getUTCMonth() + 1).padStart(2, '0')
  return `${mm}-${dd} ${hh}:${min}`
}

const LEVELS = [
  { max: 12,  label: 'Good',                    color: '#00e400' },
  { max: 35,  label: 'Moderate',                color: '#ffff00' },
  { max: 55,  label: 'Unhealthy for Sensitive', color: '#ff7e00' },
  { max: 150, label: 'Unhealthy',               color: '#ff0000' },
  { max: 250, label: 'Very Unhealthy',          color: '#8f3f97' },
  { max: 999, label: 'Hazardous',               color: '#7e0023' },
]

function getLevel(pm25) {
  return LEVELS.find(l => pm25 < l.max) || LEVELS[LEVELS.length - 1]
}

export default function AQIGauge({ data }) {
  if (!data) return null

  const forecast = data.forecast ?? data
  const sensor   = data.sensor   ?? null

  const sPm25 = sensor?.pm25   ?? null
  const fPm25 = forecast?.pm25 ?? 0

  // Main ring uses sensor value if available, else LSTM
  const mainPm25 = sPm25 ?? fPm25
  const mainLvl  = getLevel(mainPm25)
  const textColor = mainPm25 < 35 ? '#000' : '#fff'
  const fLvl = getLevel(fPm25)

  return (
    <div className="bg-slate-800 rounded-xl p-6 flex flex-col items-center gap-3 h-full justify-center">
      <h2 className="text-slate-300 text-sm font-semibold uppercase tracking-wider">Current AQI</h2>

      {/* Main gauge ring — sensor value */}
      <div
        className="w-32 h-32 rounded-full flex flex-col items-center justify-center border-4"
        style={{ borderColor: mainLvl.color }}
      >
        <span className="text-3xl font-bold text-white">{mainPm25}</span>
        <span className="text-xs text-slate-400">µg/m³</span>
      </div>

      {/* Level badge */}
      <div className="flex flex-col items-center gap-1">
        <span
          className="px-3 py-1 rounded-full text-xs font-semibold"
          style={{ backgroundColor: mainLvl.color, color: textColor }}
        >
          {mainLvl.label}
        </span>
        {sensor?.datetime && (
          <span className="text-slate-500 text-xs">Sensor · {toTashkent(sensor.datetime)} (TZ+5)</span>
        )}
      </div>

      {/* Divider */}
      <div className="w-full border-t border-slate-700" />

      {/* LSTM forecast row */}
      <div className="flex items-center justify-between w-full px-2">
        <span className="text-slate-400 text-xs">LSTM Forecast</span>
        <div className="flex items-center gap-1.5">
          <span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: fLvl.color }}
          />
          <span className="text-white font-semibold text-sm">{fPm25}</span>
          <span className="text-slate-400 text-xs">µg/m³</span>
          <span className="text-xs ml-1" style={{ color: fLvl.color }}>{fLvl.label}</span>
        </div>
      </div>

      <p className="text-xs text-slate-600">WHO guideline: 15 µg/m³ (24h)</p>
    </div>
  )
}
