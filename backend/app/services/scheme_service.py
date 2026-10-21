"""
Government Scheme Discovery Service for BhashaKheti (Phase 7).
Provides discovery, search, and preliminary eligibility evaluation for 
West Bengal State and Central Government agricultural schemes and subsidies.
Privacy-First: Never collects Aadhaar, bank credentials, or sensitive documents.
"""

import json
import os
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger

PRELIMINARY_ASSESSMENT_NOTICE_BN = (
    "গুরুত্বপূর্ণ সতর্কতা: ভাষাখেতি একটি স্বাধীন কৃষক সহায়ক প্ল্যাটফর্ম। "
    "এখানে প্রদর্শিত তথ্যাবলি সরকারি অফিসিয়াল পোর্টাল ও নির্দেশিকার ভিত্তিতে প্রস্তুত। "
    "কোনো প্রকল্পে আবেদনের জন্য কোনো অর্থ দেওয়া প্রযোজ্য নয়। "
    "চূড়ান্ত অন্তর্ভুক্তি ও অনুমোদনের সিদ্ধান্ত সংশ্লিষ্ট সরকারি দপ্তর কর্তৃক গৃহীত হয়।"
)


class SchemeService:
    """Manages agricultural government scheme discovery, filtering, and preliminary guidance."""

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or settings.SCHEMES_DATA_PATH
        self._schemes: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self) -> None:
        """Loads agricultural schemes from the official curated JSON dataset."""
        resolved_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", self.data_path))
        if not os.path.exists(resolved_path):
            alt_path = os.path.abspath(self.data_path)
            if os.path.exists(alt_path):
                resolved_path = alt_path
            else:
                logger.error(f"Schemes data file not found at: {resolved_path}")
                self._schemes = []
                return

        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                self._schemes = json.load(f)
                logger.info(f"Loaded {len(self._schemes)} agricultural schemes from {resolved_path}")
        except Exception as exc:
            logger.error(f"Failed to load schemes data: {exc}")
            self._schemes = []

    def get_categories(self) -> List[Dict[str, str]]:
        """Returns distinct scheme categories with Bengali labels."""
        seen = set()
        categories = []
        for s in self._schemes:
            cat_id = s.get("category", "")
            if cat_id and cat_id not in seen:
                seen.add(cat_id)
                categories.append({
                    "id": cat_id,
                    "label_bn": s.get("category_bn", cat_id)
                })
        return categories

    def get_schemes(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        sponsor: Optional[str] = None,
        beneficiary_type: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Searches and filters government schemes based on query, category, sponsor, and beneficiary type.
        """
        results = list(self._schemes)

        # Category filter
        if category and category.lower() != "all":
            results = [s for s in results if s.get("category") == category]

        # Sponsor filter (state, central, joint)
        if sponsor and sponsor.lower() != "all":
            results = [s for s in results if s.get("sponsor") == sponsor.lower()]

        # Beneficiary type filter (marginal_farmer, small_farmer, sharecropper, tenant_farmer, etc.)
        if beneficiary_type and beneficiary_type.lower() != "all":
            b_lower = beneficiary_type.lower()
            results = [s for s in results if b_lower in s.get("beneficiary_types", [])]

        # Text query filtering
        if query and query.strip():
            tokens = query.lower().strip().split()
            filtered = []
            for s in results:
                searchable = (
                    f"{s.get('name_bn', '')} {s.get('name_en', '')} "
                    f"{s.get('authority_bn', '')} {s.get('summary_bn', '')} "
                    f"{s.get('category_bn', '')} {s.get('benefits_bn', '')} "
                    f"{s.get('eligibility_bn', '')}"
                ).lower()
                if any(t in searchable for t in tokens):
                    filtered.append(s)
            results = filtered

        paginated = results[:limit]
        return {
            "total_matches": len(results),
            "results_count": len(paginated),
            "schemes": paginated,
            "notice_bn": PRELIMINARY_ASSESSMENT_NOTICE_BN
        }

    def get_scheme_by_id(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        """Returns full detailed breakdown of a scheme by ID."""
        for s in self._schemes:
            if s.get("id") == scheme_id:
                return dict(s)
        return None

    def check_preliminary_eligibility(
        self,
        land_size_acres: Optional[float] = None,
        is_sharecropper: bool = False,
        is_owner: bool = True,
        interests: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates preliminary eligibility for schemes based on general criteria.
        Privacy guaranteed: Zero sensitive documents or credentials requested.
        """
        matched = []
        marginal_or_small = land_size_acres is not None and land_size_acres <= 2.5

        for s in self._schemes:
            reasons = []
            is_matched = True

            # Sharecropper check
            b_types = s.get("beneficiary_types", [])
            if is_sharecropper and "sharecropper" not in b_types and not is_owner:
                is_matched = False
            elif is_sharecropper and "sharecropper" in b_types:
                reasons.append("নথিভুক্ত ভাগচাষীদের জন্য প্রকল্পটিতে স্পষ্ট অন্তর্ভুক্তি রয়েছে।")

            # Land size check
            land_crit = s.get("land_size_criteria", "all")
            if land_crit == "marginal_and_small":
                if land_size_acres is not None and land_size_acres > 2.5:
                    is_matched = False
                elif marginal_or_small:
                    reasons.append("ক্ষুদ্র ও প্রান্তিক চাষীদের জন্য বিশেষ অগ্রাধিকার রয়েছে।")
            elif land_crit == "all" and is_matched:
                reasons.append("যে কোনো পরিমাণ কৃষিজমির চাষীদের জন্য প্রযোজ্য।")

            # Interest matching if provided
            if interests and is_matched:
                cat = s.get("category", "")
                if any(i in cat for i in interests):
                    reasons.append("আপনার নির্বাচিত আগ্রহের বিষয়ের সাথে সঙ্গতিপূর্ণ।")

            if is_matched:
                matched.append({
                    "scheme_id": s["id"],
                    "name_bn": s["name_bn"],
                    "authority_bn": s["authority_bn"],
                    "benefits_summary": s["summary_bn"],
                    "status": s["status"],
                    "official_portal_url": s["official_portal_url"],
                    "eligibility_reasons": reasons
                })

        return {
            "total_matched": len(matched),
            "matched_schemes": matched,
            "privacy_statement": "ভাষাখেতি ব্যবহারকারীর কোনো ব্যক্তিগত পরিচয় বা আধার তথ্য সংগ্রহ করে না।",
            "statutory_notice": PRELIMINARY_ASSESSMENT_NOTICE_BN
        }


scheme_service = SchemeService()
