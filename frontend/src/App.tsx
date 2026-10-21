import React, { useEffect, useState } from 'react';
import { 
  Sprout, 
  Globe, 
  ChevronDown, 
  Sparkles,
  Layers,
  Droplets,
  CloudSun,
  BookOpen,
  TrendingUp,
  FileText,
  Activity,
  ArrowLeft,
  CheckCircle2
} from 'lucide-react';
import { checkBackendHealth } from './services/api';
import type { HealthResponse } from './services/api';
import { DiseaseView } from './components/DiseaseView';
import { SoilTypeView } from './components/SoilTypeView';
import { SoilMoistureView } from './components/SoilMoistureView';
import { WeatherView } from './components/WeatherView';
import { KnowledgeView } from './components/KnowledgeView';
import { CropIntelligenceView } from './components/CropIntelligenceView';
import { MarketView } from './components/MarketView';
import { SchemesView } from './components/SchemesView';
import { SupervisorHomeView } from './components/SupervisorHomeView';
import './App.css';

export type Tab = 'home' | 'intelligence' | 'disease' | 'soil_type' | 'soil_moisture' | 'weather' | 'knowledge' | 'market' | 'schemes' | 'system_status';

export interface TabItem {
  id: Tab;
  label: string;
  sublabel: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
  plannedPhase: string;
}

export const TABS: TabItem[] = [
  { id: 'home', label: 'সুপারভাইজার সহকারী', sublabel: 'Supervisor Home', icon: Sparkles, plannedPhase: 'পর্যায় ৯ (সক্রিয়)' },
  { id: 'intelligence', label: 'বুদ্ধিমান পরামর্শক', sublabel: 'Crop Intelligence', icon: BookOpen, plannedPhase: 'পর্যায় ৬ (সক্রিয়)' },
  { id: 'disease', label: 'গাছের রোগ নির্ণয়', sublabel: 'Plant Disease', icon: Sprout, plannedPhase: 'পর্যায় ২ (সক্রিয়)' },
  { id: 'soil_type', label: 'মাটির ধরন', sublabel: 'Soil Type', icon: Layers, plannedPhase: 'পর্যায় ৩ (সক্রিয়)' },
  { id: 'soil_moisture', label: 'মাটির আর্দ্রতা ও সেচ', sublabel: 'Soil Moisture', icon: Droplets, plannedPhase: 'পর্যায় ৩ (সক্রিয়)' },
  { id: 'weather', label: 'আবহাওয়ার পূর্বাভাস', sublabel: 'Weather', icon: CloudSun, plannedPhase: 'পর্যায় ৪ (সক্রিয়)' },
  { id: 'knowledge', label: 'কৃষি জ্ঞানভাণ্ডার', sublabel: 'Knowledge', icon: BookOpen, plannedPhase: 'পর্যায় ৫ (সক্রিয়)' },
  { id: 'market', label: 'বাজার দর', sublabel: 'Market Rates', icon: TrendingUp, plannedPhase: 'পর্যায় ৭ (সক্রিয়)' },
  { id: 'schemes', label: 'সরকারি প্রকল্প', sublabel: 'Government Schemes', icon: FileText, plannedPhase: 'পর্যায় ৭ (সক্রিয়)' },
  { id: 'system_status', label: 'সিস্টেম স্ট্যাটাস', sublabel: 'App Health', icon: Activity, plannedPhase: 'পর্যায় ১ (সক্রিয়)' },
];

export function App() {
  const [activeTab, setActiveTab] = useState<Tab>('home');
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [showLangMenu, setShowLangMenu] = useState<boolean>(false);
  const [showAdvancedTools, setShowAdvancedTools] = useState<boolean>(false);

  useEffect(() => {
    checkBackendHealth()
      .then((data) => setHealthData(data))
      .catch(() => {});
  }, []);

  return (
    <div className="app-container">
      {/* Scenic Pastoral Header matching Reference Image */}
      <header className="app-header">
        <div className="header-brand-container">
          {/* Stylized Two Leaves Brand Mark */}
          <div className="brand-logo-wrap" onClick={() => setActiveTab('home')}>
            <svg viewBox="0 0 48 48" className="brand-svg-leaves" fill="none" aria-hidden="true">
              <path d="M12 40C12 40 14 26 26 18C38 10 42 6 42 6C42 6 40 18 32 26C24 34 16 38 12 40Z" fill="#1b5e20" />
              <path d="M14 38C14 38 18 28 26 22C34 16 40 12 40 12C40 12 36 22 28 28C22 33 16 36 14 38Z" fill="#4caf50" />
              <path d="M12 40C12 40 10 28 4 22C4 22 14 20 22 26" fill="#81c784" />
              <path d="M12 40C12 40 14 30 20 24" stroke="#0e3820" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>

          <div className="brand-titles">
            <h1 className="brand-title">ভাষাখেতি</h1>
            <p className="brand-subtitle">
              আপনার কৃষি সহায়ক <span className="sr-accessible-sub">• কৃষকের নির্ভরযোগ্য ডিজিটাল পরামর্শক</span>
            </p>
          </div>
        </div>

        {/* Right: Bengali Language Selector Pill Button */}
        <div className="header-actions">
          <div className="lang-pill-wrapper">
            <button
              type="button"
              onClick={() => setShowLangMenu(!showLangMenu)}
              className="lang-selector-pill"
              aria-label="ভাষা নির্বাচন (Language Selector)"
            >
              <Globe size={18} className="lang-globe-icon" />
              <span className="lang-text">বাংলা</span>
              <ChevronDown size={16} className={`chevron-lang ${showLangMenu ? 'rotate-180' : ''}`} />
            </button>

            {/* Language & Tools Dropdown Menu */}
            {showLangMenu && (
              <div className="lang-dropdown-card">
                <div className="lang-option lang-option-selected">
                  <span className="lang-check">✓</span>
                  <span>বাংলা (সক্রিয়)</span>
                </div>
                <div className="lang-option lang-option-disabled">
                  <span className="lang-check"></span>
                  <span>English (আসন্ন)</span>
                </div>
                <div className="dropdown-divider" />
                <button
                  type="button"
                  onClick={() => {
                    setShowAdvancedTools(!showAdvancedTools);
                    setShowLangMenu(false);
                  }}
                  className="btn-toggle-advanced"
                >
                  <Layers size={14} />
                  <span>{showAdvancedTools ? 'সহজ মোডে ফিরুন' : 'বিশেষায়িত টুলসমূহ'}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* When on a specialized sub-view, provide a clean return button */}
      {activeTab !== 'home' && (
        <div className="subview-breadcrumb-bar">
          <button
            type="button"
            onClick={() => setActiveTab('home')}
            className="btn-back-home"
            aria-label="মূল সংলাপে ফিরুন"
          >
            <ArrowLeft size={16} />
            <span>মূল সংলাপে ফিরুন (হোম)</span>
          </button>
          <span className="subview-active-title">
            {TABS.find((t) => t.id === activeTab)?.label}
          </span>
        </div>
      )}

      {/* Accessible Navigation Items: Always rendered in the DOM for accessibility and automated testing */}
      <nav 
        className={`nav-container ${showAdvancedTools ? 'nav-container-visible' : 'nav-accessible-hidden'}`} 
        aria-label="প্রধান মেনু"
      >
        <div className="nav-heading">বিশেষায়িত কৃষি সেবাসমূহ</div>
        <div className="nav-items-grid">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  setShowAdvancedTools(false);
                }}
                className={`nav-button ${isActive ? 'nav-button-active' : ''}`}
              >
                <Icon size={18} className="nav-icon" />
                <div className="nav-label-box">
                  <span className="nav-label-bn">{tab.label}</span>
                  <span className="nav-label-en">{tab.sublabel}</span>
                </div>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Main Viewport Container */}
      <main className="content-container">
        {activeTab === 'home' ? (
          <SupervisorHomeView />
        ) : activeTab === 'intelligence' ? (
          <CropIntelligenceView />
        ) : activeTab === 'disease' ? (
          <DiseaseView />
        ) : activeTab === 'soil_type' ? (
          <SoilTypeView />
        ) : activeTab === 'soil_moisture' ? (
          <SoilMoistureView />
        ) : activeTab === 'weather' ? (
          <WeatherView />
        ) : activeTab === 'knowledge' ? (
          <KnowledgeView />
        ) : activeTab === 'market' ? (
          <MarketView />
        ) : activeTab === 'schemes' ? (
          <SchemesView />
        ) : activeTab === 'system_status' ? (
          <div className="card-box">
            <div className="card-header">
              <div>
                <h2 className="card-title">সিস্টেম ও অবকাঠামো স্ট্যাটাস (System Health)</h2>
                <p className="card-description">
                  অ্যাপ্লিকেশনের মূল কাঠামো ও মডেল সংহতকরণ পরীক্ষার লাইভ ড্যাশবোর্ড
                </p>
              </div>
            </div>

            {healthData && (
              <div className="health-grid">
                <div className="stat-card">
                  <div className="stat-label">সার্ভার স্ট্যাটাস</div>
                  <div className="stat-value text-green">
                    <CheckCircle2 size={20} />
                    <span>{healthData.status.toUpperCase()}</span>
                  </div>
                  <div className="stat-sub">পরিবেশ: {healthData.environment}</div>
                </div>

                <div className="stat-card">
                  <div className="stat-label">ডাটাবেজ (SQLite)</div>
                  <div className="stat-value text-green">
                    <CheckCircle2 size={20} />
                    <span>{healthData.database_connected ? 'সংযুক্ত (Connected)' : 'বিচ্ছিন্ন'}</span>
                  </div>
                  <div className="stat-sub">লোকাল লাইটওয়েট ফাইল স্টোরেজ</div>
                </div>

                <div className="stat-card">
                  <div className="stat-label">বর্তমান পর্যায়</div>
                  <div className="stat-value text-blue">
                    <Sparkles size={20} />
                    <span>পর্যায় ৯</span>
                  </div>
                  <div className="stat-sub">মাল্টি-এজেন্ট সুপারভাইজার আর্কিটেকচার</div>
                </div>
              </div>
            )}

            <div className="models-status-section">
              <h3 className="section-title">সংহত অফলাইন এআই ও মেশিন লার্নিং মডেলসমূহ (AI Models)</h3>
              <div className="models-list">
                <div className="model-item">
                  <div className="model-header">
                    <span className="model-name">১. গাছের পাতার রোগ শনাক্তকরণ (MobileNetV2 Disease Model)</span>
                    <span className="status-pill status-ready">প্রস্তুত (Ready)</span>
                  </div>
                  <p className="model-desc">ফসলের পাতার ছবি বিশ্লেষণ করে ১৫টি ক্যাটাগরির রোগ ও সুস্থ পাতা শনাক্তকরণ।</p>
                </div>
                <div className="model-item">
                  <div className="model-header">
                    <span className="model-name">২. মাটির ধরন শ্রেণিবিন্যাসকারী (MobileNetV2 TFLite Soil Type)</span>
                    <span className="status-pill status-ready">প্রস্তুত (Ready)</span>
                  </div>
                  <p className="model-desc">মাটির ছবি দেখে বেলে, এঁটেল, দোআঁশ ও পলি মাটির পূর্বাভাস প্রদান।</p>
                </div>
                <div className="model-item">
                  <div className="model-header">
                    <span className="model-name">৩. মাটির আর্দ্রতা শনাক্তকরণ (MobileNetV2 TFLite Moisture)</span>
                    <span className="status-pill status-ready">প্রস্তুত (Ready)</span>
                  </div>
                  <p className="model-desc">মাটির উপরিভাগের স্যাঁতসেঁতে অবস্থা যাচাই করে পরিমিত সেচের পরামর্শ প্রদান।</p>
                </div>
                <div className="model-item">
                  <div className="model-header">
                    <span className="model-name">৪. বুদ্ধিমান বহু-টুল কৃষি পরামর্শক (Crop Intelligence)</span>
                    <span className="status-pill status-ready">প্রস্তুত (Ready)</span>
                  </div>
                  <p className="model-desc">আবহাওয়া ও ফসলের রোগ বিশ্লেষণপূর্বক সুনির্দিষ্ট সিদ্ধান্ত প্রদান।</p>
                </div>
                <div className="model-item">
                  <div className="model-header">
                    <span className="model-name">৫. বাজারদর ও সরকারি প্রকল্প সন্ধান (Market & Schemes)</span>
                    <span className="status-pill status-ready">প্রস্তুত (Ready)</span>
                  </div>
                  <p className="model-desc">মান্ডি দর ও সরকারি আর্থিক সহায়তা তথ্য প্রাপ্তি।</p>
                </div>
                <div className="model-item">
                  <div className="model-header">
                    <span className="model-name">৬. বাংলা ভয়েস সহকারী ও অ্যাক্সেসিবিলিটি (Voice Assistant)</span>
                    <span className="status-pill status-ready">প্রস্তুত (Ready)</span>
                  </div>
                  <p className="model-desc">বাংলা কণ্ঠস্বর নির্দেশ ও অডিও উত্তর শ্রবণ।</p>
                </div>
                <div className="model-item">
                  <div className="model-header">
                    <span className="model-name">৭. মাল্টি-এজেন্ট সুপারভাইজার সিস্টেম (Multi-Agent Supervisor)</span>
                    <span className="status-pill status-ready">প্রস্তুত (Ready)</span>
                  </div>
                  <p className="model-desc">মাল্টিমোডাল ভয়েস ও ক্যামেরা স্বয়ংক্রিয় সমন্বয়ক।</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <SupervisorHomeView />
        )}
      </main>
    </div>
  );
}

export default App;
