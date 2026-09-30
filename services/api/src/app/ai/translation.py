"""
KrishiNet-BRICS - High-Fidelity Multilingual Translation Service.
Translates user-facing advisory narratives across BRICS languages (hi, mr, pt, ru, zh, ar, sw)
while strictly preserving agronomic numbers, units, dates, citations, and Pydantic invariants.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.ai.gemini_client import gemini_client
from app.core.config import settings
from app.schemas.advisory import AdvisoryContract

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "mr": "Marathi (मराठी)",
    "pt": "Portuguese (Português)",
    "ru": "Russian (Русский)",
    "zh": "Chinese (中文)",
    "ar": "Arabic (العربية)",
    "sw": "Swahili (Kiswahili)",
}

# Offline agronomic term dictionary for resilient fallback translation
OFFLINE_GLOSSARY: Dict[str, Dict[str, str]] = {
    "hi": {
        "Construct In-Field Contour Furrows Before Expected Rains": "अपेक्षित बारिश से पहले खेत में समोच्च खाइयां (कंटूर मेड़) बनाएं",
        "Calibrate Dolomitic Limestone Spreader for Pre-Planting Remediation": "बुवाई पूर्व उपचार के लिए डोलोमाइट चूना प्रसारक को कैलिब्रेट करें",
        "Maintain Maize Stover Residue Cover to Prevent Soil Water Evaporation": "मृदा जल वाष्पीकरण रोकने के लिए मक्का अवशेष आवरण बनाए रखें",
        "Apply well-rotted farmyard manure": "सड़ी हुई गोबर की खाद डालें",
        "biochar": "बायोचार (जैव कोयला)",
        "compost": "कम्पोस्ट खाद",
        "cover crops": "आवरण फसलें",
        "mulching": "मल्चिंग (पलवार)",
        "drip irrigation": "ड्रिप सिंचाई",
        "high urgency": "अत्यंत आवश्यक",
    },
    "mr": {
        "Construct In-Field Contour Furrows Before Expected Rains": "अपेक्षित पावसापूर्वी शेतात समपातळी चर (कंटूर बांध) तयार करा",
        "Calibrate Dolomitic Limestone Spreader for Pre-Planting Remediation": "पेरणीपूर्वी जमिनीच्या उपचारासाठी डोलोमाइट चुना पसरवण्याचे यंत्र कॅलिब्रेट करा",
        "Maintain Maize Stover Residue Cover to Prevent Soil Water Evaporation": "मातीतील पाण्याचे बाष्पीभवन रोखण्यासाठी मक्याच्या अवशेषांचे आच्छादन ठेवा",
        "Apply well-rotted farmyard manure": "चांगले कुजलेले शेणखत टाका",
        "biochar": "बायोचार",
        "compost": "कंपोस्ट खत",
        "cover crops": "आच्छादन पिके",
        "mulching": "आच्छादन (मल्चिंग)",
        "drip irrigation": "ठिबक सिंचन",
        "high urgency": "तात्काळ गरज",
    },
    "pt": {
        "Construct In-Field Contour Furrows Before Expected Rains": "Construir curvas de nível e camalhões antes das chuvas esperadas",
        "Calibrate Dolomitic Limestone Spreader for Pre-Planting Remediation": "Calibrar distribuidor de calcário dolomítico para remediação pré-plantio",
        "Maintain Maize Stover Residue Cover to Prevent Soil Water Evaporation": "Manter palhada de milho na superfície para evitar evaporação da água do solo",
        "Apply well-rotted farmyard manure": "Aplicar esterco de curral bem curtido",
        "biochar": "biocarvão",
        "compost": "compostagem",
        "cover crops": "culturas de cobertura",
        "mulching": "cobertura morta (mulching)",
        "drip irrigation": "irrigação por gotejamento",
        "high urgency": "alta urgência",
    },
    "ru": {
        "Construct In-Field Contour Furrows Before Expected Rains": "Создать контурные борозды на поле до ожидаемых дождей",
        "Calibrate Dolomitic Limestone Spreader for Pre-Planting Remediation": "Откалибровать разбрасыватель доломитовой муки перед посевом",
        "Maintain Maize Stover Residue Cover to Prevent Soil Water Evaporation": "Сохранять пожнивные остатки кукурузы для предотвращения испарения влаги",
        "Apply well-rotted farmyard manure": "Внести перепревший навоз",
        "biochar": "биоуголь",
        "compost": "компост",
        "cover crops": "покровные культуры",
        "mulching": "мульчирование",
        "drip irrigation": "капельное орошение",
        "high urgency": "высокая срочность",
    },
    "zh": {
        "Construct In-Field Contour Furrows Before Expected Rains": "在预期降雨前修建田间等高沟垄以保墒",
        "Calibrate Dolomitic Limestone Spreader for Pre-Planting Remediation": "播种前校准白云石石灰撒布机以调节酸性土壤",
        "Maintain Maize Stover Residue Cover to Prevent Soil Water Evaporation": "保持玉米秸秆覆盖以防止土壤水分蒸发",
        "Apply well-rotted farmyard manure": "施用充分腐熟的农家肥",
        "biochar": "生物炭",
        "compost": "堆肥",
        "cover crops": "覆盖作物",
        "mulching": "覆盖保墒",
        "drip irrigation": "滴灌",
        "high urgency": "紧急处理",
    },
    "ar": {
        "Construct In-Field Contour Furrows Before Expected Rains": "إنشاء خطوط كنتورية لحصاد المياه قبل هطول الأمطار المتوقعة",
        "Calibrate Dolomitic Limestone Spreader for Pre-Planting Remediation": "معايرة ناثرة الحجر الجيري الدولومايتي لمعالجة حموضة التربة قبل الزراعة",
        "Maintain Maize Stover Residue Cover to Prevent Soil Water Evaporation": "الحفاظ على بقايا محصول الذرة لمنع تبخر مياه التربة",
        "Apply well-rotted farmyard manure": "إضافة سماد عضوي متحلل جيداً",
        "biochar": "الفحم الحيوي",
        "compost": "السماد العضوي",
        "cover crops": "محاصيل التغطية",
        "mulching": "التغطية العضوية (الملش)",
        "drip irrigation": "الري بالتنقيط",
        "high urgency": "عاجل جداً",
    },
    "sw": {
        "Construct In-Field Contour Furrows Before Expected Rains": "Tengeneza mifereji ya kufuata mwinuko kabla ya mvua zinazotarajiwa",
        "Calibrate Dolomitic Limestone Spreader for Pre-Planting Remediation": "Pima na urekebishe mtambo wa chokaa ya dolomiti kabla ya kupanda",
        "Maintain Maize Stover Residue Cover to Prevent Soil Water Evaporation": "Weka mabaki ya mahindi shambani kuzuia maji ya udongo yasipotee",
        "Apply well-rotted farmyard manure": "Weka mbolea ya samadi iliyoiva vizuri",
        "biochar": "mkaa wa viumbe hai (biochar)",
        "compost": "mboji",
        "cover crops": "mimea ya kufunika ardhi",
        "mulching": "kutandaza majani (mulching)",
        "drip irrigation": "umwagiliaji wa matone",
        "high urgency": "uharaka mkubwa",
    },
}


class TranslationService:
    """
    Multilingual translation service tailored for BRICS smallholder advisories.
    """

    async def translate_advisory(
        self,
        contract: AdvisoryContract,
        target_language: str,
        user_id: Optional[str] = None,
    ) -> AdvisoryContract:
        """
        Translates human-readable fields of the AdvisoryContract into target_language.
        Returns a new or updated AdvisoryContract instance.
        """
        lang = target_language.lower().strip()
        if not lang or lang == "en" or lang not in SUPPORTED_LANGUAGES:
            contract.meta.language = "en"
            return contract

        # Extract text snippets that require translation
        text_map: Dict[str, str] = {}

        # 1. What to do today
        text_map["today_title"] = contract.what_to_do_today.title
        text_map["today_desc"] = contract.what_to_do_today.description

        # 2. Sowing window rationale
        text_map["sowing_rationale"] = contract.sowing_window.rationale

        # 3. Fertilizer plan
        for idx, step in enumerate(contract.fertiliser_plan.organic_first_steps):
            text_map[f"fert_org_{idx}"] = step
        if contract.fertiliser_plan.mineral_supplement:
            text_map["fert_mineral"] = contract.fertiliser_plan.mineral_supplement

        # 4. Crop recommendations
        for idx, rec in enumerate(contract.crop_recommendations):
            text_map[f"crop_why_{idx}"] = rec.why_it_fits

        # 5. Regenerative practices
        for idx, prac in enumerate(contract.regenerative_practices):
            text_map[f"prac_reason_{idx}"] = prac.reason
            text_map[f"prac_when_{idx}"] = prac.when_to_start

        # 6. Action calendar
        for idx, act in enumerate(contract.action_calendar_30d):
            text_map[f"act_title_{idx}"] = act.title
            text_map[f"act_desc_{idx}"] = act.description

        # 7. Risks and warnings
        for idx, rw in enumerate(contract.risks_and_warnings):
            text_map[f"risk_msg_{idx}"] = rw.message

        # 8. Explainability notes
        text_map["explain_counterfactual"] = contract.explainability.counterfactual_note
        for idx, driver in enumerate(contract.explainability.top_3_drivers):
            text_map[f"explain_driver_{idx}"] = driver
        for idx, sig in enumerate(contract.explainability.signals_used):
            text_map[f"explain_sig_{idx}"] = sig.plain_reason

        # Attempt LLM translation if enabled and configured
        translated_map = await self._translate_map_with_gemini(text_map, lang, user_id=user_id)
        if not translated_map:
            # Fallback to dictionary
            translated_map = self._translate_map_with_dictionary(text_map, lang)

        # Apply translated map back onto a cloned contract
        data = contract.model_dump()
        self._apply_translations(data, translated_map)
        data["meta"]["language"] = lang

        return AdvisoryContract.model_validate(data)

    async def _translate_map_with_gemini(
        self,
        text_map: Dict[str, str],
        target_language: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """
        Translates dictionary of text using Gemini LLM.
        """
        if settings.DEMO_MODE or not settings.GEMINI_API_KEY:
            return None

        lang_name = SUPPORTED_LANGUAGES.get(target_language, target_language)
        system_instruction = (
            f"You are a professional agricultural translator for smallholder farmers. "
            f"Translate the JSON values into clear, fluent, natural {lang_name} at a 6th-grade reading level. "
            f"Do not change or translate the keys. Preserve all numbers, units (kg, ha, mm, t/ha, °C), dates, "
            f"and chemical/biological names (e.g., Trichoderma, Rhizobium, Vertisol, Oxisol). "
            f"Return ONLY a strictly valid JSON object with the exact same keys."
        )

        user_content = json.dumps(text_map, ensure_ascii=False)

        try:
            res = await gemini_client.generate_text(
                prompt=user_content,
                system_instruction=system_instruction,
                model_name=settings.GEMINI_MODEL,
                temperature=0.1,
                user_id=user_id,
            )
            clean_res = res.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.startswith("```"):
                clean_res = clean_res[3:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            translated = json.loads(clean_res.strip())
            if isinstance(translated, dict):
                return translated
        except Exception as e:
            logger.warning(f"Gemini translation to '{target_language}' failed: {e}. Falling back to glossary.")

        return None

    def _translate_map_with_dictionary(
        self,
        text_map: Dict[str, str],
        target_language: str,
    ) -> Dict[str, str]:
        """
        Translates text snippets using the offline agronomic glossary.
        """
        glossary = OFFLINE_GLOSSARY.get(target_language, {})
        translated: Dict[str, str] = {}
        prefix = f"[{target_language.upper()}] "

        for key, text in text_map.items():
            if text in glossary:
                translated[key] = glossary[text]
            else:
                # Replace known substring terms
                out = text
                for term, trans in glossary.items():
                    if term.lower() in out.lower():
                        out = out.replace(term, trans)
                translated[key] = f"{prefix}{out}"

        return translated

    def _apply_translations(self, data: Dict[str, Any], trans: Dict[str, str]) -> None:
        """
        In-place patch of dictionary structure with translated strings.
        """
        if "today_title" in trans:
            data["what_to_do_today"]["title"] = trans["today_title"]
        if "today_desc" in trans:
            data["what_to_do_today"]["description"] = trans["today_desc"]

        if "sowing_rationale" in trans:
            data["sowing_window"]["rationale"] = trans["sowing_rationale"]

        # Fertilizer
        for idx in range(len(data.get("fertiliser_plan", {}).get("organic_first_steps", []))):
            k = f"fert_org_{idx}"
            if k in trans:
                data["fertiliser_plan"]["organic_first_steps"][idx] = trans[k]
        if "fert_mineral" in trans and data.get("fertiliser_plan", {}).get("mineral_supplement"):
            data["fertiliser_plan"]["mineral_supplement"] = trans["fert_mineral"]

        # Crop recommendations
        for idx in range(len(data.get("crop_recommendations", []))):
            k = f"crop_why_{idx}"
            if k in trans:
                data["crop_recommendations"][idx]["why_it_fits"] = trans[k]

        # Regenerative practices
        for idx in range(len(data.get("regenerative_practices", []))):
            kr = f"prac_reason_{idx}"
            kw = f"prac_when_{idx}"
            if kr in trans:
                data["regenerative_practices"][idx]["reason"] = trans[kr]
            if kw in trans:
                data["regenerative_practices"][idx]["when_to_start"] = trans[kw]

        # Action calendar
        for idx in range(len(data.get("action_calendar_30d", []))):
            kt = f"act_title_{idx}"
            kd = f"act_desc_{idx}"
            if kt in trans:
                data["action_calendar_30d"][idx]["title"] = trans[kt]
            if kd in trans:
                data["action_calendar_30d"][idx]["description"] = trans[kd]

        # Risks and warnings
        for idx in range(len(data.get("risks_and_warnings", []))):
            k = f"risk_msg_{idx}"
            if k in trans:
                data["risks_and_warnings"][idx]["message"] = trans[k]

        # Explainability
        if "explain_counterfactual" in trans:
            data["explainability"]["counterfactual_note"] = trans["explain_counterfactual"]
        for idx in range(len(data.get("explainability", {}).get("top_3_drivers", []))):
            k = f"explain_driver_{idx}"
            if k in trans:
                data["explainability"]["top_3_drivers"][idx] = trans[k]
        for idx in range(len(data.get("explainability", {}).get("signals_used", []))):
            k = f"explain_sig_{idx}"
            if k in trans:
                data["explainability"]["signals_used"][idx]["plain_reason"] = trans[k]


translation_service = TranslationService()
