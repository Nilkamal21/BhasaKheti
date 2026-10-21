import React, { useState, useEffect } from 'react';
import { 
  CloudSun, 
  MapPin, 
  Search, 
  RefreshCw, 
  Droplets, 
  Wind, 
  CloudRain, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Calendar, 
  ShieldAlert,
  Sun,
  Cloud,
  CloudLightning,
  CloudFog,
  Navigation
} from 'lucide-react';
import { fetchWeatherForecast, searchWeatherLocations } from '../services/api';
import type { WeatherForecastResponse, LocationSearchResult } from '../services/api';

// Popular West Bengal agricultural presets
const WB_PRESETS = [
  { name: 'বর্ধমান (Bardhaman)', lat: 23.2324, lon: 87.8615 },
  { name: 'কলকাতা (Kolkata)', lat: 22.5726, lon: 88.3639 },
  { name: 'শিলিগুড়ি (Siliguri)', lat: 26.7271, lon: 88.3953 },
  { name: 'মালদা (Malda)', lat: 25.0108, lon: 88.1411 },
  { name: 'মেদিনীপুর (Medinipur)', lat: 22.4257, lon: 87.3199 },
  { name: 'বাঁকুড়া (Bankura)', lat: 23.2319, lon: 87.0784 },
  { name: 'কোচবিহার (Cooch Behar)', lat: 26.3239, lon: 89.4510 },
];

function getWeatherIcon(category: string, size = 24) {
  switch (category) {
    case 'clear':
      return <Sun size={size} className="text-amber-500" />;
    case 'partly_cloudy':
      return <CloudSun size={size} className="text-amber-400" />;
    case 'cloudy':
      return <Cloud size={size} className="text-gray-400" />;
    case 'fog':
      return <CloudFog size={size} className="text-blue-300" />;
    case 'rain':
    case 'drizzle':
    case 'heavy_rain':
      return <CloudRain size={size} className="text-blue-500" />;
    case 'thunderstorm':
      return <CloudLightning size={size} className="text-purple-600" />;
    default:
      return <CloudSun size={size} className="text-green-600" />;
  }
}

function formatDateBn(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const dayNames = ['রবিবার', 'সোমবার', 'মঙ্গলবার', 'বুধবার', 'বৃহস্পতিবার', 'শুক্রবার', 'শনিবার'];
    const dayName = dayNames[d.getDay()];
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      return `${dayName}, ${parts[2]}/${parts[1]}`;
    }
    return dateStr;
  } catch {
    return dateStr;
  }
}

export function WeatherView() {
  // Default to Bardhaman (rice bowl of Bengal)
  const [currentLocation, setCurrentLocation] = useState<{ name: string; lat: number; lon: number }>(WB_PRESETS[0]);
  const [forecast, setForecast] = useState<WeatherForecastResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<LocationSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [geoLocating, setGeoLocating] = useState<boolean>(false);
  const [geoNotice, setGeoNotice] = useState<string | null>(null);

  const loadWeather = async (lat: number, lon: number, name: string, isManualRefresh = false) => {
    if (isManualRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setErrorMessage(null);

    try {
      const data = await fetchWeatherForecast(lat, lon, name);
      setForecast(data);
    } catch (err: any) {
      setErrorMessage(err.message || 'আবহাওয়া তথ্য লোড করতে সমস্যা হয়েছে। অনুগ্রহ করে পুনরায় চেষ্টা করুন।');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadWeather(currentLocation.lat, currentLocation.lon, currentLocation.name);
  }, [currentLocation]);

  const handleSelectPreset = (preset: { name: string; lat: number; lon: number }) => {
    setCurrentLocation(preset);
    setSearchResults([]);
    setSearchQuery('');
  };

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || searchQuery.trim().length < 2) return;

    setIsSearching(true);
    setGeoNotice(null);
    try {
      const results = await searchWeatherLocations(searchQuery.trim());
      setSearchResults(results);
      if (results.length === 0) {
        setGeoNotice(`"${searchQuery}" নামে কোনো স্থান পাওয়া যায়নি। জেলা বা শহরের নাম ইংরেজিতে লিখে চেষ্টা করুন (যেমন: Bardhaman, Siliguri)`);
      }
    } catch (err: any) {
      setGeoNotice(err.message || 'স্থান অনুসন্ধানে সমস্যা হয়েছে।');
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectSearchResult = (item: LocationSearchResult) => {
    setCurrentLocation({
      name: item.display_label,
      lat: item.latitude,
      lon: item.longitude
    });
    setSearchResults([]);
    setSearchQuery('');
    setGeoNotice(null);
  };

  const handleGeolocation = () => {
    if (!navigator.geolocation) {
      setGeoNotice('আপনার ব্রাউজারে ভৌগোলিক অবস্থান (Geolocation) সমর্থিত নয়।');
      return;
    }

    setGeoLocating(true);
    setGeoNotice('ব্রাউজারের মাধ্যমে আপনার বর্তমান অবস্থান শনাক্ত করা হচ্ছে...');

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGeoLocating(false);
        const lat = parseFloat(pos.coords.latitude.toFixed(4));
        const lon = parseFloat(pos.coords.longitude.toFixed(4));
        setCurrentLocation({
          name: `বর্তমান অবস্থান (${lat}, ${lon})`,
          lat,
          lon
        });
        setGeoNotice(null);
      },
      (err) => {
        setGeoLocating(false);
        if (err.code === err.PERMISSION_DENIED) {
          setGeoNotice('অবস্থান ব্যবহারের অনুমতি দেওয়া হয়নি। অনুগ্রহ করে উপরের তালিকা থেকে স্থান নির্বাচন করুন।');
        } else {
          setGeoNotice(`অবস্থান শনাক্ত করতে ব্যর্থ: ${err.message}`);
        }
      },
      { timeout: 10000, enableHighAccuracy: false }
    );
  };

  return (
    <div className="card-box weather-container">
      {/* Header */}
      <div className="weather-header">
        <div className="weather-title-area">
          <div className="weather-badge-icon">
            <CloudSun size={26} className="text-brand-green" />
          </div>
          <div>
            <h2 className="card-title">আবহাওয়া পূর্বাভাস ও কৃষি সতর্কতা (Weather Dashboard)</h2>
            <p className="card-description">
              কৃষিকাজের পরিকল্পনা ও বালাইনাশক স্প্রে করার জন্য ওপেন-মেটিও (Open-Meteo) ভিত্তিক সঠিক আবহাওয়া তথ্য
            </p>
          </div>
        </div>

        <button 
          onClick={() => loadWeather(currentLocation.lat, currentLocation.lon, currentLocation.name, true)}
          className="btn-refresh" 
          disabled={loading || refreshing}
          title="নতুন তথ্য লোড করুন"
        >
          <RefreshCw size={16} className={refreshing ? 'spin-icon' : ''} />
          <span>{refreshing ? 'হালনাগাদ হচ্ছে...' : 'হালনাগাদ'}</span>
        </button>
      </div>

      {/* Location Selector Bar */}
      <div className="location-control-panel">
        <div className="location-current-display">
          <MapPin size={18} className="text-green-700" />
          <span className="location-name-label">নির্বাচিত স্থান: <strong>{currentLocation.name}</strong></span>
          <span className="location-coords">({currentLocation.lat.toFixed(2)}° N, {currentLocation.lon.toFixed(2)}° E)</span>
        </div>

        {/* Presets and GPS Button */}
        <div className="location-actions-row">
          <div className="presets-strip">
            <span className="presets-label">দ্রুত নির্বাচন:</span>
            {WB_PRESETS.map((preset) => (
              <button
                key={preset.name}
                onClick={() => handleSelectPreset(preset)}
                className={`preset-pill ${currentLocation.name === preset.name ? 'preset-pill-active' : ''}`}
              >
                {preset.name.split(' ')[0]}
              </button>
            ))}
          </div>

          <button 
            onClick={handleGeolocation}
            disabled={geoLocating}
            className="btn-geolocation"
            title="ব্রাউজার অনুমতি সাপেক্ষে বর্তমান স্থান শনাক্ত করুন"
          >
            <Navigation size={15} />
            <span>{geoLocating ? 'শনাক্ত হচ্ছে...' : 'বর্তমান অবস্থান'}</span>
          </button>
        </div>

        {/* Search input */}
        <form onSubmit={handleSearchSubmit} className="search-form-row">
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input 
              type="text"
              placeholder="জেলা বা থানার নাম খুঁজুন (যেমন: Nadia, Burdwan, Haldia)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="weather-search-input"
            />
          </div>
          <button type="submit" disabled={isSearching || !searchQuery.trim()} className="btn-search">
            {isSearching ? 'খোঁজা হচ্ছে...' : 'অনুসন্ধান'}
          </button>
        </form>

        {/* Geolocation or Search Notices */}
        {geoNotice && (
          <div className="status-banner banner-info" style={{ marginTop: '0.5rem', marginBottom: 0 }}>
            <span>{geoNotice}</span>
          </div>
        )}

        {/* Search Results Dropdown List */}
        {searchResults.length > 0 && (
          <div className="search-results-dropdown">
            <div className="search-results-title">অনুসন্ধানের ফলাফল ({searchResults.length} টি স্থান পাওয়া গেছে):</div>
            <div className="search-results-list">
              {searchResults.map((item) => (
                <button
                  key={`${item.latitude}-${item.longitude}-${item.name}`}
                  onClick={() => handleSelectSearchResult(item)}
                  className="search-result-item"
                >
                  <MapPin size={14} className="text-brand-green" />
                  <span className="search-result-name">{item.display_label}</span>
                  <span className="search-result-coords">({item.latitude.toFixed(2)}°, {item.longitude.toFixed(2)}°)</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Error state */}
      {errorMessage && (
        <div className="status-banner banner-warning">
          <AlertTriangle size={20} />
          <div>
            <strong>আবহাওয়া তথ্য লোড ত্রুটি:</strong> {errorMessage}
            <div style={{ marginTop: '0.25rem' }}>
              <button 
                onClick={() => loadWeather(currentLocation.lat, currentLocation.lon, currentLocation.name)}
                className="btn-retry"
              >
                আবার চেষ্টা করুন
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !forecast && (
        <div className="weather-loading-skeleton">
          <div className="skeleton-spinner">
            <RefreshCw size={28} className="spin-icon text-brand-green" />
          </div>
          <p className="skeleton-text">ওপেন-মেটিও থেকে সর্বশেষ আবহাওয়া তথ্য সংগ্রহ করা হচ্ছে...</p>
        </div>
      )}

      {/* Main Forecast Content */}
      {forecast && (
        <div className="forecast-display-area">
          {/* Stale Cache Notice if present */}
          {forecast.is_stale && forecast.stale_warning_bn && (
            <div className="status-banner banner-warning">
              <Clock size={18} />
              <span>{forecast.stale_warning_bn}</span>
            </div>
          )}

          {/* Current Conditions Card */}
          <div className="current-weather-card">
            <div className="current-top-row">
              <div className="current-weather-main">
                <div className="current-icon-wrap">
                  {getWeatherIcon(forecast.current_conditions.weather_type, 44)}
                </div>
                <div>
                  <div className="current-temp-val">
                    {forecast.current_conditions.temperature_c !== null 
                      ? `${forecast.current_conditions.temperature_c}°C` 
                      : 'তথ্য নেই'}
                  </div>
                  <div className="current-desc-bn">
                    {forecast.current_conditions.weather_desc_bn}
                  </div>
                  {forecast.current_conditions.apparent_temperature_c !== null && (
                    <div className="current-feels-like">
                      অনুভূত তাপমাত্রা: {forecast.current_conditions.apparent_temperature_c}°C
                    </div>
                  )}
                </div>
              </div>

              <div className="current-meta-col">
                <span className="data-source-tag">
                  উৎস: {forecast.provider}
                </span>
                <span className="obs-time">
                  পর্যবেক্ষণ: {forecast.current_conditions.observation_time.replace('T', ' ')}
                </span>
                {forecast.is_cached && (
                  <span className="cache-tag">
                    মেমরি ক্যাশ ({forecast.cached_age_seconds} সেকেন্ড পূর্বে সংরক্ষিত)
                  </span>
                )}
              </div>
            </div>

            {/* Metrics grid */}
            <div className="current-metrics-grid">
              <div className="metric-box">
                <div className="metric-header">
                  <Droplets size={16} className="text-blue-600" />
                  <span>আপেক্ষিক আর্দ্রতা</span>
                </div>
                <div className="metric-val">
                  {forecast.current_conditions.relative_humidity_pct !== null 
                    ? `${forecast.current_conditions.relative_humidity_pct}%` 
                    : '—'}
                </div>
                <div className="metric-sub">বাতাসের জলীয় বাষ্প</div>
              </div>

              <div className="metric-box">
                <div className="metric-header">
                  <CloudRain size={16} className="text-cyan-600" />
                  <span>বর্তমান বৃষ্টিপাত</span>
                </div>
                <div className="metric-val">
                  {forecast.current_conditions.precipitation_mm !== null 
                    ? `${forecast.current_conditions.precipitation_mm} মিমি` 
                    : '—'}
                </div>
                <div className="metric-sub">পরিমাপকৃত বৃষ্টি</div>
              </div>

              <div className="metric-box">
                <div className="metric-header">
                  <Wind size={16} className="text-teal-600" />
                  <span>বাতাসের গতিবেগ</span>
                </div>
                <div className="metric-val">
                  {forecast.current_conditions.wind_speed_kmh !== null 
                    ? `${forecast.current_conditions.wind_speed_kmh} কিমি/ঘণ্টা` 
                    : '—'}
                </div>
                <div className="metric-sub">
                  দিক: {forecast.current_conditions.wind_direction_bn} ({forecast.current_conditions.wind_direction_deg !== null ? `${Math.round(forecast.current_conditions.wind_direction_deg)}°` : ''})
                </div>
              </div>
            </div>
          </div>

          {/* Agricultural Advisory Card (কৃষি আবহাওয়া পরামর্শ) */}
          <div className={`agri-advisory-box ${forecast.agricultural_advisory.is_fieldwork_advisable ? 'advisory-favorable' : 'advisory-caution'}`}>
            <div className="advisory-header-row">
              <div className="advisory-title-group">
                {forecast.agricultural_advisory.is_fieldwork_advisable ? (
                  <CheckCircle2 size={24} className="text-green-700" />
                ) : (
                  <ShieldAlert size={24} className="text-amber-700" />
                )}
                <div>
                  <h3 className="advisory-heading">
                    কৃষি আবহাওয়া পরামর্শ (Agricultural Weather Advisory)
                  </h3>
                  <span className="advisory-status-badge">
                    {forecast.agricultural_advisory.is_fieldwork_advisable 
                      ? 'মাঠের কাজের জন্য অনুকূল সময়' 
                      : 'মাঠের কাজে সতর্কতা প্রয়োজন'}
                  </span>
                </div>
              </div>
            </div>

            <ul className="advisory-bullets-list">
              {forecast.agricultural_advisory.advisory_notes_bn.map((note, idx) => (
                <li key={idx} className="advisory-bullet-item">
                  <span className="bullet-indicator">•</span>
                  <span>{note}</span>
                </li>
              ))}
            </ul>

            <div className="advisory-caution-footer">
              <AlertTriangle size={15} className="text-amber-800" />
              <span>{forecast.agricultural_advisory.caution_notice_bn}</span>
            </div>
          </div>

          {/* 5-Day Near-Term Forecast */}
          <div className="daily-forecast-container">
            <h3 className="section-title">
              <Calendar size={18} className="text-brand-green" />
              <span>আগামী ৫ দিনের আবহাওয়ার পূর্বাভাস (5-Day Daily Forecast)</span>
            </h3>

            <div className="daily-cards-grid">
              {forecast.daily_forecast.map((day) => (
                <div key={day.date} className="daily-forecast-card">
                  <div className="daily-card-header">
                    <span className="daily-date-bn">{formatDateBn(day.date)}</span>
                  </div>

                  <div className="daily-weather-visual">
                    {getWeatherIcon(day.weather_type, 32)}
                    <span className="daily-condition-name">{day.weather_desc_bn}</span>
                  </div>

                  <div className="daily-temp-range">
                    <span className="daily-temp-max" title="সর্বোচ্চ তাপমাত্রা">
                      {day.temperature_max_c !== null ? `${Math.round(day.temperature_max_c)}°` : '—'}
                    </span>
                    <span className="temp-divider">/</span>
                    <span className="daily-temp-min" title="সর্বনিম্ন তাপমাত্রা">
                      {day.temperature_min_c !== null ? `${Math.round(day.temperature_min_c)}°` : '—'}
                    </span>
                  </div>

                  <div className="daily-metrics-sub">
                    <div className="daily-sub-row" title="বৃষ্টিপাতের সম্ভাবনা">
                      <CloudRain size={13} className="text-blue-500" />
                      <span>সম্ভাবনা: <strong>{day.precipitation_probability_pct ?? 0}%</strong></span>
                    </div>

                    <div className="daily-sub-row" title="সম্ভাব্য মোট বৃষ্টিপাত">
                      <Droplets size={13} className="text-cyan-600" />
                      <span>বৃষ্টি: <strong>{day.precipitation_sum_mm ?? 0} মিমি</strong></span>
                    </div>

                    <div className="daily-sub-row" title="সর্বোচ্চ বাতাসের গতি">
                      <Wind size={13} className="text-gray-500" />
                      <span>বাতাস: {day.wind_speed_max_kmh !== null ? `${Math.round(day.wind_speed_max_kmh)} কিমি/ঘ` : '—'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Provider Terms & Educational Transparency Card */}
          <div className="disclaimer-card weather-provider-card">
            <div className="disclaimer-title-row">
              <AlertTriangle size={18} />
              <strong>উপাত্তের স্বচ্ছতা ও সীমাবদ্ধতা (Data Transparency & Limitations)</strong>
            </div>
            <p className="disclaimer-text-bn">
              এই পূর্বাভাস <strong>{forecast.provider}</strong>-এর উন্মুক্ত এপিআই (Non-commercial Free Tier) থেকে প্রাপ্ত উপাত্তের ভিত্তিতে স্বয়ংক্রিয়ভাবে তৈরি। এটি সাধারণ কৃষি পরিকল্পনার জন্য তৈরি নিয়মভিত্তিক সতর্কবার্তা প্রদান করে; এতে কোনো রাসায়নিক কীটনাশক প্রয়োগের মাত্রা বা প্রত্যক্ষ প্রেসক্রিপশন প্রদান করা হয় না। কোনো গুরুত্বপূর্ণ কৃষি সিদ্ধান্ত নেওয়ার পূর্বে আপনার ব্লকের কৃষি প্রযুক্তি সহায়ক (KPS) বা সহ-কৃষি নির্দেশকের (ADA) পরামর্শ নিন।
            </p>
            <p className="disclaimer-text-en">
              Data retrieved via Open-Meteo Free API. Weather forecasts carry inherent atmospheric uncertainty. Use this advisory as situational guidance alongside your local Krishi Vigyan Kendra (KVK) or block agriculture office recommendations.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
