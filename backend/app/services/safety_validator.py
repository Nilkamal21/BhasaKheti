"""
Agricultural Safety & Validation Engine for BhashaKheti.
Enforces strict programmatic safety rules to protect farmers from:
1. Unverified or fabricated pesticide dosages and chemical mixtures
2. Misuse of the 15-class disease model on unsupported crops (e.g., Rice)
3. False certainty regarding soil pH/NPK or root-zone moisture
4. Fabricated responses when evidence is insufficient
"""

from typing import Dict, Any, List, Optional
from app.core.logging import logger

STATUTORY_CHEMICAL_DISCLAIMER_BN = (
    "সতর্কতা: যেকোনো রাসায়নিক বালাইনাশক ব্যবহারের পূর্বে আপনার ব্লকের সহ-কৃষি নির্দেশক (ADA) "
    "অথবা কৃষি প্রযুক্তি সহায়ক (KPS)-এর পরামর্শ নিন। প্যাকেটের লেবেলে উল্লেখিত নির্দেশিকা ও "
    "অপেক্ষমাণ সময় (Waiting Period) কঠোরভাবে মেনে চলুন। অযথা বা অননুমোদিত কীটনাশক প্রয়োগ করবেন না।"
)

STATUTORY_CHEMICAL_DISCLAIMER_EN = (
    "Caution: Always consult your local Assistant Director of Agriculture (ADA) or Krishi "
    "Prajukti Sahayak (KPS) before applying any chemical pesticides. Strictly adhere to label dosage "
    "and pre-harvest waiting periods. Avoid unauthorized or indiscriminate chemical use."
)

RICE_MODEL_BOUNDARY_WARNING_BN = (
    "গুরুত্বপূর্ণ সতর্কতা: বর্তমান ভাষাখেতি রোগ শনাক্তকরণ মডেলটি শুধুমাত্র টমেটো, আলু এবং "
    "ক্যাপসিকামের পাতার রোগ শনাক্তকরণের জন্য প্রশিক্ষিত। ধানের রোগ শনাক্তকরণে এই মডেলটি কার্যকর নয়। "
    "ধানের সমস্যার ক্ষেত্রে উল্লেখিত আইসিএআর (ICAR-NRRI) নির্দেশিকা অনুসরণ করুন অথবা স্থানীয় কৃষি আধিকারিকের সাথে যোগাযোগ করুন।"
)

RICE_MODEL_BOUNDARY_WARNING_EN = (
    "Important Notice: The current BhashaKheti disease classification model is trained exclusively "
    "for tomato, potato, and bell pepper. It cannot be used to diagnose rice diseases. For rice problems, "
    "refer to verified ICAR-NRRI guidance or consult local agricultural officers."
)

SOIL_MODEL_BOUNDARY_DISCLAIMER_BN = (
    "মাটির ছবি দেখে কেবল বাহ্যিক ধরন শ্রেণিবিন্যাস করা সম্ভব; এতে সুনির্দিষ্ট পিএইচ (pH) বা "
    "এনপিকে (NPK) মাত্রা জানা যায় না। সুষম সার প্রয়োগের জন্য মাটি পরীক্ষা (Soil Health Card) করান।"
)

MOISTURE_MODEL_BOUNDARY_DISCLAIMER_BN = (
    "মাটির উপরিভাগের ছবি শিকড়ের গভীরে প্রকৃত আর্দ্রতা নির্দেশ করে না। সেচ দেওয়ার পূর্বে মাটির "
    "১৫ সেমি গভীরে আর্দ্রতা হাত দিয়ে যাচাই করুন।"
)

INSUFFICIENT_EVIDENCE_NOTICE_BN = (
    "আমাদের যাচাইকৃত তথ্যভাণ্ডারে এই বিষয়ে পর্যাপ্ত নির্ভরযোগ্য তথ্য পাওয়া যায়নি। কৃষকের সুরক্ষার্থে "
    "কোনো অনুমাননির্ভর বা অপ্রমাণিত পরামর্শ প্রদান করা হচ্ছে না। অনুগ্রহ করে সঠিক নির্দেশনার জন্য নিকটস্থ "
    "কৃষি প্রযুক্তি সহায়ক (KPS) অথবা জেলা কৃষি বিজ্ঞান কেন্দ্রে (KVK) যোগাযোগ করুন।"
)

INSUFFICIENT_EVIDENCE_NOTICE_EN = (
    "Insufficient verified evidence found in our agricultural knowledge base. To ensure farmer safety, "
    "no speculative or unverified advice is provided. Please contact your nearest Krishi Prajukti "
    "Sahayak (KPS) or district Krishi Vigyan Kendra (KVK)."
)


class AgriculturalSafetyValidator:
    """Enforces evidence verification, safety warnings, and boundary constraints."""

    @staticmethod
    def validate_record_safety(record: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures knowledge records preserve citations, provenance, and mandatory warnings."""
        validated = dict(record)

        # 1. Chemical control validation
        if validated.get("chemical_control_permitted"):
            # Ensure statutory disclaimer is explicitly present
            if STATUTORY_CHEMICAL_DISCLAIMER_BN not in validated.get("safety_notes_bn", ""):
                validated["safety_notes_bn"] = (
                    f"{validated.get('safety_notes_bn', '')}\n\n{STATUTORY_CHEMICAL_DISCLAIMER_BN}".strip()
                )
            if STATUTORY_CHEMICAL_DISCLAIMER_EN not in validated.get("safety_notes_en", ""):
                validated["safety_notes_en"] = (
                    f"{validated.get('safety_notes_en', '')}\n\n{STATUTORY_CHEMICAL_DISCLAIMER_EN}".strip()
                )
        else:
            # If chemical control is not permitted or unverified, flag non-chemical cultural approach
            validated["chemical_control_permitted"] = False

        # 2. Evidence status verification
        if not validated.get("evidence_status"):
            validated["evidence_status"] = "unverified"

        # 3. Provenance preservation check
        if not validated.get("source_org") or not validated.get("source_url"):
            validated["evidence_status"] = "provisional"
            logger.warning(f"Record {validated.get('id')} lacks complete source organization or URL.")

        return validated

    @staticmethod
    def check_query_boundaries(query: str, crop: Optional[str] = None) -> List[str]:
        """Detects if query involves unsupported model boundaries or high-risk assumptions."""
        warnings = []
        lower_query = query.lower()
        is_rice = (crop == "rice") or any(w in lower_query for w in ["ধান", "rice", "paddy", "আমন", "বোরো"])
        is_disease_model = any(w in lower_query for w in ["মডেল", "শনাক্ত", "ছবি", "ফটো", "detect", "model", "diagnose"])

        # Check Rice + Disease Model Boundary
        if is_rice and is_disease_model:
            warnings.append(RICE_MODEL_BOUNDARY_WARNING_BN)

        # Check Soil Fertility Boundary
        if any(w in lower_query for w in ["পিএইচ", "ph", "npk", "নাইট্রোজেন পরিমাণ", "উর্বরতা মাত্রা"]):
            warnings.append(SOIL_MODEL_BOUNDARY_DISCLAIMER_BN)

        # Check Moisture / Deep Irrigation Boundary
        if any(w in lower_query for w in ["কত লিটার জল", "সেচ পরিমাণ", "গভীর আর্দ্রতা", "tensio"]):
            warnings.append(MOISTURE_MODEL_BOUNDARY_DISCLAIMER_BN)

        return warnings

    @staticmethod
    def build_insufficient_evidence_response(query: str, crop: Optional[str] = None) -> Dict[str, Any]:
        """Returns structured result when knowledge base lacks verified backing."""
        return {
            "has_sufficient_evidence": False,
            "query": query,
            "crop": crop,
            "answer_bn": INSUFFICIENT_EVIDENCE_NOTICE_BN,
            "answer_en": INSUFFICIENT_EVIDENCE_NOTICE_EN,
            "records": [],
            "safety_warnings": [INSUFFICIENT_EVIDENCE_NOTICE_BN],
            "consult_expert_notice_bn": (
                "কৃষি পরামর্শ কেন্দ্র: পশ্চিমবঙ্গ কৃষি দপ্তর হেল্পলাইন অথবা নিকটস্থ "
                "কৃষি বিজ্ঞান কেন্দ্র (KVK)-এ সরাসরি যোগাযোগ করুন।"
            ),
            "evidence_status": "insufficient_evidence"
        }


safety_validator = AgriculturalSafetyValidator()
