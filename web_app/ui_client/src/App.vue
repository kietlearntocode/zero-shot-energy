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
          <!-- Country Selector (Premium Dropdown) -->
          <div class="control-group">
            <label class="control-label">Market</label>
            <div class="premium-control" tabindex="0" @blur="closeCountryDropdown" @click="toggleCountryDropdown">
              <span class="premium-control-value">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="icon-blue">
                  <path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11m16-11v11M8 14v3m4-3v3m4-3v3"/>
                </svg>
                {{ countryNames[selectedCountry] || selectedCountry }}
              </span>
              <svg class="premium-arrow" :class="{ 'rotate-180': isCountryDropdownOpen }" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/>
              </svg>
            </div>
            
            <Transition name="fade-slide">
              <div v-if="isCountryDropdownOpen" class="premium-dropdown-menu">
                <div 
                  v-for="c in countries" 
                  :key="c" 
                  class="dropdown-item"
                  :class="{ 'active': c === selectedCountry }"
                  @click="selectCountry(c)"
                >
                  {{ countryNames[c] || c }}
                </div>
              </div>
            </Transition>
          </div>

          <!-- Date Picker -->
          <div class="control-group">
            <label class="control-label">Forecast from</label>
            <VueDatePicker
              v-model="selectedDate"
              :min-date="dateRange.min_date"
              :max-date="dateRange.max_forecast_date"
              :enable-time-picker="false"
              auto-apply
              dark
              :clearable="false"
              model-type="yyyy-MM-dd"
              format="dd/MM/yyyy"
              @update:model-value="onParamsChange"
              class="premium-datepicker"
              menu-class-name="powercast-menu"
            >
              <template #trigger>
                <div class="premium-control" tabindex="0">
                  <span class="premium-control-value">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="icon-blue">
                      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                      <line x1="16" y1="2" x2="16" y2="6"></line>
                      <line x1="8" y1="2" x2="8" y2="6"></line>
                      <line x1="3" y1="10" x2="21" y2="10"></line>
                    </svg>
                    {{ formattedSelectedDate }}
                  </span>
                  <svg class="premium-arrow" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/>
                  </svg>
                </div>
              </template>
            </VueDatePicker>
          </div>

          <!-- Today Button -->
          <div class="control-group" style="justify-content: flex-end;">
            <button @click="goToToday" class="btn-today" title="Jump to latest available date">
              Today
            </button>
          </div>
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
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import axios from 'axios'
import { LineChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent,
  MarkLineComponent, DataZoomComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'

use([LineChart, GridComponent, TooltipComponent, LegendComponent,
     MarkLineComponent, DataZoomComponent, CanvasRenderer])

// ── Config ────────────────────────────────────────────────────────────────
// Trỏ về localhost khi test
const API_BASE = 'http://localhost:8000'

const countryNames = {
  BE: 'Belgium', CZ: 'Czechia', DE: 'Germany', DK: 'Denmark', ES: 'Spain',
  FI: 'Finland', FR: 'France', GB: 'Great Britain', HU: 'Hungary',
  IE: 'Ireland', IT: 'Italy', NL: 'Netherlands', NO: 'Norway',
  PL: 'Poland', PT: 'Portugal', SE: 'Sweden', SK: 'Slovakia'
}

// ── State ─────────────────────────────────────────────────────────────────
const markets = ['DE']
const loading = ref(true)
const error = ref(null)
const forecast = ref(null)
const selectedDate = ref('2026-07-20')
const selectedCountry = ref('DE')
const dateRange = ref({
  min_date: '2022-01-01',
  max_forecast_date: '2026-07-26'
})

// Premium Dropdown State
const isCountryDropdownOpen = ref(false)
function toggleCountryDropdown() {
  isCountryDropdownOpen.value = !isCountryDropdownOpen.value
}
function closeCountryDropdown() {
  setTimeout(() => {
    isCountryDropdownOpen.value = false
  }, 150)
}
function selectCountry(c) {
  selectedCountry.value = c
  isCountryDropdownOpen.value = false
  onParamsChange()
}
const countries = ref(Object.keys(countryNames))

// ── Lifecycle ─────────────────────────────────────────────────────────────
onMounted(async () => {
  await fetchCountries()
  await fetchDateRange()
  
  if (!selectedDate.value) {
    const today = new Date().toISOString().split('T')[0]
    selectedDate.value = today > dateRange.value.max_forecast_date ? dateRange.value.max_forecast_date : today
  }
  
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
    if (!selectedDate.value) {
      const today = new Date().toISOString().split('T')[0]
      selectedDate.value = today > data.max_forecast_date ? data.max_forecast_date : (today < data.min_date ? data.min_date : today)
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
  const today = new Date().toISOString().split('T')[0]
  selectedDate.value = today > dateRange.value.max_forecast_date ? dateRange.value.max_forecast_date : (today < dateRange.value.min_date ? dateRange.value.min_date : today)
  await fetchForecast()
}

// ── Computed ──────────────────────────────────────────────────────────────
const formattedSelectedDate = computed(() => {
  if (!selectedDate.value) return 'Select Date'
  const d = new Date(selectedDate.value)
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
})

const hasActual = computed(() =>
  forecast.value?.forecast?.some(d => d.actual !== null)
)

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
  gap: 8px;
  position: relative;
}

.control-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ── PREMIUM CONTROLS (DROPDOWN) ── */
.premium-control {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 0 18px;
  height: 46px;
  width: 180px;
  color: #f8fafc;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 4px 20px -2px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
}
.premium-control:hover,
.premium-control:focus {
  background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(59,130,246,0.05));
  border-color: rgba(59,130,246,0.5);
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.3), inset 0 1px 0 rgba(255,255,255,0.1);
  transform: translateY(-1px);
  outline: none;
}
.premium-control-value {
  display: flex;
  align-items: center;
  gap: 12px;
}
.icon-blue {
  color: #60a5fa;
  filter: drop-shadow(0 0 4px rgba(96,165,250,0.5));
}
.premium-arrow {
  width: 18px;
  height: 18px;
  color: #94a3b8;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.rotate-180 {
  transform: rotate(180deg);
  color: #60a5fa;
}

.premium-dropdown-menu {
  position: absolute;
  top: calc(100% + 12px);
  left: 0;
  right: 0;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 16px;
  padding: 8px;
  z-index: 50;
  box-shadow: 0 20px 40px -10px rgba(0,0,0,0.7), 0 0 30px rgba(59,130,246,0.15);
}
.dropdown-item {
  padding: 12px 16px;
  border-radius: 10px;
  color: #cbd5e1;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  position: relative;
  overflow: hidden;
}
.dropdown-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 3px;
  background: #3b82f6;
  transform: scaleY(0);
  transition: transform 0.3s ease;
  border-radius: 0 4px 4px 0;
}
.dropdown-item:hover, .dropdown-item.active {
  background: linear-gradient(90deg, rgba(59,130,246,0.15) 0%, transparent 100%);
  color: #ffffff;
  padding-left: 20px;
}
.dropdown-item:hover::before, .dropdown-item.active::before {
  transform: scaleY(1);
}
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-12px) scale(0.98);
}

/* ── PREMIUM DATEPICKER ── */
.premium-datepicker {
  width: 170px;
}

/* Global VueDatePicker CSS Variables */
body .dp__theme_dark {
  --dp-background-color: transparent !important; /* Force transparent for glassmorphism */
  --dp-text-color: #f1f5f9;
  --dp-border-color: rgba(59, 130, 246, 0.22);
  --dp-hover-color: rgba(59, 130, 246, 0.15);
  --dp-hover-text-color: #ffffff;
  --dp-hover-icon-color: #ffffff;
  --dp-primary-color: #3b82f6;
  --dp-primary-text-color: #ffffff;
  --dp-secondary-color: rgba(255, 255, 255, 0.06);
  --dp-border-color-hover: rgba(59, 130, 246, 0.5);
  --dp-disabled-color: rgba(255, 255, 255, 0.03);
  --dp-disabled-color-text: #1e293b;
  --dp-icon-color: #94a3b8;
  --dp-border-radius: 12px;
  --dp-font-family: 'Inter', sans-serif;
  --dp-menu-min-width: 320px;
}

.premium-datepicker .dp__input {
  background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.1);
  color: #f8fafc;
  border-radius: 12px;
  padding: 8px 12px 8px 42px;
  font-size: 14px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  height: 46px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 20px -2px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.premium-datepicker .dp__input:focus,
.premium-datepicker .dp__input:hover {
  background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(59,130,246,0.05));
  border-color: rgba(59,130,246,0.5);
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.3), inset 0 1px 0 rgba(255,255,255,0.1);
  transform: translateY(-1px);
}

.premium-datepicker .dp__icon {
  color: #60a5fa;
  margin-left: 8px;
  filter: drop-shadow(0 0 4px rgba(96,165,250,0.5));
}

/* ── CALENDAR POPUP (CUSTOM MENU CLASS) ── */
.powercast-menu {
  background: rgba(15, 23, 42, 0.85) !important;
  backdrop-filter: blur(24px) !important;
  -webkit-backdrop-filter: blur(24px) !important;
  border: 1px solid rgba(59, 130, 246, 0.3) !important;
  border-radius: 16px !important;
  box-shadow: 0 20px 40px -10px rgba(0,0,0,0.7), 0 0 30px rgba(59,130,246,0.15) !important;
  font-family: 'Inter', sans-serif !important;
  padding: 12px !important;
}

/* Header Text (Month/Year) */
.powercast-menu .dp__month_year_select {
  font-size: 15px !important;
  font-weight: 700 !important;
  border-radius: 8px !important;
}

.powercast-menu .dp__month_year_select:hover {
  background: linear-gradient(90deg, rgba(59,130,246,0.18) 0%, transparent 100%) !important;
  color: #60a5fa !important;
}

/* Nav Arrows */
.powercast-menu .dp__nav_btn:hover {
  background: rgba(59,130,246,0.15) !important;
  color: #60a5fa !important;
}

/* Day-of-week Headers */
.powercast-menu .dp__calendar_header_item {
  color: #475569 !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  letter-spacing: 0.05em !important;
}

/* Date Cells */
.powercast-menu .dp__cell_inner {
  border-radius: 8px !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  color: #cbd5e1 !important;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* Hovering a date */
.powercast-menu .dp__cell_inner:not(.dp__active_date):not(.dp__cell_disabled):hover {
  background: linear-gradient(135deg, rgba(59,130,246,0.25), rgba(59,130,246,0.05)) !important;
  color: #ffffff !important;
  box-shadow: inset 0 0 0 1px rgba(59,130,246,0.3) !important;
  transform: scale(1.05) !important;
}

/* Active Date (Selected) */
.powercast-menu .dp__active_date {
  background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
  color: #ffffff !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 12px rgba(59,130,246,0.4), inset 0 1px 1px rgba(255,255,255,0.2) !important;
  border-radius: 8px !important;
}

/* Today highlight */
.powercast-menu .dp__today {
  border: 1px solid rgba(59,130,246,0.6) !important;
  color: #60a5fa !important;
  font-weight: 700 !important;
}

/* Offset days (other month) */
.powercast-menu .dp__cell_offset {
  color: #334155 !important;
}

/* Action row styling */
.powercast-menu .dp__action_row {
  border-top: 1px solid rgba(255,255,255,0.08) !important;
  padding-top: 12px !important;
}

.powercast-menu .dp__action_select {
  background: linear-gradient(135deg, rgba(59,130,246,0.35), rgba(59,130,246,0.15)) !important;
  border: 1px solid rgba(59,130,246,0.45) !important;
  color: #60a5fa !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
}

.powercast-menu .dp__action_select:hover {
  background: linear-gradient(135deg, rgba(59,130,246,0.55), rgba(59,130,246,0.3)) !important;
  color: #ffffff !important;
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
  background: linear-gradient(135deg, rgba(59,130,246,0.3), rgba(59,130,246,0.1));
  border: 1px solid rgba(59,130,246,0.4);
  color: #60a5fa;
  border-radius: 12px;
  padding: 0 20px;
  height: 46px;
  font-size: 14px;
  font-weight: 700;
  font-family: 'Inter', sans-serif;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
  align-self: flex-end;
  box-shadow: 0 4px 20px -2px rgba(59,130,246,0.2), inset 0 1px 0 rgba(255,255,255,0.1);
  backdrop-filter: blur(16px);
}

.btn-today:hover {
  background: linear-gradient(135deg, rgba(59,130,246,0.5), rgba(59,130,246,0.2));
  border-color: rgba(96,165,250,0.7);
  color: #ffffff;
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255,255,255,0.2);
  transform: translateY(-1px);
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
}

@media (max-width: 768px) {
  .header-inner { flex-direction: column; align-items: flex-start; gap: 16px; }
  .header-controls { flex-wrap: wrap; }
  .cards-grid { grid-template-columns: repeat(2, 1fr); }
  .footer { flex-direction: column; gap: 8px; }
  .main { padding: 20px 16px; }
}
</style>
