# BhasaKheti (ভাষাখেতি) - Bengali-First AI Agricultural Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.x-61dafb.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://www.typescriptlang.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x_CPU-EE4C2C.svg)](https://pytorch.org)
[![Tested with Vitest & Pytest](https://img.shields.io/badge/Tests-Passing_100%25-brightgreen.svg)]()

**BhashaKheti** is an inclusive, multimodal, Bengali-first agricultural assistant engineered for smallholder and marginal farmers in India. It eliminates complex technical menus and dashboard hurdles, allowing farmers to interact naturally via **spoken Bengali** or **crop leaf/soil photographs**. 

The system couples on-device and edge-compatible computer vision with live meteorological feeds, official AGMARKNET mandi data, and verified ICAR agronomic guidance—orchestrated through a lightweight supervisor multi-agent pipeline that instantly speaks answers aloud in Bengali.

---

## 🌟 Key Capabilities

1. **Voice-In, Voice-Out Accessibility (বাংলা ভয়েস সহকারী):**
   - Built on browser-native Web Speech API configured for Bengali (`bn-IN`).
   - Speaks answers aloud automatically with conversational pacing and markdown filtration.
   - Zero external paid voice API dependency; zero user audio saved to servers.

2. **Multimodal Computer Vision (ছবি ভিত্তিক ফসল ও মাটি বিশ্লেষণ):**
   - **Plant Leaf Disease Diagnosis:** Lightweight MobileNetV2 PyTorch model classifying 15 foliar conditions across tomato, potato, and bell pepper.
   - **Soil Characterization & Moisture:** LiteRT CNN models predicting soil classification (Alluvial, Black, Clay, Red) and surface moisture state.
   - **Programmatic Safety Guardrails:** Strict boundary rejection preventing the leaf classifier from hallucinating on unsupported crops like rice, with immediate redirection to official ICAR-NRRI protocols.

3. **Weather-Grounded Irrigation Intelligence (আবহাওয়া ও সেচ পরামর্শ):**
   - Real-time Open-Meteo IMD-aligned weather forecasts.
   - 48-hour precipitation volume and rain probability analysis preventing waterlogging and fertilizer wastage.
   - Pairs visual soil analysis with practical tactile confirmation guidance ("হাত দিয়ে মাটি পরখ করুন").

4. **Market Intelligence & Price Transparency (মান্ডি বাজারদর):**
   - Real-time West Bengal AGMARKNET mandi price discovery across staple commodities (Paddy, Potato, Tomato, Mustard, Jute, etc.).
   - Transparent unit conversion (₹/Quintal to ₹/kg) and educational notices distinguishing wholesale mandi rates from farm-gate realizations.

5. **Government Welfare Scheme Discovery (সরকারি প্রকল্প সহায়তা):**
   - Discovery of state and central farmer welfare programs (Krishak Bandhu, Bangla Shasya Bima, PM-KISAN, KCC, etc.).
   - Transparent eligibility criteria, required documents, and direct links to Bangla Sahayata Kendras (BSK) with zero collection of personal identity data (no Aadhaar/bank account harvesting).

6. **Supervisor-Based Multi-Agent Orchestrator:**
   - Central deterministic router optimizing single-tool requests directly (sub-200ms latency) without expensive LLM round-trips.
   - Selective LLM grounding reserved strictly for complex, multi-tool conversational inquiries.

---

## 💻 System & Development Requirements

- **Operating System:** Windows 10/11, Linux, or macOS
- **Hardware Footprint:** Intel i5 CPU / AMD Ryzen 5, 8 GB RAM, CPU-only (no GPU required)
- **Runtimes:**
  - Python: 3.10+
  - Node.js: v18+ or v20+

---

## 📁 Repository Structure

```text
BhasaKheti/
├── plant_disease_classifier.pth     # MobileNetV2 PyTorch model artifact (15 classes)
├── soil_type_classifier.tflite      # MobileNetV2 LiteRT soil classifier (4 classes)
├── soil_moisture_classifier.tflite  # MobileNetV2 LiteRT moisture classifier
├── models/
│   ├── label_mappings/              # Verified label dictionaries (EN & BN)
│   ├── market_data/                 # Verified AGMARKNET West Bengal mandi datasets
│   └── schemes_data/                # Verified WB & Central agricultural schemes
├── backend/                         # FastAPI Multi-Agent Application
│   ├── app/
│   │   ├── api/v1/endpoints/        # REST APIs (Supervisor, Disease, Soil, Weather, Market, Schemes)
│   │   ├── services/
│   │   │   ├── supervisor_service.py # Central Multi-Agent Orchestrator
│   │   │   ├── agents/tool_registry.py # Unified Agent Tool Registry (7 tools)
│   │   │   ├── disease_service.py   # Isolated PyTorch inference engine
│   │   │   ├── soil_type_service.py # LiteRT soil inference adapter
│   │   │   ├── soil_moisture_service.py # LiteRT moisture adapter
│   │   │   ├── weather_service.py   # Open-Meteo caching & advisory
│   │   │   ├── market_service.py    # AGMARKNET price discovery & search
│   │   │   ├── schemes_service.py   # Scheme matching engine
│   │   │   └── safety_validator.py  # Regulatory boundaries & disclaimers
│   │   └── main.py                  # FastAPI entry point & CORS configuration
│   ├── tests/                       # Complete pytest suite (Unit & Integration)
│   └── requirements.txt
├── frontend/                        # React + TypeScript + Vite PWA
│   ├── src/
│   │   ├── components/
│   │   │   ├── SupervisorHomeView.tsx # Unified Hero Voice/Camera Conversation UI
│   │   │   ├── VoiceAssistant.tsx   # Bengali Speech-to-Text & TTS engine
│   │   │   └── MarketView.tsx / SchemesView.tsx # Detailed exploration views
│   │   ├── services/
│   │   │   ├── api.ts               # Axios / Fetch client
│   │   │   └── voiceService.ts      # Web Speech Recognition & Synthesis adapter
│   │   └── test/                    # Vitest UI & integration tests
│   ├── package.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Backend Setup

```bash
# 1. Navigate to the backend directory
cd backend

# 2. (Optional) Create and activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the FastAPI server
python -m uvicorn app.main:app --reload --port 8000
```

- API Base URL: `http://localhost:8000/`
- Interactive Swagger Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/v1/health`

### 2. Frontend Setup

In a new terminal window:

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

- Web Interface: `http://localhost:5173/`

---

## 🧪 Testing & Verification

Both backend and frontend are protected by automated test suites:

### Backend Tests:
```bash
cd backend
python -m pytest tests
```
*Validates multi-agent supervisor routing, crop boundaries, AGMARKNET unit conversions, and weather integration.*

### Frontend Tests:
```bash
cd frontend
npm test -- --run
```
*Validates Bengali speech recognizer integration, responsive viewport rendering, camera attachments, and conversational streaming.*

### Production Build Check:
```bash
cd frontend
npm run build
```

---

## 🛡️ Safety & Responsible AI Architecture

- **No Hallucinated Cures:** BhashaKheti does not invent chemical dosages or prescribe unverified remedies. Diagnostic outputs are grounded in official ICAR, KVK, and State Department agronomy guides.
- **Privacy by Design:** Zero harvesting of Aadhaar cards, bank details, or contact lists for scheme exploration.
- **Zero Paid Subscription Lock-in:** Designed specifically to deploy on lightweight public servers or Gram Panchayat community kiosks without mandatory paid API keys.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
