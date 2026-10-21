# Implementation Plan — Phase 9: Supervisor-Based Multimodal Multi-Agent Integration

## 1. Context & Architecture Overview
In Phase 9, BhashaKheti transitions from a tabbed multi-view prototype to a unified, Bengali-first, multimodal supervisor-based agricultural assistant.

The farmer interacts via:
1. **Voice — কথা বলুন** (Primary button)
2. **Camera — ছবি তুলুন** (Primary button)
3. **Text — প্রশ্ন লিখুন** (Accessible persistent input)

All entry points route through a shared **Supervisor Orchestrator** on the backend (`POST /api/v1/supervisor/chat` and `POST /api/v1/intelligence/ask`).
The Supervisor inspects user intent, conversation history turns, and multimodal inputs (images/audio transcripts) to invoke specialized logical tools *only when necessary*, enforcing programmatic safety checks before returning structured, grounded Bengali guidance.

---

## 2. Tools & Specialized Agents Specification

| Specialized Agent | Callable Tool Name | Underlying Service / Model | Supported Inputs / Boundary |
|---|---|---|---|
| **Crop Health Agent** | `predict_plant_disease` | `disease_model_service` (MobileNetV2 PyTorch) | Validated RGB leaf image. Boundary: 15 classes (tomato, potato, bell pepper). Explicitly rejects rice or unsupported crops. |
| **Soil Agent** | `predict_soil_type` & `predict_soil_moisture` | `soil_type_service` & `soil_moisture_service` (MobileNetV2 LiteRT) | Validated RGB soil image. Explains limits: superficial type / surface moisture; does NOT claim pH, NPK, or root-zone moisture. |
| **Weather Agent** | `get_weather_forecast` | `weather_service` (Open-Meteo) | Coordinates (lat/lon). Evaluates 48h rainfall volume & probability. Prevents overwatering. |
| **Knowledge Agent** | `retrieve_agricultural_knowledge` | `knowledge_service` | Curated ICAR / State KVK verified dataset. Token-based scoring, exact citations. |
| **Market Agent** | `search_market_prices` | `market_service` | AGMARKNET verified mandi prices. Preserves modal price, per-kg price, date, and farm-gate notice. |
| **Government Scheme Agent**| `search_government_schemes` | `scheme_service` | Verified WB & Central schemes. Preserves official portal URLs and statutory safety warnings. |

---

## 3. Selective LLM vs. Deterministic Routing Rules
- **Deterministic Routing (Bypasses LLM):**
  - Unambiguous direct queries (e.g. "আলুর নাবি ধসা রোগ", "আজ বর্ধমানে ধানের দর কত", "কৃষক বন্ধু প্রকল্প", "আজ কি সেচ দেব").
  - Camera-only inputs (prompts farmer with intent choices or auto-detects leaf vs soil).
  - Executing tools and evaluating boundary checks (e.g., rejecting rice for leaf model).
  - Safety verification and chemical disclaimers.
  - Offline fallback when LLM is unconfigured, timed out, or unavailable.
- **Selective LLM Usage (Cohere Chat v2):**
  - Ambiguous / multi-part natural language Bengali queries.
  - Multi-agent evidence synthesis (e.g. combining weather forecast + plant disease + soil type into cohesive guidance).
  - Conversational follow-ups (e.g. "তাহলে এখন কী করব?", "আর কোনো উপায় আছে?") leveraging conversation context.
  - Generating context-aware single clarification questions.

---

## 4. Multi-Turn Conversation Context & Clarification
- Conversation turns (`role`, `content`, optional tool outputs) are maintained in session state.
- If essential context (e.g., crop type for fertilizer questions, or symptom extent) is missing, the supervisor returns ONE concise clarification question.
- Once the farmer replies (e.g. "ধান"), context is preserved across turns without re-asking.

---

## 5. Mobile-First Two-Button Home Screen
- Prominent dual entry cards:
  - 🎤 **কথা বলুন (Voice)**: Direct Bengali speech capture with live preview.
  - 📷 **ছবি তুলুন (Camera / Upload)**: Direct photo capture of leaf or soil with optional question.
- Persistent text input bar for silent or non-speech usage.
- Unified conversation feed displaying supervisor answers, tool badges, citations, audio replay ("পরামর্শ শুনুন"), and follow-up prompts.
- Collapsible "বিশেষায়িত ফিচারসমূহ" (Advanced Features) accordion for power users who wish to browse individual mandi tables, scheme lists, or full weather forecasts directly.

---

## 6. Implementation Steps
1. **Backend Tools & Agent Registry (`backend/app/services/agents/`):**
   - Implement `tool_registry.py` wrapping all 7 tools with strict input schemas and boundaries.
   - Implement `supervisor_service.py` with deterministic routing, selective LLM invocation, follow-up resolution, and multi-turn context support.
   - Add unified endpoint `POST /api/v1/supervisor/chat` in `backend/app/api/v1/endpoints/supervisor.py`.
   - Wire route into FastAPI router.
2. **Backend Automated Tests:**
   - Create `backend/tests/test_supervisor.py` testing:
     - Direct tool invocation without LLM.
     - Ambiguous query LLM synthesis.
     - Single & multi-agent tool execution.
     - Crop boundary rejection (rice on disease classifier).
     - Multi-turn conversation context.
     - Safe fallback when LLM is unavailable.
3. **Frontend Integration:**
   - Update `frontend/src/services/api.ts` with `sendSupervisorMessage` and conversation schemas.
   - Create `frontend/src/components/SupervisorHomeView.tsx` with Voice ("কথা বলুন") and Camera ("ছবি তুলুন") hero buttons, interactive chat feed, voice playback, and quick follow-up chips.
   - Update `frontend/src/App.tsx` to set `SupervisorHomeView` as the primary default home view.
   - Update `frontend/src/App.css` with mobile-first styling for the two-button hero layout and conversational feed.
4. **Frontend Automated Tests & Build Verification:**
   - Add tests in `frontend/src/test/SupervisorHomeView.test.tsx` and `frontend/src/test/App.test.tsx`.
   - Run `npx vitest run` and `npm run build`.
   - Run backend `python -m pytest`.
5. **Documentation & Completion Report:**
   - Update `README.md`.
   - Present final Phase 9 completion report.
