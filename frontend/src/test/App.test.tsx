import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';

vi.mock('../services/api', () => ({
  checkBackendHealth: vi.fn().mockResolvedValue({
    status: 'ok',
    environment: 'development',
    phase: 'Phase 3: Soil Models Integration',
    database_connected: true,
    models: {
      plant_disease_classifier: {
        artifact_exists: true,
        status: 'integrated',
        note: 'Phase 2: MobileNetV2 disease model integrated on CPU.'
      },
      soil_type_classifier: {
        artifact_exists: true,
        status: 'integrated',
        note: 'Phase 3: MobileNetV2 TFLite soil type model integrated on CPU.'
      },
      soil_moisture_classifier: {
        artifact_exists: true,
        status: 'integrated',
        note: 'Phase 3: MobileNetV2 TFLite soil moisture model integrated on CPU.'
      }
    }
  }),
  predictPlantDisease: vi.fn(),
  predictSoilType: vi.fn(),
  predictSoilMoisture: vi.fn(),
  fetchWeatherForecast: vi.fn().mockResolvedValue({
    provider: 'Open-Meteo',
    provider_terms: 'Non-commercial Open-Meteo Free API',
    location_name: 'বর্ধমান (Bardhaman)',
    latitude: 23.2324,
    longitude: 87.8615,
    timezone: 'Asia/Kolkata',
    retrieved_at_unix: 1729000000,
    is_cached: false,
    is_stale: false,
    cached_age_seconds: 0,
    current_conditions: {
      observation_time: '2026-10-15T12:00',
      temperature_c: 31.5,
      apparent_temperature_c: 35.2,
      relative_humidity_pct: 65,
      precipitation_mm: 0.0,
      wind_speed_kmh: 12.0,
      wind_direction_deg: 180,
      wind_direction_bn: 'দক্ষিণ',
      weather_code: 1,
      weather_desc_en: 'Mainly clear',
      weather_desc_bn: 'প্রধানত পরিষ্কার',
      weather_type: 'partly_cloudy'
    },
    daily_forecast: [
      {
        date: '2026-10-15',
        weather_code: 1,
        weather_desc_en: 'Mainly clear',
        weather_desc_bn: 'প্রধানত পরিষ্কার',
        weather_type: 'partly_cloudy',
        temperature_max_c: 33.0,
        temperature_min_c: 24.0,
        precipitation_sum_mm: 0.0,
        precipitation_probability_pct: 10,
        wind_speed_max_kmh: 14.0
      }
    ],
    agricultural_advisory: {
      is_fieldwork_advisable: true,
      advisory_notes_bn: ['মাঠের কাজের জন্য আবহাওয়া অনুকূল রয়েছে।'],
      caution_notice_bn: 'পূর্বাভাসে অনিশ্চয়তা থাকতে পারে।'
    }
  }),
  searchWeatherLocations: vi.fn().mockResolvedValue([]),
  searchKnowledge: vi.fn().mockResolvedValue({
    has_sufficient_evidence: true,
    query: 'আলুর নাবি ধসা রোগ',
    total_matches: 1,
    results: [
      {
        id: 'KB-POTATO-001',
        title_bn: 'আলুর নাবি ধসা (লেইট ব্লাইট) রোগ ও সতর্কতামূলক ব্যবস্থাপনা',
        title_en: 'Late Blight Management in Potato',
        crop: 'potato',
        category: 'disease_management',
        topic: 'নাবি ধসা (Phytophthora infestans)',
        content_bn: 'আলুর নাবি ধসা একটি মারাত্মক ছত্রাকঘটিত রোগ। কুয়াশাচ্ছন্ন আবহাওয়ায় ম্যানকোজেব স্প্রে করুন।',
        content_en: 'Late blight thrives in foggy conditions.',
        source_org: 'ICAR-Central Potato Research Institute (CPRI)',
        source_url: 'https://cpri.icar.gov.in',
        publication_date: '2023-11-12',
        last_verified_date: '2026-10-15',
        geographic_scope: 'পশ্চিমবঙ্গ',
        evidence_status: 'verified',
        safety_notes_bn: 'বালাইনাশক ব্যবহারের আগে KPS/ADA-র পরামর্শ নিন।',
        safety_notes_en: 'Consult local officers.',
        keywords: ['আলু', 'নাবি ধসা'],
        chemical_control_permitted: true
      }
    ],
    boundary_warnings: []
  }),
  getKnowledgeCategories: vi.fn().mockResolvedValue({
    total_records: 13,
    crops: [{ id: 'potato', label_bn: 'আলু (Potato)' }],
    categories: [{ id: 'disease_management', label_bn: 'রোগ ব্যবস্থাপনা' }]
  }),
  askKnowledgeQuestion: vi.fn().mockResolvedValue({
    has_sufficient_evidence: true,
    query: 'আলুর রোগ',
    answer_bn: 'আলুর নাবি ধসার জন্য পরিমিত ছত্রাকনাশক ব্যবহার করুন।',
    source_org: 'ICAR-CPRI',
    source_url: 'https://cpri.icar.gov.in',
    publication_date: '2023-11-12',
    last_verified_date: '2026-10-15',
    evidence_status: 'verified',
    safety_warnings: []
  }),
  getKnowledgeRecord: vi.fn(),
  askCropIntelligence: vi.fn().mockResolvedValue({
    intent: 'irrigation',
    crop: 'rice',
    answer_bn: 'আগামী ৪৮ ঘণ্টায় ভারী বৃষ্টির সম্ভাবনা রয়েছে, তাই আজ জমিতে অতিরিক্ত সেচ না দেওয়াই শ্রেয়।',
    missing_context: [],
    weather_summary: {
      available: true,
      current_temp_c: 31.5,
      current_humidity: 65,
      current_rain_mm: 0,
      weather_desc_bn: 'প্রধানত পরিষ্কার',
      rain_next_48h_mm: 15.0,
      max_rain_probability_48h: 75,
      advisory_notes_bn: ['মাঠের কাজের জন্য আবহাওয়া অনুকূল রয়েছে।']
    },
    citations: [
      {
        id: 'KB-IMD-001',
        title_bn: 'আইএমডি কৃষি আবহাওয়া বুলেটিন',
        title_en: 'IMD Agromet Advisory',
        source_org: 'IMD & Open-Meteo',
        source_url: 'https://open-meteo.com',
        last_verified_date: '2026-10-15'
      }
    ],
    safety_warnings: ['বালাইনাশক ব্যবহারের আগে স্থানীয় কৃষি কর্মকর্তার পরামর্শ নিন।'],
    llm_used: true,
    provider: 'cohere'
  }),
  fetchMarketCommodities: vi.fn().mockResolvedValue([
    { id: 'potato', name_bn: 'আলু', name_en: 'Potato' }
  ]),
  fetchMarketDistricts: vi.fn().mockResolvedValue([
    { district_en: 'Bardhaman', district_bn: 'পূর্ব বর্ধমান' }
  ]),
  searchMarketPrices: vi.fn().mockResolvedValue({
    total_matches: 1,
    results_count: 1,
    prices: [
      {
        id: 'MKT-WB-POT-001',
        commodity_id: 'potato',
        commodity_name_bn: 'আলু',
        commodity_name_en: 'Potato',
        variety: 'জ্যোতি (Jyoti)',
        market_id: 'wb_bardhaman_01',
        market_name_bn: 'বর্ধমান মান্ডি',
        market_name_en: 'Burdwan Market',
        district_bn: 'পূর্ব বর্ধমান',
        district_en: 'Bardhaman',
        state: 'West Bengal',
        min_price: 1400.0,
        max_price: 1600.0,
        modal_price: 1500.0,
        modal_price_per_kg: 15.0,
        min_price_per_kg: 14.0,
        max_price_per_kg: 16.0,
        unit: '₹/কুয়িন্টাল',
        currency: 'INR',
        reported_date: '2026-10-14',
        data_status: 'verified_recent',
        is_historical: false,
        source_name: 'AGMARKNET (agmarknet.gov.in)',
        source_url: 'https://agmarknet.gov.in'
      }
    ],
    disclaimers: [
      'খামার প্রান্তের দর ও মান্ডি দরের পার্থক্য পরিবহন ও মধ্যস্বত্বভোগী খরচের কারণে হয়।'
    ],
    data_source: 'AGMARKNET',
    source_url: 'https://agmarknet.gov.in'
  }),
  fetchMarketSummary: vi.fn().mockResolvedValue({
    report_date: '2026-10-14',
    summary_highlights: [
      {
        commodity_id: 'potato',
        commodity_name_bn: 'আলু',
        commodity_name_en: 'Potato',
        average_modal_price: 1500.0,
        average_modal_per_kg: 15.0,
        unit: '₹/কুয়িন্টাল',
        latest_date: '2026-10-14',
        mandis_reporting: 4
      }
    ],
    disclaimer_bn: 'এটি মান্ডির গড় পাইকারি দর।',
    source_name: 'AGMARKNET'
  }),
  fetchSchemeCategories: vi.fn().mockResolvedValue([
    { id: 'income_support', label_bn: 'প্রত্যক্ষ আর্থিক সহায়তা' }
  ]),
  searchSchemes: vi.fn().mockResolvedValue({
    total_matches: 1,
    results_count: 1,
    schemes: [
      {
        id: 'SCHEME-WB-KB-001',
        name_bn: 'কৃষক বন্ধু (নতুন) নিশ্চিত আয় প্রকল্প',
        name_en: 'Krishak Bandhu (Natun) Assured Income Scheme',
        authority_bn: 'কৃষি বিভাগ, পশ্চিমবঙ্গ সরকার',
        authority_en: 'Department of Agriculture, Govt of West Bengal',
        sponsor: 'state',
        category: 'income_support',
        category_bn: 'প্রত্যক্ষ আর্থিক সহায়তা',
        summary_bn: 'পশ্চিমবঙ্গের কৃষকদের জন্য এককালীন বা দুই কিস্তিতে নিশ্চিত আর্থিক অনুদান।',
        summary_en: 'Direct income support for farmers in West Bengal.',
        benefits_bn: 'প্রতি বছর সর্বোচ্চ ₹১০,০০০ এবং ন্যূনতম ₹৪,০০০ দুটি সমান কিস্তিতে (খরিফ ও রবি মরসুমে)। এছাড়া কৃষক মৃত্যুতে ₹২ লক্ষ অনুদান।',
        benefits_en: 'Financial assistance up to Rs 10,000/year.',
        eligibility_bn: 'পশ্চিমবঙ্গের বাসিন্দা ও বৈধ চাষযোগ্য জমির মালিক বা নথিভুক্ত কৃষক।',
        eligibility_en: 'Resident farmers with land records in West Bengal.',
        land_size_criteria: '১ একর বা তদূর্ধ্ব জমি থাকলে ₹১০,০০০; ১ একরের কম হলে আনুপাতিক হারে ন্যূনতম ₹৪,০০০।',
        beneficiary_types: ['owner', 'small_marginal'],
        required_documents_bn: [
          'জমির সাম্প্রতিক খতিয়ান বা পরচা (RoR)',
          'ভোটার পরিচয়পত্র (Voter ID / EPIC)',
          'ব্যাংক পাসবইয়ের প্রথম পাতার কপি (IFSC কোড সহ)'
        ],
        required_documents_en: ['Land RoR', 'Voter ID', 'Bank Passbook'],
        application_mode: 'অফলাইন ও বিএসকে (Bangla Sahayata Kendra)',
        application_process_bn: 'নিকটবর্তী বাংলা সহায়তা কেন্দ্র (BSK) বা ব্লক কৃষি আধিকারিক (ADA) অফিসে ফর্ম জমা দিন।',
        official_portal_url: 'https://krishakbandhu.wb.gov.in',
        status: 'current',
        status_bn: 'চালু (Current)',
        deadline_bn: 'সারা বছর নতুন আবেদন গ্রহণ করা হয়।',
        verification_date: '2026-10-15',
        source_name: 'কৃষি বিভাগ, পশ্চিমবঙ্গ সরকার',
        safety_disclaimer_bn: 'কোনো তৃতীয় পক্ষ বা দালালকে অর্থ প্রদান করবেন না। আবেদন ফর্ম বিনামূল্যে পাওয়া যায়।'
      }
    ],
    notice_bn: 'প্রকল্পের যোগ্যতা ও শর্তাবলী সরকারি নীতিমালা অনুযায়ী পরিবর্তনশীল।'
  }),
  fetchSchemeDetails: vi.fn(),
  checkSchemeEligibility: vi.fn().mockResolvedValue({
    total_matched: 1,
    matched_schemes: [
      {
        scheme_id: 'SCHEME-WB-KB-001',
        name_bn: 'কৃষক বন্ধু (নতুন)',
        authority_bn: 'পশ্চিমবঙ্গ সরকার',
        benefits_summary: 'প্রতি বছর সর্বোচ্চ ₹১০,০০০ আর্থিক অনুদান',
        status: 'চালু',
        official_portal_url: 'https://krishakbandhu.wb.gov.in',
        eligibility_reasons: ['জমির মালিকানা শর্ত পূরণ হয়েছে']
      }
    ],
    privacy_statement: 'আপনার কোনো সংবেদনশীল ব্যক্তিগত তথ্য সংগ্রহ করা হয় না।',
    statutory_notice: 'এটি প্রাথমিক অনুমিত ফলাফল, সরকারি চূড়ান্ত সিদ্ধান্ত নয়।'
  }),
  sendSupervisorMessage: vi.fn().mockResolvedValue({
    answer_bn: 'সুপারভাইজার: আপনার কৃষি সমস্যার তথ্য যাচাই করা হচ্ছে। আগামী ৪৮ ঘণ্টায় ভারী বৃষ্টির সম্ভাবনা রয়েছে।',
    tools_invoked: ['get_weather'],
    tool_results: {},
    follow_up_prompt: 'আর কোনো সাহায্য প্রয়োজন কি?',
    citations: [],
    safety_warnings: [],
    requires_followup: false,
    detected_crop: 'rice',
    detected_intent: 'irrigation',
    llm_used: false,
    provider: 'deterministic'
  })
}));

describe('App & Multi-Model Views Smoke Tests', () => {
  it('renders Bengali brand title and header', () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1, name: /ভাষাখেতি/i })).toBeInTheDocument();
    expect(screen.getByText(/কৃষকের নির্ভরযোগ্য ডিজিটাল পরামর্শক/i)).toBeInTheDocument();
  });

  it('renders all Bengali navigation tabs', () => {
    render(<App />);
    expect(screen.getByText('সুপারভাইজার সহকারী')).toBeInTheDocument();
    expect(screen.getByText('বুদ্ধিমান পরামর্শক')).toBeInTheDocument();
    expect(screen.getByText('গাছের রোগ নির্ণয়')).toBeInTheDocument();
    expect(screen.getByText('মাটির ধরন')).toBeInTheDocument();
    expect(screen.getByText('মাটির আর্দ্রতা ও সেচ')).toBeInTheDocument();
    expect(screen.getByText('আবহাওয়ার পূর্বাভাস')).toBeInTheDocument();
    expect(screen.getByText('কৃষি জ্ঞানভাণ্ডার')).toBeInTheDocument();
    expect(screen.getByText('বাজার দর')).toBeInTheDocument();
    expect(screen.getAllByText('সরকারি প্রকল্প')[0]).toBeInTheDocument();
    expect(screen.getByText('সিস্টেম স্ট্যাটাস')).toBeInTheDocument();
  });

  it('renders supervisor multimodal home screen by default with welcome greeting and 4 visual suggestion cards', async () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 2, name: /নমস্কার!/i })).toBeInTheDocument();
    expect(screen.getByText(/আপনি কী জানতে চান\?/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /কথা বলুন \(Voice Assistant\)/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ছবি তুলুন \(Camera \/ Photo\)/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/আপনার প্রশ্ন বলুন\.\.\./i)).toBeInTheDocument();

    const paddyCard = screen.getByRole('button', { name: /ধানের সমস্যা/i });
    fireEvent.click(paddyCard);

    await waitFor(() => {
      expect(screen.getByText(/সুপারভাইজার: আপনার কৃষি সমস্যার তথ্য যাচাই করা হচ্ছে/i)).toBeInTheDocument();
    });
  });

  it('switches to crop intelligence screen and executes query', async () => {
    render(<App />);
    const intelTab = screen.getByText('বুদ্ধিমান পরামর্শক');
    fireEvent.click(intelTab);

    expect(screen.getByRole('heading', { level: 2, name: /বুদ্ধিমান কৃষি পরামর্শক/i })).toBeInTheDocument();
    const chip = screen.getByRole('button', { name: 'আজ কি ধান জমিতে সেচ দেব?' });
    fireEvent.click(chip);

    await waitFor(() => {
      expect(screen.getByText(/আগামী ৪৮ ঘণ্টায় ভারী বৃষ্টির সম্ভাবনা রয়েছে/i)).toBeInTheDocument();
      expect(screen.getByText(/স্থানীয় আবহাওয়া ও বৃষ্টিপাত পর্যবেক্ষণ/i)).toBeInTheDocument();
      expect(screen.getByText(/15 মিমি/i)).toBeInTheDocument();
    });
  });

  it('switches to disease investigation screen and renders upload controls', () => {
    render(<App />);
    const diseaseTab = screen.getByText('গাছের রোগ নির্ণয়');
    fireEvent.click(diseaseTab);

    expect(screen.getByRole('heading', { level: 2, name: /গাছের পাতার রোগ নির্ণয়/i })).toBeInTheDocument();
    expect(screen.getByText(/আক্রান্ত পাতার ছবি বেছে নিন বা ড্রপ করুন/i)).toBeInTheDocument();
  });

  it('switches to soil type screen and renders soil type upload controls', () => {
    render(<App />);
    const soilTypeTab = screen.getByText('মাটির ধরন');
    fireEvent.click(soilTypeTab);

    expect(screen.getByRole('heading', { level: 2, name: /মাটির ধরন বিশ্লেষণ/i })).toBeInTheDocument();
    expect(screen.getByText(/মাটির ছবি নির্বাচন করুন বা ড্রপ করুন/i)).toBeInTheDocument();
  });

  it('switches to soil moisture screen and renders moisture upload controls', () => {
    render(<App />);
    const moistureTab = screen.getByText('মাটির আর্দ্রতা ও সেচ');
    fireEvent.click(moistureTab);

    expect(screen.getByRole('heading', { level: 2, name: /মাটির আর্দ্রতা মূল্যায়ন/i })).toBeInTheDocument();
    expect(screen.getByText(/মাটির উপরিভাগের ছবি বেছে নিন বা ড্রপ করুন/i)).toBeInTheDocument();
  });

  it('switches to system status screen and shows all 3 integrated model items, Phase 8 voice assistant, and Phase 9 supervisor', async () => {
    render(<App />);
    const statusTabButton = screen.getByText('সিস্টেম স্ট্যাটাস');
    fireEvent.click(statusTabButton);

    await waitFor(() => {
      expect(screen.getByText(/সিস্টেম ও অবকাঠামো স্ট্যাটাস/i)).toBeInTheDocument();
      expect(screen.getByText(/১. গাছের পাতার রোগ শনাক্তকরণ/i)).toBeInTheDocument();
      expect(screen.getByText(/২. মাটির ধরন শ্রেণিবিন্যাসকারী/i)).toBeInTheDocument();
      expect(screen.getByText(/৩. মাটির আর্দ্রতা শনাক্তকরণ/i)).toBeInTheDocument();
      expect(screen.getByText(/৪. বুদ্ধিমান বহু-টুল কৃষি পরামর্শক/i)).toBeInTheDocument();
      expect(screen.getByText(/৫. বাজারদর ও সরকারি প্রকল্প সন্ধান/i)).toBeInTheDocument();
      expect(screen.getByText(/৬. বাংলা ভয়েস সহকারী ও অ্যাক্সেসিবিলিটি/i)).toBeInTheDocument();
      expect(screen.getByText(/৭. মাল্টি-এজেন্ট সুপারভাইজার সিস্টেম/i)).toBeInTheDocument();
    });
  });

  it('switches to weather screen and renders weather dashboard with current conditions and agricultural advisory', async () => {
    render(<App />);
    const weatherTab = screen.getByText('আবহাওয়ার পূর্বাভাস');
    fireEvent.click(weatherTab);

    expect(screen.getByRole('heading', { level: 2, name: /আবহাওয়া পূর্বাভাস ও কৃষি সতর্কতা/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('31.5°C')).toBeInTheDocument();
      expect(screen.getAllByText('প্রধানত পরিষ্কার').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/কৃষি আবহাওয়া পরামর্শ/i)).toBeInTheDocument();
      expect(screen.getByText(/আগামী ৫ দিনের আবহাওয়ার পূর্বাভাস/i)).toBeInTheDocument();
    });
  });

  it('switches to knowledge screen and renders verified agricultural knowledge guidelines', async () => {
    render(<App />);
    const knowledgeTab = screen.getByText('কৃষি জ্ঞানভাণ্ডার');
    fireEvent.click(knowledgeTab);

    expect(screen.getByRole('heading', { level: 2, name: /কৃষি জ্ঞানভাণ্ডার ও নির্ভরযোগ্য সুরক্ষা নির্দেশিকা/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('আলুর নাবি ধসা (লেইট ব্লাইট) রোগ ও সতর্কতামূলক ব্যবস্থাপনা')).toBeInTheDocument();
      expect(screen.getByText(/ICAR-Central Potato Research Institute/i)).toBeInTheDocument();
      expect(screen.getByText(/যাচাইকৃত \(Verified\)/i)).toBeInTheDocument();
      expect(screen.getByText(/তথ্যভাণ্ডারের উৎস ও প্রাতিষ্ঠানিক স্বচ্ছতা/i)).toBeInTheDocument();
    });
  });

  it('switches to market view and renders mandi prices, educational disclaimer and AGMARKNET links', async () => {
    render(<App />);
    const marketTab = screen.getByText('বাজার দর');
    fireEvent.click(marketTab);

    expect(screen.getByRole('heading', { level: 2, name: /পশ্চিমবঙ্গ কৃষি বাজারদর/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByText(/আলু/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/বর্ধমান মান্ডি/i)).toBeInTheDocument();
      expect(screen.getByText(/খামার বিক্রয়মূল্যের/i)).toBeInTheDocument();
      expect(screen.getByText(/অফিসিয়াল AGMARKNET পোর্টাল/i)).toBeInTheDocument();
    });
  });

  it('switches to schemes view and renders government schemes, benefits and official links', async () => {
    render(<App />);
    const schemesTab = screen.getAllByText('সরকারি প্রকল্প')[0];
    fireEvent.click(schemesTab);

    expect(screen.getByRole('heading', { level: 2, name: /সরকারি কৃষি প্রকল্প ও সহায়তা/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/কৃষক বন্ধু \(নতুন\) নিশ্চিত আয় প্রকল্প/i)).toBeInTheDocument();
      expect(screen.getByText(/কৃষি বিভাগ, পশ্চিমবঙ্গ সরকার/i)).toBeInTheDocument();
      expect(screen.getByText(/প্রতি বছর সর্বোচ্চ ₹১০,০০০/i)).toBeInTheDocument();
      expect(screen.getByText(/জমির সাম্প্রতিক খতিয়ান বা পরচা/i)).toBeInTheDocument();
      expect(screen.getByText(/অফিসিয়াল পোর্টালে যান/i)).toBeInTheDocument();
    });
  });

  it('renders Bengali voice assistant controls and handles voice playback and fallback', async () => {
    render(<App />);
    // Voice button on persistent bottom bar
    const micButton = screen.getByRole('button', { name: /কথা বলুন \(Voice Assistant\)/i });
    expect(micButton).toBeInTheDocument();

    // After querying supervisor, speech synthesis button becomes available
    const paddyCard = screen.getByRole('button', { name: /ধানের সমস্যা/i });
    fireEvent.click(paddyCard);

    await waitFor(() => {
      expect(screen.getByText(/সুপারভাইজার: আপনার কৃষি সমস্যার তথ্য যাচাই করা হচ্ছে/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /পরামর্শ শুনুন/i })).toBeInTheDocument();
    });
  });
});
