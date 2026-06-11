import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const fetchHealth          = () => axios.get(`${BASE}/health`).then(r => r.data)
export const fetchMetrics         = () => axios.get(`${BASE}/metrics`).then(r => r.data)
export const fetchPredictions     = (days = 7) => axios.get(`${BASE}/predictions?days=${days}`).then(r => r.data)
export const fetchForecast        = (hours = 168) => axios.get(`${BASE}/forecast?hours=${hours}`).then(r => r.data)
export const fetchFeatureImportance = () => axios.get(`${BASE}/feature-importance`).then(r => r.data)
export const fetchAQI             = () => axios.get(`${BASE}/aqi`).then(r => r.data)
export const fetchMonthly         = () => axios.get(`${BASE}/monthly`).then(r => r.data)
export const postRefreshForecast  = (hours = 72) => axios.post(`${BASE}/refresh-forecast?hours=${hours}`).then(r => r.data)
export const fetchRefreshStatus   = () => axios.get(`${BASE}/refresh-status`).then(r => r.data)
