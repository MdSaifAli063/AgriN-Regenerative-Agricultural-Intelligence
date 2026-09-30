import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.core.config import settings
from app.core.database import Base, AsyncSessionLocal, async_engine
from app.models.user import BricsCountry, User, FarmerConsent
from app.models.farm import Farm, Field, SatelliteMetric, SoilProfile, WeatherRecord
from app.models.advisory import RegenerativeAdvisory, AgronomyKnowledgeDocument
from app.models.diagnostic import DiseaseDiagnosis, DiseaseOutbreak
from app.models.brics import FederatedModelRegistry, ClimateAnalogueMatch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("krishinet.seed")


async def seed_data():
    logger.info("Initializing database schema...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        result = await session.execute(select(BricsCountry).where(BricsCountry.code == "IND"))
        if result.scalar_one_or_none():
            logger.info("Database already seeded with BRICS data. Skipping.")
            return

        logger.info("Seeding BRICS partner nations...")
        countries = [
            BricsCountry(
                code="IND",
                name="India",
                national_registry_url="https://agricoop.nic.in",
                contact_agency="ICAR / Department of Agriculture & Farmers Welfare",
                public_signing_key="brics-rsa-pub-ind-icar-2026-v1",
                is_active=True
            ),
            BricsCountry(
                code="BRA",
                name="Brazil",
                national_registry_url="https://embrapa.br",
                contact_agency="EMBRAPA / Ministério da Agricultura e Pecuária",
                public_signing_key="brics-rsa-pub-bra-embrapa-2026-v1",
                is_active=True
            ),
            BricsCountry(
                code="ZAF",
                name="South Africa",
                national_registry_url="https://arc.agric.za",
                contact_agency="Agricultural Research Council (ARC)",
                public_signing_key="brics-rsa-pub-zaf-arc-2026-v1",
                is_active=True
            ),
            BricsCountry(
                code="CHN",
                name="China",
                national_registry_url="https://caas.cn",
                contact_agency="Chinese Academy of Agricultural Sciences (CAAS)",
                public_signing_key="brics-rsa-pub-chn-caas-2026-v1",
                is_active=True
            ),
            BricsCountry(
                code="RUS",
                name="Russia",
                national_registry_url="https://mcx.gov.ru",
                contact_agency="Ministry of Agriculture of the Russian Federation",
                public_signing_key="brics-rsa-pub-rus-mcx-2026-v1",
                is_active=True
            )
        ]
        session.add_all(countries)
        await session.flush()

        logger.info("Seeding demo users across roles...")
        farmer_ind = User(
            id="demo-farmer-id-india-001",
            country_code="IND",
            phone_number="+919876543210",
            email="ramesh.patil@krishinet.org",
            full_name="Ramesh Patil",
            preferred_language="hi",
            role="farmer",
            is_verified=True
        )
        farmer_bra = User(
            id="demo-farmer-id-brazil-002",
            country_code="BRA",
            phone_number="+5566998765432",
            email="mateus.silva@krishinet.org",
            full_name="Mateus Silva",
            preferred_language="pt",
            role="farmer",
            is_verified=True
        )
        farmer_zaf = User(
            id="demo-farmer-id-zaf-003",
            country_code="ZAF",
            phone_number="+27821234567",
            email="sipho.nkosi@krishinet.org",
            full_name="Sipho Nkosi",
            preferred_language="en",
            role="farmer",
            is_verified=True
        )
        officer = User(
            id="demo-officer-id-001",
            country_code="IND",
            phone_number="+919876500000",
            email="dr.priya.sharma@icar.gov.in",
            full_name="Dr. Priya Sharma (Agri Extension Officer)",
            preferred_language="en",
            role="extension_officer",
            is_verified=True
        )
        session.add_all([farmer_ind, farmer_bra, farmer_zaf, officer])
        await session.flush()

        # Seed consents
        for u in [farmer_ind, farmer_bra, farmer_zaf]:
            consent = FarmerConsent(
                farmer_id=u.id,
                share_anonymized_soil=True,
                share_disease_telemetry=True,
                participate_in_federated_learning=True
            )
            session.add(consent)

        # ====================================================================
        # 1. DEMO FARM 1: INDIA (Maharashtra, Wardha - Cotton Vertisol)
        # ====================================================================
        logger.info("Seeding Demo Farm 1: India (Maharashtra Cotton)...")
        farm_ind = Farm(
            id="demo-farm-india-001",
            user_id=farmer_ind.id,
            farm_name="Vidarbha Regenerative Cotton Farm",
            village_district="Wardha District",
            state_province="Maharashtra",
            country_code="IND",
            total_area_hectares=2.45
        )
        session.add(farm_ind)
        await session.flush()

        field_ind = Field(
            id="demo-field-india-001",
            farm_id=farm_ind.id,
            field_name="Plot 1 - Vertisol Cotton Parcel",
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [
                    [
                        [78.5833, 20.7453],
                        [78.5880, 20.7453],
                        [78.5880, 20.7490],
                        [78.5833, 20.7490],
                        [78.5833, 20.7453]
                    ]
                ]
            },
            centroid_lat=20.74715,
            centroid_lon=78.58565,
            area_hectares=2.45,
            irrigation_type="drip",
            current_crop="cotton",
            sowing_date=date(2026, 6, 18),
            previous_crops=[
                {"season": "2025-kharif", "crop": "cotton"},
                {"season": "2024-rabi", "crop": "chickpea"}
            ]
        )
        session.add(field_ind)
        await session.flush()

        soil_ind = SoilProfile(
            field_id=field_ind.id,
            source="ISRIC SoilGrids 250m v2.0",
            depth_slice="0-30cm",
            ph_water=7.4,
            organic_carbon_g_kg=6.8,
            total_nitrogen_g_kg=0.85,
            cation_exchange_capacity_cmolc_kg=38.5,
            clay_fraction_percentage=54.0,
            sand_fraction_percentage=18.0,
            silt_fraction_percentage=28.0,
            texture_class="clay",
            bulk_density_g_cm3=1.35,
            soil_health_score=68,
            score_interpretation="Moderate Health (Vertisol/Black Cotton Soil). High moisture retention; needs organic carbon enrichment and cover cropping."
        )
        session.add(soil_ind)

        # 90-day NDVI history
        today = datetime.now(timezone.utc)
        for i, val in enumerate([0.22, 0.26, 0.33, 0.42, 0.51, 0.60, 0.67, 0.65, 0.62, 0.61]):
            session.add(
                SatelliteMetric(
                    field_id=field_ind.id,
                    acquisition_date=today - timedelta(days=(9 - i) * 9),
                    satellite_source="Sentinel-2 L2A",
                    cloud_coverage_percentage=3.5,
                    mean_ndvi=val,
                    mean_ndwi=round(val * 0.4 - 0.05, 3),
                    mean_evi=round(val * 0.72, 3),
                    tile_geojson=None
                )
            )

        # ====================================================================
        # 2. DEMO FARM 2: BRAZIL (Mato Grosso, Sorriso - Soybean Oxisol)
        # ====================================================================
        logger.info("Seeding Demo Farm 2: Brazil (Mato Grosso Soybean)...")
        farm_bra = Farm(
            id="demo-farm-brazil-002",
            user_id=farmer_bra.id,
            farm_name="Fazenda Esperança Cerrado",
            village_district="Sorriso",
            state_province="Mato Grosso",
            country_code="BRA",
            total_area_hectares=18.5
        )
        session.add(farm_bra)
        await session.flush()

        field_bra = Field(
            id="demo-field-brazil-002",
            farm_id=farm_bra.id,
            field_name="Talhão 04 - Soja Regenerativa",
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [
                    [
                        [-55.7250, -12.5480],
                        [-55.7150, -12.5480],
                        [-55.7150, -12.5400],
                        [-55.7250, -12.5400],
                        [-55.7250, -12.5480]
                    ]
                ]
            },
            centroid_lat=-12.5440,
            centroid_lon=-55.7200,
            area_hectares=18.5,
            irrigation_type="rainfed",
            current_crop="soybean",
            sowing_date=date(2026, 10, 10),
            previous_crops=[
                {"season": "2025-safrinha", "crop": "maize"},
                {"season": "2024-safra", "crop": "soybean"}
            ]
        )
        session.add(field_bra)
        await session.flush()

        soil_bra = SoilProfile(
            field_id=field_bra.id,
            source="ISRIC SoilGrids 250m v2.0",
            depth_slice="0-30cm",
            ph_water=5.8,
            organic_carbon_g_kg=18.2,
            total_nitrogen_g_kg=1.45,
            cation_exchange_capacity_cmolc_kg=12.4,
            clay_fraction_percentage=42.0,
            sand_fraction_percentage=48.0,
            silt_fraction_percentage=10.0,
            texture_class="sandy_clay_loam",
            bulk_density_g_cm3=1.28,
            soil_health_score=82,
            score_interpretation="High Health (Cerrado Oxisol/Ferralsol). Highly weathered, good organic carbon from no-till; monitor phosphorus fixation."
        )
        session.add(soil_bra)

        for i, val in enumerate([0.31, 0.38, 0.49, 0.62, 0.74, 0.81, 0.79, 0.76, 0.75, 0.73]):
            session.add(
                SatelliteMetric(
                    field_id=field_bra.id,
                    acquisition_date=today - timedelta(days=(9 - i) * 9),
                    satellite_source="Sentinel-2 L2A",
                    cloud_coverage_percentage=5.0,
                    mean_ndvi=val,
                    mean_ndwi=round(val * 0.5 - 0.08, 3),
                    mean_evi=round(val * 0.82, 3),
                    tile_geojson=None
                )
            )

        # ====================================================================
        # 3. DEMO FARM 3: SOUTH AFRICA (Free State, Bothaville - Maize Sandy Loam)
        # ====================================================================
        logger.info("Seeding Demo Farm 3: South Africa (Free State Maize)...")
        farm_zaf = Farm(
            id="demo-farm-zaf-003",
            user_id=farmer_zaf.id,
            farm_name="Bothaville Maize Commons",
            village_district="Lejweleputswa",
            state_province="Free State",
            country_code="ZAF",
            total_area_hectares=12.0
        )
        session.add(farm_zaf)
        await session.flush()

        field_zaf = Field(
            id="demo-field-zaf-003",
            farm_id=farm_zaf.id,
            field_name="Camp B - Yellow Maize",
            boundary_geojson={
                "type": "Polygon",
                "coordinates": [
                    [
                        [26.6150, -27.3850],
                        [26.6250, -27.3850],
                        [26.6250, -27.3780],
                        [26.6150, -27.3780],
                        [26.6150, -27.3850]
                    ]
                ]
            },
            centroid_lat=-27.3815,
            centroid_lon=26.6200,
            area_hectares=12.0,
            irrigation_type="sprinkler",
            current_crop="maize",
            sowing_date=date(2026, 11, 5),
            previous_crops=[
                {"season": "2025-summer", "crop": "sunflower"},
                {"season": "2024-summer", "crop": "maize"}
            ]
        )
        session.add(field_zaf)
        await session.flush()

        soil_zaf = SoilProfile(
            field_id=field_zaf.id,
            source="ISRIC SoilGrids 250m v2.0",
            depth_slice="0-30cm",
            ph_water=6.2,
            organic_carbon_g_kg=7.4,
            total_nitrogen_g_kg=0.72,
            cation_exchange_capacity_cmolc_kg=8.2,
            clay_fraction_percentage=16.0,
            sand_fraction_percentage=68.0,
            silt_fraction_percentage=16.0,
            texture_class="sandy_loam",
            bulk_density_g_cm3=1.45,
            soil_health_score=59,
            score_interpretation="Fair Health (Arenosol / Sandy Loam). High infiltration, vulnerable to nitrogen leaching and wind erosion. Mulching essential."
        )
        session.add(soil_zaf)

        for i, val in enumerate([0.20, 0.25, 0.32, 0.41, 0.50, 0.58, 0.56, 0.53, 0.51, 0.50]):
            session.add(
                SatelliteMetric(
                    field_id=field_zaf.id,
                    acquisition_date=today - timedelta(days=(9 - i) * 9),
                    satellite_source="Sentinel-2 L2A",
                    cloud_coverage_percentage=2.1,
                    mean_ndvi=val,
                    mean_ndwi=round(val * 0.35 - 0.1, 3),
                    mean_evi=round(val * 0.65, 3),
                    tile_geojson=None
                )
            )

        # ====================================================================
        # 4. SEED SAMPLE REGENERATIVE ADVISORY FOR DEMO FARM 1
        # ====================================================================
        logger.info("Seeding Baseline Regenerative Advisory...")
        advisory = RegenerativeAdvisory(
            id="demo-advisory-india-001",
            field_id=field_ind.id,
            advisory_status="published",
            confidence_score=0.925,
            hallucination_guard_passed=True,
            top_crop_recommendations=[
                {
                    "crop_name": "Desi Cotton & Pigeonpea Intercrop",
                    "scientific_name": "Gossypium arboreum + Cajanus cajan",
                    "suitability_score": 0.94,
                    "expected_yield_range": "18-22 quintals/ha",
                    "water_need_mm": 550,
                    "climate_risk_rating": "low",
                    "market_demand": "High - organic textile export premium"
                },
                {
                    "crop_name": "Sorghum (Jowar)",
                    "scientific_name": "Sorghum bicolor",
                    "suitability_score": 0.89,
                    "expected_yield_range": "25-30 quintals/ha",
                    "water_need_mm": 400,
                    "climate_risk_rating": "very_low",
                    "market_demand": "High - domestic millet initiative"
                },
                {
                    "crop_name": "Chickpea (Gram)",
                    "scientific_name": "Cicer arietinum",
                    "suitability_score": 0.86,
                    "expected_yield_range": "14-17 quintals/ha",
                    "water_need_mm": 350,
                    "climate_risk_rating": "low",
                    "market_demand": "Moderate"
                }
            ],
            regenerative_practices=[
                {
                    "practice_name": "Cover Cropping with Sunn Hemp (Crotalaria juncea)",
                    "fao_category": "Conservation Agriculture",
                    "description": "Sow sunn hemp 45 days before primary crop to fix up to 80 kg N/ha and suppress nematodes.",
                    "cost_level": "low",
                    "soil_benefit": "Increases organic matter by 0.4% and enriches active biology.",
                    "carbon_benefit": "Est. 1.2 t CO2e/ha sequestered per season.",
                    "implementation_steps": [
                        "Broadcast seeds at 25 kg/ha after first light pre-monsoon shower.",
                        "Terminate at 50% flowering (day 45) using roller-crimper or shallow mulch incorporation."
                    ]
                },
                {
                    "practice_name": "Biochar and Farmyard Compost Blend",
                    "fao_category": "Soil Carbon Enhancement",
                    "description": "Apply 500 kg/ha of pyrolyzed crop residue biochar charged with jeevamrutha liquid bio-inoculant.",
                    "cost_level": "medium",
                    "soil_benefit": "Improves Vertisol aeration and reduces swelling/shrinkage cracking.",
                    "carbon_benefit": "Est. 2.1 t CO2e/ha recalcitrant carbon stored for decades.",
                    "implementation_steps": [
                        "Blend 1 part biochar with 4 parts aged cattle manure.",
                        "Apply along the crop furrow before drip irrigation."
                    ]
                },
                {
                    "practice_name": "Push-Pull Pest Management with Marigold & Castor",
                    "fao_category": "Integrated Pest Management (IPM)",
                    "description": "Plant African tall marigold border rows to trap bollworms and castor border rows to deflect spodoptera.",
                    "cost_level": "low",
                    "soil_benefit": "Eliminates need for synthetic pyrethroids, safeguarding beneficial mycorrhizae.",
                    "carbon_benefit": "Reduces farm chemical scope-3 emissions by 34%.",
                    "implementation_steps": [
                        "Plant 1 row of marigold every 16 rows of cotton.",
                        "Plant border perimeter of castor around the field boundary."
                    ]
                }
            ],
            sowing_window={
                "optimal_start": "2026-06-15",
                "optimal_end": "2026-06-28",
                "trigger_condition": "Accumulation of at least 75mm cumulative monsoon rain with soil moist to 15cm."
            },
            irrigation_schedule={
                "strategy": "Alternate Furrow / Pulse Drip",
                "frequency": "Every 4 days for 90 minutes during vegetative phase",
                "water_saving_pct": 38
            },
            organic_fertilizer_plan={
                "basal": "Neem cake (250 kg/ha) + Vermicompost (2 tonnes/ha)",
                "foliar": "Panchagavya 3% spray at 30, 60, and 90 DAS",
                "bio_fertilizer": "Rhizobium + PSB seed coating at 250g / 10kg seed"
            },
            action_calendar_30days=[
                {"day": 1, "task": "Field preparation: Subsoil aerator pass without overturning topsoil", "status": "pending"},
                {"day": 5, "task": "Broadcast green manure (Sunn Hemp) seeds", "status": "pending"},
                {"day": 12, "task": "Soil moisture check via NDVI satellite sync", "status": "pending"},
                {"day": 20, "task": "Install yellow sticky traps (10 per hectare) for early sucking pest monitoring", "status": "pending"},
                {"day": 30, "task": "Crimper termination of cover crop & furrow preparation", "status": "pending"}
            ],
            data_signals_cited={
                "satellite_ndvi": 0.61,
                "soil_ph": 7.4,
                "soil_organic_carbon": "6.8 g/kg (low, driving cover crop recommendation)",
                "clay_fraction": "54% (heavy Vertisol, requiring biochar aeration)",
                "precipitation_anomaly": "-14.2% (drought buffer required)"
            },
            carbon_sequestration_est_t_ha=2.85,
            water_conservation_est_pct=35,
            yield_uplift_est_pct=18,
            disclaimer_notice="Advisory generated by KrishiNet-BRICS AI Agronomy Engine validated against ICAR and FAO agro-ecological guidelines. In case of unexpected extreme weather, consult your district Krishi Vigyan Kendra (KVK)."
        )
        session.add(advisory)

        # ====================================================================
        # 5. SEED SAMPLE DISEASE DIAGNOSIS & OUTBREAK CLUSTER
        # ====================================================================
        logger.info("Seeding Disease Outbreaks & Sample Diagnostic...")
        outbreak_ind = DiseaseOutbreak(
            id="outbreak-ind-001",
            country_code="IND",
            disease_name="Cotton Bacterial Blight (Angular Leaf Spot)",
            affected_crop="Cotton",
            incident_count=14,
            risk_level="high",
            latitude=20.7500,
            longitude=78.5900,
            h3_hexagon_index="86608976fffffff",
            first_detected=today - timedelta(days=7),
            last_reported=today,
            active_advisory="High humidity (>75%) coupled with 32°C temperatures in Wardha district has accelerated Xanthomonas citri spread. Apply Pseudomonas fluorescens 10g/L immediately."
        )
        session.add(outbreak_ind)

        # Climate Analogue Seed
        analogue = ClimateAnalogueMatch(
            source_region="Vidarbha, Maharashtra",
            source_country="IND",
            analogue_region="Mato Grosso (Cerrado-Pantanal Ecotone)",
            analogue_country="BRA",
            bioclimatic_similarity_score=0.884,
            shared_crop_successes=[
                {"crop": "Soybean & Cotton Rotation", "yield_benefit": "+22%", "source": "EMBRAPA / ICAR Joint Study"}
            ],
            validated_regenerative_practices=[
                {"practice": "No-Till with Brachiaria mulching", "adoption_rate": "78% in Mato Grosso", "applicability_to_source": "High during Rabi season"}
            ]
        )
        session.add(analogue)

        await session.commit()
        logger.info("Successfully seeded all 3 BRICS demo farms and telemetry!")


if __name__ == "__main__":
    asyncio.run(seed_data())
