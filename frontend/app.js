/* =====================================================
   WeatherSense AI — Frontend JavaScript
   All data comes from the real Flask backend.
   No fake data, no random numbers, no client-side ML.

   API endpoints consumed:
     GET /api/health
     GET /api/weather/current?city=…
     GET /api/weather/history?city=…&hours=24
     GET /api/forecast?city=…
     GET /api/ml/predict?city=…
     GET /api/ml/classify?city=…
     GET /api/ml/anomalies?city=…
   ===================================================== */
'use strict';

const API = '';          // Flask serves frontend on same origin
const REFRESH_MS = 30000; // Auto-refresh every 30 seconds

let currentCity = 'nagpur';
let charts = {};
let refreshTimer = null;

// ── Helpers ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const setText = (id, v) => { const el = $(id); if (el) el.textContent = v ?? '—'; };
const setDot  = (id, ok) => {
  const el = $(id);
  if (!el) return;
  el.style.background  = ok ? 'var(--accent-green)' : '#ff4f6a';
  el.style.boxShadow   = ok ? '0 0 6px var(--accent-green)' : '0 0 6px #ff4f6a';
};

async function apiFetch(path) {
  const resp = await fetch(API + path, { cache: 'no-store' });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${path}`);
  return resp.json();
}

// ── Navigation ───────────────────────────────────────────────────────────────
const PAGE_TITLES = {
  dashboard: 'Dashboard Overview',
  aiml:      'AI/ML Engine (scikit-learn)',
  forecast:  '7-Day AI Forecast',
  health:    'Health Advisory',
  anomaly:   'Anomaly Detection (Z-Score)',
  alerts:    'Smart Alerts',
  db:        'Live Database Viewer',
};

function showSection(id, el) {
  document.querySelectorAll('.section').forEach(s  => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n  => n.classList.remove('active'));
  const sec = $('section-' + id);
  if (sec) sec.classList.add('active');
  if (el)  el.classList.add('active');
  setText('pageTitle',  PAGE_TITLES[id] || id);
  setText('breadcrumb', 'Home / ' + (PAGE_TITLES[id] || id));

  // Lazy-load section data
  if (id === 'aiml')    { runMLPredict(); runMLClassify(); }
  if (id === 'forecast') loadForecast();
  if (id === 'anomaly')  loadAnomalies();
  if (id === 'db')       loadDBView();
}

function toggleSidebar() {
  $('sidebar').classList.toggle('collapsed');
  $('mainContent').classList.toggle('expanded');
}

function onCityChange() {
  currentCity = $('citySelect').value;
  refreshAll();
}

// ── Clock ────────────────────────────────────────────────────────────────────
function updateClock() {
  const el = $('liveTime');
  if (el) el.textContent = new Date().toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
}

// ── Particles ────────────────────────────────────────────────────────────────
function initParticles() {
  const c = $('particles');
  for (let i = 0; i < 18; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const sz = Math.random() * 80 + 20;
    p.style.cssText = `width:${sz}px;height:${sz}px;left:${Math.random()*100}%;animation-duration:${Math.random()*25+15}s;animation-delay:${Math.random()*20}s;opacity:${Math.random()*0.12};`;
    c.appendChild(p);
  }
}

// ── Chart helpers ─────────────────────────────────────────────────────────────
const CHART_OPTS = {
  line: (label, color) => ({
    type: 'line',
    data: { labels: [], datasets: [{ label, data: [], borderColor: color, backgroundColor: color + '18', fill: true, tension: 0.4, pointRadius: 2, borderWidth: 2 }] },
    options: { animation: false, responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
      scales: {
        x: { ticks: { color: '#415175', font: { size: 10 }, maxTicksLimit: 8 }, grid: { color: 'rgba(255,255,255,0.03)' } },
        y: { ticks: { color: '#415175', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
      }
    }
  }),
  bar: (label, color) => ({
    type: 'bar',
    data: { labels: [], datasets: [
      { label: 'Max °C', data: [], backgroundColor: color + 'cc', borderRadius: 4 },
      { label: 'Min °C', data: [], backgroundColor: '#598cff88', borderRadius: 4 },
    ]},
    options: { animation: false, responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#8fa0c2', font: { size: 10 } } } },
      scales: {
        x: { ticks: { color: '#415175', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.03)' } },
        y: { ticks: { color: '#415175', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
      }
    }
  }),
};

function getOrCreate(id, config) {
  if (charts[id]) { charts[id].destroy(); }
  const ctx = $(id);
  if (!ctx) return null;
  charts[id] = new Chart(ctx, config);
  return charts[id];
}

// ── WMO code → emoji + label ──────────────────────────────────────────────────
const WMO = {
  0: ['☀️','Clear'], 1: ['🌤️','Mostly Clear'], 2: ['⛅','Partly Cloudy'],
  3: ['☁️','Overcast'], 45: ['🌫️','Foggy'], 48: ['🌫️','Icy Fog'],
  51: ['🌦️','Light Drizzle'], 61: ['🌧️','Rain'], 63: ['🌧️','Moderate Rain'],
  65: ['🌧️','Heavy Rain'], 71: ['🌨️','Light Snow'], 73: ['❄️','Snow'],
  80: ['🌦️','Rain Showers'], 81: ['🌧️','Heavy Showers'], 85: ['🌨️','Snow Showers'],
  95: ['⛈️','Thunderstorm'], 96: ['⛈️','Heavy Thunderstorm'], 99: ['⛈️','Hail Storm'],
};
function wmoInfo(code) { return WMO[code] || ['🌡️', `Code ${code}`]; }

// ── UV label ─────────────────────────────────────────────────────────────────
function uvLabel(v) {
  if (v === null || v === undefined) return '—';
  if (v < 3)  return 'Low';
  if (v < 6)  return 'Moderate';
  if (v < 8)  return 'High';
  if (v < 11) return 'Very High';
  return 'Extreme';
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. DASHBOARD — fetch current weather + history
// ─────────────────────────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    // Fetch current weather (also stores to DB)
    const data = await apiFetch(`/api/weather/current?city=${currentCity}`);

    // Update status dots
    setDot('dot-backend', true);
    setDot('dot-api', true);
    $('connectionDot').classList.add('online');
    setText('connectionText', 'Backend Connected');

    // Primary cards
    setText('mainTemp',   data.temperature !== null ? data.temperature + '°C' : '—');
    setText('feelsLike',  data.apparent_temp !== null ? data.apparent_temp + '°C' : '—');
    setText('mainHum',    data.humidity !== null ? data.humidity + '%' : '—');
    setText('mainWind',   data.wind_speed !== null ? data.wind_speed + ' km/h' : '—');
    setText('windDir',    data.wind_direction ?? '—');
    setText('mainPress',  data.pressure !== null ? data.pressure + ' hPa' : '—');
    setText('mainRain',   data.rain !== null ? data.rain + ' mm' : '—');
    setText('mainUV',     data.uv_index ?? '—');
    setText('uvLabel',    uvLabel(data.uv_index));

    // Info row
    setText('cityName',   data.city_name ?? '—');
    setText('wmoCode',    data.weather_code ?? '—');
    const fetchTime = data.timestamp ? new Date(data.timestamp + 'Z').toLocaleTimeString('en-IN') : '—';
    setText('lastFetch', fetchTime);

    // Health section update
    updateHealth(data);
    updateAlerts(data);

    // Fetch history & hourly for charts
    await loadHistoryCharts();
    await loadHourlyChart();

  } catch (err) {
    console.error('Dashboard load failed:', err);
    setDot('dot-backend', false);
    $('connectionDot').classList.remove('online');
    setText('connectionText', 'Backend Offline');
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 1B. GPS GEOLOCATION AUTO-DETECT
// ─────────────────────────────────────────────────────────────────────────────
async function detectGPSLocation() {
  const btn = $('geoBtn');
  if (!navigator.geolocation) {
    alert('Geolocation is not supported by your browser.');
    return;
  }
  if (btn) { btn.textContent = '⏳ Locating…'; btn.disabled = true; }

  navigator.geolocation.getCurrentPosition(
    async pos => {
      const { latitude, longitude } = pos.coords;
      try {
        const data = await apiFetch(`/api/weather/coords?lat=${latitude}&lon=${longitude}`);
        setText('mainTemp',   data.temperature !== null ? data.temperature + '°C' : '—');
        setText('feelsLike',  data.apparent_temp !== null ? data.apparent_temp + '°C' : '—');
        setText('mainHum',    data.humidity !== null ? data.humidity + '%' : '—');
        setText('mainWind',   data.wind_speed !== null ? data.wind_speed + ' km/h' : '—');
        setText('windDir',    data.wind_direction ?? '—');
        setText('mainPress',  data.pressure !== null ? data.pressure + ' hPa' : '—');
        setText('mainRain',   data.rain !== null ? data.rain + ' mm' : '—');
        setText('mainUV',     data.uv_index ?? '—');
        setText('uvLabel',    uvLabel(data.uv_index));
        setText('cityName',   data.city_name ?? 'GPS Location');
        updateHealth(data);
        updateAlerts(data);
        if (btn) btn.textContent = '📍 GPS (Active)';
      } catch (e) {
        alert('Could not fetch weather for your location: ' + e.message);
        if (btn) btn.textContent = '📍 GPS';
      } finally {
        if (btn) btn.disabled = false;
      }
    },
    err => {
      alert('Location access denied or unavailable: ' + err.message);
      if (btn) { btn.textContent = '📍 GPS'; btn.disabled = false; }
    }
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 1C. 24-HOUR HOURLY TIMELINE CHART
// ─────────────────────────────────────────────────────────────────────────────
async function loadHourlyChart() {
  try {
    const data = await apiFetch(`/api/weather/hourly?city=${currentCity}`);
    if (!data.times || !data.temperatures) return;

    if (charts.hourlyChart) charts.hourlyChart.destroy();
    const ctx = $('hourlyChart');
    if (!ctx) return;

    charts.hourlyChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.times,
        datasets: [
          { label: 'Temperature °C', data: data.temperatures, borderColor: '#00d4ff', backgroundColor: '#00d4ff18', fill: true, tension: 0.4, yAxisID: 'y' },
          { label: 'Rain Probability %', data: data.rain_probability, borderColor: '#a370ff', backgroundColor: '#a370ff33', type: 'bar', borderRadius: 3, yAxisID: 'y1' }
        ]
      },
      options: {
        animation: false, responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#8fa0c2', font: { size: 10 } } } },
        scales: {
          x: { ticks: { color: '#415175', font: { size: 10 }, maxTicksLimit: 12 }, grid: { color: 'rgba(255,255,255,0.03)' } },
          y: { position: 'left', title: { display: true, text: '°C', color: '#00d4ff', font: { size: 10 } }, ticks: { color: '#415175', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y1: { position: 'right', title: { display: true, text: 'Rain %', color: '#a370ff', font: { size: 10 } }, ticks: { color: '#415175', font: { size: 10 } }, grid: { drawOnChartArea: false } }
        }
      }
    });
  } catch (e) {
    console.error('Hourly chart error:', e);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 1D. EXPORT DATABASE AS CSV
// ─────────────────────────────────────────────────────────────────────────────
function exportDatabaseCSV() {
  window.open(API + `/api/weather/export?city=${currentCity}`, '_blank');
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. HISTORY CHARTS — from SQLite DB
// ─────────────────────────────────────────────────────────────────────────────
async function loadHistoryCharts() {
  try {
    const hist = await apiFetch(`/api/weather/history?city=${currentCity}&hours=24`);
    const readings = hist.readings || [];

    setText('dbCount',  readings.length);
    setText('dbCount2', readings.length);

    const labels = readings.map(r => {
      const d = new Date(r.timestamp + 'Z');
      return d.getHours() + ':' + String(d.getMinutes()).padStart(2,'0');
    });
    const temps  = readings.map(r => r.temperature);
    const humids = readings.map(r => r.humidity);

    // Temperature chart
    const tc = getOrCreate('tempHistChart', CHART_OPTS.line('Temperature °C', '#ff6b6b'));
    if (tc) {
      tc.data.labels          = labels;
      tc.data.datasets[0].data = temps;
      tc.update();
    }

    // Humidity chart
    const hc = getOrCreate('humHistChart', CHART_OPTS.line('Humidity %', '#598cff'));
    if (hc) {
      hc.data.labels          = labels;
      hc.data.datasets[0].data = humids;
      hc.update();
    }

  } catch (err) {
    console.error('History charts failed:', err);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. ML — Linear Regression
// ─────────────────────────────────────────────────────────────────────────────
async function runMLPredict() {
  setText('lrStatus', 'Training…');
  try {
    const data = await apiFetch(`/api/ml/predict?city=${currentCity}`);
    setDot('dot-ml', true);

    if (data.status === 'insufficient_data') {
      setText('lrStatus', 'Insufficient data');
      setText('lrR2',      data.n_samples + ' readings');
      setText('lrRMSE',    '—');
      setText('lrSamples', data.n_samples);
      setText('pred1h', '—'); setText('pred2h', '—'); setText('pred3h', '—');
      $('lrCoefficients').innerHTML = `<span class="coeff-item">${data.message}</span>`;
      return;
    }

    setText('lrStatus',  'OK');
    setText('lrR2',      data.r2);
    setText('lrRMSE',    data.rmse);
    setText('lrSamples', data.n_samples);
    setText('pred1h', (data.predictions?.['1h'] ?? '—') + '°C');
    setText('pred2h', (data.predictions?.['2h'] ?? '—') + '°C');
    setText('pred3h', (data.predictions?.['3h'] ?? '—') + '°C');

    // Coefficients display
    if (data.coefficients) {
      $('lrCoefficients').innerHTML = Object.entries(data.coefficients)
        .map(([k, v]) => `<div class="coeff-item"><span class="coeff-key">${k}</span><span class="coeff-val">${v}</span></div>`)
        .join('');
    }

    // LR Chart — actual vs predicted from history
    await buildLRChart(data);

  } catch (err) {
    console.error('ML predict failed:', err);
    setText('lrStatus', 'Error');
    setDot('dot-ml', false);
  }
}

async function buildLRChart(lrData) {
  try {
    const hist = await apiFetch(`/api/weather/history?city=${currentCity}&hours=24`);
    const readings = hist.readings || [];
    if (readings.length < 2) return;

    const labels  = readings.map((_, i) => i);
    const actuals  = readings.map(r => r.temperature);
    const slope    = lrData.coefficients?.time_index ?? 0;
    const intercept= lrData.intercept ?? (actuals[0] || 25);
    const preds    = labels.map(i => +(slope * i + intercept).toFixed(2));

    if (charts.lrChart) charts.lrChart.destroy();
    const ctx = $('lrChart');
    if (!ctx) return;
    charts.lrChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Actual °C',    data: actuals, borderColor: '#00e5a0', backgroundColor: '#00e5a01a', tension: 0.3, pointRadius: 2, borderWidth: 1.5 },
          { label: 'Predicted °C', data: preds,   borderColor: '#a370ff', backgroundColor: 'transparent', tension: 0, pointRadius: 0, borderWidth: 1.5, borderDash: [5,3] },
        ]
      },
      options: { animation: false, responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#8fa0c2', font: { size: 10 } } } },
        scales: {
          x: { ticks: { color: '#415175', font: { size: 10 }, maxTicksLimit: 10 }, grid: { color: 'rgba(255,255,255,0.03)' } },
          y: { ticks: { color: '#415175', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
        }
      }
    });
  } catch (e) { console.error('LR chart error:', e); }
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. ML — Random Forest
// ─────────────────────────────────────────────────────────────────────────────
async function runMLClassify() {
  setText('rfStatus', 'Training…');
  try {
    const data = await apiFetch(`/api/ml/classify?city=${currentCity}`);

    if (data.status === 'insufficient_data') {
      setText('rfStatus',    'Insufficient data');
      setText('rfCondition', '—');
      setText('rfRainProb',  '—');
      setText('rfSamples',   data.n_samples);
      $('rfImportances').innerHTML  = data.message;
      $('rfProbabilities').innerHTML = '';
      return;
    }

    setText('rfStatus',    'OK');
    setText('rfCondition', data.predicted_condition ?? '—');
    setText('rfRainProb',  (data.rain_probability ?? '—') + '%');
    setText('rfSamples',   data.n_samples);

    // Feature importances bars
    if (data.feature_importances) {
      $('rfImportances').innerHTML = Object.entries(data.feature_importances)
        .map(([k, v]) => {
          const pct = (v * 100).toFixed(1);
          return `<div class="imp-item">
            <span class="imp-label">${k}</span>
            <div class="imp-bar-wrap"><div class="imp-bar-fill" style="width:${Math.min(100, pct * 3)}%"></div></div>
            <span class="imp-pct">${pct}%</span>
          </div>`;
        }).join('');
    }

    // Class probabilities chips
    if (data.condition_probabilities) {
      const dominant = data.predicted_condition;
      $('rfProbabilities').innerHTML = Object.entries(data.condition_probabilities)
        .filter(([, v]) => v > 0)
        .sort(([,a],[,b]) => b - a)
        .map(([label, prob]) => {
          const cls = label === dominant ? 'proba-chip dominant' : 'proba-chip';
          return `<span class="${cls}">${label}: ${prob}%</span>`;
        }).join('');
    }

  } catch (err) {
    console.error('ML classify failed:', err);
    setText('rfStatus', 'Error');
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. FORECAST — from backend cache
// ─────────────────────────────────────────────────────────────────────────────
async function loadForecast() {
  $('forecastGrid').innerHTML = '<div class="loading-msg">Loading 7-day forecast from backend…</div>';
  try {
    const data = await apiFetch(`/api/forecast?city=${currentCity}`);
    const days = data.days || [];

    $('forecastGrid').innerHTML = days.map((d, i) => {
      const date = new Date(d.date);
      const dayName = i === 0 ? 'Today' : date.toLocaleDateString('en-IN', { weekday: 'short' });
      const [icon, cond] = wmoInfo(d.weather_code);
      return `<div class="fc-card glass ${i === 0 ? 'today' : ''}">
        <div class="fc-day">${dayName}</div>
        <span class="fc-icon">${icon}</span>
        <div class="fc-hi">${d.temp_max ?? '—'}°C</div>
        <div class="fc-lo">${d.temp_min ?? '—'}°C</div>
        <div class="fc-rain">💧 ${d.rain_probability ?? 0}%</div>
        <div class="fc-cond">${cond}</div>
      </div>`;
    }).join('');

    // Forecast bar chart
    const fc = getOrCreate('forecastChart', CHART_OPTS.bar('Forecast', '#ff6b6b'));
    if (fc) {
      fc.data.labels              = days.map((d, i) => i === 0 ? 'Today' : new Date(d.date).toLocaleDateString('en-IN', { weekday: 'short' }));
      fc.data.datasets[0].data   = days.map(d => d.temp_max);
      fc.data.datasets[1].data   = days.map(d => d.temp_min);
      fc.update();
    }

  } catch (err) {
    console.error('Forecast failed:', err);
    $('forecastGrid').innerHTML = `<div class="loading-msg">⚠️ Failed to load forecast: ${err.message}</div>`;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. HEALTH ADVISORY — computed from current data
// ─────────────────────────────────────────────────────────────────────────────
function updateHealth(d) {
  const temp  = d.temperature ?? 25;
  const hum   = d.humidity    ?? 50;
  const wind  = d.wind_speed  ?? 10;
  const uv    = d.uv_index    ?? 0;
  const feels = d.apparent_temp ?? temp;

  // Heat index (simplified Rothfusz)
  const hi = feels;
  const hiLabel = hi > 41 ? 'Dangerous 🔴' : hi > 35 ? 'Very Hot 🟠' : hi > 28 ? 'Hot 🟡' : 'Comfortable 🟢';
  setText('heatIndex', hi + '°C');
  setText('heatMsg',   `Heat index: ${hiLabel}`);

  // Hydration
  const hydRisk = hum > 80 ? 'Low Risk' : hum < 40 ? 'High Risk' : 'Moderate Risk';
  setText('hydrationLevel', hydRisk);
  setText('hydrationMsg',   temp > 35 ? 'Drink 500ml every hour outdoors' : 'Stay adequately hydrated');

  // UV
  setText('uvLevel', uvLabel(uv));
  setText('uvMsg',   uv > 6 ? 'Apply SPF 50+ sunscreen. Seek shade.' : uv > 3 ? 'SPF 30 recommended' : 'UV is low — minimal protection needed');

  // Wind chill
  const wc = uv < 1 && wind > 20 ? 'Cold Wind' : wind > 40 ? 'Gusty' : 'Calm';
  setText('windChillLevel', wc);
  setText('windChillMsg',   wind > 40 ? 'Secure loose objects. High wind advisory.' : 'Wind conditions are normal');

  // Wellness index (0–100)
  let wellness = 100;
  if (temp > 40) wellness -= 30;
  else if (temp > 35) wellness -= 15;
  if (hum > 85)  wellness -= 20;
  if (uv > 8)    wellness -= 15;
  if (wind > 50) wellness -= 10;
  wellness = Math.max(0, Math.min(100, wellness));

  setText('wellnessScore', wellness + ' / 100');
  $('wellnessBar').style.width = wellness + '%';

  const tips = [];
  if (temp > 35)  tips.push('🌡️ High temperature — limit outdoor activity during peak hours');
  if (hum > 80)   tips.push('💧 High humidity — risk of heat exhaustion increases');
  if (uv > 6)     tips.push('☀️ High UV — wear protective clothing and sunscreen');
  if (wind > 30)  tips.push('💨 Strong winds — secure loose items outdoors');
  if (!tips.length) tips.push('✅ Conditions are comfortable. Enjoy the weather!');

  $('wellnessTips').innerHTML = tips.map(t => `<div class="tip-item">${t}</div>`).join('');
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. ANOMALY DETECTION
// ─────────────────────────────────────────────────────────────────────────────
async function loadAnomalies() {
  try {
    const data = await apiFetch(`/api/ml/anomalies?city=${currentCity}&hours=24`);

    setText('anomTotal',    data.readings_analyzed ?? '—');
    setText('anomFound',    data.anomalies_found   ?? '—');
    setText('anomTempMean', data.stats?.temp_mean  ?? '—');
    setText('anomTempStd',  data.stats?.temp_std   ?? '—');

    const listEl = $('anomalyList');
    if (!data.anomalies || data.anomalies.length === 0) {
      listEl.innerHTML = '<div class="anom-empty">✅ No anomalies detected in the last 24 hours.</div>';
      return;
    }

    listEl.innerHTML = data.anomalies.map(a => {
      const ts = a.timestamp ? new Date(a.timestamp + 'Z').toLocaleString('en-IN') : '—';
      const flags = (a.flags || []).map(f =>
        `<span class="anom-flag">${f.metric}: ${f.value} (z=${f.z_score}σ)</span>`
      ).join('  ');
      return `<div class="anom-entry"><span class="anom-time">${ts}</span>${flags}</div>`;
    }).join('');

  } catch (err) {
    console.error('Anomaly load failed:', err);
    $('anomalyList').innerHTML = `<div class="loading-msg">⚠️ ${err.message}</div>`;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. ALERTS — generated from live data thresholds
// ─────────────────────────────────────────────────────────────────────────────
function updateAlerts(d) {
  const now   = new Date().toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });
  const alerts = [];

  const maxTemp = parseFloat($('threshTemp')?.value || 38);
  const maxWind = parseFloat($('threshWind')?.value || 50);
  const maxHum  = parseFloat($('threshHum')?.value || 85);

  if (d.temperature > maxTemp) alerts.push({ type:'danger',  icon:'🔥', title:'Extreme Heat Warning', desc:`Temperature ${d.temperature}°C exceeds threshold (${maxTemp}°C)` });
  if (d.wind_speed  > maxWind) alerts.push({ type:'danger',  icon:'🌪️', title:'High Wind Alert',     desc:`Wind speed ${d.wind_speed} km/h exceeds threshold (${maxWind} km/h)` });
  if (d.humidity    > maxHum)  alerts.push({ type:'warning', icon:'💧', title:'High Humidity Alert', desc:`Humidity ${d.humidity}% exceeds threshold (${maxHum}%)` });
  if (d.pressure    < 995)     alerts.push({ type:'warning', icon:'⛈️', title:'Low Pressure System', desc:`Pressure ${d.pressure} hPa — storm risk` });
  if (d.uv_index    > 7)       alerts.push({ type:'warning', icon:'☀️', title:'High UV Index',       desc:`UV index ${d.uv_index} — use sunscreen` });
  if (d.rain        > 5)       alerts.push({ type:'warning', icon:'🌧️', title:'Heavy Rain Warning',   desc:`${d.rain} mm rain recorded` });
  if (!alerts.length)          alerts.push({ type:'info',    icon:'✅', title:'All Systems Normal',  desc:'All weather parameters are within safe limits' });

  setText('alertBadge', alerts.filter(a => a.type !== 'info').length || '0');
  $('alertsList').innerHTML = alerts.map(a => `
    <div class="alert-item ${a.type}">
      <span class="alert-icon">${a.icon}</span>
      <div class="alert-body">
        <div class="alert-title">${a.title}</div>
        <div class="alert-desc">${a.desc}</div>
      </div>
      <span class="alert-time">${now}</span>
    </div>
  `).join('');
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. DATABASE VIEWER
// ─────────────────────────────────────────────────────────────────────────────
async function loadDBView() {
  try {
    const data = await apiFetch(`/api/weather/history?city=${currentCity}&hours=24`);
    const rows  = data.readings || [];

    setText('dbTotal', rows.length);
    setText('dbCity',  data.city_name ?? currentCity);

    const tbody = $('dbTableBody');
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="loading-msg">No data yet — fetching…</td></tr>';
      return;
    }

    tbody.innerHTML = [...rows].reverse().map(r => {
      const ts = r.timestamp ? new Date(r.timestamp + 'Z').toLocaleString('en-IN') : '—';
      return `<tr>
        <td>${r.id}</td>
        <td>${ts}</td>
        <td>${r.temperature ?? '—'}</td>
        <td>${r.humidity ?? '—'}</td>
        <td>${r.pressure ?? '—'}</td>
        <td>${r.wind_speed ?? '—'}</td>
        <td>${r.rain ?? '—'}</td>
        <td>${r.uv_index ?? '—'}</td>
        <td>${r.source ?? '—'}</td>
      </tr>`;
    }).join('');

    setDot('dot-db', true);

  } catch (err) {
    console.error('DB view failed:', err);
    $('dbTableBody').innerHTML = `<tr><td colspan="9" class="loading-msg">⚠️ ${err.message}</td></tr>`;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 10. REFRESH ALL
// ─────────────────────────────────────────────────────────────────────────────
async function refreshAll() {
  const btn = $('refreshBtn');
  if (btn) btn.classList.add('spinning');
  await loadDashboard();
  if (btn) btn.classList.remove('spinning');
}

// ─────────────────────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────────────────────
async function init() {
  initParticles();
  setInterval(updateClock, 1000);
  updateClock();

  const loadMsg = $('aiLoadMsg');

  // Check backend health
  try {
    if (loadMsg) loadMsg.textContent = 'Checking Flask backend…';
    await apiFetch('/api/health');
    setDot('dot-backend', true);

    if (loadMsg) loadMsg.textContent = 'Fetching live weather from Open-Meteo API…';
    await loadDashboard();

    if (loadMsg) loadMsg.textContent = 'Warming up scikit-learn models…';
    setDot('dot-ml', true);

    if (loadMsg) loadMsg.textContent = 'Loading SQLite database…';
    setDot('dot-db', true);

  } catch (err) {
    console.error('Init error:', err);
    setDot('dot-backend', false);
    if (loadMsg) loadMsg.textContent = '⚠️ Backend offline. Start: python backend/app.py';
    // Still hide overlay after 3s so user can see the message
    setTimeout(() => {
      const overlay = $('aiOverlay');
      if (overlay) overlay.classList.add('hidden');
    }, 3000);
    return;
  }

  // Hide loading overlay
  setTimeout(() => {
    const overlay = $('aiOverlay');
    if (overlay) overlay.classList.add('hidden');
  }, 1200);

  // Auto-refresh every 30 seconds
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(loadDashboard, REFRESH_MS);
}

document.addEventListener('DOMContentLoaded', init);
