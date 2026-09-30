/**
 * KrishiNet-BRICS – Shared API Types & Contracts.
 * Source of truth mapped to Phase 2–5 FastAPI backend schemas.
 */

// ---------------------------------------------------------------------------
// Error Envelope & Provenance (Global Contracts)
// ---------------------------------------------------------------------------

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown> | Array<unknown> | null;
  request_id: string;
}

export interface ApiErrorEnvelope {
  error: ApiErrorDetail;
}

export type ProvenanceMode = "live" | "cache" | "demo";

export interface Provenance {
  source: string;
  mode: ProvenanceMode;
  fetched_at: string;
  ttl: number;
  confidence?: number;
  notes?: string;
}

export interface WithProvenance {
  provenance: Provenance;
}

// ---------------------------------------------------------------------------
// Health & Demo Mode Contracts
// ---------------------------------------------------------------------------

export interface HealthReadyResponse {
  status: "ready" | "degraded";
  demo_mode: boolean;
  components: {
    database: boolean;
    redis: boolean;
    minio: boolean;
    keycloak: boolean;
  };
}

export interface DemoModeResponse {
  demo_mode: boolean;
  dev_auth_bypass: boolean;
  node_id: string;
  country: string;
  node_country: string;
  fallback_providers: string[];
}

// ---------------------------------------------------------------------------
// Authentication & RBAC Contracts
// ---------------------------------------------------------------------------

export type UserRole = "farmer" | "extension_officer" | "government_admin" | "researcher";

export interface DevLoginRequest {
  user_id?: string;
  role: UserRole;
  country_iso: string;
  full_name: string;
  phone_number: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  expires_in_minutes: number;
}

export interface UserProfileResponse {
  id: string;
  full_name: string;
  phone_number: string;
  country_iso: string;
  role: UserRole;
  roles: UserRole[];
  created_at?: string;
}

// ---------------------------------------------------------------------------
// Onboarding & Field Contracts
// ---------------------------------------------------------------------------

export interface GeoPolygon {
  type: "Polygon";
  coordinates: number[][][]; // [ [ [lon, lat], ... ] ]
}

export interface OnboardingRequest {
  full_name: string;
  phone_number: string;
  country_iso: string;
  preferred_language: string;
  field_name: string;
  crop_type: string;
  irrigation_type: "rainfed" | "drip" | "canal" | "borewell" | "sprinkler";
  area_ha?: number;
  field_geometry: GeoPolygon;
  consents: {
    share_anonymised_disease: boolean;
    share_anonymised_soil: boolean;
    share_model_updates: boolean;
  };
}

export interface FieldSummary {
  id: string;
  farmer_id: string;
  name: string;
  crop_type: string;
  area_ha: number;
  centroid_lat: number;
  centroid_lon: number;
  geometry: GeoPolygon;
  soil_health_score?: number;
  latest_ndvi?: number;
  health_status: "healthy" | "watch" | "risk";
  created_at: string;
}

// ---------------------------------------------------------------------------
// Field Intelligence Contracts (Satellite, Soil, Weather)
// ---------------------------------------------------------------------------

export interface NdviTimeSeriesPoint {
  date: string;
  ndvi: number;
  ndwi?: number;
  evi?: number;
  ndmi?: number;
  is_anomaly?: boolean;
}

export interface SatelliteIntelligence {
  field_id: string;
  latest_ndvi: number;
  mean_ndvi_30d: number;
  trend: "improving" | "stable" | "declining";
  history: NdviTimeSeriesPoint[];
  tile_url?: string;
  bounds?: [number, number, number, number]; // [minLon, minLat, maxLon, maxLat]
  provenance: Provenance;
}

export interface SoilComponentScore {
  name: string;
  value: number;
  unit: string;
  status: "healthy" | "watch" | "risk";
  optimal_range: string;
}

export interface SoilIntelligence {
  field_id: string;
  overall_score: number; // 0 - 100
  components: SoilComponentScore[];
  limiting_factors: string[];
  improvement_hints: string[];
  ph: number;
  organic_carbon_percent: number;
  clay_percent: number;
  nitrogen_level: string;
  phosphorus_level: string;
  potassium_level: string;
  provenance: Provenance;
}

export interface WeatherDayForecast {
  date: string;
  temp_min_c: number;
  temp_max_c: number;
  rain_prob_pct: number;
  rain_amount_mm: number;
  humidity_pct: number;
  condition: string;
  spray_window_favorable: boolean;
}

export interface WeatherIntelligence {
  field_id: string;
  forecast: WeatherDayForecast[];
  heat_stress_risk: boolean;
  frost_risk: boolean;
  drought_index: number;
  irrigation_need_mm: number;
  next_7d_total_rain_mm: number;
  provenance: Provenance;
}

// ---------------------------------------------------------------------------
// Advisory Contracts (Phase 4)
// ---------------------------------------------------------------------------

export interface TopDriver {
  feature: string;
  impact: "positive" | "negative";
  magnitude: number;
  description: string;
}

export interface AdvisoryCitation {
  id: string;
  title: string;
  source: string;
  url?: string;
  fao_agrovoc_uri?: string;
}

export interface AdvisoryExplainability {
  signals_used: {
    name: string;
    value: string | number;
    support: "supports" | "cautions" | "neutral";
  }[];
  top_drivers: TopDriver[];
  sources: AdvisoryCitation[];
  counterfactual: string;
}

export interface CropRecommendation {
  crop_name: string;
  suitability_score: number; // 0 - 100
  yield_estimate_range: string;
  water_need_mm: number;
  climate_risk_level: "low" | "medium" | "high";
}

export interface RegenerativePractice {
  id: string;
  title: string;
  summary: string;
  cost_level: "low" | "medium" | "high";
  benefit_category: "soil_organic_matter" | "water_retention" | "biodiversity" | "pest_suppression";
  difficulty: "easy" | "moderate" | "advanced";
  verified_indigenous: boolean;
}

export interface ActionCalendarItem {
  id: string;
  day_offset: number;
  date_iso: string;
  action_text: string;
  category: "irrigation" | "fertilisation" | "pest_scouting" | "harvesting" | "sowing";
  is_completed: boolean;
  urgency: "urgent" | "normal" | "flexible";
}

export interface WhatToDoToday {
  headline: string;
  summary: string;
  urgency: "urgent" | "attention" | "optimal" | "routine";
  recommended_actions: string[];
  read_aloud_text: string;
}

export interface AdvisoryResponse {
  id: string;
  field_id: string;
  confidence_level: "high" | "medium" | "low";
  confidence_score: number;
  needs_expert_escalation: boolean;
  escalation_message?: string;
  what_to_do_today: WhatToDoToday;
  crop_recommendations: CropRecommendation[];
  regenerative_practices: RegenerativePractice[];
  fertiliser_plan: {
    organic_options: string[];
    chemical_options: string[];
    safety_guidelines: string;
  };
  sowing_window: {
    start_date: string;
    end_date: string;
    rationale: string;
  };
  timeline_30d: ActionCalendarItem[];
  explainability: AdvisoryExplainability;
  created_at: string;
  provenance: Provenance;
}

// ---------------------------------------------------------------------------
// Disease Diagnostic & Outbreak Contracts (Phase 5)
// ---------------------------------------------------------------------------

export interface Top3Prediction {
  label: string;
  confidence: number;
  canonical_name?: string | null;
}

export interface DiseaseDiagnosisResponse {
  detection_id: string;
  primary_disease_name: string;
  primary_disease_label: string;
  canonical_name?: string | null;
  fao_agrovoc_uri?: string | null;
  severity_level: "mild" | "moderate" | "severe";
  spread_risk_score: "low" | "moderate" | "high" | "critical";
  top_3_predictions: Top3Prediction[];
  ensemble_confidence: number;
  organic_treatment: string;
  chemical_treatment?: string | null;
  chemical_safety_warning?: string | null;
  prevention_measures: string[];
  weather_risk_amplified: boolean;
  weather_risk_factors: string[];
  visual_reasoning: string;
  is_healthy: boolean;
  confidence_sufficient: boolean;
  confidence_guard_threshold: number;
  fusion_strategy: string;
  edge_weight: number;
  gemini_weight: number;
  ood_rejected: boolean;
  model_version: string;
  image_s3_uri?: string;
  created_at: string;
}

export interface OfflineSyncItem {
  client_id: string;
  captured_at: string;
  crop_hint?: string;
  latitude?: number;
  longitude?: number;
  offline_prediction_label?: string;
  offline_confidence?: number;
  image_s3_uri: string;
}

export interface OfflineSyncResponse {
  synced_count: number;
  errors_count: number;
  results: {
    client_id: string;
    detection_id?: string;
    status: "synced" | "duplicate" | "error";
    error_message?: string;
  }[];
}

export interface GeoJsonOutbreakFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number]; // [lon, lat]
  };
  properties: {
    h3_index: string;
    disease_label: string;
    disease_name: string;
    reported_cases: number;
    severity: "low" | "medium" | "high" | "critical";
    is_spike: boolean;
    period_start: string;
    period_end: string;
  };
}

export interface OutbreakFeedResponse {
  type: "FeatureCollection";
  features: GeoJsonOutbreakFeature[];
}

// ---------------------------------------------------------------------------
// Phase 7 Forward Adapters (Model Hub, Climate Analogues, Node Registry)
// ---------------------------------------------------------------------------

export interface ModelCardSummary {
  id: string;
  model_name: string;
  version: string;
  crop_coverage: string[];
  accuracy_top1: number;
  accuracy_top3: number;
  quantization: "int8" | "fp16";
  size_mb: number;
  license: string;
  download_count: number;
  onnx_url: string;
  sha256_hash: string;
}

export interface ClimateAnalogue {
  source_district: string;
  source_country: string;
  matched_district: string;
  matched_country: string;
  similarity_score: number;
  key_shared_attributes: string[];
  successful_regenerative_interventions: string[];
}

export interface BricsNodeSummary {
  country_iso: string;
  country_name: string;
  status: "active" | "invited" | "syncing";
  farmers_count: number;
  hectares_regenerated: number;
  water_saved_megalitres: number;
  co2e_sequestered_tonnes: number;
  active_alerts: number;
  participating_models: number;
}
