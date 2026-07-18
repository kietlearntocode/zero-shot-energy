<template>
  <div class="app-root">
    <!-- ── HEADER ─────────────────────────────────────────────────────── -->
    <header class="header">
      <div class="header-inner">
        <div class="logo">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13 2L3 14H12L11 22L21 10H12L13 2Z" fill="url(#bolt-grad)" stroke="url(#bolt-grad)" stroke-width="0.5" stroke-linejoin="round"/>
            <defs>
              <linearGradient id="bolt-grad" x1="3" y1="2" x2="21" y2="22" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#60a5fa"/>
                <stop offset="100%" stop-color="#f59e0b"/>
              </linearGradient>
            </defs>
          </svg>
          <span class="logo-text">PowerCast<span class="logo-eu">EU</span></span>
        </div>

        <div class="header-controls">
          <!-- Country Selector -->
          <div class="control-group">
            <label class="control-label">Market</label>
            <div class="select-wrapper">
              <select v-model="selectedCountry" @change="onParamsChange" class="custom-select" id="country-select">
                <option v-for="c in countries" :key="c" :value="c">{{ countryNames[c] || c }}</option>
              </select>
              <svg class="select-arrow" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/>
              </svg>
            </div>
          </div>

          <!-- Date Picker -->
          <div class="control-group">
            <label class="control-label">Forecast from</label>
            <input
              type="date"
              v-model="selectedDate"
              :min="dateRange.min_date"
              :max="dateRange.max_forecast_date"
              @change="onParamsChange"
              class="custom-date"
              id="date-picker"
            />
          </div>

          <!-- Today Button -->
          <button @click="goToToday" class="btn-today" title="Jump to latest available date">
            Today
          </button>
        </div>
      </div>
    </header>

    <!-- ── MAIN CONTENT ───────────────────────────────────────────────── -->
    <main class="main">

      <!-- Loading overlay -->
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <p>Fetching forecast...</p>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="error-card">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        {{ error }}
      </div>

      <template v-else-if="forecast">
        <!-- Mode Badge + Country Info -->
        <div class="status-row">
          <div class="status-left">
            <span :class="['mode-badge', forecast.mode === 'backtest' ? 'mode-backtest' : 'mode-forecast']">
              <span class="mode-dot"></span>
              {{ forecast.mode === 'backtest' ? 'Backtest — Actual available' : 'Forecast — Live prediction' }}
            </span>
            <span class="country-label">{{ countryNames[selectedCountry] }}</span>
          </div>
          <div class="status-right">
            <span class="data-label">Data through {{ forecast.data_last_date }}</span>
          </div>
        </div>

        <!-- ── 7-DAY FORECAST CARDS ─────────────────────────────────── -->
        <div class="cards-grid">
          <div
            v-for="(day, idx) in forecast.forecast"
            :key="day.date"
            :class="['day-card', idx === 0 ? 'day-card--active' : '', day.actual !== null ? 'day-card--has-actual' : '']"
          >
            <div class="card-weekday">{{ day.weekday.slice(0,3).toUpperCase() }}</div>
            <div class="card-date">{{ formatShortDate(day.date) }}</div>

            <div class="card-price-block">
              <div class="card-price">{{ day.predicted.toFixed(1) }}</div>
              <div class="card-unit">EUR/MWh</div>
            </div>

            <div v-if="day.actual !== null" class="card-actual">
              <span class="actual-dot"></span>
              Actual: {{ day.actual.toFixed(1) }}
            </div>

            <div :class="['card-indicator', getPriceLevel(day.predicted)]">
              <svg v-if="idx > 0 && day.predicted > forecast.forecast[idx-1].predicted"
                width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="18 15 12 9 6 15"/>
              </svg>
              <svg v-else-if="idx > 0 && day.predicted < forecast.forecast[idx-1].predicted"
                width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
              <svg v-else-if="idx === 0"
                width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <circle cx="12" cy="12" r="4" fill="currentColor"/>
              </svg>
              <span>{{ getPriceLevelLabel(day.predicted) }}</span>
            </div>
          </div>
        </div>

        <!-- ── CHART ─────────────────────────────────────────────────── -->
        <div class="chart-card">
          <div class="chart-header">
            <div class="chart-title">7-Day Price Trajectory</div>
            <div class="chart-legend">
              <span class="legend-item">
                <span class="legend-line legend-predicted"></span>
                Predicted
              </span>
              <span v-if="hasActual" class="legend-item">
                <span class="legend-line legend-actual"></span>
                Actual
              </span>
            </div>
          </div>
          <v-chart :option="chartOption" :autoresize="true" class="chart-container" />
        </div>

        <!-- ── MACRO INDICATORS ──────────────────────────────────────── -->
        <div class="macro-section">
          <div class="macro-title">Market Inputs (T-1)</div>
          <div class="macro-grid">
            <div class="macro-card" v-for="(item, key) in macroItems" :key="key">
              <div class="macro-icon">
                <component :is="item.icon" />
              </div>
              <div class="macro-info">
                <div class="macro-name">{{ item.label }}</div>
                <div class="macro-value">{{ formatMacro(item.value, item.unit) }}</div>
              </div>
              <div :class="['macro-bar', item.color]" :style="{ width: item.pct + '%' }"></div>
            </div>
          </div>
        </div>
      </template>

      <!-- Empty state -->
      <div v-else class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="empty-icon">
          <path d="M13 2L3 14H12L11 22L21 10H12L13 2Z" stroke-linejoin="round"/>
        </svg>
        <p>Select a market and date to view forecast</p>
      </div>

    </main>

    <!-- ── FOOTER ─────────────────────────────────────────────────────── -->
    <footer class="footer">
      <span>Sources: ENTSO-E Transparency Platform · GIE AGSI+ · Yahoo Finance · EMBER</span>
      <span>Model: XGBoost · Walk-Forward CV · 15 Features</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent,
  MarkLineComponent, DataZoomComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([LineChart, GridComponent, TooltipComponent, LegendComponent,
     MarkLineComponent, DataZoomComponent, CanvasRenderer])

// ── Config ────────────────────────────────────────────────────────────────
// API endpoint Backend (Deploy trên Render)
const API_BASE = 'https://zero-shot-energy.onrender.com'

const countryNames = {
  BE: 'Belgium', CZ: 'Czechia', DE: 'Germany', DK: 'Denmark', ES: 'Spain',
  FI: 'Finland', FR: 'France', GB: 'Great Britain', HU: 'Hungary',
  IE: 'Ireland', IT: 'Italy', NL: 'Netherlands', NO: 'Norway',
  PL: 'Poland', PT: 'Portugal', SE: 'Sweden', SK: 'Slovakia'
}

// ── State ─────────────────────────────────────────────────────────────────
const loading        = ref(false)
const error          = ref(null)
const countries      = ref(Object.keys(countryNames))
const selectedCountry = ref('DE')
const selectedDate   = ref('')
const dateRange      = ref({ min_date: '2019-01-01', max_date: '2025-12-31', max_forecast_date: '2026-01-07' })
const forecast       = ref(null)

// ── Lifecycle ─────────────────────────────────────────────────────────────
onMounted(async () => {
  await fetchCountries()
  await fetchDateRange()
  selectedDate.value = forecast.value?.data_last_date || dateRange.value.max_date
  await fetchForecast()
})

// ── API calls ─────────────────────────────────────────────────────────────
async function fetchCountries() {
  try {
    const { data } = await axios.get(`${API_BASE}/api/countries`)
    countries.value = data
  } catch { /* use defaults */ }
}

async function fetchDateRange() {
  try {
    const { data } = await axios.get(`${API_BASE}/api/date_range`, {
      params: { country: selectedCountry.value }
    })
    dateRange.value = data
    // Set default date = last available
    if (!selectedDate.value) {
      selectedDate.value = data.max_date
    }
  } catch (e) {
    console.warn('date_range error:', e)
  }
}

async function fetchForecast() {
  if (!selectedDate.value) return
  loading.value = true
  error.value = null
  try {
    const { data } = await axios.get(`${API_BASE}/api/forecast`, {
      params: { country: selectedCountry.value, date: selectedDate.value }
    })
    forecast.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to fetch forecast'
  } finally {
    loading.value = false
  }
}

async function onParamsChange() {
  await fetchDateRange()
  await fetchForecast()
}

async function goToToday() {
  await fetchDateRange()
  selectedDate.value = dateRange.value.max_date
  await fetchForecast()
}

// ── Computed ──────────────────────────────────────────────────────────────
const hasActual = computed(() =>
  forecast.value?.forecast?.some(d => d.actual !== null)
)

const macroItems = computed(() => {
  if (!forecast.value?.macro_snapshot) return []
  const s = forecast.value.macro_snapshot
  return [
    { label: 'TTF Gas (T-2)',  value: s.TTF_Gas_Lag2,          unit: '€/MWh', color: 'bar-amber',   pct: clamp((s.TTF_Gas_Lag2   / 120) * 100, 5, 95) },
    { label: 'Coal API2 (T-2)',value: s.Coal_Lag2,             unit: '$/t',   color: 'bar-gray',    pct: clamp((s.Coal_Lag2      / 250) * 100, 5, 95) },
    { label: 'EU ETS (T-2)',   value: s.EU_ETS_Lag2,           unit: '€/t',   color: 'bar-green',   pct: clamp((s.EU_ETS_Lag2    / 150) * 100, 5, 95) },
    { label: 'Brent (T-2)',    value: s.Brent_Oil_Lag2,        unit: '$/bbl', color: 'bar-orange',  pct: clamp((s.Brent_Oil_Lag2 / 120) * 100, 5, 95) },
    { label: 'Avg Res Load',   value: s.Country_Avg_Residual_Load, unit: 'MW',color: 'bar-blue',    pct: clamp((s.Country_Avg_Residual_Load / 40000) * 100, 5, 95) },
    { label: 'Gas Stor (T-2)', value: s.EU_Gas_Storage_Lag2,   unit: '%',     color: 'bar-teal',    pct: clamp((s.EU_Gas_Storage_Lag2 * 100 + 50), 5, 95) },
  ]
})

const chartOption = computed(() => {
  if (!forecast.value?.forecast) return {}
  const days = forecast.value.forecast
  const dates    = days.map(d => formatShortDate(d.date))
  const predicted = days.map(d => d.predicted)
  const actual    = days.filter(d => d.actual !== null).length > 0
                    ? days.map(d => d.actual) : []

  const series = [
    {
      name: 'Predicted',
      type: 'line',
      data: predicted,
      smooth: 0.4,
      symbol: 'circle',
      symbolSize: 7,
      lineStyle: { color: '#3b82f6', width: 2.5 },
      itemStyle: { color: '#3b82f6', borderColor: '#0f172a', borderWidth: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(59,130,246,0.18)' },
            { offset: 1, color: 'rgba(59,130,246,0.0)' }
          ]
        }
      }
    }
  ]

  if (actual.length > 0) {
    series.push({
      name: 'Actual',
      type: 'line',
      data: actual,
      smooth: 0.3,
      symbol: 'diamond',
      symbolSize: 8,
      lineStyle: { color: '#10b981', width: 2.5 },
      itemStyle: { color: '#10b981', borderColor: '#0f172a', borderWidth: 2 },
    })
  }

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15,23,42,0.95)',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      textStyle: { color: '#f1f5f9', fontSize: 13, fontFamily: 'Inter, sans-serif' },
      formatter: params => {
        let html = `<div style="margin-bottom:6px;font-weight:600;color:#94a3b8">${params[0].axisValue}</div>`
        params.forEach(p => {
          const color = p.seriesName === 'Predicted' ? '#3b82f6' : '#10b981'
          const val = Number(p.value)
          const valDisplay = !isNaN(val) && p.value !== null && p.value !== undefined && p.value !== '' ? val.toFixed(2) : '–'
          html += `<div style="display:flex;align-items:center;gap:8px;margin:2px 0">
            <span style="width:10px;height:10px;border-radius:50%;background:${color};display:inline-block"></span>
            <span style="color:#94a3b8">${p.seriesName}:</span>
            <span style="font-weight:600;color:#f1f5f9">${valDisplay} EUR/MWh</span>
          </div>`
        })
        return html
      }
    },
    grid: { left: 52, right: 24, top: 20, bottom: 32 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine:  { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisTick:  { show: false },
      axisLabel: { color: '#64748b', fontSize: 12, fontFamily: 'Inter, sans-serif' },
    },
    yAxis: {
      type: 'value',
      name: 'EUR/MWh',
      nameTextStyle: { color: '#475569', fontSize: 11, fontFamily: 'Inter, sans-serif' },
      axisLine:  { show: false },
      axisTick:  { show: false },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontSize: 12, fontFamily: 'Inter, sans-serif',
                   formatter: v => v.toFixed(0) },
    },
    series,
  }
})

// ── Helpers ───────────────────────────────────────────────────────────────
function formatShortDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
}

function formatMacro(value, unit) {
  if (value === null || value === undefined || isNaN(value)) return '—'
  if (unit === 'MW') return Math.round(value).toLocaleString() + ' ' + unit
  if (unit === '%') return (value * 100).toFixed(1) + '%'
  return value.toFixed(1) + ' ' + unit
}

function getPriceLevel(price) {
  if (price < 40)  return 'level-low'
  if (price < 80)  return 'level-mid'
  if (price < 120) return 'level-high'
  return 'level-extreme'
}

function getPriceLevelLabel(price) {
  if (price < 40)  return 'Low'
  if (price < 80)  return 'Normal'
  if (price < 120) return 'High'
  return 'Extreme'
}

function clamp(v, min, max) {
  return Math.min(Math.max(v, min), max)
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:       #060b14;
  --surface:  rgba(255,255,255,0.035);
  --surface2: rgba(255,255,255,0.06);
  --border:   rgba(255,255,255,0.08);
  --border2:  rgba(255,255,255,0.12);
  --text-1:   #f1f5f9;
  --text-2:   #94a3b8;
  --text-3:   #475569;
  --blue:     #3b82f6;
  --blue-dim: rgba(59,130,246,0.15);
  --amber:    #f59e0b;
  --green:    #10b981;
  --red:      #ef4444;
}

html, body { height: 100%; }

body {
  font-family: 'Inter', sans-serif;
  background: var(--bg);
  color: var(--text-1);
  min-height: 100vh;
  background-image:
    radial-gradient(ellipse 60% 50% at 50% -10%, rgba(59,130,246,0.12) 0%, transparent 70%),
    radial-gradient(ellipse 40% 30% at 80% 80%, rgba(245,158,11,0.06) 0%, transparent 60%);
}

.app-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ── HEADER ── */
.header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(6,11,20,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
}

.header-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 14px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-1);
}

.logo-eu {
  color: var(--blue);
  font-weight: 800;
}

.header-controls {
  display: flex;
  align-items: flex-end;
  gap: 20px;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.control-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-3);
}

.select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.custom-select, .custom-date {
  background: var(--surface2);
  border: 1px solid var(--border2);
  color: var(--text-1);
  border-radius: 8px;
  padding: 8px 36px 8px 14px;
  font-size: 14px;
  font-weight: 500;
  font-family: 'Inter', sans-serif;
  outline: none;
  appearance: none;
  -webkit-appearance: none;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  min-width: 140px;
}

.custom-date {
  padding: 8px 14px;
  min-width: 160px;
  color-scheme: dark;
}

.custom-select:focus, .custom-date:focus {
  border-color: var(--blue);
  background: rgba(59,130,246,0.08);
}

.select-arrow {
  position: absolute;
  right: 10px;
  width: 16px;
  height: 16px;
  color: var(--text-3);
  pointer-events: none;
}

.btn-today {
  background: var(--blue-dim);
  border: 1px solid rgba(59,130,246,0.3);
  color: var(--blue);
  border-radius: 8px;
  padding: 9px 18px;
  font-size: 13px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  white-space: nowrap;
  align-self: flex-end;
}

.btn-today:hover {
  background: rgba(59,130,246,0.2);
  border-color: rgba(59,130,246,0.5);
}

/* ── MAIN ── */
.main {
  flex: 1;
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px;
  width: 100%;
  position: relative;
}

/* Loading */
.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 80px 0;
  color: var(--text-2);
  font-size: 15px;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Error */
.error-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  background: rgba(239,68,68,0.08);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 12px;
  color: #fca5a5;
  font-size: 14px;
}

/* Status row */
.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.status-left { display: flex; align-items: center; gap: 16px; }
.status-right { display: flex; align-items: center; gap: 8px; }

.mode-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 14px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.mode-backtest {
  background: rgba(16,185,129,0.1);
  border: 1px solid rgba(16,185,129,0.25);
  color: #34d399;
}

.mode-forecast {
  background: rgba(245,158,11,0.1);
  border: 1px solid rgba(245,158,11,0.25);
  color: #fbbf24;
}

.mode-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.country-label {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
}

.data-label {
  font-size: 12px;
  color: var(--text-3);
}

/* ── 7-DAY CARDS ── */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
  margin-bottom: 24px;
}

.day-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  transition: border-color 0.2s, background 0.2s, transform 0.2s;
  cursor: default;
  position: relative;
  overflow: hidden;
}

.day-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(59,130,246,0.4), transparent);
  opacity: 0;
  transition: opacity 0.2s;
}

.day-card:hover {
  border-color: var(--border2);
  background: var(--surface2);
  transform: translateY(-2px);
}

.day-card:hover::before { opacity: 1; }

.day-card--active {
  background: rgba(59,130,246,0.07);
  border-color: rgba(59,130,246,0.3);
}

.day-card--active::before { opacity: 1; }

.card-weekday {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--text-3);
}

.card-date {
  font-size: 11px;
  color: var(--text-2);
  font-weight: 500;
}

.card-price-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  margin: 4px 0;
}

.card-price {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-1);
  line-height: 1;
}

.card-unit {
  font-size: 10px;
  color: var(--text-3);
  font-weight: 500;
}

.card-actual {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--green);
  font-weight: 500;
}

.actual-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--green);
}

.card-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 100px;
}

.level-low     { background: rgba(16,185,129,0.12); color: #34d399; }
.level-mid     { background: rgba(59,130,246,0.12); color: #60a5fa; }
.level-high    { background: rgba(245,158,11,0.12); color: #fbbf24; }
.level-extreme { background: rgba(239,68,68,0.12);  color: #f87171; }

/* ── CHART ── */
.chart-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
}

.chart-legend {
  display: flex;
  gap: 20px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-2);
  font-weight: 500;
}

.legend-line {
  width: 24px;
  height: 2.5px;
  border-radius: 2px;
}

.legend-predicted { background: var(--blue); }
.legend-actual    { background: var(--green); }

.chart-container {
  height: 300px;
  width: 100%;
}

/* ── MACRO INDICATORS ── */
.macro-section { margin-bottom: 24px; }

.macro-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-3);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 14px;
}

.macro-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
}

.macro-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s;
}

.macro-card:hover {
  border-color: var(--border2);
}

.macro-info { position: relative; z-index: 1; }
.macro-icon { display: none; }

.macro-name {
  font-size: 11px;
  color: var(--text-3);
  font-weight: 600;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}

.macro-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-1);
  letter-spacing: -0.02em;
}

.macro-bar {
  position: absolute;
  bottom: 0; left: 0;
  height: 3px;
  border-radius: 0 2px 0 0;
  opacity: 0.7;
  transition: width 0.5s ease;
}

.bar-amber  { background: var(--amber); }
.bar-gray   { background: #6b7280; }
.bar-green  { background: var(--green); }
.bar-orange { background: #f97316; }
.bar-blue   { background: var(--blue); }
.bar-teal   { background: #14b8a6; }

/* ── EMPTY ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 100px 0;
  color: var(--text-3);
  font-size: 15px;
}

.empty-icon { opacity: 0.3; }

/* ── FOOTER ── */
.footer {
  border-top: 1px solid var(--border);
  padding: 16px 32px;
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-3);
}

/* ── RESPONSIVE ── */
@media (max-width: 1024px) {
  .cards-grid { grid-template-columns: repeat(4, 1fr); }
  .macro-grid { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 768px) {
  .header-inner { flex-direction: column; align-items: flex-start; gap: 16px; }
  .header-controls { flex-wrap: wrap; }
  .cards-grid { grid-template-columns: repeat(2, 1fr); }
  .macro-grid { grid-template-columns: repeat(2, 1fr); }
  .footer { flex-direction: column; gap: 8px; }
  .main { padding: 20px 16px; }
}
</style>
