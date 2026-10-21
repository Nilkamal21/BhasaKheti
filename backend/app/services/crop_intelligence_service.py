"""
Crop Intelligence & Context-Aware Orchestration Service for BhashaKheti.
Coordinates:
1. Intent & Context Extraction (Crop, Soil, Weather/Irrigation, Plant health)
2. Interactive Clarification Prompts (Asks farmer for missing crop name, soil photo, etc.)
3. Intelligent Tool Selection (Weather tool for watering, Knowledge base for advice, Disease/Soil models if photos supplied)
4. Strict Agricultural Safety & Boundary Guard (Prevents overwatering, model misuse on rice, fake chemical doses)
5. Cohere LLM Generation with Grounded Evidence + Deterministic Fallback
"""

from typing import Dict, Any, List, Optional
from app.core.logging import logger
from app.services.knowledge_service import knowledge_service
from app.services.weather_service import weather_service
from app.services.market_service import market_service, DISCLAIMER_FARM_GATE_BN
from app.services.scheme_service import scheme_service, PRELIMINARY_ASSESSMENT_NOTICE_BN
from app.services.safety_validator import (
    safety_validator,
    STATUTORY_CHEMICAL_DISCLAIMER_BN,
    RICE_MODEL_BOUNDARY_WARNING_BN
)
from app.services.llm import get_llm_provider


SYSTEM_PROMPT_BN = (
    "আপনি 'ভাষাখেতি' (BhasaKheti)-র একজন বিশ্বস্ত, সহানুভূতিশীল ও বৈজ্ঞানিক কৃষি সহায়ক। "
    "পশ্চিমবঙ্গের কৃষকদের জন্য আপনি কাজ করছেন।\n\n"
    "নিয়মাবলী কঠোরভাবে মেনে চলুন:\n"
    "১. প্রদত্ত যাচাইকৃত তথ্যের (verified agricultural documents) এবং আবহাওয়া উপাত্তের বাইরে কোনো মনগড়া তথ্য বলবেন না।\n"
    "২. কখনোই কোনো কাল্পনিক কীটনাশকের নাম, মাত্রা, ডোজ বা ককটেল মিশ্রণের প্রেসক্রিপশন তৈরি করবেন না।\n"
    "৩. কোনো গুরুত্বপূর্ণ তথ্য না থাকলে সরাসরি সংক্ষেপে জিজ্ঞাসা করুন (যেমন ফসলের নাম বা মাটির ধরন)।\n"
    "৪. সেচের প্রশ্নে আবহাওয়ার বৃষ্টিপাতের পূর্বাভাস ও অতিরিক্ত সেচের (Overwatering) ঝুঁকি বিবেচনা করে সতর্ক পরামর্শ দিন।\n"
    "৫. অত্যন্ত সহজ, স্পষ্ট এবং শ্রদ্ধাশীল বাংলা ভাষায় সংক্ষিপ্ত ও কর্মোপযোগী (actionable) উত্তর দিন।"
)


class CropIntelligenceService:
    """Orchestrates multi-modal tools, contextual inquiry, and LLM reasoning."""

    def __init__(self):
        self.llm = get_llm_provider()

    def analyze_intent_and_context(
        self,
        query: str,
        crop: Optional[str] = None,
        has_leaf_image: bool = False,
        has_soil_image: bool = False
    ) -> Dict[str, Any]:
        """Classifies farmer intent and detects missing essential context."""
        lower_q = query.lower()

        # Crop detection if not passed explicitly
        detected_crop = crop
        if not detected_crop:
            if any(w in lower_q for w in ["ধান", "rice", "paddy", "আমন", "বোরো"]):
                detected_crop = "rice"
            elif any(w in lower_q for w in ["আলু", "potato", "আলুর"]):
                detected_crop = "potato"
            elif any(w in lower_q for w in ["টমেটো", "tomato", "টমেটোর"]):
                detected_crop = "tomato"
            elif any(w in lower_q for w in ["ক্যাপসিকাম", "লঙ্কা", "মরিচ", "chilli", "pepper"]):
                detected_crop = "bell_pepper"

        # Intent classification
        is_market = any(w in lower_q for w in ["বাজারদর", "বাজার দর", "দাম", "দর", "রেট", "মূল্য", "মন্ডি", "মার্কেট", "price", "rate", "market", "mandi"])
        is_scheme = any(w in lower_q for w in ["প্রকল্প", "সরকারি", "ভর্তুকি", "অনুদান", "কৃষক বন্ধু", "বিমা", "লোন", "ঋণ", "সাহায্য", "টাকা দেয়", "scheme", "subsidy", "pm-kisan", "kcc"])
        is_irrigation = any(w in lower_q for w in ["জল", "সেচ", "পানি", "ভিজানো", "water", "irrigation", "আজ কি সেচ দেব", "বৃষ্টি"])
        is_fertilizer = any(w in lower_q for w in ["সার", "ইউরিয়া", "পটাশ", "ডিএপি", "পুষ্টি", "fertilizer", "nutrient", "খাবার"])
        is_disease = any(w in lower_q for w in ["দাগ", "রোগ", "পচা", "ধসা", "পোকা", "হলুদ", "কুঁকড়ে", "disease", "blight", "curl", "spot"])
        is_soil = any(w in lower_q for w in ["মাটি", "পলি", "ল্যাটেরাইট", "বেলে", "soil"])

        intent = "general_guidance"
        if is_market:
            intent = "market_intelligence"
        elif is_scheme:
            intent = "government_schemes"
        elif is_irrigation:
            intent = "irrigation_weather"
        elif is_fertilizer:
            intent = "fertilizer_soil"
        elif is_disease:
            intent = "plant_health"
        elif is_soil:
            intent = "soil_management"

        # Missing context detection
        missing_context = []
        clarification_prompt_bn = None

        if is_fertilizer and not detected_crop:
            missing_context.append("crop_name")
            clarification_prompt_bn = (
                "আপনি কোন ফসলে সার প্রয়োগ করতে চান? ফসলের সঠিক নাম (যেমন ধান, আলু বা টমেটো) জানালে "
                "অনুমোদিত মাত্রায় সুষম সার প্রয়োগের সঠিক পরামর্শ দেওয়া সম্ভব।"
            )
        elif is_market and not detected_crop and not any(w in lower_q for w in ["সবজি", "শস্য", "ফসল", "সর্বশেষ", "তালিকা"]):
            missing_context.append("crop_name")
            clarification_prompt_bn = (
                "আপনি কোন ফসলের বাজারদর জানতে চান? যেমন ধান, আলু, টমেটো, পাট বা সরিষা জানালে সংশ্লিষ্ট মন্ডির সঠিক দর প্রদর্শন করা যাবে।"
            )
        elif is_disease and not has_leaf_image and detected_crop in ["tomato", "potato", "bell_pepper"]:
            missing_context.append("leaf_image_optional")

        return {
            "intent": intent,
            "crop": detected_crop,
            "is_market": is_market,
            "is_scheme": is_scheme,
            "is_irrigation": is_irrigation,
            "is_fertilizer": is_fertilizer,
            "is_disease": is_disease,
            "missing_context": missing_context,
            "clarification_prompt_bn": clarification_prompt_bn
        }

    async def get_weather_context(self, lat: float = 23.23, lon: float = 87.86) -> Dict[str, Any]:
        """Fetches live weather conditions and rainfall analysis."""
        try:
            weather_data = await weather_service.get_forecast(latitude=lat, longitude=lon)
            curr = weather_data.get("current_conditions", {})
            daily = weather_data.get("daily_forecast", [])

            rain_next_48h_mm = 0.0
            max_prob_next_48h = 0
            if len(daily) >= 2:
                rain_next_48h_mm = (daily[0].get("precipitation_sum_mm") or 0.0) + (daily[1].get("precipitation_sum_mm") or 0.0)
                max_prob_next_48h = max(daily[0].get("precipitation_probability_pct") or 0, daily[1].get("precipitation_probability_pct") or 0)

            return {
                "available": True,
                "current_temp_c": curr.get("temperature_c"),
                "current_humidity": curr.get("relative_humidity_pct"),
                "current_rain_mm": curr.get("precipitation_mm", 0.0),
                "weather_desc_bn": curr.get("weather_desc_bn", ""),
                "rain_next_48h_mm": round(rain_next_48h_mm, 1),
                "max_rain_probability_48h": max_prob_next_48h,
                "advisory_notes_bn": weather_data.get("agricultural_advisory", {}).get("advisory_notes_bn", [])
            }
        except Exception as exc:
            logger.warning(f"Weather context retrieval failed: {exc}")
            return {"available": False}

    async def orchestrate(
        self,
        query: str,
        crop: Optional[str] = None,
        latitude: float = 23.23,
        longitude: float = 87.86,
        leaf_disease_prediction: Optional[Dict[str, Any]] = None,
        soil_type_prediction: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Executes the full crop intelligence workflow."""
        cleaned_query = query.strip()
        context_analysis = self.analyze_intent_and_context(
            query=cleaned_query,
            crop=crop,
            has_leaf_image=bool(leaf_disease_prediction),
            has_soil_image=bool(soil_type_prediction)
        )

        detected_crop = context_analysis["crop"]
        intent = context_analysis["intent"]

        # Tool 1: Safety & Boundary Check
        boundary_warnings = safety_validator.check_query_boundaries(cleaned_query, detected_crop)

        # Tool 2: Knowledge Retrieval
        kb_results = knowledge_service.search(cleaned_query, crop=detected_crop, limit=3)
        retrieved_docs = kb_results.get("results", [])

        # Tool 3: Weather Analysis (Active when query involves irrigation/water/today's conditions)
        weather_ctx = {}
        if context_analysis["is_irrigation"] or "আবহাওয়া" in cleaned_query:
            weather_ctx = await self.get_weather_context(lat=latitude, lon=longitude)

        # Tool 4: Market Price Discovery (Active when query asks for market rates/prices)
        market_matches = []
        if context_analysis["is_market"]:
            m_res = market_service.search_prices(commodity=detected_crop, query=cleaned_query, limit=3)
            market_matches = m_res.get("prices", [])

        # Tool 5: Government Schemes Discovery (Active when query asks for schemes/subsidies)
        scheme_matches = []
        if context_analysis["is_scheme"]:
            s_res = scheme_service.get_schemes(query=cleaned_query, limit=3)
            scheme_matches = s_res.get("schemes", [])

        # Check if urgent clarification is required before advice
        if (
            context_analysis["missing_context"]
            and not retrieved_docs
            and not weather_ctx.get("available")
            and not market_matches
            and not scheme_matches
        ):
            return {
                "answer_bn": context_analysis["clarification_prompt_bn"],
                "intent": intent,
                "crop": detected_crop,
                "missing_context": context_analysis["missing_context"],
                "citations": [],
                "weather_summary": None,
                "safety_warnings": boundary_warnings,
                "llm_used": False,
                "provider": "deterministic_clarifier"
            }

        # Build Synthesis Context for LLM / Deterministic Generator
        prompt_parts = [
            f"কৃষকের প্রশ্ন: {cleaned_query}",
            f"চিহ্নিত ফসল: {detected_crop or 'নির্দিষ্ট করা নেই'}",
            f"চিহ্নিত উদ্দেশ্য: {intent}"
        ]

        if market_matches:
            prompt_parts.append("যাচাইকৃত মান্ডি বাজারদর উপাত্ত (AGMARKNET):")
            for m in market_matches:
                prompt_parts.append(
                    f"- {m['commodity_name_bn']} ({m['market_name_bn']}, {m['district_bn']}): "
                    f"মডেল দর ₹{m['modal_price']} / কুইন্টাল (প্রতি কেজি ₹{m['modal_price_per_kg']}), "
                    f"সর্বনিম্ন ₹{m['min_price']}, সর্বোচ্চ ₹{m['max_price']}, তারিখ: {m['reported_date']}."
                )

        if scheme_matches:
            prompt_parts.append("যাচাইকৃত সরকারি কৃষি প্রকল্প তথ্য:")
            for s in scheme_matches:
                prompt_parts.append(
                    f"- {s['name_bn']} ({s['authority_bn']}): {s['summary_bn']} সুবিধা: {s['benefits_bn']}"
                )

        if weather_ctx.get("available"):
            prompt_parts.append(
                f"স্থানীয় আবহাওয়া: বর্তমান অবস্থা {weather_ctx['weather_desc_bn']}, "
                f"তাপমাত্রা {weather_ctx['current_temp_c']}°C, আর্দ্রতা {weather_ctx['current_humidity']}%, "
                f"আগামী ৪৮ ঘণ্টায় সম্ভাব্য মোট বৃষ্টিপাত: {weather_ctx['rain_next_48h_mm']} মিমি "
                f"(সর্বোচ্চ বৃষ্টির সম্ভাবনা: {weather_ctx['max_rain_probability_48h']}%)."
            )

        if leaf_disease_prediction:
            primary = leaf_disease_prediction.get("primary_prediction", {})
            prompt_parts.append(
                f"পাতার ছবির মডেল ফলাফল: {primary.get('display_name_bn')} "
                f"({primary.get('display_name_en')}), সম্ভাব্যতা: {round(primary.get('model_score', 0) * 100, 1)}%."
            )

        if soil_type_prediction:
            primary_soil = soil_type_prediction.get("primary_prediction", {})
            prompt_parts.append(
                f"মাটির ছবির মডেল ফলাফল: {primary_soil.get('display_name_bn')} "
                f"({primary_soil.get('display_name_en')})."
            )

        prompt_str = "\n".join(prompt_parts)

        # Attempt Grounded LLM Response with Cohere
        final_answer_bn = ""
        llm_used = False
        provider_name = "deterministic_fallback"

        if self.llm.is_available():
            try:
                llm_res = await self.llm.generate_grounded_response(
                    prompt=prompt_str,
                    system_instruction=SYSTEM_PROMPT_BN,
                    context_documents=retrieved_docs
                )
                final_answer_bn = llm_res.get("text", "")
                llm_used = True
                provider_name = self.llm.get_provider_name()
            except Exception as exc:
                logger.warning(f"LLM generation failed, switching to deterministic fallback: {exc}")
                llm_used = False

        # Deterministic Fallback Synthesis
        if not final_answer_bn:
            final_answer_bn = self._generate_deterministic_fallback(
                query=cleaned_query,
                crop=detected_crop,
                intent=intent,
                retrieved_docs=retrieved_docs,
                weather_ctx=weather_ctx,
                leaf_disease_pred=leaf_disease_prediction,
                soil_type_pred=soil_type_prediction,
                market_matches=market_matches,
                scheme_matches=scheme_matches
            )
            provider_name = "deterministic_fallback"

        # Format Citations & Provenance
        citations = []
        has_chemical_advice = False
        for doc in retrieved_docs:
            citations.append({
                "id": doc.get("id"),
                "title_bn": doc.get("title_bn"),
                "title_en": doc.get("title_en"),
                "source_org": doc.get("source_org"),
                "source_url": doc.get("source_url"),
                "last_verified_date": doc.get("last_verified_date")
            })
            if doc.get("chemical_control_permitted"):
                has_chemical_advice = True

        for m in market_matches:
            citations.append({
                "id": m.get("id"),
                "title_bn": f"{m.get('commodity_name_bn')} বাজারদর ({m.get('market_name_bn')})",
                "title_en": f"{m.get('commodity_name_en')} Price ({m.get('market_name_en')})",
                "source_org": m.get("source_name", "AGMARKNET"),
                "source_url": m.get("source_url", "https://agmarknet.gov.in"),
                "last_verified_date": m.get("reported_date")
            })

        for s in scheme_matches:
            citations.append({
                "id": s.get("id"),
                "title_bn": s.get("name_bn"),
                "title_en": s.get("name_en"),
                "source_org": s.get("authority_bn"),
                "source_url": s.get("official_portal_url"),
                "last_verified_date": s.get("verification_date")
            })

        # Append Statutory Warning if Chemical is Mentioned
        if has_chemical_advice and STATUTORY_CHEMICAL_DISCLAIMER_BN not in boundary_warnings:
            boundary_warnings.append(STATUTORY_CHEMICAL_DISCLAIMER_BN)

        return {
            "answer_bn": final_answer_bn,
            "intent": intent,
            "crop": detected_crop,
            "missing_context": context_analysis["missing_context"],
            "citations": citations,
            "weather_summary": weather_ctx if weather_ctx.get("available") else None,
            "safety_warnings": boundary_warnings,
            "llm_used": llm_used,
            "provider": provider_name
        }

    def _generate_deterministic_fallback(
        self,
        query: str,
        crop: Optional[str],
        intent: str,
        retrieved_docs: List[Dict[str, Any]],
        weather_ctx: Dict[str, Any],
        leaf_disease_pred: Optional[Dict[str, Any]],
        soil_type_pred: Optional[Dict[str, Any]],
        market_matches: Optional[List[Dict[str, Any]]] = None,
        scheme_matches: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Constructs an evidence-backed Bengali answer without requiring an external LLM."""
        sections = []

        # 1. Market Price Intelligence
        if market_matches:
            sections.append("💰 **যাচাইকৃত মান্ডি বাজারদর (AGMARKNET):**")
            for m in market_matches:
                sections.append(
                    f"• **{m['commodity_name_bn']}** ({m['market_name_bn']}, {m['district_bn']}):\n"
                    f"  - গড় পাইকারি দর (Modal): **₹{m['modal_price']} / কুইন্টাল** (প্রতি কেজি প্রায় **₹{m['modal_price_per_kg']}**)\n"
                    f"  - ওঠানামা পরিসর: সর্বনিম্ন ₹{m['min_price']} - সর্বোচ্চ ₹{m['max_price']} / কুইন্টাল\n"
                    f"  - রিপোর্টের তারিখ: {m['reported_date']} | অবস্থা: {'ঐতিহাসিক তথ্য' if m.get('is_historical') else 'সাম্প্রতিক দর'}"
                )
            sections.append(f"ℹ️ *{DISCLAIMER_FARM_GATE_BN}*")

        # 2. Government Schemes Discovery
        if scheme_matches:
            sections.append("🏛️ **প্রযোজ্য সরকারি কৃষি সহায়তা প্রকল্প:**")
            for s in scheme_matches:
                sections.append(
                    f"• **{s['name_bn']}** ({s['authority_bn']}):\n"
                    f"  - মূল সুবিধা: {s['summary_bn']}\n"
                    f"  - আবেদনের যোগ্যতা: {s['eligibility_bn'].splitlines()[0] if s.get('eligibility_bn') else 'যোগ্যতা যাচাই সাপেক্ষ'}\n"
                    f"  - বর্তমান অবস্থা: {s.get('status_bn', 'চলমান')} | অফিসিয়াল পোর্টাল: {s['official_portal_url']}"
                )
            sections.append(f"ℹ️ *{PRELIMINARY_ASSESSMENT_NOTICE_BN}*")

        # 3. Irrigation / Weather Advice
        if intent == "irrigation_weather" and weather_ctx.get("available"):
            rain_48h = weather_ctx.get("rain_next_48h_mm", 0.0)
            prob_48h = weather_ctx.get("max_rain_probability_48h", 0)

            sections.append("💧 **সেচ ও আবহাওয়া ভিত্তিক পরামর্শ:**")
            if rain_48h >= 5.0 or prob_48h >= 60:
                sections.append(
                    f"আগামী ৪৮ ঘণ্টায় মোট প্রায় {rain_48h} মিমি বৃষ্টিপাতের সম্ভাবনা রয়েছে (সম্ভাবনা {prob_48h}%)। "
                    f"জমিতে অতিরিক্ত জল জমে শিকড় পচন (Root rot) বা জলাবদ্ধতা এড়াতে **আজ জমিতে সেচ দেওয়া বন্ধ রাখুন** "
                    f"এবং নিষ্কাশন নালা পরিষ্কার রাখুন।"
                )
            else:
                sections.append(
                    f"বর্তমানে আবহাওয়া {weather_ctx.get('weather_desc_bn')} এবং আগামী ৪৮ ঘণ্টায় ভারী বৃষ্টির সম্ভাবনা কম। "
                    f"মাটির আর্দ্রতা পরীক্ষা করে প্রয়োজন অনুসারে পরিমিত সেচ দিতে পারেন।"
                )

        # 2. Disease / Leaf Image Advice
        if leaf_disease_pred:
            prim = leaf_disease_pred.get("primary_prediction", {})
            sections.append(
                f"🌿 **পাতার ছবি বিশ্লেষণ:**\n"
                f"সম্ভাব্য রোগ: **{prim.get('display_name_bn')}** ({prim.get('display_name_en')})। "
                f"সতর্কতা: এটি প্রাথমিক কৃত্রিম বুদ্ধিমত্তা ভিত্তিক অনুমান; নিশ্চিত তথ্যের জন্য নিকটস্থ কেভিকে (KVK) বিশেষজ্ঞদের সাথে যোগাযোগ করুন।"
            )

        # 3. Soil Image Advice
        if soil_type_pred:
            prim_soil = soil_type_pred.get("primary_prediction", {})
            sections.append(
                f"🌱 **মাটির ধরন বিশ্লেষণ:**\n"
                f"শনাক্তকৃত ধরন: **{prim_soil.get('display_name_bn')}** ({prim_soil.get('display_name_en')})। "
                f"স্মরণে রাখবেন, ছবির সাহায্যে মাটির সুনির্দিষ্ট উর্বরতা বা পিএইচ (pH) জানা যায় না।"
            )

        # 4. Verified Knowledge Guidelines
        if retrieved_docs:
            primary_doc = retrieved_docs[0]
            sections.append(f"\n📖 **{primary_doc.get('title_bn')}** ({primary_doc.get('source_org')}):")
            sections.append(primary_doc.get("content_bn", ""))
            if primary_doc.get("safety_notes_bn"):
                sections.append(f"\n⚠️ **সুরক্ষা নির্দেশনা:** {primary_doc.get('safety_notes_bn')}")
        elif not sections:
            sections.append(
                "আমাদের যাচাইকৃত তথ্যভাণ্ডারে এই প্রশ্নের সরাসরি নির্ভরযোগ্য তথ্য পাওয়া যায়নি। "
                "কৃষকের সুরক্ষার্থে কোনো অনুমাননির্ভর তথ্য দেওয়া হচ্ছে না। আপনার ব্লকের কৃষি সহায়ক কেন্দ্র "
                "(KPS/ADA) অথবা নিকটস্থ কৃষি বিজ্ঞান কেন্দ্রে (KVK) যোগাযোগ করুন।"
            )

        return "\n\n".join(sections)


crop_intelligence_service = CropIntelligenceService()
