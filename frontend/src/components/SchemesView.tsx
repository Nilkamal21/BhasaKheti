import { useState, useEffect } from 'react';
import { 
  FileText, 
  Search, 
  ExternalLink, 
  CheckCircle2, 
  ShieldAlert, 
  RefreshCw, 
  AlertCircle, 
  Check, 
  Building2, 
  Calendar, 
  Sparkles,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  Lock
} from 'lucide-react';
import { 
  fetchSchemeCategories, 
  searchSchemes, 
  checkSchemeEligibility 
} from '../services/api';
import type { 
  SchemeRecord, 
  EligibilityResponse 
} from '../services/api';

export function SchemesView() {
  const [categories, setCategories] = useState<Array<{ id: string; label_bn: string }>>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedSponsor, setSelectedSponsor] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [schemes, setSchemes] = useState<SchemeRecord[]>([]);
  const [notice, setNotice] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Preliminary Eligibility Checker State
  const [showEligibilityChecker, setShowEligibilityChecker] = useState<boolean>(false);
  const [landAcres, setLandAcres] = useState<string>('1.5');
  const [isSharecropper, setIsSharecropper] = useState<boolean>(false);
  const [isOwner, setIsOwner] = useState<boolean>(true);
  const [eligibilityResult, setEligibilityResult] = useState<EligibilityResponse | null>(null);
  const [checkingEligibility, setCheckingEligibility] = useState<boolean>(false);

  useEffect(() => {
    async function loadCategories() {
      try {
        const catList = await fetchSchemeCategories();
        setCategories(catList);
      } catch (err: any) {
        console.error('Failed to load scheme categories:', err);
      }
    }
    loadCategories();
    executeSearch('', 'all', 'all');
  }, []);

  const executeSearch = async (q: string, cat: string, spon: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await searchSchemes(
        q.trim() || undefined,
        cat === 'all' ? undefined : cat,
        spon === 'all' ? undefined : spon
      );
      setSchemes(res.schemes);
      setNotice(res.notice_bn);
    } catch (err: any) {
      setError(err.message || 'সরকারি প্রকল্পের তথ্য লোড করা যায়নি।');
      setSchemes([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(searchQuery, selectedCategory, selectedSponsor);
  };

  const handleCategorySelect = (catId: string) => {
    setSelectedCategory(catId);
    executeSearch(searchQuery, catId, selectedSponsor);
  };

  const handleSponsorSelect = (sponId: string) => {
    setSelectedSponsor(sponId);
    executeSearch(searchQuery, selectedCategory, sponId);
  };

  const handleReset = () => {
    setSelectedCategory('all');
    setSelectedSponsor('all');
    setSearchQuery('');
    executeSearch('', 'all', 'all');
  };

  const handleRunEligibility = async (e: React.FormEvent) => {
    e.preventDefault();
    setCheckingEligibility(true);
    try {
      const acres = landAcres ? parseFloat(landAcres) : undefined;
      const res = await checkSchemeEligibility(acres, isSharecropper, isOwner);
      setEligibilityResult(res);
    } catch (err: any) {
      console.error('Eligibility check error:', err);
    } finally {
      setCheckingEligibility(false);
    }
  };

  return (
    <div className="card-box schemes-container">
      {/* Header */}
      <div className="schemes-header">
        <div className="schemes-title-area">
          <div className="schemes-badge-icon">
            <FileText size={26} className="text-brand-green" />
          </div>
          <div>
            <h2 className="card-title">সরকারি কৃষি প্রকল্প ও সহায়তা (Government Schemes)</h2>
            <p className="card-description">
              পশ্চিমবঙ্গ ও কেন্দ্রীয় সরকারের অনুমোদিত কৃষক কল্যাণ প্রকল্প, আর্থিক অনুদান ও ভর্তুকি নির্দেশিকা
            </p>
          </div>
        </div>

        {/* Eligibility Checker Toggle Button */}
        <button
          onClick={() => setShowEligibilityChecker(!showEligibilityChecker)}
          className="btn-toggle-eligibility"
          aria-expanded={showEligibilityChecker}
        >
          <Sparkles size={16} />
          <span>প্রকল্পের প্রাথমিক যোগ্যতা যাচাই</span>
          {showEligibilityChecker ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {/* Interactive Collapsible Preliminary Eligibility Checker */}
      {showEligibilityChecker && (
        <div className="eligibility-checker-panel">
          <div className="checker-header-row">
            <div className="checker-title">
              <HelpCircle size={18} className="text-blue-600" />
              <strong>সহজ প্রশ্নোত্তরে প্রযোজ্য সরকারি প্রকল্প খুঁজুন</strong>
            </div>
            <div className="privacy-badge">
              <Lock size={13} className="text-emerald-700" />
              <span>গোপনীয়তা সুরক্ষিত (আধার বা ব্যাংক নম্বর প্রয়োজন নেই)</span>
            </div>
          </div>

          <form onSubmit={handleRunEligibility} className="checker-form-grid">
            <div className="checker-field">
              <label htmlFor="land-size-input">আপনার চাষযোগ্য জমির পরিমাণ (একর):</label>
              <input
                id="land-size-input"
                type="number"
                step="0.1"
                min="0"
                max="500"
                value={landAcres}
                onChange={(e) => setLandAcres(e.target.value)}
                placeholder="যেমন: ১.৫"
                className="checker-input"
              />
            </div>

            <div className="checker-checkbox-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={isSharecropper}
                  onChange={(e) => setIsSharecropper(e.target.checked)}
                />
                <span>আমি সরকারি নথিভুক্ত ভাগচাষী (Recorded Bargadar)</span>
              </label>

              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={isOwner}
                  onChange={(e) => setIsOwner(e.target.checked)}
                />
                <span>আমার বা পরিবারের নিজস্ব চাষের জমি আছে</span>
              </label>
            </div>

            <div className="checker-actions">
              <button type="submit" disabled={checkingEligibility} className="btn-run-check">
                {checkingEligibility ? <RefreshCw size={15} className="spin-icon" /> : <Check size={15} />}
                <span>যোগ্য প্রকল্প দেখুন</span>
              </button>
            </div>
          </form>

          {/* Eligibility Result Banner */}
          {eligibilityResult && (
            <div className="eligibility-results-card">
              <div className="eligibility-results-header">
                <CheckCircle2 size={18} className="text-brand-green" />
                <strong>আপনার তথ্যানুসারে {eligibilityResult.total_matched}টি প্রকল্পে আবেদনের প্রাথমিক সম্ভাবনা রয়েছে:</strong>
              </div>
              <div className="matched-schemes-list">
                {eligibilityResult.matched_schemes.map((m) => (
                  <div key={m.scheme_id} className="matched-scheme-item">
                    <div className="matched-name">{m.name_bn}</div>
                    <div className="matched-authority">{m.authority_bn}</div>
                    <div className="matched-reasons">
                      {m.eligibility_reasons.map((r, idx) => (
                        <span key={idx} className="reason-tag">✓ {r}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              <div className="checker-disclaimer-note">
                {eligibilityResult.statutory_notice}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Filter Chips Bar */}
      <div className="schemes-filter-panel">
        {/* Search Input Bar */}
        <form onSubmit={handleSearchSubmit} className="schemes-search-bar">
          <div className="search-input-wrap">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="প্রকল্পের নাম, সুবিধা বা বিষয় লিখে খুঁজুন (যেমন: কৃষক বন্ধু, বিমা, বীজ, লোন)..."
              className="schemes-main-input"
            />
          </div>
          <button type="submit" disabled={loading} className="btn-schemes-search">
            {loading ? <RefreshCw size={16} className="spin-icon" /> : <Search size={16} />}
            <span>অনুসন্ধান</span>
          </button>
          <button type="button" onClick={handleReset} className="btn-schemes-reset">
            রিসেট
          </button>
        </form>

        {/* Sponsor Filters */}
        <div className="sponsor-filter-row">
          <span className="filter-row-label">উদ্যোগ / সরকার:</span>
          <button
            type="button"
            onClick={() => handleSponsorSelect('all')}
            className={`filter-pill ${selectedSponsor === 'all' ? 'pill-active' : ''}`}
          >
            সকল উদ্যোগ
          </button>
          <button
            type="button"
            onClick={() => handleSponsorSelect('state')}
            className={`filter-pill ${selectedSponsor === 'state' ? 'pill-active' : ''}`}
          >
            পশ্চিমবঙ্গ সরকার
          </button>
          <button
            type="button"
            onClick={() => handleSponsorSelect('central')}
            className={`filter-pill ${selectedSponsor === 'central' ? 'pill-active' : ''}`}
          >
            ভারত সরকার
          </button>
        </div>

        {/* Categories Chips */}
        {categories.length > 0 && (
          <div className="category-chips-row">
            <span className="filter-row-label">শ্রেণি:</span>
            <button
              type="button"
              onClick={() => handleCategorySelect('all')}
              className={`category-chip ${selectedCategory === 'all' ? 'chip-active' : ''}`}
            >
              সকল বিভাগ
            </button>
            {categories.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => handleCategorySelect(c.id)}
                className={`category-chip ${selectedCategory === c.id ? 'chip-active' : ''}`}
              >
                {c.label_bn}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="status-banner banner-warning">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="market-loading-skeleton">
          <RefreshCw size={28} className="spin-icon text-brand-green" />
          <p className="skeleton-text">সরকারি প্রকল্পের অনুমোদিত তথ্য যাচাই ও লোড করা হচ্ছে...</p>
        </div>
      )}

      {/* Schemes Grid */}
      {!loading && schemes.length > 0 && (
        <div className="schemes-grid">
          {schemes.map((s) => (
            <div key={s.id} className="scheme-card">
              {/* Card Header */}
              <div className="scheme-card-header">
                <div>
                  <div className="scheme-authority">
                    <Building2 size={13} className="text-gray-500" />
                    <span>{s.authority_bn}</span>
                  </div>
                  <h3 className="scheme-title">{s.name_bn}</h3>
                  <div className="scheme-title-en">{s.name_en}</div>
                </div>

                <div className="scheme-status-badge">
                  <span className={`status-pill ${s.status === 'current' ? 'pill-current' : 'pill-periodic'}`}>
                    {s.status_bn}
                  </span>
                </div>
              </div>

              {/* Benefit Highlight Banner */}
              <div className="scheme-benefit-banner">
                <div className="benefit-label">প্রকল্পের মূল আর্থিক সুবিধা:</div>
                <div className="benefit-desc">{s.summary_bn}</div>
              </div>

              {/* Detailed Breakdown */}
              <div className="scheme-body-details">
                {/* Benefits text */}
                <div className="detail-section">
                  <div className="detail-heading">আর্থিক সহায়তা ও অনুদানের বিবরণ:</div>
                  <p className="detail-content">{s.benefits_bn}</p>
                </div>

                {/* Eligibility */}
                <div className="detail-section">
                  <div className="detail-heading">কারা আবেদনের যোগ্য (Eligibility):</div>
                  <p className="detail-content">{s.eligibility_bn}</p>
                </div>

                {/* Required Documents */}
                <div className="detail-section">
                  <div className="detail-heading">প্রয়োজনীয় নথিপত্র (Required Documents):</div>
                  <div className="docs-chips-list">
                    {s.required_documents_bn.map((doc, idx) => (
                      <span key={idx} className="doc-pill">📄 {doc}</span>
                    ))}
                  </div>
                </div>

                {/* Deadline & Application Mode */}
                <div className="scheme-meta-strip">
                  <div className="meta-item">
                    <Calendar size={14} className="text-gray-500" />
                    <span>সময়সীমা: <strong>{s.deadline_bn}</strong></span>
                  </div>
                  <div className="meta-item">
                    <span>আবেদন প্রক্রিয়া: <strong>{s.application_process_bn}</strong></span>
                  </div>
                </div>
              </div>

              {/* Card Footer & Action */}
              <div className="scheme-card-footer">
                <div className="safety-note-small">
                  <ShieldAlert size={14} className="text-amber-700 flex-shrink-0" />
                  <span>{s.safety_disclaimer_bn}</span>
                </div>

                <a
                  href={s.official_portal_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-official-portal"
                  title="অফিসিয়াল সরকারি পোর্টাল খুলুন"
                >
                  <span>অফিসিয়াল পোর্টালে যান</span>
                  <ExternalLink size={14} />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && schemes.length === 0 && !error && (
        <div className="schemes-empty-state">
          <FileText size={40} className="text-gray-400" />
          <h3>কোনো সরকারি প্রকল্প পাওয়া যায়নি</h3>
          <p>আপনার অনুসন্ধানের সাথে সঙ্গতিপূর্ণ কোনো রেকর্ড পাওয়া যায়নি। অন্য শব্দ বা বিভাগ নির্বাচন করুন।</p>
          <button onClick={handleReset} className="btn-schemes-reset">সকল প্রকল্প দেখুন</button>
        </div>
      )}

      {/* Institutional Notice & Transparency */}
      {notice && (
        <div className="schemes-institutional-notice">
          <ShieldAlert size={18} className="text-amber-800 flex-shrink-0" />
          <p>{notice}</p>
        </div>
      )}
    </div>
  );
}
