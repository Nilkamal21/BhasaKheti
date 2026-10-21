export interface ModelStatus {
  artifact_exists: boolean;
  status: string;
  note: string;
}

export interface HealthResponse {
  status: string;
  environment: string;
  phase: string;
  database_connected: boolean;
  models: Record<string, ModelStatus>;
}

export interface PredictionCandidate {
  rank: number;
  class_index: number;
  raw_class_name: string;
  crop?: string;
  disease?: string;
  is_healthy?: boolean;
  display_name_en: string;
  display_name_bn: string;
  model_score: number;
  is_verified: boolean;
}

export interface DiseasePredictionResponse {
  success: boolean;
  model_identifier: string;
  verification_status: string;
  verification_source: string;
  primary_prediction: PredictionCandidate;
  top_candidates: PredictionCandidate[];
  disclaimer_bn: string;
  disclaimer_en: string;
}

export interface SoilPredictionResponse {
  success: boolean;
  model_identifier: string;
  verification_status: string;
  verification_source: string;
  primary_prediction: PredictionCandidate;
  all_classes: PredictionCandidate[];
  disclaimer_bn: string;
  disclaimer_en: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function checkBackendHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`);
  if (!response.ok) {
    throw new Error(`সার্ভার থেকে সঠিক সাড়া পাওয়া যায়নি (HTTP ${response.status})`);
  }
  return response.json();
}

export async function predictPlantDisease(file: File): Promise<DiseasePredictionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/v1/disease/predict`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = 'রোগ নির্ণয় অনুরোধে ত্রুটি ঘটেছে।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export async function predictSoilType(file: File): Promise<SoilPredictionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/v1/soil/type/predict`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = 'মাটির ধরন নির্ণয় অনুরোধে ত্রুটি ঘটেছে।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export async function predictSoilMoisture(file: File): Promise<SoilPredictionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/v1/soil/moisture/predict`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = 'মাটির আর্দ্রতা নির্ণয় অনুরোধে ত্রুটি ঘটেছে।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export interface CurrentConditions {
  observation_time: string;
  temperature_c: number | null;
  apparent_temperature_c: number | null;
  relative_humidity_pct: number | null;
  precipitation_mm: number | null;
  wind_speed_kmh: number | null;
  wind_direction_deg: number | null;
  wind_direction_bn: string;
  weather_code: number;
  weather_desc_en: string;
  weather_desc_bn: string;
  weather_type: string;
}

export interface DailyForecastItem {
  date: string;
  weather_code: number;
  weather_desc_en: string;
  weather_desc_bn: string;
  weather_type: string;
  temperature_max_c: number | null;
  temperature_min_c: number | null;
  precipitation_sum_mm: number | null;
  precipitation_probability_pct: number | null;
  wind_speed_max_kmh: number | null;
}

export interface AgriculturalAdvisory {
  is_fieldwork_advisable: boolean;
  advisory_notes_bn: string[];
  caution_notice_bn: string;
}

export interface WeatherForecastResponse {
  provider: string;
  provider_terms: string;
  location_name: string;
  latitude: number;
  longitude: number;
  timezone: string;
  retrieved_at_unix: number;
  is_cached: boolean;
  is_stale: boolean;
  cached_age_seconds: number;
  stale_warning_bn?: string | null;
  current_conditions: CurrentConditions;
  daily_forecast: DailyForecastItem[];
  agricultural_advisory: AgriculturalAdvisory;
}

export interface LocationSearchResult {
  id: number;
  name: string;
  admin1?: string | null;
  country?: string | null;
  display_label: string;
  latitude: number;
  longitude: number;
}

export async function fetchWeatherForecast(
  latitude: number,
  longitude: number,
  locationName?: string
): Promise<WeatherForecastResponse> {
  const params = new URLSearchParams({
    latitude: latitude.toString(),
    longitude: longitude.toString(),
  });
  if (locationName) {
    params.append('location_name', locationName);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/weather/forecast?${params.toString()}`);
  if (!response.ok) {
    let errorDetail = 'আবহাওয়া পূর্বাভাস সংগ্রহে ত্রুটি ঘটেছে।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function searchWeatherLocations(query: string): Promise<LocationSearchResult[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/weather/search?query=${encodeURIComponent(query)}`);
  if (!response.ok) {
    let errorDetail = 'স্থান অনুসন্ধানে সমস্যা হয়েছে।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export interface KnowledgeRecord {
  id: string;
  title_bn: string;
  title_en: string;
  crop: string;
  category: string;
  topic: string;
  growth_stage?: string | null;
  content_bn: string;
  content_en: string;
  source_org: string;
  source_url: string;
  publication_date: string;
  last_verified_date: string;
  geographic_scope: string;
  evidence_status: string;
  safety_notes_bn: string;
  safety_notes_en: string;
  keywords: string[];
  chemical_control_permitted: boolean;
  search_relevance_score?: number;
}

export interface KnowledgeSearchResponse {
  has_sufficient_evidence: boolean;
  query: string;
  crop_filter?: string | null;
  category_filter?: string | null;
  total_matches: number;
  results: KnowledgeRecord[];
  boundary_warnings: string[];
  insufficient_evidence_notice_bn?: string | null;
}

export interface KnowledgeCategoriesResponse {
  total_records: number;
  crops: Array<{ id: string; label_bn: string }>;
  categories: Array<{ id: string; label_bn: string }>;
}

export interface AskQuestionResponse {
  has_sufficient_evidence: boolean;
  query: string;
  crop?: string;
  primary_topic?: string;
  growth_stage?: string;
  answer_bn: string;
  source_org?: string;
  source_url?: string;
  publication_date?: string;
  last_verified_date?: string;
  evidence_status?: string;
  primary_record?: KnowledgeRecord;
  related_records?: KnowledgeRecord[];
  safety_warnings: string[];
  statutory_disclaimer_bn?: string;
  consult_expert_notice_bn?: string;
}

export async function searchKnowledge(
  query: string,
  crop?: string,
  category?: string
): Promise<KnowledgeSearchResponse> {
  const params = new URLSearchParams({ query });
  if (crop && crop !== 'all') params.append('crop', crop);
  if (category && category !== 'all') params.append('category', category);

  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/search?${params.toString()}`);
  if (!response.ok) {
    let errorDetail = 'জ্ঞানভাণ্ডার অনুসন্ধানে ত্রুটি ঘটেছে।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) errorDetail = errorJson.detail;
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function getKnowledgeCategories(): Promise<KnowledgeCategoriesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/categories`);
  if (!response.ok) {
    throw new Error('কৃষি জ্ঞানভাণ্ডারের তালিকা সংগ্রহ করা যায়নি।');
  }
  return response.json();
}

export async function askKnowledgeQuestion(
  query: string,
  crop?: string,
  growthStage?: string
): Promise<AskQuestionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, crop, growth_stage: growthStage })
  });

  if (!response.ok) {
    let errorDetail = 'প্রশ্ন প্রক্রিয়াকরণে সমস্যা হয়েছে।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) errorDetail = errorJson.detail;
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function getKnowledgeRecord(recordId: string): Promise<KnowledgeRecord> {
  const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/records/${encodeURIComponent(recordId)}`);
  if (!response.ok) {
    throw new Error('নির্দেশিকা রেকর্ড পাওয়া যায়নি।');
  }
  return response.json();
}

export interface IntelligenceCitation {
  id: string;
  title_bn: string;
  title_en: string;
  source_org: string;
  source_url: string;
  last_verified_date: string;
}

export interface CropIntelligenceResponse {
  answer_bn: string;
  intent: string;
  crop?: string | null;
  missing_context: string[];
  citations: IntelligenceCitation[];
  weather_summary?: {
    available: boolean;
    current_temp_c?: number;
    current_humidity?: number;
    current_rain_mm?: number;
    weather_desc_bn?: string;
    rain_next_48h_mm?: number;
    max_rain_probability_48h?: number;
    advisory_notes_bn?: string[];
  } | null;
  safety_warnings: string[];
  llm_used: boolean;
  provider: string;
}

export async function askCropIntelligence(
  query: string,
  crop?: string,
  latitude: number = 23.23,
  longitude: number = 87.86,
  leafImage?: File,
  soilImage?: File
): Promise<CropIntelligenceResponse> {
  const formData = new FormData();
  formData.append('query', query);
  if (crop && crop !== 'all') formData.append('crop', crop);
  formData.append('latitude', latitude.toString());
  formData.append('longitude', longitude.toString());
  if (leafImage) formData.append('leaf_image', leafImage);
  if (soilImage) formData.append('soil_image', soilImage);

  const response = await fetch(`${API_BASE_URL}/api/v1/intelligence/ask`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    let errorDetail = 'বুদ্ধিমান কৃষি পরামর্শ প্রদানে ত্রুটি ঘটেছে।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) errorDetail = errorJson.detail;
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

// -------------------------------------------------------------
// Phase 7: Market Intelligence & Government Scheme Discovery Types
// -------------------------------------------------------------

export interface MarketPriceRecord {
  id: string;
  commodity_id: string;
  commodity_name_bn: string;
  commodity_name_en: string;
  variety: string;
  market_id: string;
  market_name_bn: string;
  market_name_en: string;
  district_bn: string;
  district_en: string;
  state: string;
  min_price: number;
  max_price: number;
  modal_price: number;
  modal_price_per_kg: number;
  min_price_per_kg: number;
  max_price_per_kg: number;
  unit: string;
  currency: string;
  reported_date: string;
  data_status: 'verified_recent' | 'historical';
  is_historical: boolean;
  source_name: string;
  source_url: string;
}

export interface MarketSearchResponse {
  total_matches: number;
  results_count: number;
  prices: MarketPriceRecord[];
  disclaimers: string[];
  data_source: string;
  source_url: string;
}

export interface MarketSummaryHighlight {
  commodity_id: string;
  commodity_name_bn: string;
  commodity_name_en: string;
  average_modal_price: number;
  average_modal_per_kg: number;
  unit: string;
  latest_date: string;
  mandis_reporting: number;
}

export interface MarketSummaryResponse {
  report_date: string;
  summary_highlights: MarketSummaryHighlight[];
  disclaimer_bn: string;
  source_name: string;
}

export interface SchemeRecord {
  id: string;
  name_bn: string;
  name_en: string;
  authority_bn: string;
  authority_en: string;
  sponsor: 'state' | 'central' | 'joint';
  category: string;
  category_bn: string;
  summary_bn: string;
  summary_en: string;
  benefits_bn: string;
  benefits_en: string;
  eligibility_bn: string;
  eligibility_en: string;
  land_size_criteria: string;
  beneficiary_types: string[];
  required_documents_bn: string[];
  required_documents_en: string[];
  application_mode: string;
  application_process_bn: string;
  official_portal_url: string;
  status: 'current' | 'periodic' | 'unverified';
  status_bn: string;
  deadline_bn: string;
  verification_date: string;
  source_name: string;
  safety_disclaimer_bn: string;
}

export interface SchemesResponse {
  total_matches: number;
  results_count: number;
  schemes: SchemeRecord[];
  notice_bn: string;
}

export interface MatchedScheme {
  scheme_id: string;
  name_bn: string;
  authority_bn: string;
  benefits_summary: string;
  status: string;
  official_portal_url: string;
  eligibility_reasons: string[];
}

export interface EligibilityResponse {
  total_matched: number;
  matched_schemes: MatchedScheme[];
  privacy_statement: string;
  statutory_notice: string;
}

// -------------------------------------------------------------
// Phase 7: Market API Client Functions
// -------------------------------------------------------------

export async function fetchMarketCommodities(): Promise<Array<{ id: string; name_bn: string; name_en: string }>> {
  const response = await fetch(`${API_BASE_URL}/api/v1/market/commodities`);
  if (!response.ok) throw new Error('ফসলের তালিকা লোড করা যায়নি।');
  return response.json();
}

export async function fetchMarketDistricts(): Promise<Array<{ district_en: string; district_bn: string }>> {
  const response = await fetch(`${API_BASE_URL}/api/v1/market/districts`);
  if (!response.ok) throw new Error('জেলার তালিকা লোড করা যায়নি।');
  return response.json();
}

export async function searchMarketPrices(
  commodity?: string,
  district?: string,
  query?: string,
  limit: number = 20
): Promise<MarketSearchResponse> {
  const params = new URLSearchParams();
  if (commodity && commodity !== 'all') params.append('commodity', commodity);
  if (district && district !== 'all') params.append('district', district);
  if (query && query.trim()) params.append('q', query.trim());
  params.append('limit', limit.toString());

  const response = await fetch(`${API_BASE_URL}/api/v1/market/prices?${params.toString()}`);
  if (!response.ok) {
    let errorDetail = 'বাজারদর তথ্য লোড করা যায়নি।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) errorDetail = errorJson.detail;
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function fetchMarketSummary(): Promise<MarketSummaryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/market/summary`);
  if (!response.ok) throw new Error('বাজারদরের সার্বিক চিত্র লোড করা যায়নি।');
  return response.json();
}

// -------------------------------------------------------------
// Phase 7: Government Schemes API Client Functions
// -------------------------------------------------------------

export async function fetchSchemeCategories(): Promise<Array<{ id: string; label_bn: string }>> {
  const response = await fetch(`${API_BASE_URL}/api/v1/schemes/categories`);
  if (!response.ok) throw new Error('প্রকল্পের শ্রেণিবিভাগ লোড করা যায়নি।');
  return response.json();
}

export async function searchSchemes(
  query?: string,
  category?: string,
  sponsor?: string,
  beneficiaryType?: string,
  limit: number = 20
): Promise<SchemesResponse> {
  const params = new URLSearchParams();
  if (query && query.trim()) params.append('q', query.trim());
  if (category && category !== 'all') params.append('category', category);
  if (sponsor && sponsor !== 'all') params.append('sponsor', sponsor);
  if (beneficiaryType && beneficiaryType !== 'all') params.append('beneficiary_type', beneficiaryType);
  params.append('limit', limit.toString());

  const response = await fetch(`${API_BASE_URL}/api/v1/schemes?${params.toString()}`);
  if (!response.ok) {
    let errorDetail = 'সরকারি প্রকল্পের তথ্য পাওয়া যায়নি।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) errorDetail = errorJson.detail;
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export async function fetchSchemeDetails(schemeId: string): Promise<SchemeRecord> {
  const response = await fetch(`${API_BASE_URL}/api/v1/schemes/${encodeURIComponent(schemeId)}`);
  if (!response.ok) throw new Error('প্রকল্পের বিস্তারিত তথ্য পাওয়া যায়নি।');
  return response.json();
}

export async function checkSchemeEligibility(
  landSizeAcres?: number,
  isSharecropper: boolean = false,
  isOwner: boolean = true,
  interests?: string[]
): Promise<EligibilityResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/schemes/check-eligibility`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      land_size_acres: landSizeAcres,
      is_sharecropper: isSharecropper,
      is_owner: isOwner,
      interests: interests
    })
  });
  if (!response.ok) throw new Error('যোগ্যতা মূল্যায়ন সম্পন্ন করা যায়নি।');
  return response.json();
}

// -------------------------------------------------------------
// Phase 9: Supervisor Multi-Agent Types & Client Functions
// -------------------------------------------------------------

export interface SupervisorTurn {
  role: 'user' | 'assistant';
  content: string;
  detected_crop?: string | null;
  tools_called?: string[];
}

export interface SupervisorChatResponse {
  answer_bn: string;
  intent: string;
  detected_crop?: string | null;
  tools_invoked: string[];
  follow_up_prompt_bn?: string | null;
  citations: Array<{
    id?: string;
    title_bn?: string;
    source_org?: string;
    source_url?: string;
  }>;
  safety_warnings: string[];
  llm_used: boolean;
  provider: string;
}

export async function sendSupervisorMessage(
  query?: string,
  imageFile?: File,
  imageType: string = 'auto',
  crop?: string,
  latitude: number = 23.23,
  longitude: number = 87.86,
  history: SupervisorTurn[] = []
): Promise<SupervisorChatResponse> {
  const formData = new FormData();
  if (query && query.trim()) formData.append('query', query.trim());
  if (imageFile) formData.append('image', imageFile);
  if (imageType) formData.append('image_type', imageType);
  if (crop && crop !== 'all') formData.append('crop', crop);
  formData.append('latitude', latitude.toString());
  formData.append('longitude', longitude.toString());
  if (history && history.length > 0) {
    formData.append('history_json', JSON.stringify(history));
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/supervisor/chat`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    let errorDetail = 'সুপারভাইজার প্রক্রিয়াকরণে ত্রুটি ঘটেছে।';
    try {
      const errorJson = await response.json();
      if (errorJson.detail) errorDetail = errorJson.detail;
    } catch {
      errorDetail = `সার্ভার ত্রুটি (HTTP ${response.status})`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}


