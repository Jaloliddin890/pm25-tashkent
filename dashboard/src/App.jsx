import { useEffect, useRef, useState } from 'react'
import {
  fetchHealth, fetchMetrics, fetchPredictions, fetchForecast,
  fetchFeatureImportance, fetchAQI, fetchMonthly,
  postRefreshForecast, fetchRefreshStatus,
} from './api'
import Navbar from './components/Navbar'
import AQIGauge from './components/AQIGauge'
import ForecastChart from './components/ForecastChart'
import ModelComparison from './components/ModelComparison'
import FeatureImportance from './components/FeatureImportance'
import TashkentMap from './components/TashkentMap'
import MonthlyChart from './components/MonthlyChart'
import HealthAdvisory from './components/HealthAdvisory'

export default function App() {
  const [health, setHealth]           = useState(null)
  const [metrics, setMetrics]         = useState([])
  const [predictions, setPredictions] = useState([])
  const [forecast, setForecast]       = useState({})
  const [features, setFeatures]       = useState([])
  const [aqi, setAqi]                 = useState(null)
  const [monthly, setMonthly]         = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)

  const [predDays, setPredDays]           = useState(7)
  const [forecastHours, setForecastHours] = useState(168)

  // Pipeline status: { status, step, message }
  const [pipelineState, setPipelineState] = useState({ status: 'idle', step: '', message: '' })
  const pollRef = useRef(null)

  // ── Static data — fetch once on mount ────────────────────
  useEffect(() => {
    Promise.all([
      fetchHealth(),
      fetchMetrics(),
      fetchFeatureImportance(),
      fetchAQI(),
      fetchMonthly(),
    ])
      .then(([h, m, fi, a, mo]) => {
        setHealth(h); setMetrics(m); setFeatures(fi); setAqi(a); setMonthly(mo)
        setLoading(false)
      })
      .catch(() => {
        setError('API server is not running. Start FastAPI on port 8000.')
        setLoading(false)
      })
  }, [])

  // ── Refetch dynamic data on filter change ─────────────────
  useEffect(() => {
    fetchPredictions(predDays).then(setPredictions).catch(() => {})
  }, [predDays])

  useEffect(() => {
    fetchForecast(forecastHours).then(setForecast).catch(() => {})
  }, [forecastHours])

  // ── Polling helpers ───────────────────────────────────────
  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const startPolling = () => {
    stopPolling()
    pollRef.current = setInterval(() => {
      fetchRefreshStatus()
        .then(s => {
          setPipelineState(s)
          if (s.status === 'done') {
            stopPolling()
            // Reload all data after successful pipeline
            fetchPredictions(predDays).then(setPredictions)
            fetchForecast(forecastHours).then(setForecast)
            fetchAQI().then(setAqi)
            setTimeout(() => setPipelineState({ status: 'idle', step: '', message: '' }), 5000)
          } else if (s.status === 'error') {
            stopPolling()
            setTimeout(() => setPipelineState({ status: 'idle', step: '', message: '' }), 6000)
          }
        })
        .catch(() => {})
    }, 2000)
  }

  useEffect(() => () => stopPolling(), [])   // cleanup on unmount

  // ── Run Forecast handler ──────────────────────────────────
  const handleRefreshForecast = () => {
    postRefreshForecast(forecastHours)
      .then(() => {
        setPipelineState({ status: 'running', step: '', message: 'Starting pipeline...' })
        startPolling()
      })
      .catch(err => {
        const detail = err.response?.data?.detail || 'Could not start pipeline.'
        setPipelineState({ status: 'error', step: '', message: detail })
        setTimeout(() => setPipelineState({ status: 'idle', step: '', message: '' }), 5000)
      })
  }

  if (loading) return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <p className="text-slate-400 text-lg">Loading data...</p>
    </div>
  )

  if (error) return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="bg-red-900/40 border border-red-700 rounded-xl p-8 max-w-md text-center">
        <p className="text-red-300 text-lg font-semibold mb-2">Connection Error</p>
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-900">
      <Navbar generated_at={health?.generated_at} />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">

        {/* Row 1: Health Advisory */}
        <HealthAdvisory aqi={aqi} />

        {/* Row 2: AQI + Map */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-1"><AQIGauge data={aqi} /></div>
          <div className="md:col-span-2"><TashkentMap aqi={aqi} /></div>
        </div>

        {/* Row 2: Charts */}
        <ForecastChart
          predictions={predictions}
          forecast={forecast}
          predDays={predDays}
          setPredDays={setPredDays}
          forecastHours={forecastHours}
          setForecastHours={setForecastHours}
          pipelineState={pipelineState}
          onRefresh={handleRefreshForecast}
        />

        {/* Row 3: Model comparison */}
        <ModelComparison metrics={metrics} />

        {/* Row 4: Feature importance + Monthly avg */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <FeatureImportance data={features} />
          <MonthlyChart data={monthly} />
        </div>


      </main>
    </div>
  )
}
