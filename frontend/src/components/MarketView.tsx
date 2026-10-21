import { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Search, 
  MapPin, 
  Clock, 
  ExternalLink, 
  RefreshCw, 
  AlertCircle, 
  Info,
  Calendar,
  Layers,
  Sparkles
} from 'lucide-react';
import { 
  fetchMarketCommodities, 
  fetchMarketDistricts, 
  searchMarketPrices, 
  fetchMarketSummary 
} from '../services/api';
import type { 
  MarketPriceRecord, 
  MarketSummaryHighlight 
} from '../services/api';

export function MarketView() {
  const [commodities, setCommodities] = useState<Array<{ id: string; name_bn: string; name_en: string }>>([]);
  const [districts, setDistricts] = useState<Array<{ district_en: string; district_bn: string }>>([]);
  const [selectedCommodity, setSelectedCommodity] = useState<string>('all');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  const [summaryHighlights, setSummaryHighlights] = useState<MarketSummaryHighlight[]>([]);
  const [prices, setPrices] = useState<MarketPriceRecord[]>([]);
  const [disclaimers, setDisclaimers] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load initial dropdowns and summary
  useEffect(() => {
    async function loadMeta() {
      try {
        const [commList, distList, sumData] = await Promise.all([
          fetchMarketCommodities().catch(() => []),
          fetchMarketDistricts().catch(() => []),
          fetchMarketSummary().catch(() => null)
        ]);
        setCommodities(commList);
        setDistricts(distList);
        if (sumData && sumData.summary_highlights) {
          setSummaryHighlights(sumData.summary_highlights);
        }
      } catch (err: any) {
        console.error('Failed to load market meta:', err);
      }
    }
    loadMeta();
    executeSearch('all', 'all', '');
  }, []);

  const executeSearch = async (comm: string, dist: string, q: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await searchMarketPrices(
        comm === 'all' ? undefined : comm,
        dist === 'all' ? undefined : dist,
        q.trim() || undefined
      );
      setPrices(res.prices);
      setDisclaimers(res.disclaimers);
    } catch (err: any) {
      setError(err.message || 'বাজারদরের তথ্য লোড করা যায়নি।');
      setPrices([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(selectedCommodity, selectedDistrict, searchQuery);
  };

  const handleReset = () => {
    setSelectedCommodity('all');
    setSelectedDistrict('all');
    setSearchQuery('');
    executeSearch('all', 'all', '');
  };

  const handleSummaryChipClick = (commodityId: string) => {
    setSelectedCommodity(commodityId);
    executeSearch(commodityId, selectedDistrict, searchQuery);
  };

  return (
    <div className="card-box market-container">
      {/* Header */}
      <div className="market-header">
        <div className="market-title-area">
          <div className="market-badge-icon">
            <TrendingUp size={26} className="text-brand-green" />
          </div>
          <div>
            <h2 className="card-title">পশ্চিমবঙ্গ কৃষি বাজারদর (Market Intelligence)</h2>
            <p className="card-description">
              কৃষিপণ্যের মান্ডিভিত্তিক পাইকারি দর ও বিশ্লেষণ • AGMARKNET প্রাতিষ্ঠানিক তথ্যভাণ্ডার
            </p>
          </div>
        </div>

        <div className="market-portal-pill">
          <ExternalLink size={14} />
          <a 
            href="https://agmarknet.gov.in" 
            target="_blank" 
            rel="noopener noreferrer"
            className="external-portal-link"
          >
            অফিসিয়াল AGMARKNET পোর্টাল
          </a>
        </div>
      </div>

      {/* Staple Crops Summary Highlights Bar */}
      {summaryHighlights.length > 0 && (
        <div className="market-summary-bar">
          <div className="summary-bar-heading">
            <Sparkles size={16} className="text-amber-600" />
            <span>পশ্চিমবঙ্গের প্রধান ফসলের গড় পাইকারি দর:</span>
          </div>
          <div className="summary-chips-grid">
            {summaryHighlights.map((h) => (
              <button
                key={h.commodity_id}
                onClick={() => handleSummaryChipClick(h.commodity_id)}
                className={`summary-chip-card ${selectedCommodity === h.commodity_id ? 'chip-active' : ''}`}
              >
                <div className="chip-crop-name">{h.commodity_name_bn}</div>
                <div className="chip-price">₹{h.average_modal_price} <span className="chip-unit">/ কুইন্টাল</span></div>
                <div className="chip-subprice">প্রায় ₹{h.average_modal_per_kg} / কেজি</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search & Filter Form */}
      <div className="market-filter-panel">
        <form onSubmit={handleSearchSubmit} className="market-filter-form">
          <div className="filter-row">
            {/* Free text search */}
            <div className="search-input-box">
              <Search size={16} className="filter-icon" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="ফসলের নাম, মান্ডি বা জেলা অনুসন্ধান করুন..."
                className="market-search-input"
              />
            </div>

            {/* Commodity select */}
            <div className="select-box">
              <Layers size={16} className="filter-icon" />
              <select
                value={selectedCommodity}
                onChange={(e) => {
                  setSelectedCommodity(e.target.value);
                  executeSearch(e.target.value, selectedDistrict, searchQuery);
                }}
                className="market-select"
                aria-label="ফসল নির্বাচন"
              >
                <option value="all">সকল ফসল / পণ্য</option>
                {commodities.map((c) => (
                  <option key={c.id} value={c.id}>{c.name_bn} ({c.name_en})</option>
                ))}
              </select>
            </div>

            {/* District select */}
            <div className="select-box">
              <MapPin size={16} className="filter-icon" />
              <select
                value={selectedDistrict}
                onChange={(e) => {
                  setSelectedDistrict(e.target.value);
                  executeSearch(selectedCommodity, e.target.value, searchQuery);
                }}
                className="market-select"
                aria-label="জেলা নির্বাচন"
              >
                <option value="all">পশ্চিমবঙ্গের সকল জেলা</option>
                {districts.map((d) => (
                  <option key={d.district_en} value={d.district_en}>{d.district_bn}</option>
                ))}
              </select>
            </div>

            {/* Action buttons */}
            <div className="filter-actions">
              <button type="submit" disabled={loading} className="btn-market-search">
                {loading ? <RefreshCw size={16} className="spin-icon" /> : <Search size={16} />}
                <span>খুঁজুন</span>
              </button>
              <button type="button" onClick={handleReset} className="btn-market-reset">
                রিসেট
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Educational Notice: Mandi vs Farm-gate Difference */}
      <div className="market-education-card">
        <div className="edu-title">
          <Info size={18} className="text-blue-600 flex-shrink-0" />
          <strong>কৃষক সচেতনতা: মন্ডির পাইকারি দর ও খামার বিক্রয়মূল্যের (Farm-gate Price) পার্থক্য</strong>
        </div>
        <p className="edu-text">
          উপরে প্রদর্শিত দরগুলো সরকারি নিবন্ধিত মান্ডিতে পাইকারি ক্রেতাদের গড় ক্রয়মূল্য। 
          মাঠে বা খামারে সরাসরি বিক্রির সময় স্থানীয় পরিবহন খরচ, আর্দ্রতার মাত্রা ও গ্রেডিং এবং ফড়ে বা আড়তদারের কমিশনের কারণে প্রাপ্ত মূল্য মান্ডি দরের চেয়ে কিছুটা কম হতে পারে।
        </p>
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
          <p className="skeleton-text">সরকারি মান্ডির সাম্প্রতিক বাজারদর তথ্য লোড করা হচ্ছে...</p>
        </div>
      )}

      {/* Price Cards Grid */}
      {!loading && prices.length > 0 && (
        <div className="market-cards-grid">
          {prices.map((p) => (
            <div key={p.id} className="price-card">
              <div className="price-card-header">
                <div>
                  <h3 className="price-crop-title">{p.commodity_name_bn}</h3>
                  <div className="price-crop-sub">{p.commodity_name_en} • জাত: {p.variety}</div>
                </div>
                <span className={`status-pill ${p.is_historical ? 'pill-historical' : 'pill-recent'}`}>
                  {p.is_historical ? 'ঐতিহাসিক তথ্য' : 'সাম্প্রতিক দর'}
                </span>
              </div>

              <div className="price-location-strip">
                <MapPin size={15} className="text-gray-500" />
                <span>{p.market_name_bn}, {p.district_bn}</span>
              </div>

              {/* Price Highlights */}
              <div className="price-main-box">
                <div className="modal-price-wrap">
                  <div className="price-label">গড় পাইকারি দর (Modal Price)</div>
                  <div className="modal-amount">
                    ₹{p.modal_price.toLocaleString('en-IN')} <span className="modal-unit">/ কুইন্টাল</span>
                  </div>
                  <div className="per-kg-tag">
                    প্রতি কেজি প্রায়: <strong>₹{p.modal_price_per_kg}</strong>
                  </div>
                </div>

                <div className="price-range-strip">
                  <div className="range-item">
                    <span className="range-label">সর্বনিম্ন:</span>
                    <span className="range-val">₹{p.min_price}</span>
                  </div>
                  <div className="range-bar-visual">
                    <div className="range-fill"></div>
                  </div>
                  <div className="range-item">
                    <span className="range-label">সর্বোচ্চ:</span>
                    <span className="range-val">₹{p.max_price}</span>
                  </div>
                </div>
              </div>

              {/* Footer Metadata & Provenance */}
              <div className="price-card-footer">
                <div className="reported-date-wrap">
                  <Calendar size={13} className="text-gray-500" />
                  <span>তারিখ: {p.reported_date}</span>
                </div>
                <a
                  href={p.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="card-source-link"
                  title="AGMARKNET পোর্টাল দেখুন"
                >
                  <span>AGMARKNET</span>
                  <ExternalLink size={12} />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && prices.length === 0 && !error && (
        <div className="market-empty-state">
          <Clock size={36} className="text-gray-400" />
          <h3>কোনো বাজারদর রেকর্ড পাওয়া যায়নি</h3>
          <p>আপনার নির্বাচিত ফসল বা জেলায় সাম্প্রতিক কোনো মান্ডি রিপোর্ট নেই। অন্য ফসল বা জেলা বেছে নিন।</p>
          <button onClick={handleReset} className="btn-market-reset">সকল রেকর্ড দেখুন</button>
        </div>
      )}

      {/* Transparent Disclaimers */}
      {disclaimers.length > 0 && (
        <div className="market-disclaimer-box">
          <div className="disclaimer-heading">
            <Info size={15} />
            <span>আইনি ও তথ্যগত স্পষ্টীকরণ:</span>
          </div>
          <ul className="disclaimer-list">
            {disclaimers.map((d, idx) => (
              <li key={idx}>{d}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
