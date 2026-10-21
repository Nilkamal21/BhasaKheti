import { useState, useEffect } from 'react';
import { 
  BookOpen, 
  Search, 
  ExternalLink, 
  ShieldCheck, 
  AlertTriangle, 
  Clock, 
  Filter, 
  Info,
  Calendar,
  Building2,
  RefreshCw,
  MessageSquareQuote
} from 'lucide-react';
import { 
  searchKnowledge, 
  askKnowledgeQuestion, 
  getKnowledgeCategories 
} from '../services/api';
import type { 
  KnowledgeSearchResponse, 
  AskQuestionResponse, 
  KnowledgeCategoriesResponse 
} from '../services/api';

const QUICK_QUERIES = [
  'আলুর নাবি ধসা রোগ',
  'ধানের ব্লাস্ট রোগ',
  'টমেটোর পাতা কোঁকড়ানো ভাইরাস',
  'গাঙ্গেয় পলি মাটির উর্বরতা',
  'ক্যাপসিকামের ফল পচা রোগ',
  'বোরো ধানে পর্যায়ক্রমিক সেচ (AWD)'
];

const CROPS = [
  { id: 'all', label: 'সকল ফসল ও মাটি' },
  { id: 'rice', label: 'ধান (Rice)' },
  { id: 'potato', label: 'আলু (Potato)' },
  { id: 'tomato', label: 'টমেটো (Tomato)' },
  { id: 'bell_pepper', label: 'ক্যাপসিকাম / লঙ্কা' },
  { id: 'soil_general', label: 'মাটি ও পুষ্টি' }
];

export function KnowledgeView() {
  const [query, setQuery] = useState<string>('আলুর নাবি ধসা রোগ');
  const [selectedCrop, setSelectedCrop] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [categories, setCategories] = useState<KnowledgeCategoriesResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResponse | null>(null);
  const [directAnswer, setDirectAnswer] = useState<AskQuestionResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeMode, setActiveMode] = useState<'search' | 'ask'>('search');

  // Load category metadata on mount
  useEffect(() => {
    getKnowledgeCategories()
      .then(setCategories)
      .catch((err) => console.error('Failed to load knowledge categories:', err));
  }, []);

  const handleSearch = async (overrideQuery?: string, overrideCrop?: string) => {
    const q = overrideQuery !== undefined ? overrideQuery : query;
    const c = overrideCrop !== undefined ? overrideCrop : selectedCrop;

    if (!q.trim()) return;

    setLoading(true);
    setErrorMessage(null);
    setDirectAnswer(null);

    try {
      if (activeMode === 'ask') {
        const answer = await askKnowledgeQuestion(q.trim(), c === 'all' ? undefined : c);
        setDirectAnswer(answer);
      } else {
        const results = await searchKnowledge(
          q.trim(),
          c === 'all' ? undefined : c,
          selectedCategory === 'all' ? undefined : selectedCategory
        );
        setSearchResults(results);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'জ্ঞানভাণ্ডার থেকে তথ্য সংগ্রহ করা যায়নি।');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleSearch('আলুর নাবি ধসা রোগ', 'all');
  }, [activeMode, selectedCategory]);

  const handleQuickQuery = (text: string) => {
    setQuery(text);
    handleSearch(text, selectedCrop);
  };

  const handleCropSelect = (cropId: string) => {
    setSelectedCrop(cropId);
    handleSearch(query, cropId);
  };

  return (
    <div className="card-box knowledge-container">
      {/* Header */}
      <div className="knowledge-header">
        <div className="knowledge-title-area">
          <div className="knowledge-badge-icon">
            <BookOpen size={26} className="text-brand-green" />
          </div>
          <div>
            <h2 className="card-title">কৃষি জ্ঞানভাণ্ডার ও নির্ভরযোগ্য সুরক্ষা নির্দেশিকা (Agricultural Knowledge)</h2>
            <p className="card-description">
              আইসিএআর (ICAR), বিসিকেভি (BCKV) ও পশ্চিমবঙ্গ কৃষি দপ্তরের যাচাইকৃত প্রমাণভিত্তিক কৃষি পরামর্শ
            </p>
          </div>
        </div>

        {/* Mode Selector */}
        <div className="knowledge-mode-toggle">
          <button
            onClick={() => setActiveMode('search')}
            className={`mode-btn ${activeMode === 'search' ? 'mode-btn-active' : ''}`}
          >
            <Search size={15} />
            <span>নির্দেশিকা খুঁজুন</span>
          </button>
          <button
            onClick={() => setActiveMode('ask')}
            className={`mode-btn ${activeMode === 'ask' ? 'mode-btn-active' : ''}`}
          >
            <MessageSquareQuote size={15} />
            <span>সরাসরি উত্তর</span>
          </button>
        </div>
      </div>

      {/* Search Input Bar */}
      <div className="knowledge-search-panel">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="search-form-row"
        >
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="ফসলের রোগ, বালাই দমন বা মাটির যত্ন সম্পর্কে লিখুন..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="weather-search-input"
            />
          </div>
          <button type="submit" disabled={loading || !query.trim()} className="btn-search">
            {loading ? 'অনুসন্ধান হচ্ছে...' : 'অনুসন্ধান'}
          </button>
        </form>

        {/* Quick Suggestion Chips */}
        <div className="quick-suggestions-row">
          <span className="suggestions-label">জনপ্রিয় অনুসন্ধান:</span>
          {QUICK_QUERIES.map((text) => (
            <button
              key={text}
              type="button"
              onClick={() => handleQuickQuery(text)}
              className="suggestion-chip"
            >
              {text}
            </button>
          ))}
        </div>

        {/* Crop and Category Filters */}
        <div className="filter-controls-row">
          <div className="crop-filters-strip">
            {CROPS.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => handleCropSelect(c.id)}
                className={`preset-pill ${selectedCrop === c.id ? 'preset-pill-active' : ''}`}
              >
                {c.label}
              </button>
            ))}
          </div>

          {activeMode === 'search' && categories && categories.categories.length > 0 && (
            <div className="category-select-wrap">
              <Filter size={14} className="text-gray-500" />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="category-dropdown"
              >
                <option value="all">সকল বিষয় (All Categories)</option>
                {categories.categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.label_bn}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Boundary Warnings (e.g. Rice Model Caveat) */}
      {(searchResults?.boundary_warnings?.length || directAnswer?.safety_warnings?.length) ? (
        <div className="boundary-warnings-box">
          {(searchResults?.boundary_warnings || directAnswer?.safety_warnings || []).map((w, idx) => (
            <div key={idx} className="status-banner banner-warning">
              <AlertTriangle size={20} className="flex-shrink-0" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      ) : null}

      {/* Error Banner */}
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
          <p className="skeleton-text">যাচাইকৃত কৃষি তথ্যভাণ্ডার অনুসন্ধান করা হচ্ছে...</p>
        </div>
      )}

      {/* Direct Answer View (Ask Mode) */}
      {!loading && directAnswer && (
        <div className="direct-answer-card">
          <div className="answer-header-row">
            <div className="answer-title-group">
              {directAnswer.has_sufficient_evidence ? (
                <ShieldCheck size={24} className="text-brand-green" />
              ) : (
                <AlertTriangle size={24} className="text-amber-600" />
              )}
              <div>
                <h3 className="answer-heading">
                  {directAnswer.has_sufficient_evidence ? 'যাচাইকৃত কৃষি পরামর্শ' : 'অপ্রতুল প্রমাণ সংক্রান্ত তথ্য'}
                </h3>
                <span className="source-meta-tag">
                  উৎস: {directAnswer.source_org || 'সরকারি কৃষি সংস্থা'} | যাচাইকৃত: {directAnswer.last_verified_date || '২০২৬'}
                </span>
              </div>
            </div>
            {directAnswer.source_url && (
              <a
                href={directAnswer.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-source-link"
              >
                <span>মূল তথ্যসূত্র</span>
                <ExternalLink size={13} />
              </a>
            )}
          </div>

          <div className="answer-content-body">
            {directAnswer.answer_bn.split('\n').map((line, idx) => (
              <p key={idx} className={line.startsWith('**') ? 'answer-strong-line' : 'answer-regular-line'}>
                {line.replace(/\*\*/g, '')}
              </p>
            ))}
          </div>

          {/* Statutory Chemical Advisory */}
          {directAnswer.statutory_disclaimer_bn && (
            <div className="statutory-disclaimer-box">
              <AlertTriangle size={18} className="text-amber-800 flex-shrink-0" />
              <p>{directAnswer.statutory_disclaimer_bn}</p>
            </div>
          )}

          {/* Consult Expert Notice if Insufficient Evidence */}
          {!directAnswer.has_sufficient_evidence && directAnswer.consult_expert_notice_bn && (
            <div className="insufficient-evidence-box">
              <Info size={18} className="text-blue-700 flex-shrink-0" />
              <p>{directAnswer.consult_expert_notice_bn}</p>
            </div>
          )}
        </div>
      )}

      {/* Search Results View */}
      {!loading && searchResults && (
        <div className="knowledge-results-area">
          {/* Insufficient Evidence Notice */}
          {!searchResults.has_sufficient_evidence && searchResults.insufficient_evidence_notice_bn && (
            <div className="insufficient-evidence-card">
              <div className="insufficient-title-row">
                <AlertTriangle size={22} className="text-amber-600" />
                <strong>কোনো যাচাইকৃত প্রমাণ পাওয়া যায়নি</strong>
              </div>
              <p className="insufficient-text-bn">{searchResults.insufficient_evidence_notice_bn}</p>
              <div className="insufficient-recommendation">
                <p>
                  <strong>কৃষকের জন্য করণীয়:</strong> ফসল বা মাটির অজানা লক্ষণের ক্ষেত্রে অনুমাননির্ভর ওষুধ প্রয়োগ না করে স্থানীয় সহ-কৃষি নির্দেশক (ADA), ব্লক কৃষি প্রযুক্তি সহায়ক (KPS) অথবা নিকটস্থ কৃষি বিজ্ঞান কেন্দ্র (KVK)-এর বিশেষজ্ঞদের পরামর্শ নিন।
                </p>
              </div>
            </div>
          )}

          {/* Results List */}
          {searchResults.has_sufficient_evidence && (
            <div className="records-list">
              <div className="records-count-meta">
                মোট {searchResults.results.length} টি যাচাইকৃত নির্দেশিকা পাওয়া গেছে
              </div>

              {searchResults.results.map((record) => (
                <div key={record.id} className="knowledge-record-card">
                  <div className="record-top-row">
                    <div className="record-title-group">
                      <span className="record-badge verified-tag">
                        <ShieldCheck size={12} />
                        <span>যাচাইকৃত (Verified)</span>
                      </span>
                      <span className="record-crop-tag">{record.crop.toUpperCase()}</span>
                      <h3 className="record-title-bn">{record.title_bn}</h3>
                      <h4 className="record-title-en">{record.title_en}</h4>
                    </div>

                    <a
                      href={record.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-source-link"
                      title="অফিসিয়াল ওয়েবসাইটে মূল নির্দেশিকা দেখুন"
                    >
                      <Building2 size={13} />
                      <span>{record.source_org}</span>
                      <ExternalLink size={12} />
                    </a>
                  </div>

                  {/* Growth Stage and Geographic Scope */}
                  <div className="record-meta-strip">
                    {record.growth_stage && (
                      <span className="meta-item">
                        <Clock size={13} className="text-gray-500" />
                        <span>পর্যায়: {record.growth_stage}</span>
                      </span>
                    )}
                    <span className="meta-item">
                      <Info size={13} className="text-gray-500" />
                      <span>এলাকা: {record.geographic_scope}</span>
                    </span>
                    <span className="meta-item">
                      <Calendar size={13} className="text-gray-500" />
                      <span>যাচাইকৃত: {record.last_verified_date}</span>
                    </span>
                  </div>

                  {/* Content */}
                  <div className="record-content-box">
                    {record.content_bn.split('\n').map((line, idx) => (
                      <p key={idx} className="record-content-line">
                        {line}
                      </p>
                    ))}
                  </div>

                  {/* Safety Notes */}
                  {record.safety_notes_bn && (
                    <div className="record-safety-card">
                      <AlertTriangle size={15} className="text-amber-800 flex-shrink-0" />
                      <div className="safety-text-group">
                        <span className="safety-label">সুরক্ষা ও প্রয়োগ সতর্কতা:</span>
                        <p className="safety-content">{record.safety_notes_bn}</p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Regulatory & Institutional Provenance Card */}
      <div className="disclaimer-card knowledge-source-disclaimer">
        <div className="disclaimer-title-row">
          <ShieldCheck size={18} className="text-green-800" />
          <strong>তথ্যভাণ্ডারের উৎস ও প্রাতিষ্ঠানিক স্বচ্ছতা (Institutional Provenance)</strong>
        </div>
        <p className="disclaimer-text-bn">
          ভাষাখেতি-র কৃষি তথ্যভাণ্ডারের প্রতিটি নির্দেশিকা <strong>ICAR-NRRI</strong> (জাতীয় ধান গবেষণা সংস্থা), <strong>ICAR-CPRI</strong> (আলু গবেষণা সংস্থা), <strong>ICAR-IIVR</strong> (সবজি গবেষণা সংস্থা), <strong>BCKV</strong> (বিধানচন্দ্র কৃষি বিশ্ববিদ্যালয়) এবং <strong>পশ্চিমবঙ্গ রাজ্য কৃষি দপ্তরের</strong> সরকারি কৃষিতাত্ত্বিক বুলেটিন থেকে সরাসরি সংকলিত। কৃষকের স্বাস্থ্য ও পরিবেশগত সুরক্ষার্থে কোনো কাল্পনিক বা অনুমাননির্ভর রাসায়নিক প্রেসক্রিপশন প্রদান করা হয় না।
        </p>
        <p className="disclaimer-text-en">
          All knowledge records are verified against official publications from ICAR institutes, BCKV Mohanpur, and the Department of Agriculture, Govt of West Bengal. Prescriptions and dosages must be validated with block-level agricultural officers before field application.
        </p>
      </div>
    </div>
  );
}
