const AQI_ADVICE = [
  {
    max: 12,
    color: '#00e400',
    ring: '#16a34a',
    title: 'Excellent Air Quality',
    advice: 'PM2.5 levels are well within safe limits. Great day for outdoor activities — children can play freely without any restrictions.',
    tag: 'Outdoor play: Recommended',
    tagOk: true,
    mask: false,
    mood: 'happy',
  },
  {
    max: 35,
    color: '#d4d400',
    ring: '#ca8a04',
    title: 'Moderate Air Quality',
    advice: 'Air quality is acceptable for most people. Unusually sensitive children may experience minor discomfort during extended outdoor activity.',
    tag: 'Outdoor play: OK for most',
    tagOk: true,
    mask: false,
    mood: 'neutral',
  },
  {
    max: 55,
    color: '#ff7e00',
    ring: '#ea580c',
    title: 'Unhealthy for Sensitive Groups',
    advice: 'Children with asthma or respiratory conditions should reduce prolonged outdoor exertion. Others may continue normal activities.',
    tag: 'Sensitive groups: limit outdoor time',
    tagOk: false,
    mask: true,
    mood: 'worried',
  },
  {
    max: 150,
    color: '#ff0000',
    ring: '#dc2626',
    title: 'Unhealthy Air Quality',
    advice: 'Everyone, especially children and elderly, should reduce outdoor activity. Consider wearing an N95/KN95 mask when going outside.',
    tag: 'All groups: limit outdoor activity',
    tagOk: false,
    mask: true,
    mood: 'sad',
  },
  {
    max: 250,
    color: '#8f3f97',
    ring: '#7c3aed',
    title: 'Very Unhealthy',
    advice: 'Children should stay indoors. Avoid all outdoor physical activity. Use air purifiers and keep windows closed.',
    tag: 'Stay indoors — especially children',
    tagOk: false,
    mask: true,
    mood: 'sad',
  },
  {
    max: 999,
    color: '#7e0023',
    ring: '#9f1239',
    title: 'Hazardous',
    advice: 'Emergency air quality conditions. Keep all children indoors with windows and doors sealed. Seek immediate medical advice if breathing symptoms appear.',
    tag: 'Emergency — do not go outside',
    tagOk: false,
    mask: true,
    mood: 'sad',
  },
]

function ChildSVG({ color, mask, mood }) {
  const isHappy   = mood === 'happy'
  const isNeutral = mood === 'neutral'

  return (
    <svg viewBox="0 0 100 130" xmlns="http://www.w3.org/2000/svg" width="90" height="117">
      {/* Glow ring */}
      <circle cx="50" cy="30" r="28" fill={color} opacity="0.18" />

      {/* Hair */}
      <ellipse cx="50" cy="14" rx="17" ry="9" fill="#92400e" />
      <ellipse cx="35" cy="18" rx="5" ry="8" fill="#92400e" />
      <ellipse cx="65" cy="18" rx="5" ry="8" fill="#92400e" />

      {/* Head */}
      <circle cx="50" cy="30" r="18" fill="#fcd9a0" />

      {/* Eyes */}
      <ellipse cx="43" cy="26" rx="3" ry={isHappy ? 3 : 2.5} fill="#1e293b" />
      <ellipse cx="57" cy="26" rx="3" ry={isHappy ? 3 : 2.5} fill="#1e293b" />
      {/* Eye shine */}
      <circle cx="44.5" cy="24.5" r="1.1" fill="white" />
      <circle cx="58.5" cy="24.5" r="1.1" fill="white" />

      {/* Eyebrows */}
      {mood === 'sad' && <>
        <path d="M 39 20 Q 43 18 47 20" stroke="#92400e" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
        <path d="M 53 20 Q 57 18 61 20" stroke="#92400e" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
      </>}

      {/* Mouth / mask */}
      {mask ? (
        <>
          <rect x="38" y="32" width="24" height="14" rx="6" fill={color} opacity="0.85" />
          <line x1="38" y1="39" x2="62" y2="39" stroke="white" strokeWidth="1" opacity="0.5" />
        </>
      ) : isHappy ? (
        <path d="M 42 35 Q 50 42 58 35" stroke="#c2410c" strokeWidth="2" fill="none" strokeLinecap="round"/>
      ) : isNeutral ? (
        <path d="M 43 36 Q 50 38 57 36" stroke="#c2410c" strokeWidth="2" fill="none" strokeLinecap="round"/>
      ) : (
        <path d="M 43 38 Q 50 34 57 38" stroke="#c2410c" strokeWidth="2" fill="none" strokeLinecap="round"/>
      )}

      {/* Neck */}
      <rect x="45" y="47" width="10" height="8" fill="#fcd9a0" />

      {/* Body */}
      <rect x="32" y="54" width="36" height="38" rx="10" fill="#38bdf8" opacity="0.85" />

      {/* Arms */}
      <rect x="16" y="54" width="17" height="8" rx="4" fill="#38bdf8" opacity="0.85" />
      <rect x="67" y="54" width="17" height="8" rx="4" fill="#38bdf8" opacity="0.85" />
      {/* Hands */}
      <circle cx="16" cy="58" r="5" fill="#fcd9a0" />
      <circle cx="84" cy="58" r="5" fill="#fcd9a0" />

      {/* Legs */}
      <rect x="34" y="90" width="13" height="26" rx="6" fill="#1d4ed8" opacity="0.85" />
      <rect x="53" y="90" width="13" height="26" rx="6" fill="#1d4ed8" opacity="0.85" />

      {/* Shoes */}
      <ellipse cx="40" cy="118" rx="11" ry="5" fill="#1e293b" />
      <ellipse cx="60" cy="118" rx="11" ry="5" fill="#1e293b" />
    </svg>
  )
}

export default function HealthAdvisory({ aqi }) {
  // aqi may be { forecast, sensor } (new) or flat { pm25 } (old)
  const pm25 = aqi?.sensor?.pm25 ?? aqi?.forecast?.pm25 ?? aqi?.pm25 ?? 0
  const info = AQI_ADVICE.find(a => pm25 < a.max) || AQI_ADVICE[AQI_ADVICE.length - 1]

  return (
    <div
      className="rounded-xl p-5 border"
      style={{
        background: `linear-gradient(135deg, ${info.color}12 0%, #1e293b 60%)`,
        borderColor: info.ring,
      }}
    >
      <div className="flex items-start gap-5">

        {/* Illustration */}
        <div className="flex-shrink-0 flex flex-col items-center gap-2">
          <ChildSVG color={info.color} mask={info.mask} mood={info.mood} />
          <div
            className="text-xs font-bold px-2 py-0.5 rounded-full"
            style={{ background: info.color, color: pm25 < 35 ? '#000' : '#fff' }}
          >
            {pm25} µg/m³
          </div>
        </div>

        {/* Text */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">👶</span>
            <h3 className="text-white font-semibold text-sm">Health Advisory</h3>
          </div>

          <p
            className="text-xs font-bold mb-1"
            style={{ color: info.color }}
          >
            {info.title}
          </p>

          <p className="text-slate-300 text-xs leading-relaxed mb-3">
            {info.advice}
          </p>

          <span
            className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full"
            style={{
              background: info.tagOk ? '#16a34a22' : '#dc262622',
              color: info.tagOk ? '#4ade80' : '#f87171',
              border: `1px solid ${info.tagOk ? '#16a34a' : '#dc2626'}`,
            }}
          >
            {info.tagOk ? '✓' : '⚠'} {info.tag}
          </span>

          <p className="text-slate-600 text-xs mt-3">
            WHO 24h guideline: 15 µg/m³ · AQI based on LSTM forecast
          </p>
        </div>
      </div>
    </div>
  )
}
