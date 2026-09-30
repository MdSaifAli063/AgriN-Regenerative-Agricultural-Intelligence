-- ============================================================================
-- KrishiNet-BRICS Database Initialization Script
-- Extensions: PostGIS for spatial fields, pgvector for semantic search, uuid-ossp
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enum Types
DO $$ BEGIN
    CREATE TYPE country_iso AS ENUM ('IND', 'BRA', 'ZAF', 'CHN', 'RUS', 'EGY', 'ETH', 'IRN', 'ARE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('farmer', 'extension_officer', 'government_admin', 'researcher');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE irrigation_system AS ENUM ('rainfed', 'drip', 'sprinkler', 'furrow', 'flood', 'subsurface');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE soil_texture_class AS ENUM ('clay', 'sandy_clay', 'silty_clay', 'clay_loam', 'sandy_clay_loam', 'silty_clay_loam', 'loam', 'sandy_loam', 'silt_loam', 'sand', 'loamy_sand', 'silt');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE risk_level AS ENUM ('low', 'moderate', 'high', 'severe');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE cost_level AS ENUM ('low', 'medium', 'high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Table schemas
CREATE TABLE IF NOT EXISTS brics_countries (
    code VARCHAR(3) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    national_registry_url VARCHAR(255) NOT NULL,
    contact_agency VARCHAR(255) NOT NULL,
    public_signing_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    country_code VARCHAR(3) NOT NULL REFERENCES brics_countries(code),
    phone_number VARCHAR(32) UNIQUE,
    email VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255) NOT NULL,
    preferred_language VARCHAR(10) DEFAULT 'en',
    role VARCHAR(32) DEFAULT 'farmer',
    keycloak_sub UUID UNIQUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS farms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    farm_name VARCHAR(255) NOT NULL,
    village_district VARCHAR(255),
    state_province VARCHAR(255) NOT NULL,
    country_code VARCHAR(3) NOT NULL REFERENCES brics_countries(code),
    total_area_hectares NUMERIC(10, 4) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fields (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farm_id UUID NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    boundary_geojson JSONB NOT NULL,
    centroid_lat NUMERIC(9, 6) NOT NULL,
    centroid_lon NUMERIC(9, 6) NOT NULL,
    area_hectares NUMERIC(10, 4) NOT NULL,
    irrigation_type VARCHAR(32) DEFAULT 'rainfed',
    current_crop VARCHAR(100),
    sowing_date DATE,
    previous_crops JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS satellite_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    acquisition_date TIMESTAMPTZ NOT NULL,
    satellite_source VARCHAR(64) DEFAULT 'Sentinel-2 L2A',
    cloud_coverage_percentage NUMERIC(5, 2) NOT NULL,
    mean_ndvi NUMERIC(6, 4) NOT NULL,
    p10_ndvi NUMERIC(6, 4),
    p90_ndvi NUMERIC(6, 4),
    mean_ndwi NUMERIC(6, 4) NOT NULL,
    mean_evi NUMERIC(6, 4) NOT NULL,
    tile_geojson JSONB,
    storage_thumbnail_url VARCHAR(512),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS soil_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    source VARCHAR(64) DEFAULT 'ISRIC SoilGrids 250m v2.0',
    depth_slice VARCHAR(32) DEFAULT '0-30cm',
    ph_water NUMERIC(4, 2) NOT NULL,
    organic_carbon_g_kg NUMERIC(6, 2) NOT NULL,
    total_nitrogen_g_kg NUMERIC(6, 2),
    cation_exchange_capacity_cmolc_kg NUMERIC(6, 2),
    clay_fraction_percentage NUMERIC(5, 2) NOT NULL,
    sand_fraction_percentage NUMERIC(5, 2) NOT NULL,
    silt_fraction_percentage NUMERIC(5, 2) NOT NULL,
    texture_class VARCHAR(32),
    bulk_density_g_cm3 NUMERIC(4, 2),
    soil_health_score INTEGER CHECK (soil_health_score BETWEEN 0 AND 100),
    score_interpretation TEXT NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weather_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    record_date DATE NOT NULL,
    temp_min_celsius NUMERIC(5, 2) NOT NULL,
    temp_max_celsius NUMERIC(5, 2) NOT NULL,
    precipitation_mm NUMERIC(6, 2) NOT NULL,
    relative_humidity_pct NUMERIC(5, 2) NOT NULL,
    wind_speed_kmh NUMERIC(5, 2),
    rainfall_anomaly_pct NUMERIC(6, 2),
    heat_stress_hours INTEGER DEFAULT 0,
    frost_risk_flag BOOLEAN DEFAULT FALSE,
    drought_index NUMERIC(5, 3),
    forecast_horizon_days INTEGER DEFAULT 7,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agronomy_knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    source_agency VARCHAR(100) NOT NULL,
    agrovoc_concept_uri VARCHAR(255),
    crop_focus VARCHAR(100),
    climate_zone VARCHAR(100),
    chunk_index INTEGER NOT NULL,
    content_chunk TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS regenerative_advisories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    advisory_status VARCHAR(32) DEFAULT 'published',
    confidence_score NUMERIC(4, 3) NOT NULL,
    hallucination_guard_passed BOOLEAN DEFAULT TRUE,
    top_crop_recommendations JSONB NOT NULL,
    regenerative_practices JSONB NOT NULL,
    sowing_window JSONB NOT NULL,
    irrigation_schedule JSONB NOT NULL,
    organic_fertilizer_plan JSONB NOT NULL,
    action_calendar_30days JSONB NOT NULL,
    data_signals_cited JSONB NOT NULL,
    carbon_sequestration_est_t_ha NUMERIC(6, 3),
    water_conservation_est_pct INTEGER,
    yield_uplift_est_pct INTEGER,
    human_in_the_loop_flag BOOLEAN DEFAULT FALSE,
    disclaimer_notice TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disease_diagnoses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id UUID REFERENCES fields(id) ON DELETE SET NULL,
    farmer_id UUID NOT NULL REFERENCES users(id),
    original_image_url VARCHAR(512) NOT NULL,
    edge_model_prediction JSONB,
    gemini_vision_prediction JSONB,
    ensemble_prediction JSONB NOT NULL,
    primary_disease_name VARCHAR(150) NOT NULL,
    fao_agrovoc_disease_uri VARCHAR(255),
    severity_rating VARCHAR(32) NOT NULL,
    organic_treatment TEXT NOT NULL,
    chemical_treatment TEXT,
    chemical_safety_warning TEXT,
    prevention_measures JSONB NOT NULL,
    spread_risk_level VARCHAR(32) DEFAULT 'low',
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disease_outbreaks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    country_code VARCHAR(3) NOT NULL REFERENCES brics_countries(code),
    disease_name VARCHAR(150) NOT NULL,
    affected_crop VARCHAR(100) NOT NULL,
    incident_count INTEGER NOT NULL,
    risk_level VARCHAR(32) DEFAULT 'moderate',
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    h3_hexagon_index VARCHAR(32),
    first_detected TIMESTAMPTZ NOT NULL,
    last_reported TIMESTAMPTZ NOT NULL,
    active_advisory TEXT
);

CREATE TABLE IF NOT EXISTS federated_model_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(150) NOT NULL,
    version VARCHAR(32) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    participating_countries TEXT[] NOT NULL,
    global_round_index INTEGER NOT NULL,
    accuracy_score NUMERIC(5, 4) NOT NULL,
    f1_score NUMERIC(5, 4),
    weights_s3_key VARCHAR(512) NOT NULL,
    model_card_markdown TEXT NOT NULL,
    dpg_standard_compliant BOOLEAN DEFAULT TRUE,
    license_type VARCHAR(64) DEFAULT 'Apache-2.0',
    published_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS farmer_consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farmer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    share_anonymized_soil BOOLEAN DEFAULT TRUE,
    share_disease_telemetry BOOLEAN DEFAULT TRUE,
    participate_in_federated_learning BOOLEAN DEFAULT TRUE,
    consent_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS climate_analogue_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_region VARCHAR(150) NOT NULL,
    source_country VARCHAR(3) NOT NULL,
    analogue_region VARCHAR(150) NOT NULL,
    analogue_country VARCHAR(3) NOT NULL,
    bioclimatic_similarity_score NUMERIC(4, 3) NOT NULL,
    shared_crop_successes JSONB NOT NULL,
    validated_regenerative_practices JSONB NOT NULL
);
