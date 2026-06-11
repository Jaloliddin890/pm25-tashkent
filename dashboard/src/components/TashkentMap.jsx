import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

const SENSORS = [
  { name: 'US Embassy', lat: 41.3012, lng: 69.2798, desc: 'Yunusabad district' },
  { name: 'Sputnik-4',  lat: 41.2856, lng: 69.2032, desc: 'Mirzo Ulugbek district' },
]

const AQI_LEVELS = [
  [12,  '#00e400', 'Good'],
  [35,  '#ffff00', 'Moderate'],
  [55,  '#ff7e00', 'Unhealthy for Sensitive'],
  [150, '#ff0000', 'Unhealthy'],
  [250, '#8f3f97', 'Very Unhealthy'],
  [999, '#7e0023', 'Hazardous'],
]

function getAQI(pm25) {
  for (const [max, color, label] of AQI_LEVELS) {
    if (pm25 < max) return { color, label }
  }
  return { color: '#7e0023', label: 'Hazardous' }
}

function makeMarkerIcon(pm25, color) {
  const textColor = pm25 < 35 ? '#000000' : '#ffffff'
  return L.divIcon({
    className: '',
    html: `
      <div style="
        background: ${color};
        border: 3px solid white;
        border-radius: 50%;
        width: 52px; height: 52px;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.6);
        font-family: system-ui, sans-serif;
        cursor: pointer;
      ">
        <span style="color:${textColor}; font-weight:800; font-size:15px; line-height:1.1;">${pm25}</span>
        <span style="color:${textColor}; opacity:0.85; font-size:8.5px; font-weight:500;">µg/m³</span>
      </div>
    `,
    iconSize: [52, 52],
    iconAnchor: [26, 26],
    popupAnchor: [0, -30],
  })
}

export default function TashkentMap({ aqi }) {
  // aqi may be { forecast, sensor } (new) or flat { pm25 } (old)
  const pm25  = aqi?.sensor?.pm25 ?? aqi?.forecast?.pm25 ?? aqi?.pm25 ?? 0
  const { color, label } = getAQI(pm25)
  const textColor = pm25 < 35 ? '#000' : '#fff'
  const icon = makeMarkerIcon(pm25, color)

  return (
    <div className="bg-slate-800 rounded-xl p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-white font-semibold text-base">Tashkent — Sensor Locations</h2>
          <p className="text-slate-400 text-xs mt-0.5">US Embassy · Sputnik-4</p>
        </div>
        <span
          className="px-3 py-1 rounded-full text-xs font-bold"
          style={{ background: color, color: textColor }}
        >
          {label} — {pm25} µg/m³
        </span>
      </div>

      <div className="rounded-lg overflow-hidden flex-1" style={{ minHeight: 260 }}>
        <MapContainer
          center={[41.2995, 69.2401]}
          zoom={12}
          style={{ height: '100%', width: '100%', minHeight: 260 }}
          scrollWheelZoom={false}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />

          {/* AQI coverage circle */}
          <Circle
            center={[41.2995, 69.2401]}
            radius={4000}
            pathOptions={{ color, fillColor: color, fillOpacity: 0.12, weight: 2 }}
          />

          {/* Sensor markers with PM2.5 value */}
          {SENSORS.map(s => (
            <Marker key={s.name} position={[s.lat, s.lng]} icon={icon}>
              <Popup>
                <div style={{ fontFamily: 'system-ui', minWidth: 140 }}>
                  <strong style={{ fontSize: 13 }}>{s.name}</strong>
                  <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>{s.desc}</div>
                  <div style={{
                    background: color, color: textColor,
                    borderRadius: 6, padding: '4px 8px',
                    fontWeight: 700, fontSize: 14, textAlign: 'center',
                  }}>
                    PM2.5: {pm25} µg/m³
                  </div>
                  <div style={{ fontSize: 11, color: '#555', marginTop: 4, textAlign: 'center' }}>
                    {label}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      <p className="text-xs text-slate-500 mt-2">
        Marker colour &amp; circle reflect current AQI level · WHO 24h limit: 15 µg/m³
      </p>
    </div>
  )
}
