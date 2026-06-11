import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine, Area, AreaChart, Legend
} from 'recharts'

const HIST_OPTIONS = [
  { label: 'Yesterday', days: 1  },
  { label: '3 Days',    days: 3  },
  { label: '7 Days',    days: 7  },
  { label: '30 Days',   days: 30 },
]

const FC_OPTIONS = [
  { label: 'Tomorrow', hours: 24  },
  { label: '3 Days',   hours: 72  },
  { label: '7 Days',   hours: 168 },
]

const HIST_INTERVAL = { 1: 2, 3: 8, 7: 24, 30: 48 }
const FC_INTERVAL   = { 24: 2, 72: 8, 168: 24 }

function FilterBar({ options, active, onChange, activeColor, disabledAll }) {
  return (
    <div className="flex gap-2 flex-wrap">
      {options.map(o => {
        const val      = o.days ?? o.hours
        const isActive = active === val
        const isDisabled = o.disabled || disabledAll
        return (
          <button
            key={val}
            onClick={() => !isDisabled && onChange(val)}
            title={o.disabled ? 'Unreliable beyond 3 days — flat line' : undefined}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
              isDisabled
                ? 'bg-slate-800 text-slate-600 cursor-not-allowed'
                : isActive
                  ? `${activeColor} text-white`
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

const tooltipStyle = { background: '#1e293b', border: '1px solid #475569', color: '#f1f5f9' }
const gridColor    = '#334155'
const axisStyle    = { fill: '#94a3b8', fontSize: 11 }

// UTC → Tashkent (UTC+5)
const toTashkent = (dtStr) => {
  const d = new Date(dtStr)
  const t = new Date(d.getTime() + 5 * 60 * 60 * 1000)
  const mm  = String(t.getUTCMonth() + 1).padStart(2, '0')
  const dd  = String(t.getUTCDate()).padStart(2, '0')
  const hh  = String(t.getUTCHours()).padStart(2, '0')
  const min = String(t.getUTCMinutes()).padStart(2, '0')
  return `${mm}-${dd} ${hh}:${min}`
}

// Show only MM-DD for 7+ day views, full date+time for shorter
const dateFmt  = t => t.slice(0, 5)
const timeFmt  = t => t

const STEP_LABELS = {
  'fetch_data.py':  '1/4 — Fetching WAQI data...',
  'preprocess.py':  '2/4 — Preprocessing...',
  'evaluate.py':    '3/4 — Updating predictions...',
  'predict.py':     '4/4 — Generating forecast...',
}

function RefreshButton({ pipelineState, onClick, forecastHours }) {
  const base = 'px-4 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-2'
  const { status, step, message } = pipelineState || {}
  const days = forecastHours ? forecastHours / 24 : 3
  const label = days === 1 ? '1-day' : `${days}-day`

  if (status === 'running') return (
    <button disabled className={`${base} bg-slate-600 text-slate-300 cursor-not-allowed`}>
      <span className="animate-spin inline-block w-3 h-3 border-2 border-slate-400 border-t-white rounded-full" />
      {STEP_LABELS[step] || 'Running...'}
    </button>
  )
  if (status === 'done') return (
    <button disabled className={`${base} bg-green-600 text-white`}>
      ✓ {message || 'Forecast updated!'}
    </button>
  )
  if (status === 'error') return (
    <button disabled className={`${base} bg-red-600 text-white`}>
      ✕ Error — check API
    </button>
  )
  return (
    <button onClick={onClick} className={`${base} bg-orange-500 hover:bg-orange-400 text-white`}>
      Run {label} Forecast
    </button>
  )
}

export default function ForecastChart({
  predictions, forecast,
  predDays, setPredDays,
  forecastHours, setForecastHours,
  pipelineState, onRefresh,
}) {

  // Historical: only actual PM2.5 values (Tashkent time)
  const histData = (predictions || []).map(d => ({
    time:   toTashkent(d.datetime),
    PM2_5:  d.actual ?? null,
  }))

  // Forecast: merge all 3 models by index
  const fc_rf   = forecast?.rf   || []
  const fc_xgb  = forecast?.xgb  || []
  const fc_lstm = forecast?.lstm || []
  const fcLen   = Math.max(fc_rf.length, fc_xgb.length, fc_lstm.length)
  const fcData  = Array.from({ length: fcLen }, (_, i) => ({
    time:    toTashkent((fc_lstm[i] ?? fc_xgb[i] ?? fc_rf[i])?.datetime),
    RF:      fc_rf[i]?.pm25_forecast   ?? null,
    XGBoost: fc_xgb[i]?.pm25_forecast  ?? null,
    LSTM:    fc_lstm[i]?.pm25_forecast  ?? null,
  }))

  const histInterval = HIST_INTERVAL[predDays]    ?? 24
  const fcInterval   = FC_INTERVAL[forecastHours] ?? 48
  const histTickFmt  = predDays     >= 7   ? dateFmt : timeFmt
  const fcTickFmt    = forecastHours >= 168 ? dateFmt : timeFmt

  return (
    <div className="space-y-6">

      {/* ── Card 1: Historical ─────────────────────────────── */}
      <div className="bg-slate-800 rounded-xl p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
          <div>
            <h2 className="text-white font-semibold text-base">Historical PM2.5</h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Real sensor &amp; CAMS data — {histData.length} hours
            </p>
          </div>
          <FilterBar
            options={HIST_OPTIONS}
            active={predDays}
            onChange={setPredDays}
            activeColor="bg-sky-500"
            disabledAll={pipelineState?.status === 'running'}
          />
        </div>

        {histData.length === 0 ? (
          <p className="text-slate-500 text-sm py-10 text-center">No historical data.</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={histData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <defs>
                <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#38bdf8" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}    />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="time" tick={axisStyle} interval={histInterval} tickFormatter={histTickFmt} />
              <YAxis tick={axisStyle} unit=" µg" />
              <Tooltip contentStyle={tooltipStyle} formatter={v => [`${v} µg/m³`, 'PM2.5']} />
              <ReferenceLine y={35} stroke="#ff7e00" strokeDasharray="4 2"
                label={{ value: 'Moderate', fill: '#ff7e00', fontSize: 10 }} />
              <ReferenceLine y={75} stroke="#ef4444" strokeDasharray="4 2"
                label={{ value: 'Unhealthy', fill: '#ef4444', fontSize: 10 }} />
              <Area
                type="monotone" dataKey="PM2_5"
                stroke="#38bdf8" strokeWidth={2}
                fill="url(#histGrad)" dot={false}
                name="PM2.5"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Card 2: Forecast ───────────────────────────────── */}
      <div className="bg-slate-800 rounded-xl p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
          <div>
            <h2 className="text-white font-semibold text-base">PM2.5 Forecast</h2>
            <p className="text-slate-400 text-xs mt-0.5">
              RF · XGBoost · LSTM — {fcData.length} hours ahead
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <FilterBar
              options={FC_OPTIONS}
              active={forecastHours}
              onChange={setForecastHours}
              activeColor="bg-orange-500"
              disabledAll={pipelineState?.status === 'running'}
            />
            <RefreshButton pipelineState={pipelineState} onClick={onRefresh} forecastHours={forecastHours} />
          </div>
        </div>

        {/* Pipeline progress banner */}
        {pipelineState?.status === 'running' && (
          <div className="flex items-center gap-3 bg-slate-700/60 border border-slate-600 rounded-lg px-4 py-3 mb-4">
            <span className="animate-spin inline-block w-4 h-4 border-2 border-slate-400 border-t-orange-400 rounded-full flex-shrink-0" />
            <div>
              <p className="text-orange-300 text-sm font-medium">
                {STEP_LABELS[pipelineState.step] || 'Running pipeline...'}
              </p>
              <p className="text-slate-400 text-xs mt-0.5">{pipelineState.message}</p>
            </div>
          </div>
        )}
        {pipelineState?.status === 'error' && (
          <div className="bg-red-900/40 border border-red-700 rounded-lg px-4 py-3 mb-4">
            <p className="text-red-300 text-sm font-medium">Pipeline Error</p>
            <p className="text-red-400 text-xs mt-0.5">{pipelineState.message}</p>
          </div>
        )}

        {fcData.length === 0 ? (
          <p className="text-slate-500 text-sm py-10 text-center">No forecast available. Run the pipeline.</p>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={fcData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="time" tick={axisStyle} interval={fcInterval} tickFormatter={fcTickFmt} />
              <YAxis tick={axisStyle} unit=" µg" />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v, name) => v != null ? [`${v} µg/m³`, name] : ['-', name]}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              <ReferenceLine y={35} stroke="#ff7e00" strokeDasharray="4 2"
                label={{ value: 'Moderate', fill: '#ff7e00', fontSize: 10 }} />
              <ReferenceLine y={75} stroke="#ef4444" strokeDasharray="4 2"
                label={{ value: 'Unhealthy', fill: '#ef4444', fontSize: 10 }} />
              <Line type="monotone" dataKey="RF"
                stroke="#34d399" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              <Line type="monotone" dataKey="XGBoost"
                stroke="#fbbf24" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              <Line type="monotone" dataKey="LSTM"
                stroke="#fb923c" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

    </div>
  )
}
