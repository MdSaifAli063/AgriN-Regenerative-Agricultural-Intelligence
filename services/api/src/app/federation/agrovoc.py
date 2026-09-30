"""
FAO AGROVOC Ontology Resolver & Linked Data Enricher.
Binds KrishiNet domain entities (crops, soil properties, pests, regenerative practices)
to standard FAO AGROVOC multilingual thesaurus URIs and Linked Data contexts.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("krishinet.agrovoc")


class AgrovocResolver:
    """Loads and resolves concepts against canonical FAO AGROVOC thesaurus."""

    _instance: Optional["AgrovocResolver"] = None

    def __init__(self, mapping_path: Optional[Path] = None):
        if mapping_path is None:
            # Look in multiple candidate locations
            candidates = [
                Path(__file__).parents[4] / "data" / "seed" / "agrovoc_mapping.json",
                Path(__file__).parents[3] / "data" / "seed" / "agrovoc_mapping.json",
                Path("data/seed/agrovoc_mapping.json"),
            ]
            for candidate in candidates:
                if candidate.exists():
                    mapping_path = candidate
                    break

        self.mapping_path = mapping_path
        self._data: Dict[str, Any] = {}
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load_mappings()

    @classmethod
    def get_instance(cls) -> "AgrovocResolver":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_mappings(self) -> None:
        if not self.mapping_path or not self.mapping_path.exists():
            logger.warning(f"AGROVOC mapping file not found at {self.mapping_path}")
            return

        try:
            with open(self.mapping_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            self._build_index()
            logger.info(f"Loaded AGROVOC mappings with {len(self._index)} indexed keys.")
        except Exception as e:
            logger.error(f"Failed to load AGROVOC mappings: {e}")

    def _build_index(self) -> None:
        self._index.clear()
        mappings = self._data.get("mappings", {})

        for category, items in mappings.items():
            for key, val in items.items():
                record = {**val, "category": category, "key": key}
                # Index key
                self._index[key.lower()] = record
                self._index[val.get("agrovoc_id", "").lower()] = record
                
                # Index labels
                pref_labels = val.get("pref_label", {})
                for lang, label in pref_labels.items():
                    self._index[label.lower()] = record

                # Index scientific name
                sci = val.get("scientific_name")
                if sci:
                    self._index[sci.lower()] = record

                # Index common name
                cmn = val.get("common_name")
                if cmn:
                    self._index[cmn.lower()] = record

    def lookup(self, term: str, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Look up a concept by term (English, scientific, localized, or key)."""
        if not term:
            return None
        cleaned = term.strip().lower()
        res = self._index.get(cleaned)
        if res:
            if category and res.get("category") != category:
                return None
            return res

        # Fallback substring search across keys
        for key, record in self._index.items():
            if cleaned in key or key in cleaned:
                if category and record.get("category") != category:
                    continue
                return record

        return None

    def get_uri(self, term: str, category: Optional[str] = None) -> Optional[str]:
        match = self.lookup(term, category)
        return match.get("uri") if match else None

    def get_agrovoc_id(self, term: str, category: Optional[str] = None) -> Optional[str]:
        match = self.lookup(term, category)
        return match.get("agrovoc_id") if match else None

    def enrich_entity(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inject JSON-LD @context and AGROVOC URIs into domain responses."""
        enriched = dict(data)
        context_base = "/contexts"

        if entity_type == "soil_intelligence":
            enriched["@context"] = f"{context_base}/soil-intelligence.jsonld"
            properties = enriched.get("properties", {})
            enriched_props = {}
            for prop_key, val in properties.items():
                match = self.lookup(prop_key, category="soil_properties")
                enriched_props[prop_key] = {
                    "value": val,
                    "agrovoc_uri": match.get("uri") if match else None,
                    "agrovoc_id": match.get("agrovoc_id") if match else None,
                }
            enriched["properties"] = enriched_props

        elif entity_type == "disease_diagnosis":
            enriched["@context"] = f"{context_base}/disease-diagnosis.jsonld"
            crop = enriched.get("crop")
            disease = enriched.get("disease") or enriched.get("diagnosis")
            if crop:
                c_match = self.lookup(crop, category="crops")
                if c_match:
                    enriched["crop_agrovoc_uri"] = c_match.get("uri")
            if disease:
                d_match = self.lookup(disease, category="pests_and_diseases")
                if d_match:
                    enriched["disease_agrovoc_uri"] = d_match.get("uri")

        elif entity_type == "outbreak_aggregate":
            enriched["@context"] = f"{context_base}/outbreak-aggregate.jsonld"
            disease = enriched.get("disease")
            crop = enriched.get("crop")
            if disease:
                d_match = self.lookup(disease, category="pests_and_diseases")
                if d_match:
                    enriched["disease_agrovoc_uri"] = d_match.get("uri")
            if crop:
                c_match = self.lookup(crop, category="crops")
                if c_match:
                    enriched["crop_agrovoc_uri"] = c_match.get("uri")

        elif entity_type == "climate_analogue":
            enriched["@context"] = f"{context_base}/climate-analogue.jsonld"
            recommended_crops = enriched.get("recommended_crops", [])
            enriched_crops = []
            for crop_name in recommended_crops:
                c_match = self.lookup(crop_name, category="crops")
                enriched_crops.append({
                    "crop": crop_name,
                    "agrovoc_uri": c_match.get("uri") if c_match else None,
                    "agrovoc_id": c_match.get("agrovoc_id") if c_match else None,
                })
            enriched["recommended_crops_agrovoc"] = enriched_crops

        return enriched

    def get_all_mappings(self) -> Dict[str, Any]:
        return self._data.get("mappings", {})


agrovoc_resolver = AgrovocResolver()
