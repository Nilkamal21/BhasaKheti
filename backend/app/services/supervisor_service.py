"""
Supervisor / Orchestrator Engine for BhashaKheti (Phase 9).
Central coordinator responsible for:
1. Multimodal inquiry analysis (Voice transcript, Camera image, Text input).
2. Multi-turn conversation context tracking and follow-up question generation.
3. Selective LLM usage vs. deterministic tool execution.
4. Programmatic safety verification prior to response emission.
5. Structured Bengali response formatting with citations.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.logging import logger
from app.services.agents.tool_registry import tool_registry, ToolResult
from app.services.safety_validator import (
    safety_validator,
    RICE_MODEL_BOUNDARY_WARNING_BN,
    STATUTORY_CHEMICAL_DISCLAIMER_BN,
    SOIL_MODEL_BOUNDARY_DISCLAIMER_BN,
    MOISTURE_MODEL_BOUNDARY_DISCLAIMER_BN
)
from app.services.llm import get_llm_provider


class ChatTurn(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text in Bengali or English")
    detected_crop: Optional[str] = None
    tools_called: List[str] = Field(default_factory=list)


class SupervisorResponse(BaseModel):
    answer_bn: str
    intent: str
    detected_crop: Optional[str] = None
    tools_invoked: List[str] = Field(default_factory=list)
    follow_up_prompt_bn: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    safety_warnings: List[str] = Field(default_factory=list)
    llm_used: bool = False
    provider: str = "deterministic_supervisor"


class SupervisorOrchestrator:
    """Central supervisor coordinating specialized tools and selective LLM."""

    def __init__(self):
        self.llm = get_llm_provider()

    def detect_crop_from_context(self, current_query: str, history: List[ChatTurn]) -> Optional[str]:
        """Infers crop name from current query or prior conversation turns."""
        lower_q = current_query.lower()
        if any(w in lower_q for w in ["ধান", "rice", "paddy", "আমন", "বোরো"]):
            return "rice"
        if any(w in lower_q for w in ["আলু", "potato", "আলুর"]):
            return "potato"
        if any(w in lower_q for w in ["টমেটো", "tomato", "টমেটোর"]):
            return "tomato"
        if any(w in lower_q for w in ["ক্যাপসিকাম", "লঙ্কা", "মরিচ", "chilli", "pepper"]):
            return "bell_pepper"
        if any(w in lower_q for w in ["পাট", "jute"]):
            return "jute"
        if any(w in lower_q for w in ["সরিষা", "mustard"]):
            return "mustard"

        # Check prior user/assistant turns in history
        for turn in reversed(history):
            if turn.detected_crop:
                return turn.detected_crop
            t_lower = turn.content.lower()
            if any(w in t_lower for w in ["ধান", "rice", "paddy"]):
                return "rice"
            if any(w in t_lower for w in ["আলু", "potato"]):
                return "potato"
            if any(w in t_lower for w in ["টমেটো", "tomato"]):
                return "tomato"
            if any(w in t_lower for w in ["ক্যাপসিকাম", "লঙ্কা"]):
                return "bell_pepper"

        return None

    @staticmethod
    def normalize_bengali_text(text: str) -> str:
        """Normalizes Unicode and fixes separated vowels or dotted circle sequences."""
        import unicodedata
        import re
        normalized = unicodedata.normalize("NFC", text or "")
        # Strip dotted circle (U+25CC) and join detached vowels with preceding consonant
        cleaned = re.sub(r'[\u25cc\s]+([\u09be-\u09cd])', r'\1', normalized)
        return cleaned.lower()

    @staticmethod
    def detect_visual_category(image_bytes: bytes) -> str:
        """
        Determines whether the provided image is a crop leaf or bare farm soil
        using deterministic color-histogram domain rules.
        """
        if not image_bytes:
            return "unknown"
        try:
            import io
            from PIL import Image
            import numpy as np

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img.thumbnail((120, 120))
            arr = np.array(img, dtype=float)
            r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

            # Green dominance indicates plant leaf/foliage
            green_dom = (g > r + 15) & (g > b)
            green_ratio = float(np.mean(green_dom))

            # Earthy / brown dominance indicates soil
            soil_dom = (r >= g - 5) & (g >= b) & (r > b + 10)
            soil_ratio = float(np.mean(soil_dom))

            if soil_ratio > 0.35 and green_ratio < 0.20:
                return "soil"
            elif green_ratio > 0.20:
                return "leaf"
            elif soil_ratio > green_ratio:
                return "soil"
            else:
                return "leaf"
        except Exception:
            return "auto"

    def analyze_intent(self, query: str, has_image: bool) -> Dict[str, Any]:
        """Classifies intent using deterministic keywords with fallback."""
        lower_q = self.normalize_bengali_text(query)

        is_market = any(w in lower_q for w in ["বাজারদর", "বাজার দর", "দাম", "দর", "রেট", "মূল্য", "মন্ডি", "মার্কেট", "price", "rate", "mandi"])
        is_scheme = any(w in lower_q for w in ["প্রকল্প", "সরকারি", "ভর্তুকি", "অনুদান", "কৃষক বন্ধু", "বিমা", "লোন", "ঋণ", "সাহায্য", "scheme", "subsidy", "pm-kisan", "kcc"])
        is_irrigation = any(w in lower_q for w in ["জল", "সেচ", "পানি", "ভিজানো", "water", "watering", "irrigate", "irrigation", "সেচ দেব", "বৃষ্টি", "খরা", "rain", "weather", "আবহাওয়া"])
        is_fertilizer = any(w in lower_q for w in ["সার", "ইউরিয়া", "পটাশ", "ডিএপি", "পুষ্টি", "fertilizer", "nutrient", "খাবার"])
        is_disease = any(w in lower_q for w in ["দাগ", "রোগ", "পচা", "ধসা", "পোকা", "হলুদ", "কুঁকড়ে", "blight", "curl", "spot", "পোকা"])
        is_soil = any(w in lower_q for w in [
            "মাটি", "মাটিতে", "মাটির", "পলি", "ল্যাটেরাইট", "বেলে", "দোআঁশ", "এঁটেল", "soil",
            "জমি", "জমিতে", "জমির", "খেত", "ক্ষেত", "কী চাষ", "কী ফসল", "কী লাগাব", "চাষ করব",
            "বপন", "রোপণ", "মরশুম", "ঋতু", "ফসল লাগা"
        ])

        if is_market:
            primary_intent = "market"
        elif is_scheme:
            primary_intent = "schemes"
        elif is_irrigation:
            primary_intent = "irrigation_weather"
        elif is_disease:
            primary_intent = "crop_health"
        elif is_fertilizer or is_soil:
            primary_intent = "soil_fertilizer"
        elif has_image:
            primary_intent = "visual_inspection"
        else:
            primary_intent = "general_guidance"

        return {
            "intent": primary_intent,
            "is_market": is_market,
            "is_scheme": is_scheme,
            "is_irrigation": is_irrigation,
            "is_fertilizer": is_fertilizer,
            "is_disease": is_disease,
            "is_soil": is_soil
        }

    async def plan_and_execute(
        self,
        query: str,
        image_bytes: Optional[bytes] = None,
        image_type: Optional[str] = None,  # 'leaf', 'soil', or 'auto'
        history: Optional[List[ChatTurn]] = None,
        crop: Optional[str] = None,
        latitude: float = 23.23,
        longitude: float = 87.86
    ) -> SupervisorResponse:
        """
        Main supervisor pipeline:
        1. Context extraction & crop resolution
        2. Tool planning (deterministic vs LLM)
        3. Bounded tool execution
        4. Safety verification
        5. Grounded synthesis
        """
        history = history or []
        cleaned_query = query.strip() if query else ""
        has_image = bool(image_bytes and len(image_bytes) > 0)

        # Step 1: Resolve crop from current message or conversation history
        detected_crop = crop or self.detect_crop_from_context(cleaned_query, history)

        # Step 2: Intent analysis
        intent_info = self.analyze_intent(cleaned_query, has_image)
        intent = intent_info["intent"]

        tools_invoked: List[str] = []
        collected_results: List[ToolResult] = []
        safety_warnings: List[str] = []
        citations: List[Dict[str, Any]] = []

        # Check safety boundaries on text query ONLY when relevant
        if cleaned_query:
            # If the query is about irrigation, market, or schemes, do not check leaf disease boundaries
            if not intent_info["is_irrigation"] and not intent_info["is_market"] and not intent_info["is_scheme"]:
                boundary_warnings = safety_validator.check_query_boundaries(cleaned_query, detected_crop)
                safety_warnings.extend(boundary_warnings)

        # Step 3: Tool Selection & Execution
        # Case A: Visual Image Provided (Camera input)
        resolved_image_type = (image_type or "auto").lower()
        if has_image and resolved_image_type == "auto":
            vis_cat = self.detect_visual_category(image_bytes)
            if vis_cat == "soil" or intent_info["is_soil"]:
                resolved_image_type = "soil"
            elif vis_cat == "leaf" or intent_info["is_disease"]:
                resolved_image_type = "leaf"
            else:
                resolved_image_type = "soil" if intent_info["is_soil"] else "leaf"

        if has_image:
            # If farmer is asking about irrigation, analyze soil moisture without triggering leaf disease warnings
            if intent_info["is_irrigation"]:
                moist_res = tool_registry.predict_soil_moisture(image_bytes)
                collected_results.append(moist_res)
                tools_invoked.append("predict_soil_moisture")

            elif resolved_image_type == "soil" or intent_info["is_soil"] or "মাটি" in cleaned_query:
                # Soil Agent tools
                soil_res = tool_registry.predict_soil_type(image_bytes)
                collected_results.append(soil_res)
                tools_invoked.append("predict_soil_type")

                moist_res = tool_registry.predict_soil_moisture(image_bytes)
                collected_results.append(moist_res)
                tools_invoked.append("predict_soil_moisture")
                safety_warnings.append(SOIL_MODEL_BOUNDARY_DISCLAIMER_BN)
                safety_warnings.append(MOISTURE_MODEL_BOUNDARY_DISCLAIMER_BN)

            elif resolved_image_type == "leaf" or intent_info["is_disease"] or intent in ["crop_health", "visual_inspection"]:
                # Crop Health Agent tool: Disease model on leaf
                if detected_crop == "rice":
                    # Programmatic safety boundary: Do NOT run 15-class model on rice when diagnosing diseases
                    safety_warnings.append(RICE_MODEL_BOUNDARY_WARNING_BN)
                else:
                    disease_res = tool_registry.predict_plant_disease(image_bytes, crop=detected_crop)
                    collected_results.append(disease_res)
                    tools_invoked.append("predict_plant_disease")
                    if disease_res.disclaimer_bn:
                        safety_warnings.append(disease_res.disclaimer_bn)

        # Case B: Weather Agent
        if intent_info["is_irrigation"] or "আবহাওয়া" in cleaned_query:
            weather_res = await tool_registry.get_weather(latitude=latitude, longitude=longitude)
            collected_results.append(weather_res)
            tools_invoked.append("get_weather")
            citations.extend(weather_res.citations)

        # Case C: Market Agent
        if intent_info["is_market"]:
            mkt_res = tool_registry.search_market_prices(commodity=detected_crop, query=cleaned_query)
            collected_results.append(mkt_res)
            tools_invoked.append("search_market_prices")
            citations.extend(mkt_res.citations)
            if mkt_res.disclaimer_bn:
                safety_warnings.append(mkt_res.disclaimer_bn)

        # Case D: Government Scheme Agent
        if intent_info["is_scheme"]:
            scheme_res = tool_registry.search_government_schemes(query=cleaned_query)
            collected_results.append(scheme_res)
            tools_invoked.append("search_government_schemes")
            citations.extend(scheme_res.citations)
            if scheme_res.disclaimer_bn:
                safety_warnings.append(scheme_res.disclaimer_bn)

        # Case E: Agricultural Knowledge Agent (Fallback / Grounding)
        if intent_info["is_disease"] or intent_info["is_fertilizer"] or intent_info["is_soil"] or (not collected_results and cleaned_query):
            kb_res = tool_registry.retrieve_agricultural_knowledge(query=cleaned_query, crop=detected_crop)
            collected_results.append(kb_res)
            tools_invoked.append("retrieve_agricultural_knowledge")
            citations.extend(kb_res.citations)

        # Deduplicate citations and warnings
        unique_citations = []
        seen_cids = set()
        for c in citations:
            cid = c.get("id") or c.get("source_url")
            if cid and cid not in seen_cids:
                seen_cids.add(cid)
                unique_citations.append(c)

        unique_warnings = list(dict.fromkeys(safety_warnings))

        # Step 4: Missing context check -> Return single polite follow-up if needed
        follow_up_prompt_bn = None
        if intent_info["is_fertilizer"] and not detected_crop:
            follow_up_prompt_bn = "আপনি কোন ফসলে সার প্রয়োগের সঠিক নিয়ম জানতে চান? (যেমন ধান, আলু বা টমেটো)"
        elif intent_info["is_market"] and not detected_crop and not any(w in cleaned_query.lower() for w in ["সবজি", "শস্য", "ফসল", "সর্বশেষ"]):
            follow_up_prompt_bn = "আপনি কোন ফসলের বর্তমান মান্ডি বাজারদর জানতে চান? (যেমন ধান, আলু বা পাট)"
        elif has_image and not cleaned_query:
            follow_up_prompt_bn = "ছবিতে প্রদর্শিত ফসলটির বিষয়ে আপনি কী জানতে চান? (যেমন কোনো রোগ বা সেচের পরামর্শ)"

        # Step 5: Synthesize Final Answer (Selective LLM vs. Deterministic synthesis)
        # Decision rule: If query is simple and deterministic templates suffice, synthesize directly.
        # If query is a conversational follow-up or combines multiple tools, invoke Cohere LLM.
        is_follow_up = any(w in cleaned_query.lower() for w in ["তাহলে", "এখন কী করব", "উপায়", "আর কোনো", "কেন", "বলছ"])
        needs_llm = (is_follow_up or (len(tools_invoked) >= 2 and intent != "irrigation_weather" and cleaned_query)) and self.llm.is_available()

        final_answer_bn = ""
        llm_used = False
        provider = "deterministic_supervisor"

        if needs_llm:
            try:
                llm_prompt = self._build_llm_synthesis_prompt(
                    query=cleaned_query,
                    crop=detected_crop,
                    intent=intent,
                    tools_results=collected_results,
                    history=history,
                    follow_up=follow_up_prompt_bn
                )
                llm_res = await self.llm.generate_grounded_response(
                    prompt=llm_prompt,
                    system_instruction="আপনি 'ভাষাখেতি'র বৈজ্ঞানিক কৃষি সহায়ক। শুধুমাত্র যাচাইকৃত তথ্যের ভিত্তিতে উত্তর দিন।"
                )
                llm_text = llm_res.get("text", "")
                if llm_text and len(llm_text.strip()) > 20 and not llm_res.get("is_fallback", False):
                    final_answer_bn = llm_text.strip()
                    llm_used = True
                    provider = f"{self.llm.get_provider_name()}_supervisor"
            except Exception as e:
                logger.warning(f"LLM synthesis failed, falling back to deterministic template: {e}")

        if not final_answer_bn:
            final_answer_bn = self._build_deterministic_synthesis(
                query=cleaned_query,
                crop=detected_crop,
                intent=intent,
                tools_results=collected_results,
                follow_up=follow_up_prompt_bn
            )

        return SupervisorResponse(
            answer_bn=final_answer_bn,
            intent=intent,
            detected_crop=detected_crop,
            tools_invoked=tools_invoked,
            follow_up_prompt_bn=follow_up_prompt_bn,
            citations=unique_citations,
            safety_warnings=unique_warnings,
            llm_used=llm_used,
            provider=provider
        )

    def _build_llm_synthesis_prompt(
        self,
        query: str,
        crop: Optional[str],
        intent: str,
        tools_results: List[ToolResult],
        history: List[ChatTurn],
        follow_up: Optional[str]
    ) -> str:
        prompt_parts = [
            "আপনি 'ভাষাখেতি'র কৃষিবান্ধব, সহজ-সরল ও ব্যবহারিক কৃষি পরামর্শক।",
            "কঠোর নির্দেশাবলী:",
            "1. কৃষকের প্রশ্নের সরাসরি উত্তর দিন। অপ্রয়োজনীয় ভূমিকা বা কঠিন আবহাওয়া পরিভাষা বাদ দিন। 'কারণ / as / because' ব্যবহার করে সিদ্ধান্ত স্পষ্ট করুন।",
            "2. সেচ বা জল দেওয়ার ক্ষেত্রে আবহাওয়া এবং মাটির অবস্থা মিলিয়ে সিদ্ধান্ত দিন:",
            "   - ছবিতে মাটি ভেজা দেখালে: আগামী ১-২ দিনে বৃষ্টি না থাকলেও স্পষ্ট বলুন যে আজ সেচ দেওয়ার প্রয়োজন নেই কারণ মাটি ইতিমধ্যে ভেজা দেখাচ্ছে। নিশ্চিত হতে হাত দিয়ে ২-৩ ইঞ্চি গভীরে মাটি পরখ করতে বলুন।",
            "   - ছবিতে মাটি শুকনো দেখালে এবং বৃষ্টি না থাকলে: সেচ দিতে বলুন, তবে হাত দিয়ে মাটি পরখ করে পরিমিত জল দিতে বলুন।",
            "   - কোনো ছবি না থাকলে: মাটি শুকনো থাকলে সেচ দিতে বলুন এবং সেচের আগে হাত দিয়ে ২-৩ ইঞ্চি গভীরে আর্দ্রতা পরখ করতে বলুন।",
            "   - বৃষ্টিপাতের সম্ভাবনা থাকলে: সেচ দেওয়া বন্ধ রাখতে বলুন।",
            "3. প্রশ্ন বহির্ভূত কোনো সতর্কবার্তা বা অপ্রাসঙ্গিক মডেলের সীমাবদ্ধতার কথা বলবেন না।",
            "4. কৃষক যদি ইংরেজিতে প্রশ্ন করেন, তবে ইংরেজিতে সহজ সরাসরি উত্তর দিন এবং নিচে সহজ বাংলায় সিদ্ধান্ত দিন। বাংলায় প্রশ্ন করলে সহজ বাংলায় উত্তর দিন।",
            f"কৃষকের বর্তমান প্রশ্ন: {query}",
            f"চিহ্নিত ফসল: {crop or 'নির্দিষ্ট নেই'}"
        ]

        if history:
            prompt_parts.append("পূর্ববর্তী বার্তালাপের প্রাসঙ্গিক সূত্র:")
            for turn in history[-2:]:
                prompt_parts.append(f"- {turn.role}: {turn.content}")

        prompt_parts.append("যাচাইকৃত টুল ফলাফল:")
        for r in tools_results:
            if r.success:
                prompt_parts.append(f"[{r.tool_name}]: {r.data}")

        if follow_up:
            prompt_parts.append(f"প্রয়োজনীয় ফলো-আপ প্রশ্ন: {follow_up}")

        return "\n".join(prompt_parts)

    def _build_deterministic_synthesis(
        self,
        query: str,
        crop: Optional[str],
        intent: str,
        tools_results: List[ToolResult],
        follow_up: Optional[str]
    ) -> str:
        sections = []
        is_english = any('a' <= c.lower() <= 'z' for c in query) and not any('\u0980' <= c <= '\u09ff' for c in query)

        # Special focused handling for Irrigation & Weather Advice
        weather_result = next((r for r in tools_results if r.tool_name == "get_weather" and r.success), None)
        moist_result = next((r for r in tools_results if r.tool_name == "predict_soil_moisture" and r.success), None)

        if intent == "irrigation_weather" and weather_result:
            w_data = weather_result.data
            rain_48h = float(w_data.get("rain_next_48h_mm") or 0.0)
            prob_48h = int(w_data.get("max_rain_probability_48h") or 0)
            temp_c = w_data.get("current_temp_c", 31)
            desc_bn = w_data.get("weather_desc_bn", "পরিষ্কার আকাশ")
            desc_en = w_data.get("weather_desc_en", "Clear sky")

            crop_name_bn = f"{'ধান ' if crop == 'rice' else ''}জমিতে"
            crop_name_en = f"{crop + ' ' if crop else ''}field"

            # Rain forecast threshold (5mm or 50% probability)
            rain_expected = (rain_48h >= 5.0 or prob_48h >= 50)

            # Check soil moisture model output if image was provided
            has_soil_image = moist_result is not None
            soil_is_wet = False
            soil_is_dry = False
            if has_soil_image:
                pred = moist_result.data.get("primary_prediction", {})
                raw_label = str(pred.get("raw_class_name", "")).lower()
                disp_en = str(pred.get("display_name_en", "")).lower()
                disp_bn = str(pred.get("display_name_bn", "")).lower()
                soil_is_wet = ("wet" in raw_label) or ("moist" in raw_label) or ("wet" in disp_en) or ("ভেজা" in disp_bn) or ("আর্দ্র" in disp_bn)
                soil_is_dry = ("dry" in raw_label) or ("dry" in disp_en) or ("শুকনো" in disp_bn)

            # Case 1: Soil image provided and it looks WET -> DO NOT NEED TO IRRIGATE
            if has_soil_image and soil_is_wet:
                if is_english:
                    sections.append(
                        f"**You do not need to irrigate today.** The soil in your photo already looks wet/moist, "
                        f"and irrigation is not required ({desc_en}, {temp_c}°C).\n\n"
                        f"👉 **Practical Check:** To be sure, touch and feel the soil 2–3 inches deep with your hand. "
                        f"If it feels damp and holds together, hold off on watering.\n\n"
                        f"**সিদ্ধান্ত:** আজ {crop_name_bn} সেচ দেওয়ার প্রয়োজন নেই। ছবিতে মাটি ইতিমধ্যে ভেজা বা রসযুক্ত দেখাচ্ছে "
                        f"({desc_bn}, {temp_c}°C)।\n"
                        f"👉 **পরখ করুন:** নিশ্চিত হতে মাটির ২–৩ ইঞ্চি গভীরে হাত দিয়ে পরখ করে দেখুন। মাটি যদি এখনও ভিজে থাকে, তবে সেচ দেওয়া থেকে বিরত থাকুন।"
                    )
                else:
                    sections.append(
                        f"**সিদ্ধান্ত:** আজ {crop_name_bn} সেচ দেওয়ার প্রয়োজন নেই।\n"
                        f"ছবিতে মাটি ইতিমধ্যে ভেজা বা রসযুক্ত দেখাচ্ছে ({desc_bn}, {temp_c}°C)।\n\n"
                        f"👉 **মাটি পরখ করুন:** নিশ্চিত হওয়ার জন্য মাটির ২–৩ ইঞ্চি গভীরে হাত দিয়ে আর্দ্রতা পরখ করে দেখুন। "
                        f"মাটিতে পর্যাপ্ত রস থাকলে সেচ দেওয়া বন্ধ রাখুন।"
                    )

            # Case 2: Rain is expected in the next 1-2 days -> DO NOT IRRIGATE
            elif rain_expected:
                if is_english:
                    sections.append(
                        f"**Do not irrigate today.** Rain is expected in the next 1–2 days "
                        f"(Forecast: approx {rain_48h} mm rain, {prob_48h}% chance, {desc_en}). "
                        f"Let the natural rainfall water your crops to avoid waterlogging and root rot.\n\n"
                        f"👉 **Practical Check:** Touch and feel the soil 2–3 inches deep. Since rain is on the way, hold off on watering.\n\n"
                        f"**সিদ্ধান্ত:** আজ {crop_name_bn} সেচ দেওয়া বন্ধ রাখুন। আগামী ১–২ দিনে বৃষ্টিপাতের সম্ভাবনা রয়েছে "
                        f"(সম্ভাব্য বৃষ্টি: {rain_48h} মিমি, সম্ভাবনা: {prob_48h}%)। জমিতে অতিরিক্ত জল জমতে দেবেন না।\n"
                        f"👉 **পরখ করুন:** নিশ্চিত হতে মাটির ২–৩ ইঞ্চি গভীরে হাত দিয়ে আর্দ্রতা পরখ করে দেখুন।"
                    )
                else:
                    sections.append(
                        f"**সিদ্ধান্ত:** আজ {crop_name_bn} সেচ দেওয়া বন্ধ রাখুন।\n"
                        f"আগামী ১–২ দিনে বৃষ্টিপাতের সম্ভাবনা রয়েছে (সম্ভাব্য বৃষ্টি: {rain_48h} মিমি, সম্ভাবনা: {prob_48h}%)। "
                        f"অতিরিক্ত জল জমে শিকড় পচন এড়াতে বৃষ্টির জলের ওপর নির্ভর করুন।\n\n"
                        f"👉 **মাটি পরখ করুন:** নিশ্চিত হওয়ার জন্য মাটির ২–৩ ইঞ্চি গভীরে হাত দিয়ে আর্দ্রতা পরখ করে দেখুন।"
                    )

            # Case 3: No rain expected, and soil image looks DRY -> YES, IRRIGATE
            elif has_soil_image and soil_is_dry:
                if is_english:
                    sections.append(
                        f"**Yes, you can irrigate your {crop_name_en} today.** The soil surface looks dry, "
                        f"and there is no rain forecast for the next 1–2 days (0 mm expected, {desc_en}, {temp_c}°C).\n\n"
                        f"👉 **Practical Check:** Touch and feel the soil 2–3 inches beneath the surface to check moisture depth, and apply moderate watering.\n\n"
                        f"**সিদ্ধান্ত:** আজ {crop_name_bn} সেচ দিতে পারেন। মাটির উপরিভাগ শুকনো দেখাচ্ছে এবং আগামী ১–২ দিনে বৃষ্টির কোনো সম্ভাবনা নেই ({desc_bn}, {temp_c}°C)।\n"
                        f"👉 **মাটি পরখ করুন:** সেচ দেওয়ার পূর্বে মাটির ২–৩ ইঞ্চি গভীরে হাত দিয়ে পরখ করে পরিমিত জল দিন।"
                    )
                else:
                    sections.append(
                        f"**সিদ্ধান্ত:** আজ {crop_name_bn} সেচ দিতে পারেন।\n"
                        f"মাটির উপরিভাগ শুকনো দেখাচ্ছে এবং আগামী ১–২ দিনে (৪৮ ঘণ্টায়) বৃষ্টির কোনো সম্ভাবনা নেই ({desc_bn}, {temp_c}°C)।\n\n"
                        f"👉 **মাটি পরখ করুন:** সেচ দেওয়ার পূর্বে মাটির ২–৩ ইঞ্চি গভীরে হাত দিয়ে আর্দ্রতা পরখ করে পরিমিত জল দিন।"
                    )

            # Case 4: No rain expected, NO soil image provided -> IRRIGATE IF SOIL IS DRY, CONFIRM BY TOUCH
            else:
                if is_english:
                    sections.append(
                        f"**You can irrigate your {crop_name_en} today if the soil is dry**, "
                        f"as there is no rain forecast for the next 1–2 days (0 mm expected, {desc_en}, {temp_c}°C).\n\n"
                        f"👉 **Practical Check:** Before watering, touch and feel the soil 2–3 inches beneath the surface with your hand. "
                        f"If the soil is still wet or damp, do not irrigate yet.\n\n"
                        f"**সিদ্ধান্ত:** মাটি শুকনো থাকলে আজ {crop_name_bn} সেচ দিতে পারেন, কারণ আগামী ১–২ দিনে বৃষ্টির কোনো সম্ভাবনা নেই ({desc_bn}, {temp_c}°C)।\n"
                        f"👉 **মাটি পরখ করুন:** সেচ দেওয়ার আগে জমিতে মাটির ২–৩ ইঞ্চি গভীরে হাত দিয়ে পরখ করে নিশ্চিত হয়ে নিন। মাটি যদি ইতিমধ্যে ভেজা থাকে, তবে আজ সেচ দেওয়ার প্রয়োজন নেই।"
                    )
                else:
                    sections.append(
                        f"**সিদ্ধান্ত:** মাটি শুকনো থাকলে আজ {crop_name_bn} সেচ দিতে পারেন, কারণ আগামী ১–২ দিনে (৪৮ ঘণ্টায়) বৃষ্টির কোনো সম্ভাবনা নেই ({desc_bn}, {temp_c}°C)।\n\n"
                        f"👉 **মাটি পরখ করুন:** সেচ দেওয়ার আগে জমিতে মাটির ২–৩ ইঞ্চি গভীরে হাত দিয়ে পরখ করে নিশ্চিত হয়ে নিন। মাটি যদি ইতিমধ্যে ভেজা থাকে, তবে আজ সেচ দেওয়ার প্রয়োজন নেই।"
                    )

            if follow_up:
                sections.append(f"**প্রয়োজনীয় তথ্য:** {follow_up}")
            return "\n\n".join(sections)

        # Process each tool result for other intents
        for r in tools_results:
            if not r.success:
                continue

            if r.tool_name == "predict_plant_disease":
                primary = r.data.get("primary_prediction", {})
                name_bn = primary.get("display_name_bn", "অজানা রোগ")
                score = round(primary.get("model_score", 0) * 100, 1)
                sections.append(
                    f"**গাছের পাতার মডেল ফলাফল:**\n"
                    f"আপনার আপলোড করা পাতার ছবিতে **{name_bn}**-এর লক্ষণ শনাক্ত হয়েছে (সম্ভাব্যতা: {score}%)।"
                )

            elif r.tool_name == "predict_soil_type":
                primary = r.data.get("primary_prediction", {})
                sections.append(
                    f"**মাটির ধরন বিশ্লেষণ:**\n"
                    f"ছবিতে মাটির বাহ্যিক ধরন **{primary.get('display_name_bn', 'অজানা')}** হিসেবে পরিলক্ষিত হয়েছে।"
                )

            elif r.tool_name == "predict_soil_moisture":
                primary = r.data.get("primary_prediction", {})
                sections.append(
                    f"**মাটির আর্দ্রতা অবস্থা:**\n"
                    f"মাটির উপরিভাগের দৃশ্যমান আর্দ্রতা: **{primary.get('display_name_bn', 'স্বাভাবিক')}**।"
                )

            elif r.tool_name == "get_weather":
                data = r.data
                sections.append(
                    f"**আবহাওয়া পর্যবেক্ষণ:**\n"
                    f"বর্তমান অবস্থা {data.get('weather_desc_bn')}, তাপমাত্রা {data.get('current_temp_c')}°C। "
                    f"আগামী ৪৮ ঘণ্টায় বৃষ্টির সম্ভাবনা: {data.get('max_rain_probability_48h')}% "
                    f"(সম্ভাব্য বৃষ্টি: {data.get('rain_next_48h_mm')} মিমি)।"
                )

            elif r.tool_name == "search_market_prices":
                prices = r.data.get("prices", [])
                if prices:
                    if is_english:
                        p_lines = [f"**West Bengal Mandi Market Prices (AGMARKNET):**"]
                        for p in prices[:3]:
                            p_lines.append(
                                f"• {p.get('commodity_name_en', p['commodity_name_bn'])} ({p.get('market_name_en', p['market_name_bn'])}, {p.get('district_en', p['district_bn'])}): "
                                f"Modal wholesale price ₹{p['modal_price']}/Quintal (~₹{p['modal_price_per_kg']}/kg) "
                                f"[Date: {p['reported_date']}]."
                            )
                        p_lines.append("\n**পশ্চিমবঙ্গ মান্ডি বাজারদর (AGMARKNET):**")
                        for p in prices[:3]:
                            p_lines.append(
                                f"• {p['commodity_name_bn']} ({p['market_name_bn']}, {p['district_bn']}): "
                                f"গড় পাইকারি দর ₹{p['modal_price']}/কুইন্টাল (প্রতি কেজি প্রায় ₹{p['modal_price_per_kg']}) "
                                f"[তারিখ: {p['reported_date']}]."
                            )
                    else:
                        p_lines = [f"**পশ্চিমবঙ্গ মান্ডি বাজারদর (AGMARKNET):**"]
                        for p in prices[:3]:
                            p_lines.append(
                                f"• {p['commodity_name_bn']} ({p['market_name_bn']}, {p['district_bn']}): "
                                f"গড় পাইকারি দর ₹{p['modal_price']}/কুইন্টাল (প্রতি কেজি প্রায় ₹{p['modal_price_per_kg']}) "
                                f"[তারিখ: {p['reported_date']}]."
                            )
                    sections.append("\n".join(p_lines))

            elif r.tool_name == "search_government_schemes":
                schemes = r.data.get("schemes", [])
                if schemes:
                    s_lines = [f"**প্রাসঙ্গিক সরকারি কৃষক কল্যাণ প্রকল্প:**"]
                    for s in schemes[:2]:
                        s_lines.append(f"• **{s['name_bn']}** ({s['authority_bn']}): {s['summary_bn']}")
                    sections.append("\n".join(s_lines))

            elif r.tool_name == "retrieve_agricultural_knowledge":
                docs = r.data.get("results", [])
                if docs:
                    d_lines = [f"**যাচাইকৃত কৃষি বিজ্ঞান নির্দেশিকা (ICAR/KVK):**"]
                    for d in docs[:2]:
                        d_lines.append(f"• {d['title_bn']}: {d['content_bn']}")
                    sections.append("\n".join(d_lines))

        # Check if query asks for seasonal crop recommendation on soil
        has_soil_tool = any(r.tool_name in ["predict_soil_type", "predict_soil_moisture"] for r in tools_results)
        if has_soil_tool and any(w in query.lower() for w in ["কী চাষ", "কী ফসল", "কী লাগাব", "চাষ করব", "চাষ", "ফসল", "লাগানো"]):
            sections.append(
                "**রবি মরশুমি ফসল বপন নির্দেশিকা (অক্টোবর-নভেম্বর):**\n"
                "• বর্তমান রবি মরশুমে উপযুক্ত আর্দ্রতাযুক্ত দোআঁশ বা এঁটেল মাটিতে **আলু (কুফরি জ্যোতি/পোখরাজ)**, **সরিষা**, **বাঁধাকপি**, **ফুলকপি** এবং **রবি ডাল (মসুর/মুগ)** চাষের জন্য শ্রেষ্ঠ সময়।\n"
                "• জমি তৈরির সময় বিঘাপ্রতি পর্যাপ্ত জৈব কম্পোস্ট বা পচা গোবর সার প্রয়োগ করুন এবং মাটির জো বুঝে বীজ বপন করুন।"
            )

        if follow_up:
            sections.append(f"**প্রয়োজনীয় তথ্য:** {follow_up}")

        if not sections:
            return (
                "আপনার প্রশ্নটি ভাষাখেতি সুপারভাইজার গ্রহণ করেছে। আরও নিখুঁত পরামর্শের জন্য অনুগ্রহ করে "
                "ফসলের সঠিক নাম (যেমন ধান, আলু বা টমেটো) উল্লেখ করুন অথবা আক্রান্ত অংশ/মাটির ছবি যুক্ত করুন।"
            )

        return "\n\n".join(sections)


supervisor_service = SupervisorOrchestrator()
