<script setup>
import { ref, onMounted, watch } from 'vue';
import axios from 'axios';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GaugeChart } from 'echarts/charts';
import { TooltipComponent } from 'echarts/components';
import VChart from 'vue-echarts';
import {
  SparklesIcon,
  CpuChipIcon,
  DocumentTextIcon,
  ArrowPathIcon,
  QuestionMarkCircleIcon,
  GlobeEuropeAfricaIcon
} from '@heroicons/vue/24/outline';

use([CanvasRenderer, GaugeChart, TooltipComponent]);

const prediction = ref(null);
const isLoading = ref(false);

const availableCountries = ref(['DE', 'FR', 'ES', 'IT', 'PL', 'NL', 'BE', 'AT']);
const selectedCountry = ref('DE');

// Features state (Input Boxes)
const features = ref({
  eu_load_mw: 0,
  eu_renewables_mw: 0,
  ttf_gas_price: 40,
  coal_price: 120,
  eu_ets_price: 80,
  brent_oil_price: 85,
  eu_gas_storage_anomaly: 0.0
});

const chartOption = ref({});
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' });

const fetchCountries = async () => {
  try {
    const res = await api.get('/api/countries');
    if (res.data && res.data.length > 0) {
      availableCountries.value = res.data;
    }
  } catch (e) {
    console.error("Lỗi lấy danh sách quốc gia:", e);
  }
};

const fetchLiveData = async () => {
  try {
    isLoading.value = true;
    const res = await api.get(`/api/fetch_live?country=${selectedCountry.value}`);
    if (res.data) {
      features.value.eu_load_mw = Math.round(res.data.eu_load_mw);
      features.value.eu_renewables_mw = Math.round(res.data.eu_renewables_mw);
      features.value.ttf_gas_price = Math.round(res.data.ttf_gas_price);
      features.value.coal_price = Math.round(res.data.coal_price);
      features.value.eu_ets_price = Math.round(res.data.eu_ets_price);
      features.value.brent_oil_price = Math.round(res.data.brent_oil_price);
      features.value.eu_gas_storage_anomaly = Number(res.data.eu_gas_storage_anomaly.toFixed(3));
      await fetchPrediction();
    }
  } catch (e) {
    console.error("Lỗi gọi Live API:", e);
  } finally {
    isLoading.value = false;
  }
};

const fetchPrediction = async () => {
  try {
    const payload = {
      country_code: selectedCountry.value,
      eu_load_mw: features.value.eu_load_mw,
      eu_renewables_mw: features.value.eu_renewables_mw,
      ttf_gas_price: features.value.ttf_gas_price,
      coal_price: features.value.coal_price,
      eu_ets_price: features.value.eu_ets_price,
      brent_oil_price: features.value.brent_oil_price,
      eu_gas_storage_anomaly: features.value.eu_gas_storage_anomaly
    };
    const res = await api.post('/api/predict_weekly', payload);
    prediction.value = res.data.predicted_next_week_price_eur;
    updateGauge();
  } catch (e) {
    console.error(e);
  }
};

watch(selectedCountry, () => {
  fetchLiveData();
});

watch(features, () => {
  fetchPrediction();
}, { deep: true });

const updateGauge = () => {
  if (prediction.value === null) return;
  const val = prediction.value;
  
  chartOption.value = {
    tooltip: {
      formatter: '{a} <br/>{b} : {c} €'
    },
    series: [
      {
        name: 'Mức Giá Dự Báo',
        type: 'gauge',
        min: 0,
        max: 300,
        splitNumber: 6,
        axisLine: {
          lineStyle: {
            width: 15,
            color: [
              [0.2, '#10b981'], // Rẻ (0-60)
              [0.5, '#f59e0b'], // Trung bình (60-150)
              [1, '#ef4444']    // Đắt (150-300)
            ]
          }
        },
        pointer: { itemStyle: { color: 'auto' } },
        axisTick: { distance: -15, length: 8, lineStyle: { color: '#fff', width: 2 } },
        splitLine: { distance: -15, length: 15, lineStyle: { color: '#fff', width: 3 } },
        axisLabel: { color: '#475569', distance: 20, fontSize: 12 },
        detail: {
          valueAnimation: true,
          formatter: '{value} €',
          color: 'inherit',
          fontSize: 30,
          fontWeight: 'bold',
          offsetCenter: [0, '70%']
        },
        data: [{ value: Number(val.toFixed(2)), name: 'Giá điện Tuần Tới' }]
      }
    ]
  };
};

onMounted(async () => {
  await fetchCountries();
  fetchLiveData();
});
</script>

<template>
  <div class="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-800">
    <!-- Header -->
    <header class="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shadow-sm sticky top-0 z-10">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-blue-100 rounded-lg text-blue-600">
          <SparklesIcon class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-900">Zero-Shot Giá Điện Châu Âu</h1>
          <p class="text-sm text-slate-500">Mô hình AI dự báo giá theo thời gian thực (Live Data)</p>
        </div>
      </div>
      <div class="flex items-center gap-4">
        <!-- Nút Fetch Live API -->
        <button @click="fetchLiveData" class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm">
          <ArrowPathIcon class="w-4 h-4" :class="{'animate-spin': isLoading}" />
          Tự động lấy Live API
        </button>
      </div>
    </header>

    <main class="flex-1 p-8">
      <div class="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
        
        <!-- Cột Input -->
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 relative">
          <!-- Hiệu ứng mờ khi đang lấy dữ liệu -->
          <div v-if="isLoading" class="absolute inset-0 bg-white/60 backdrop-blur-[1px] z-20 flex items-center justify-center rounded-xl">
             <div class="flex flex-col items-center text-blue-600 font-semibold gap-2">
                <ArrowPathIcon class="w-8 h-8 animate-spin" />
                Đang gọi API ENTSO-E & Yahoo Finance...
             </div>
          </div>
          
          <div class="flex items-center justify-between mb-6 border-b border-slate-100 pb-4">
            <div class="flex items-center gap-2">
                <DocumentTextIcon class="w-5 h-5 text-slate-500" />
                <h2 class="text-lg font-bold">Thông Số Tuần Này (Input)</h2>
            </div>
            
            <!-- Dropdown Quốc Gia -->
            <div class="flex items-center gap-2 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
                <GlobeEuropeAfricaIcon class="w-5 h-5 text-slate-600" />
                <select v-model="selectedCountry" class="bg-transparent border-none text-sm font-bold text-slate-700 focus:ring-0 cursor-pointer">
                    <option v-for="c in availableCountries" :key="c" :value="c">{{ c }}</option>
                </select>
            </div>
          </div>
          
          <div class="space-y-5">
            <!-- Load & Renewables -->
            <div class="grid grid-cols-2 gap-4 bg-blue-50/50 p-4 rounded-lg border border-blue-100">
              <!-- Tổng Nhu cầu (Load) -->
              <div class="relative group">
                <label class="flex items-center gap-1 text-sm font-semibold text-slate-700 mb-1">
                    Tổng Nhu cầu Tiêu thụ
                    <QuestionMarkCircleIcon class="w-4 h-4 text-slate-400 cursor-help" />
                </label>
                <!-- Tooltip -->
                <div class="absolute bottom-full left-0 mb-1 w-64 bg-slate-800 text-white text-xs rounded p-2 hidden group-hover:block z-30 shadow-xl">
                    (Load) Tổng nhu cầu tiêu thụ điện năng của quốc gia trong 1 Tuần (Đơn vị: MW). Tự động lấy từ API ENTSO-E.
                </div>
                <div class="flex items-center gap-2">
                  <input type="number" v-model="features.eu_load_mw" class="block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2 bg-white">
                  <span class="text-slate-500 text-sm font-mono">MW</span>
                </div>
              </div>
              
              <!-- Năng lượng Tái tạo (Renewables) -->
              <div class="relative group">
                <label class="flex items-center gap-1 text-sm font-semibold text-slate-700 mb-1">
                    Điện Gió & Mặt trời
                    <QuestionMarkCircleIcon class="w-4 h-4 text-slate-400 cursor-help" />
                </label>
                <!-- Tooltip -->
                <div class="absolute bottom-full left-0 mb-1 w-64 bg-slate-800 text-white text-xs rounded p-2 hidden group-hover:block z-30 shadow-xl">
                    (Renewables) Sản lượng điện Gió & Mặt trời dự kiến phát sinh trong Tuần (MW). Hệ thống sẽ lấy [Load] - [Renewables] để ra Tải dư.
                </div>
                <div class="flex items-center gap-2">
                  <input type="number" v-model="features.eu_renewables_mw" class="block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2 bg-white">
                  <span class="text-slate-500 text-sm font-mono">MW</span>
                </div>
              </div>
            </div>
            
            <div class="grid grid-cols-2 gap-4 mt-2">
              <!-- Khí TTF -->
              <div class="relative group">
                <label class="flex items-center gap-1 text-sm font-medium text-slate-700 mb-1">
                    Giá Khí TTF (Châu Âu)
                    <QuestionMarkCircleIcon class="w-3 h-3 text-slate-400 cursor-help" />
                </label>
                <div class="absolute bottom-full left-0 mb-1 w-48 bg-slate-800 text-white text-xs rounded p-2 hidden group-hover:block z-30">
                    Dutch TTF Natural Gas. Tự động cào từ Yahoo Finance (Mã: TTF=F).
                </div>
                <div class="flex items-center gap-2">
                  <input type="number" v-model="features.ttf_gas_price" class="block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2 bg-slate-50">
                  <span class="text-slate-500 text-sm">€</span>
                </div>
              </div>
              
              <!-- Than API2 -->
              <div class="relative group">
                <label class="flex items-center gap-1 text-sm font-medium text-slate-700 mb-1">
                    Giá Than API2
                    <QuestionMarkCircleIcon class="w-3 h-3 text-slate-400 cursor-help" />
                </label>
                <div class="absolute bottom-full left-0 mb-1 w-48 bg-slate-800 text-white text-xs rounded p-2 hidden group-hover:block z-30">
                    Giá than nhập khẩu cảng Rotterdam. Lấy từ Yahoo Finance (Mã: MTF=F).
                </div>
                <div class="flex items-center gap-2">
                  <input type="number" v-model="features.coal_price" class="block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2 bg-slate-50">
                  <span class="text-slate-500 text-sm">$</span>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <!-- Carbon ETS -->
              <div class="relative group">
                <label class="flex items-center gap-1 text-sm font-medium text-slate-700 mb-1">
                    Giá Quyền Xả Carbon
                    <QuestionMarkCircleIcon class="w-3 h-3 text-slate-400 cursor-help" />
                </label>
                <div class="absolute bottom-full left-0 mb-1 w-48 bg-slate-800 text-white text-xs rounded p-2 hidden group-hover:block z-30">
                    Giá EU ETS (Quyền phát thải). Nguồn: Yahoo Finance (Mã: MOZ=F).
                </div>
                <div class="flex items-center gap-2">
                  <input type="number" v-model="features.eu_ets_price" class="block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2 bg-slate-50">
                  <span class="text-slate-500 text-sm">€</span>
                </div>
              </div>
              
              <!-- Dầu Brent -->
              <div class="relative group">
                <label class="flex items-center gap-1 text-sm font-medium text-slate-700 mb-1">
                    Giá Dầu Brent
                    <QuestionMarkCircleIcon class="w-3 h-3 text-slate-400 cursor-help" />
                </label>
                 <div class="absolute bottom-full left-0 mb-1 w-48 bg-slate-800 text-white text-xs rounded p-2 hidden group-hover:block z-30">
                    Dầu thô Brent biển Bắc (Mã: BZ=F).
                </div>
                <div class="flex items-center gap-2">
                  <input type="number" v-model="features.brent_oil_price" class="block w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2 bg-slate-50">
                  <span class="text-slate-500 text-sm">$</span>
                </div>
              </div>
            </div>

            <!-- Lưu trữ khí -->
            <div class="relative group pt-2 border-t border-slate-100 mt-2">
              <label class="flex items-center gap-1 text-sm font-medium text-slate-700 mb-1">
                  Bất thường Khí lưu trữ
                  <QuestionMarkCircleIcon class="w-3 h-3 text-amber-500 cursor-help" />
              </label>
              <div class="absolute bottom-full left-0 mb-1 w-64 bg-slate-800 text-white text-xs rounded p-2 hidden group-hover:block z-30">
                  Độ lệch của lượng khí dự trữ Châu Âu hiện tại so với mức trung bình 5 năm lịch sử. Tự động tính toán thông qua API GIE AGSI.
              </div>
              <input type="number" step="0.01" v-model="features.eu_gas_storage_anomaly" class="block w-full rounded-md border-slate-300 shadow-sm focus:border-amber-500 focus:ring-amber-500 sm:text-sm border p-2 bg-amber-50">
            </div>
          </div>
        </div>

        <!-- Cột Output -->
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col items-center justify-center">
          <div class="flex flex-col items-center text-center mb-8">
            <CpuChipIcon class="w-10 h-10 text-emerald-500 mb-2" />
            <h2 class="text-2xl font-bold text-slate-900">Mức Giá Dự Báo Tuần Tới</h2>
            <p class="text-slate-500 text-sm font-semibold">Tự động điều chỉnh thang đo theo chuẩn {{ selectedCountry }}</p>
          </div>
          
          <div class="w-full h-[350px]">
            <v-chart class="w-full h-full" :option="chartOption" autoresize />
          </div>
          
        </div>

      </div>
    </main>
  </div>
</template>
