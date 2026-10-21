import { useState } from 'react';
import { 
  Sparkles, 
  Send, 
  CloudRain, 
  AlertTriangle, 
  CheckCircle2, 
  ExternalLink, 
  RefreshCw, 
  Upload, 
  Layers, 
  Sprout, 
  HelpCircle,
  ShieldCheck,
  Bot
} from 'lucide-react';
import { askCropIntelligence } from '../services/api';
import type { CropIntelligenceResponse } from '../services/api';
import { VoiceAssistant } from './VoiceAssistant';

const EXAMPLE_PROMPTS = [
  'আজ কি ধান জমিতে সেচ দেব?',
  'আলু চাষে কোন সার কখন প্রয়োগ করব?',
  'টমেটোর পাতা কোঁকড়ানো রোগ হচ্ছে, কী করব?',
  'ক্যাপসিকামের ফুল ঝরে পড়ছে, প্রতিকার কী?',
  'মাটিতে অতিরিক্ত জল জমলে কী ক্ষতি হতে পারে?'
];

const CROPS = [
  { id: 'all', label: 'সাধারণ কৃষি প্রশ্ন' },
  { id: 'rice', label: 'ধান (Rice)' },
  { id: 'potato', label: 'আলু (Potato)' },
  { id: 'tomato', label: 'টমেটো (Tomato)' },
  { id: 'bell_pepper', label: 'ক্যাপসিকাম / লঙ্কা' }
];

export function CropIntelligenceView() {
  const [query, setQuery] = useState<string>('আজ কি ধান জমিতে সেচ দেব?');
  const [selectedCrop, setSelectedCrop] = useState<string>('rice');
  const [leafFile, setLeafFile] = useState<File | null>(null);
  const [soilFile, setSoilFile] = useState<File | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<CropIntelligenceResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e?: React.FormEvent, overrideQuery?: string, overrideCrop?: string) => {
    if (e) e.preventDefault();
    const q = overrideQuery || query;
    const c = overrideCrop !== undefined ? overrideCrop : selectedCrop;

    if (!q.trim()) return;

    setLoading(true);
    setErrorMessage(null);

    try {
      const response = await askCropIntelligence(
        q.trim(),
        c === 'all' ? undefined : c,
        23.23,
        87.86,
        leafFile || undefined,
        soilFile || undefined
      );
      setResult(response);
    } catch (err: any) {
      setErrorMessage(err.message || 'পরামর্শ তৈরিতে সমস্যা হয়েছে। অনুগ্রহ করে পুনরায় চেষ্টা করুন।');
    } finally {
      setLoading(false);
    }
  };

  const handlePromptSelect = (promptText: string) => {
    setQuery(promptText);
    let autoCrop = selectedCrop;
    if (promptText.includes('ধান')) autoCrop = 'rice';
    else if (promptText.includes('আলু')) autoCrop = 'potato';
    else if (promptText.includes('টমেটো')) autoCrop = 'tomato';
    else if (promptText.includes('ক্যাপসিকাম')) autoCrop = 'bell_pepper';
    setSelectedCrop(autoCrop);
    handleSubmit(undefined, promptText, autoCrop);
  };

  return (
    <div className="card-box crop-intelligence-container">
      {/* Header */}
      <div className="intelligence-header">
        <div className="intelligence-title-area">
          <div className="intelligence-badge-icon">
            <Sparkles size={26} className="text-brand-green" />
          </div>
          <div>
            <h2 className="card-title">বুদ্ধিমান কৃষি পরামর্শক (Crop Intelligence Assistant)</h2>
            <p className="card-description">
              আবহাওয়া, মাটির অবস্থা ও আইসিএআর (ICAR) যাচাইকৃত জ্ঞানভাণ্ডার সমন্বিত বুদ্ধিমান কৃষি সহায়ক
            </p>
          </div>
        </div>

        <div className="assistant-provider-pill">
          <Bot size={15} />
          <span>সহায়তাকারী: Cohere LLM + যাচাইকৃত তথ্যভাণ্ডার</span>
        </div>
      </div>

      {/* Phase 8: Voice-First Bengali Interaction Bar */}
      <VoiceAssistant
        onQuestionSubmit={(spokenQuestion) => {
          setQuery(spokenQuestion);
          handleSubmit(undefined, spokenQuestion);
        }}
        isSubmitting={loading}
        disabled={loading}
        lastAnswerBn={result?.answer_bn}
      />

      {/* Interactive Question Input Box (Text fallback remains always available) */}
      <div className="intelligence-query-panel">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          className="intelligence-form"
        >
          <div className="form-input-row">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="আপনার প্রশ্ন লিখুন (যেমন: আজ কি জমিতে সেচ দেব? আলুর পাতায় দাগ দেখা যাচ্ছে...)"
              className="intelligence-main-input"
            />
            <button
              type="submit"
              onClick={() => handleSubmit()}
              disabled={loading || !query.trim()}
              className="btn-send-intelligence"
            >
              {loading ? <RefreshCw size={18} className="spin-icon" /> : <Send size={18} />}
              <span>{loading ? 'বিশ্লেষণ হচ্ছে...' : 'জানুন'}</span>
            </button>
          </div>

          {/* Quick Example Chips */}
          <div className="quick-suggestions-row">
            <span className="suggestions-label">উদাহরণ প্রশ্ন:</span>
            {EXAMPLE_PROMPTS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => handlePromptSelect(p)}
                className="suggestion-chip"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Context Options Bar */}
          <div className="context-options-strip">
            <div className="crop-selector-group">
              <span className="context-label">ফসল নির্বাচন:</span>
              <div className="crop-pills-row">
                {CROPS.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setSelectedCrop(c.id)}
                    className={`preset-pill ${selectedCrop === c.id ? 'preset-pill-active' : ''}`}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Optional Image Attachments for Multi-Modal Soil / Disease */}
            <div className="attachment-buttons-row">
              <label className={`btn-attachment ${leafFile ? 'btn-attachment-active' : ''}`} title="আক্রান্ত পাতার ছবি যোগ করুন">
                <Upload size={14} />
                <span>{leafFile ? 'পাতার ছবি সংযুক্ত' : 'পাতার ছবি যোগ'}</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setLeafFile(e.target.files ? e.target.files[0] : null)}
                  style={{ display: 'none' }}
                />
              </label>

              <label className={`btn-attachment ${soilFile ? 'btn-attachment-active' : ''}`} title="মাটির ছবি যোগ করুন">
                <Layers size={14} />
                <span>{soilFile ? 'মাটির ছবি সংযুক্ত' : 'মাটির ছবি যোগ'}</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setSoilFile(e.target.files ? e.target.files[0] : null)}
                  style={{ display: 'none' }}
                />
              </label>

              {(leafFile || soilFile) && (
                <button
                  type="button"
                  onClick={() => {
                    setLeafFile(null);
                    setSoilFile(null);
                  }}
                  className="btn-clear-attachments"
                >
                  মুছুন
                </button>
              )}
            </div>
          </div>
        </form>
      </div>

      {/* Error state */}
      {errorMessage && (
        <div className="status-banner banner-warning">
          <AlertTriangle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="weather-loading-skeleton">
          <RefreshCw size={28} className="spin-icon text-brand-green" />
          <p className="skeleton-text">আবহাওয়া উপাত্ত ও কৃষি জ্ঞানভাণ্ডার বিশ্লেষণ করে পরামর্শ প্রস্তুত করা হচ্ছে...</p>
        </div>
      )}

      {/* Result Card */}
      {!loading && result && (
        <div className="intelligence-result-card">
          {/* Header Metadata */}
          <div className="result-header-row">
            <div className="result-intent-badge">
              <Sprout size={16} />
              <span>
                বিষয়: {result.intent === 'irrigation_weather' ? 'সেচ ও আবহাওয়া' :
                        result.intent === 'fertilizer_soil' ? 'সার ও পুষ্টি ব্যবস্থাপনা' :
                        result.intent === 'plant_health' ? 'গাছের স্বাস্থ্য ও রোগবালাই' : 'কৃষি সহায়তা'}
              </span>
            </div>

            <div className="result-engine-meta">
              <span className={`engine-tag ${result.llm_used ? 'engine-llm' : 'engine-fallback'}`}>
                {result.llm_used ? `জেনারেটেড: ${result.provider} (LLM)` : 'যাচাইকৃত ব্যাকএন্ড ইঞ্জিন'}
              </span>
            </div>
          </div>

          {/* Missing Context Clarification Prompt */}
          {result.missing_context && result.missing_context.length > 0 && (
            <div className="clarification-banner">
              <HelpCircle size={18} className="text-amber-700 flex-shrink-0" />
              <div>
                <strong>আরও সঠিক পরামর্শের জন্য:</strong>
                <p>
                  {result.missing_context.includes('crop_name') && 'আপনার ফসলের সঠিক নামটি উপরে নির্বাচন করুন। '}
                  {result.missing_context.includes('leaf_image_optional') && 'রোগাক্রান্ত পাতার ছবি আপলোড করলে মোবাইলনেট-ভি২ মডেল আরও সঠিকভাবে রোগ অনুমান করতে পারবে।'}
                </p>
              </div>
            </div>
          )}

          {/* Weather Context Note if Used */}
          {result.weather_summary && (
            <div className="weather-context-card">
              <div className="weather-ctx-title">
                <CloudRain size={16} className="text-blue-600" />
                <span>স্থানীয় আবহাওয়া ও বৃষ্টিপাত পর্যবেক্ষণ:</span>
              </div>
              <div className="weather-ctx-details">
                <span>বর্তমান অবস্থা: <strong>{result.weather_summary.weather_desc_bn}</strong> ({result.weather_summary.current_temp_c}°C)</span>
                <span>আগামী ৪৮ ঘণ্টায় বৃষ্টিপাত: <strong>{result.weather_summary.rain_next_48h_mm} মিমি</strong> (সম্ভাবনা: {result.weather_summary.max_rain_probability_48h}%)</span>
              </div>
            </div>
          )}

          {/* Main Formatted Answer */}
          <div className="intelligence-answer-body">
            {result.answer_bn.split('\n').map((paragraph, idx) => (
              <p key={idx} className={paragraph.startsWith('**') ? 'answer-heading-line' : 'answer-body-line'}>
                {paragraph.replace(/\*\*/g, '')}
              </p>
            ))}
          </div>

          {/* Safety Warnings & Statutory Disclaimers */}
          {result.safety_warnings && result.safety_warnings.length > 0 && (
            <div className="intelligence-safety-box">
              {result.safety_warnings.map((w, idx) => (
                <div key={idx} className="safety-warning-item">
                  <AlertTriangle size={16} className="text-amber-800 flex-shrink-0" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          {/* Grounded Citations & Sources */}
          {result.citations && result.citations.length > 0 && (
            <div className="intelligence-citations-strip">
              <div className="citations-label">
                <ShieldCheck size={14} className="text-brand-green" />
                <span>প্রমাণভিত্তিক মূল তথ্যসূত্র (Verified Sources):</span>
              </div>
              <div className="citations-list">
                {result.citations.map((c) => (
                  <a
                    key={c.id}
                    href={c.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="citation-pill"
                    title={c.title_en}
                  >
                    <span>{c.source_org}</span>
                    <ExternalLink size={11} />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Educational Notice Footer */}
      <div className="disclaimer-card">
        <div className="disclaimer-title-row">
          <CheckCircle2 size={18} className="text-brand-green" />
          <strong>ভাষাখেতি নির্দেশিকা নীতি (BhashaKheti Advisory Policy)</strong>
        </div>
        <p className="disclaimer-text-bn">
          এই সহকারী আইসিএআর (ICAR) গবেষণা বুলেটিন, ওপেন-মেটিও লাইভ পূর্বাভাস ও বিদ্যমান ইমেজ ক্লাসিফায়ার সমন্বয় করে উত্তর তৈরি করে। এটি কোনো কাল্পনিক রাসায়নিক ওষুধের মাত্রা সুপারিশ করে না। কোনো রাসায়নিক প্রয়োগের পূর্বে অবশ্যই স্থানীয় সহ-কৃষি নির্দেশক (ADA) বা কৃষি প্রযুক্তি সহায়ক (KPS)-এর পরামর্শ নিন।
        </p>
      </div>
    </div>
  );
}
