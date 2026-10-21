"""
Agricultural Knowledge Retrieval Service for BhashaKheti.
Provides CPU-friendly, evidence-based agricultural knowledge retrieval
with strict provenance preservation, crop/category filtering, and safety checks.
"""

import json
import re
from typing import List, Dict, Any, Optional
from app.core.logging import logger
from app.db.session import get_db_connection
from app.services.safety_validator import (
    safety_validator,
    STATUTORY_CHEMICAL_DISCLAIMER_BN,
    INSUFFICIENT_EVIDENCE_NOTICE_BN,
    INSUFFICIENT_EVIDENCE_NOTICE_EN
)

# Bengali & English stop words / question noise particles to ignore during token scoring
NOISE_WORDS = {
    "কী", "কি", "কীভাবে", "কিভাবে", "কেন", "কখন", "কোথায়", "কোথায়", "কোন", "কোনটি",
    "হলে", "হলো", "হলেকি", "হয়", "হয়", "করনীয়", "করণীয়", "উচিত", "পরামর্শ", "উপায়",
    "উপায়", "পদ্ধতি", "ব্যবস্থা", "ব্যবস্থাপনা", "সমস্যা", "সমাধান", "গাছ", "গাছের", "চাষ",
    "চাষের", "করা", "করব", "হবে", "আছে", "জন্য", "হলে", "থেকে", "দিয়ে", "দিয়ে",
    "how", "what", "why", "when", "where", "which", "is", "are", "the", "in", "for", "to", "of", "and", "a", "an"
}

MIN_SCORE_THRESHOLD = 40.0


def tokenize(text: str) -> List[str]:
    """Extracts alphanumeric words and Bengali character tokens."""
    if not text:
        return []
    # Match Bengali unicode block (\u0980-\u09FF) and standard alphanumeric words
    tokens = re.findall(r"[\u0980-\u09FFa-zA-Z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in NOISE_WORDS]


class KnowledgeService:
    """Retrieval service backed by verified agricultural knowledge repository."""

    def _get_all_records(self) -> List[Dict[str, Any]]:
        """Loads records from SQLite database."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agricultural_knowledge")
            rows = cursor.fetchall()
            records = []
            for r in rows:
                item = dict(r)
                # Parse JSON keywords
                if isinstance(item.get("keywords"), str):
                    try:
                        item["keywords"] = json.loads(item["keywords"])
                    except Exception:
                        item["keywords"] = []
                item["chemical_control_permitted"] = bool(item.get("chemical_control_permitted", 0))
                records.append(safety_validator.validate_record_safety(item))
            return records
        finally:
            conn.close()

    def get_categories_and_crops(self) -> Dict[str, Any]:
        """Returns available crop tags and category metadata."""
        records = self._get_all_records()
        crops = sorted(list({r["crop"] for r in records}))
        categories = sorted(list({r["category"] for r in records}))

        crop_labels_bn = {
            "all": "সব ফসল",
            "rice": "ধান (Rice)",
            "potato": "আলু (Potato)",
            "tomato": "টমেটো (Tomato)",
            "bell_pepper": "ক্যাপসিকাম ও লঙ্কা (Bell Pepper / Chilli)",
            "soil_general": "মাটি ও সার ব্যবস্থাপনা (Soil & Nutrition)"
        }

        category_labels_bn = {
            "disease_management": "রোগ ব্যবস্থাপনা (Disease Management)",
            "pest_management": "কীটপতঙ্গ ও বালাই দমন (Pest Management)",
            "nutrient_management": "পুষ্টি ও সার প্রয়োগ (Nutrient Management)",
            "soil_fertility": "মাটির উর্বরতা ও স্বাস্থ্য (Soil Health)",
            "irrigation": "সেচ ও জল নিষ্কাশন (Irrigation & Water)",
            "cultural_practices": "চাষাবাদ ও পরিচর্যা (Cultural Practices)"
        }

        return {
            "total_records": len(records),
            "crops": [{"id": c, "label_bn": crop_labels_bn.get(c, c)} for c in crops],
            "categories": [{"id": cat, "label_bn": category_labels_bn.get(cat, cat)} for cat in categories]
        }

    def get_record_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single verified record by ID."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agricultural_knowledge WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            if isinstance(item.get("keywords"), str):
                try:
                    item["keywords"] = json.loads(item["keywords"])
                except Exception:
                    item["keywords"] = []
            item["chemical_control_permitted"] = bool(item.get("chemical_control_permitted", 0))
            return safety_validator.validate_record_safety(item)
        finally:
            conn.close()

    def search(
        self,
        query: str,
        crop: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Searches verified agricultural knowledge base with multi-field scoring."""
        records = self._get_all_records()
        cleaned_query = query.strip()
        query_tokens = tokenize(cleaned_query)
        lower_query = cleaned_query.lower()

        scored_records = []
        for r in records:
            # 1. Hard filters
            if crop and crop != "all" and r["crop"] != crop and r["crop"] != "all":
                continue
            if category and category != "all" and r["category"] != category:
                continue

            score = 0.0
            primary_match = False

            # 2. Exact substring match in title or topic
            if lower_query in r["title_bn"].lower() or lower_query in r["title_en"].lower():
                score += 50.0
                primary_match = True
            if lower_query in r["topic"].lower():
                score += 35.0
                primary_match = True

            # 3. Token-based scoring
            for tok in query_tokens:
                # Title match
                if tok in r["title_bn"].lower() or tok in r["title_en"].lower():
                    score += 25.0
                    primary_match = True
                # Topic match
                if tok in r["topic"].lower():
                    score += 20.0
                    primary_match = True
                # Keywords match
                for kw in r.get("keywords", []):
                    if tok == kw.lower() or (len(tok) >= 4 and tok in kw.lower()):
                        score += 30.0
                        primary_match = True
                        break
                # Content match (only contributes if there is relevance)
                if tok in r["content_bn"].lower():
                    score += 3.0
                if tok in r["content_en"].lower():
                    score += 2.0

            # Only accept records that matched a core concept in title, topic, or keywords
            if not primary_match:
                continue

            # 4. Filter boost
            if crop and (r["crop"] == crop or r["crop"] == "all"):
                score += 10.0
            if category and r["category"] == category:
                score += 10.0

            if score >= MIN_SCORE_THRESHOLD:
                r_copy = dict(r)
                r_copy["search_relevance_score"] = round(score, 2)
                scored_records.append(r_copy)

        # Sort descending by relevance score
        scored_records.sort(key=lambda x: x["search_relevance_score"], reverse=True)
        top_results = scored_records[:limit]

        # Check boundaries & caveats
        boundary_warnings = safety_validator.check_query_boundaries(cleaned_query, crop)

        has_sufficient_evidence = len(top_results) > 0

        return {
            "has_sufficient_evidence": has_sufficient_evidence,
            "query": cleaned_query,
            "crop_filter": crop,
            "category_filter": category,
            "total_matches": len(scored_records),
            "results": top_results,
            "boundary_warnings": boundary_warnings,
            "insufficient_evidence_notice_bn": INSUFFICIENT_EVIDENCE_NOTICE_BN if not has_sufficient_evidence else None
        }

    def ask(
        self,
        query: str,
        crop: Optional[str] = None,
        growth_stage: Optional[str] = None
    ) -> Dict[str, Any]:
        """Provides a direct, structured agricultural answer backed by verified evidence."""
        cleaned_query = query.strip()
        search_res = self.search(cleaned_query, crop=crop, limit=3)

        boundary_warnings = safety_validator.check_query_boundaries(cleaned_query, crop)

        if not search_res["has_sufficient_evidence"]:
            response = safety_validator.build_insufficient_evidence_response(cleaned_query, crop)
            if boundary_warnings:
                response["safety_warnings"].extend(boundary_warnings)
            return response

        top_match = search_res["results"][0]
        other_matches = search_res["results"][1:]

        # Build concise answer text in Bengali directly from verified source
        answer_parts = [
            f"**{top_match['title_bn']}**",
            f"উৎস: {top_match['source_org']} (যাচাইকরণ তারিখ: {top_match['last_verified_date']})",
            "",
            top_match["content_bn"],
            ""
        ]

        if top_match.get("safety_notes_bn"):
            answer_parts.append(f"📌 **সতর্কতামূলক পরামর্শ:**\n{top_match['safety_notes_bn']}")

        answer_bn = "\n".join(answer_parts)

        return {
            "has_sufficient_evidence": True,
            "query": cleaned_query,
            "crop": crop or top_match["crop"],
            "primary_topic": top_match["topic"],
            "growth_stage": growth_stage or top_match.get("growth_stage"),
            "answer_bn": answer_bn,
            "source_org": top_match["source_org"],
            "source_url": top_match["source_url"],
            "publication_date": top_match["publication_date"],
            "last_verified_date": top_match["last_verified_date"],
            "evidence_status": top_match["evidence_status"],
            "primary_record": top_match,
            "related_records": other_matches,
            "safety_warnings": boundary_warnings,
            "statutory_disclaimer_bn": STATUTORY_CHEMICAL_DISCLAIMER_BN if top_match.get("chemical_control_permitted") else None
        }


knowledge_service = KnowledgeService()
