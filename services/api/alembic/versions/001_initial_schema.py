"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-29 21:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostgreSQL Extensions if running on postgresql dialect
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
        op.execute('CREATE EXTENSION IF NOT EXISTS "postgis";')
        op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')

    # 2. brics_nodes
    op.create_table(
        "brics_nodes",
        sa.Column("country_iso", sa.String(3), primary_key=True),
        sa.Column("country_name", sa.String(100), nullable=False),
        sa.Column("lead_agency", sa.String(255), nullable=False),
        sa.Column("node_base_url", sa.String(255), nullable=False),
        sa.Column("public_x509_cert", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. organisations
    op.create_table(
        "organisations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("country_iso", sa.String(3), sa.ForeignKey("brics_nodes.country_iso", ondelete="CASCADE"), nullable=False),
        sa.Column("org_name", sa.String(255), nullable=False),
        sa.Column("org_type", sa.String(64), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 4. users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("country_iso", sa.String(3), sa.ForeignKey("brics_nodes.country_iso", ondelete="RESTRICT"), nullable=False),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("phone_number", sa.String(32), unique=True, index=True, nullable=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("preferred_language", sa.String(10), server_default="en", nullable=False),
        sa.Column("role", sa.String(32), server_default="farmer", nullable=False),
        sa.Column("keycloak_sub", sa.String(36), unique=True, nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 5. consents
    op.create_table(
        "consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("share_anonymized_soil", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("share_outbreak_telemetry", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("participate_in_federated_learning", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 6. farms
    op.create_table(
        "farms",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("farm_name", sa.String(255), nullable=False),
        sa.Column("village_district", sa.String(255), nullable=True),
        sa.Column("state_province", sa.String(255), nullable=False),
        sa.Column("country_iso", sa.String(3), sa.ForeignKey("brics_nodes.country_iso", ondelete="RESTRICT"), nullable=False),
        sa.Column("total_area_hectares", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 7. fields
    op.create_table(
        "fields",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farm_id", sa.String(36), sa.ForeignKey("farms.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("boundary_geojson", sa.JSON(), nullable=False),
        sa.Column("centroid_lat", sa.Float(), nullable=False),
        sa.Column("centroid_lon", sa.Float(), nullable=False),
        sa.Column("area_hectares", sa.Float(), nullable=False),
        sa.Column("irrigation_type", sa.String(32), server_default="rainfed", nullable=False),
        sa.Column("current_crop", sa.String(100), nullable=True),
        sa.Column("sowing_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 8. crop_history
    op.create_table(
        "crop_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("field_id", sa.String(36), sa.ForeignKey("fields.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("crop_name", sa.String(100), nullable=False),
        sa.Column("fao_agrovoc_uri", sa.String(255), nullable=True),
        sa.Column("season_name", sa.String(64), nullable=False),
        sa.Column("sowing_date", sa.Date(), nullable=True),
        sa.Column("harvest_date", sa.Date(), nullable=True),
        sa.Column("yield_kg_ha", sa.Float(), nullable=True),
        sa.Column("fertilizers_applied", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 9. satellite_observations
    op.create_table(
        "satellite_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("field_id", sa.String(36), sa.ForeignKey("fields.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("acquisition_date", sa.DateTime(timezone=True), index=True, nullable=False),
        sa.Column("satellite_name", sa.String(64), server_default="Sentinel-2 L2A", nullable=False),
        sa.Column("cloud_cover_pct", sa.Float(), nullable=False),
        sa.Column("mean_ndvi", sa.Float(), nullable=False),
        sa.Column("p10_ndvi", sa.Float(), nullable=True),
        sa.Column("p90_ndvi", sa.Float(), nullable=True),
        sa.Column("mean_ndwi", sa.Float(), nullable=False),
        sa.Column("mean_evi", sa.Float(), nullable=False),
        sa.Column("raw_tile_geojson", sa.JSON(), nullable=True),
        sa.Column("s3_storage_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 10. soil_profiles
    op.create_table(
        "soil_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("field_id", sa.String(36), sa.ForeignKey("fields.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("data_source", sa.String(64), server_default="ISRIC SoilGrids 250m v2.0", nullable=False),
        sa.Column("depth_interval", sa.String(32), server_default="0-30cm", nullable=False),
        sa.Column("ph_h2o", sa.Float(), nullable=False),
        sa.Column("soil_organic_carbon_g_kg", sa.Float(), nullable=False),
        sa.Column("nitrogen_total_g_kg", sa.Float(), nullable=True),
        sa.Column("cation_exchange_capacity_cmol_kg", sa.Float(), nullable=True),
        sa.Column("clay_pct", sa.Float(), nullable=False),
        sa.Column("sand_pct", sa.Float(), nullable=False),
        sa.Column("silt_pct", sa.Float(), nullable=False),
        sa.Column("bulk_density_cg_cm3", sa.Float(), nullable=True),
        sa.Column("soil_health_score", sa.Integer(), nullable=False),
        sa.Column("plain_language_interpretation", sa.Text(), nullable=False),
        sa.Column("sampled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 11. weather_snapshots
    op.create_table(
        "weather_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("field_id", sa.String(36), sa.ForeignKey("fields.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("snapshot_date", sa.Date(), index=True, nullable=False),
        sa.Column("temp_min_c", sa.Float(), nullable=False),
        sa.Column("temp_max_c", sa.Float(), nullable=False),
        sa.Column("precipitation_mm", sa.Float(), nullable=False),
        sa.Column("relative_humidity_pct", sa.Float(), nullable=False),
        sa.Column("wind_speed_kmh", sa.Float(), nullable=True),
        sa.Column("rainfall_anomaly_pct", sa.Float(), nullable=True),
        sa.Column("heat_stress_hours", sa.Integer(), server_default="0", nullable=False),
        sa.Column("frost_risk_detected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("drought_spei_index", sa.Float(), nullable=True),
        sa.Column("forecast_type", sa.String(32), server_default="7day_forecast", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 12. advisories
    op.create_table(
        "advisories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("field_id", sa.String(36), sa.ForeignKey("fields.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("hallucination_guard_passed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("top_3_crops", sa.JSON(), nullable=False),
        sa.Column("regenerative_practices", sa.JSON(), nullable=False),
        sa.Column("sowing_window", sa.JSON(), nullable=False),
        sa.Column("irrigation_schedule", sa.JSON(), nullable=False),
        sa.Column("organic_fertilizer_plan", sa.JSON(), nullable=False),
        sa.Column("explainability_signals", sa.JSON(), nullable=False),
        sa.Column("carbon_sequestration_t_ha", sa.Float(), nullable=True),
        sa.Column("water_saved_pct", sa.Integer(), nullable=True),
        sa.Column("yield_uplift_pct", sa.Integer(), nullable=True),
        sa.Column("disclaimer_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 13. advisory_actions
    op.create_table(
        "advisory_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("advisory_id", sa.String(36), sa.ForeignKey("advisories.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("calendar_day", sa.Integer(), nullable=False),
        sa.Column("action_title", sa.String(255), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("is_completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 14. knowledge_documents & knowledge_chunks
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("publishing_agency", sa.String(100), nullable=False),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("license_type", sa.String(64), server_default="CC-BY-4.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("fao_agrovoc_concept", sa.String(255), nullable=True),
        sa.Column("target_crop", sa.String(100), index=True, nullable=True),
        sa.Column("climate_zone", sa.String(100), nullable=True),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default="{}", nullable=False),
    )

    # 15. disease_detections & outbreak_aggregates
    op.create_table(
        "disease_detections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("farmer_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("field_id", sa.String(36), sa.ForeignKey("fields.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("image_s3_uri", sa.String(512), nullable=False),
        sa.Column("edge_prediction", sa.JSON(), nullable=True),
        sa.Column("gemini_vision_prediction", sa.JSON(), nullable=True),
        sa.Column("ensemble_prediction", sa.JSON(), nullable=False),
        sa.Column("primary_disease_name", sa.String(150), index=True, nullable=False),
        sa.Column("fao_agrovoc_uri", sa.String(255), nullable=True),
        sa.Column("severity_level", sa.String(32), server_default="moderate", nullable=False),
        sa.Column("organic_treatment", sa.Text(), nullable=False),
        sa.Column("chemical_treatment", sa.Text(), nullable=True),
        sa.Column("chemical_safety_warning", sa.Text(), nullable=True),
        sa.Column("prevention_measures", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("spread_risk_score", sa.String(32), server_default="low", nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "outbreak_aggregates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("country_iso", sa.String(3), sa.ForeignKey("brics_nodes.country_iso", ondelete="CASCADE"), nullable=False),
        sa.Column("disease_name", sa.String(150), index=True, nullable=False),
        sa.Column("affected_crop", sa.String(100), nullable=False),
        sa.Column("incident_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("risk_severity", sa.String(32), server_default="moderate", nullable=False),
        sa.Column("h3_hex_index", sa.String(32), index=True, nullable=False),
        sa.Column("centroid_lat", sa.Float(), nullable=False),
        sa.Column("centroid_lon", sa.Float(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
    )

    # 16. ml_models & model_cards & federated_rounds
    op.create_table(
        "ml_models",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_name", sa.String(150), nullable=False),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("license_type", sa.String(64), server_default="Apache-2.0", nullable=False),
        sa.Column("dpg_compliant", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "model_cards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), sa.ForeignKey("ml_models.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("version_tag", sa.String(32), nullable=False),
        sa.Column("accuracy_score", sa.Float(), nullable=False),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column("training_data_summary", sa.Text(), nullable=False),
        sa.Column("bias_limitations", sa.Text(), nullable=False),
        sa.Column("s3_weights_uri", sa.String(512), nullable=False),
        sa.Column("weights_sha256", sa.String(64), nullable=False),
        sa.Column("card_markdown", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "federated_rounds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), sa.ForeignKey("ml_models.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("participating_nodes", sa.JSON(), nullable=False),
        sa.Column("aggregation_strategy", sa.String(64), server_default="FedAvg-DP", nullable=False),
        sa.Column("epsilon_privacy_budget", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 17. agreements, analogues & impact
    op.create_table(
        "data_sharing_agreements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("signatory_country", sa.String(3), sa.ForeignKey("brics_nodes.country_iso", ondelete="RESTRICT"), nullable=False),
        sa.Column("agreement_title", sa.String(255), nullable=False),
        sa.Column("terms_url", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("ratified_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "climate_analogues",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_region", sa.String(150), nullable=False),
        sa.Column("source_country", sa.String(3), nullable=False),
        sa.Column("analogue_region", sa.String(150), nullable=False),
        sa.Column("analogue_country", sa.String(3), nullable=False),
        sa.Column("similarity_index", sa.Float(), nullable=False),
        sa.Column("successful_regenerative_practices", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "impact_metrics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("country_iso", sa.String(3), sa.ForeignKey("brics_nodes.country_iso", ondelete="CASCADE"), nullable=False),
        sa.Column("recorded_date", sa.Date(), index=True, nullable=False),
        sa.Column("active_farmers_count", sa.Integer(), nullable=False),
        sa.Column("total_area_under_regeneration_ha", sa.Float(), nullable=False),
        sa.Column("estimated_water_saved_m3", sa.Float(), nullable=False),
        sa.Column("estimated_co2e_sequestered_tonnes", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 18. audit_logs, notifications & message_sessions
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("client_ip", sa.String(45), nullable=True),
        sa.Column("details", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True, nullable=False),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(64), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "message_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("phone_number", sa.String(32), index=True, nullable=False),
        sa.Column("channel", sa.String(32), server_default="whatsapp", nullable=False),
        sa.Column("session_state", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("last_interaction", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("message_sessions")
    op.drop_table("notifications")
    op.drop_table("audit_logs")
    op.drop_table("impact_metrics")
    op.drop_table("climate_analogues")
    op.drop_table("data_sharing_agreements")
    op.drop_table("federated_rounds")
    op.drop_table("model_cards")
    op.drop_table("ml_models")
    op.drop_table("outbreak_aggregates")
    op.drop_table("disease_detections")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("advisory_actions")
    op.drop_table("advisories")
    op.drop_table("weather_snapshots")
    op.drop_table("soil_profiles")
    op.drop_table("satellite_observations")
    op.drop_table("crop_history")
    op.drop_table("fields")
    op.drop_table("farms")
    op.drop_table("consents")
    op.drop_table("users")
    op.drop_table("organisations")
    op.drop_table("brics_nodes")
