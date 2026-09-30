"""KrishiNet-BRICS - Idempotent Database Seeding Script.

Populates:
1. Sovereign BRICS partner nodes (IND, BRA, ZAF, CHN, RUS).
2. National agricultural research and extension organisations.
3. Demo users for all 4 RBAC roles (Farmer, Extension Officer, Admin, Researcher).
4. Sovereign farmer consents for cross-border telemetry.
5. Three realistic demo farms:
   - India (Vidarbha, Maharashtra - Cotton, Vertisol/black soil)
   - Brazil (Sorriso, Mato Grosso - Soybean, Cerrado Oxisol)
   - South Africa (Bothaville, Free State - Maize, Arenosol sandy loam)
6. Satellite metrics, soil profiles, weather records, and crop histories.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone

# Ensure services/api/src is on the module search path
current_dir = os.path.dirname(os.path.abspath(__file__))
api_src_dir = os.path.abspath(os.path.join(current_dir, "..", "services", "api", "src"))
if api_src_dir not in sys.path:
    sys.path.insert(0, api_src_dir)

from sqlalchemy import select, or_
from app.db.base import Base
from app.db.session import AsyncSessionLocal, async_engine
from app.models.node import BricsNode, Organisation
from app.models.user import User, Consent
from app.models.farm import Farm, Field, CropHistory
from app.models.telemetry import SatelliteObservation, SoilProfile, WeatherSnapshot
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("krishinet.seed")


async def seed():
    logger.info("Verifying database schema...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        logger.info("Upserting Sovereign BRICS Partner Nodes...")
        nodes_data = [
            ("IND", "Republic of India", "Indian Council of Agricultural Research (ICAR) & DA&FW", "https://ind.node.krishinet.brics.int"),
            ("BRA", "Federative Republic of Brazil", "Empresa Brasileira de Pesquisa Agropecuária (EMBRAPA)", "https://bra.node.krishinet.brics.int"),
            ("ZAF", "Republic of South Africa", "Agricultural Research Council (ARC)", "https://zaf.node.krishinet.brics.int"),
            ("CHN", "People's Republic of China", "Chinese Academy of Agricultural Sciences (CAAS)", "https://chn.node.krishinet.brics.int"),
            ("RUS", "Russian Federation", "Ministry of Agriculture & Russian Academy of Sciences", "https://rus.node.krishinet.brics.int"),
        ]
        for iso, name, agency, url in nodes_data:
            existing = (await session.execute(select(BricsNode).where(BricsNode.country_iso == iso))).scalar_one_or_none()
            if existing:
                existing.country_name = name
                existing.lead_agency = agency
                existing.node_base_url = url
            else:
                session.add(BricsNode(
                    country_iso=iso,
                    country_name=name,
                    lead_agency=agency,
                    node_base_url=url,
                    public_x509_cert="-----BEGIN CERTIFICATE-----\nMIIDXTCCAkWgAwIBAgIJAKRISHI_NODE_CERT_2026\n-----END CERTIFICATE-----",
                    is_active=True,
                ))
        await session.flush()

        logger.info("Upserting Research & Extension Organisations...")
        orgs_data = [
            ("org-ind-icar-01", "IND", "ICAR-Central Institute for Cotton Research (CICR)", "research_institute", "director.cicr@icar.gov.in"),
            ("org-bra-embrapa-01", "BRA", "Embrapa Soja / Cerrado Research Station", "research_institute", "contato.soja@embrapa.br"),
            ("org-zaf-arc-01", "ZAF", "ARC-Grain Crops Institute", "research_institute", "info@arc.agric.za"),
        ]
        for org_id, c_iso, name, o_type, email in orgs_data:
            existing_org = (await session.execute(select(Organisation).where(Organisation.id == org_id))).scalar_one_or_none()
            if existing_org:
                existing_org.org_name = name
                existing_org.contact_email = email
            else:
                session.add(Organisation(
                    id=org_id,
                    country_iso=c_iso,
                    org_name=name,
                    org_type=o_type,
                    contact_email=email,
                ))
        await session.flush()

        logger.info("Upserting Demo Users across 4 RBAC Roles...")
        dev_hash = get_password_hash("KrishiDemo2026!")

        users_spec = [
            {
                "id": "user-farmer-ind-001",
                "country_iso": "IND",
                "phone_number": "+919876543210",
                "email": "ramesh.patil@krishinet.org",
                "full_name": "Ramesh Patil",
                "preferred_language": "hi",
                "role": "farmer",
                "organisation_id": None,
            },
            {
                "id": "user-farmer-bra-002",
                "country_iso": "BRA",
                "phone_number": "+5566998765432",
                "email": "mateus.silva@krishinet.org",
                "full_name": "Mateus Silva",
                "preferred_language": "pt",
                "role": "farmer",
                "organisation_id": None,
            },
            {
                "id": "user-farmer-zaf-003",
                "country_iso": "ZAF",
                "phone_number": "+27821234567",
                "email": "sipho.nkosi@krishinet.org",
                "full_name": "Sipho Nkosi",
                "preferred_language": "en",
                "role": "farmer",
                "organisation_id": None,
            },
            {
                "id": "user-officer-ind-004",
                "country_iso": "IND",
                "phone_number": "+919123456789",
                "email": "priya.sharma@krishinet.org",
                "full_name": "Dr. Priya Sharma",
                "preferred_language": "en",
                "role": "extension_officer",
                "organisation_id": "org-ind-icar-01",
            },
            {
                "id": "user-admin-ind-005",
                "country_iso": "IND",
                "phone_number": "+919988776655",
                "email": "rajesh.kumar@krishinet.org",
                "full_name": "Rajesh Kumar",
                "preferred_language": "en",
                "role": "government_admin",
                "organisation_id": None,
            },
            {
                "id": "user-researcher-bra-006",
                "country_iso": "BRA",
                "phone_number": "+5561988887777",
                "email": "carlos.mendez@krishinet.org",
                "full_name": "Dr. Carlos Mendez",
                "preferred_language": "es",
                "role": "researcher",
                "organisation_id": "org-bra-embrapa-01",
            },
        ]

        created_user_ids = {}
        for spec in users_spec:
            # Query by id, phone_number, or email
            existing_user = (await session.execute(
                select(User).where(
                    or_(
                        User.id == spec["id"],
                        User.phone_number == spec["phone_number"],
                        User.email == spec["email"],
                    )
                )
            )).scalar_one_or_none()

            if existing_user:
                existing_user.full_name = spec["full_name"]
                existing_user.role = spec["role"]
                existing_user.password_hash = dev_hash
                existing_user.country_iso = spec["country_iso"]
                existing_user.organisation_id = spec["organisation_id"]
                existing_user.is_verified = True
                created_user_ids[spec["id"]] = existing_user.id
            else:
                new_user = User(
                    id=spec["id"],
                    country_iso=spec["country_iso"],
                    organisation_id=spec["organisation_id"],
                    phone_number=spec["phone_number"],
                    email=spec["email"],
                    password_hash=dev_hash,
                    full_name=spec["full_name"],
                    preferred_language=spec["preferred_language"],
                    role=spec["role"],
                    is_verified=True,
                )
                session.add(new_user)
                created_user_ids[spec["id"]] = spec["id"]
        await session.flush()

        logger.info("Upserting Farmer Consent Records...")
        farmer_ids = [
            created_user_ids["user-farmer-ind-001"],
            created_user_ids["user-farmer-bra-002"],
            created_user_ids["user-farmer-zaf-003"],
        ]
        for f_id in farmer_ids:
            existing_consent = (await session.execute(
                select(Consent).where(Consent.user_id == f_id)
            )).scalar_one_or_none()
            if not existing_consent:
                session.add(Consent(
                    user_id=f_id,
                    share_anonymized_soil=True,
                    share_outbreak_telemetry=True,
                    participate_in_federated_learning=True,
                ))
        await session.flush()

        logger.info("Upserting 3 Realistic Demo Farms...")

        # ---------------------------------------------------------------------
        # DEMO FARM 1: INDIA (Vidarbha Cotton Parcel)
        # ---------------------------------------------------------------------
        f_ind_id = created_user_ids["user-farmer-ind-001"]
        farm_ind = (await session.execute(
            select(Farm).where(Farm.id == "farm-ind-vidarbha-01")
        )).scalar_one_or_none()
        if not farm_ind:
            farm_ind = Farm(
                id="farm-ind-vidarbha-01",
                user_id=f_ind_id,
                farm_name="Patil Krishi Farm",
                village_district="Barshitakli, Akola District",
                state_province="Maharashtra",
                country_iso="IND",
                total_area_hectares=3.25,
            )
            session.add(farm_ind)
            await session.flush()

        field_ind = (await session.execute(
            select(Field).where(Field.id == "field-ind-vidarbha-cotton-01")
        )).scalar_one_or_none()
        if not field_ind:
            field_ind = Field(
                id="field-ind-vidarbha-cotton-01",
                farm_id=farm_ind.id,
                field_name="East Cotton Parcel",
                centroid_lat=20.5824,
                centroid_lon=77.0752,
                area_hectares=3.25,
                irrigation_type="rainfed",
                current_crop="cotton",
                sowing_date=date(2025, 6, 25),
                boundary_geojson={
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [77.0735, 20.5810],
                            [77.0770, 20.5812],
                            [77.0768, 20.5838],
                            [77.0732, 20.5835],
                            [77.0735, 20.5810],
                        ]
                    ],
                },
            )
            session.add(field_ind)
            await session.flush()

            now = datetime.now(timezone.utc)
            session.add(SatelliteObservation(
                id="sat-ind-vidarbha-01",
                field_id=field_ind.id,
                acquisition_date=now - timedelta(days=3),
                satellite_name="Sentinel-2 L2A",
                cloud_cover_pct=2.1,
                mean_ndvi=0.582,
                p10_ndvi=0.490,
                p90_ndvi=0.665,
                mean_ndwi=0.215,
                mean_evi=0.442,
            ))
            session.add(SoilProfile(
                id="soil-ind-vidarbha-01",
                field_id=field_ind.id,
                data_source="ISRIC SoilGrids 250m v2.0",
                depth_interval="0-30cm",
                ph_h2o=8.10,
                soil_organic_carbon_g_kg=5.20,
                nitrogen_total_g_kg=0.45,
                cation_exchange_capacity_cmol_kg=48.5,
                clay_pct=56.2,
                sand_pct=18.4,
                silt_pct=25.4,
                bulk_density_cg_cm3=1.35,
                soil_health_score=68,
                plain_language_interpretation="Deep Vertisol (black cotton soil) with excellent moisture retention and cation buffering. Moderate organic carbon deficit. Advised: Apply Farmyard Manure (FYM) and retain pigeonpea residues to enhance soil biology.",
            ))
            session.add(WeatherSnapshot(
                id="weather-ind-vidarbha-01",
                field_id=field_ind.id,
                snapshot_date=date.today(),
                temp_min_c=23.4,
                temp_max_c=33.8,
                precipitation_mm=4.2,
                relative_humidity_pct=72.0,
                wind_speed_kmh=12.5,
                rainfall_anomaly_pct=-8.5,
                heat_stress_hours=2,
                frost_risk_detected=False,
                drought_spei_index=-0.35,
            ))
            session.add(CropHistory(
                id="crophist-ind-cotton-01",
                field_id=field_ind.id,
                crop_name="cotton",
                fao_agrovoc_uri="http://aims.fao.org/aos/agrovoc/c_1907",
                season_name="Kharif 2024",
                sowing_date=date(2024, 6, 20),
                harvest_date=date(2024, 12, 10),
                yield_kg_ha=1450.0,
                fertilizers_applied=[{"name": "DAP", "kg_ha": 50}, {"name": "Urea", "kg_ha": 65}],
            ))

        # ---------------------------------------------------------------------
        # DEMO FARM 2: BRAZIL (Sorriso Cerrado Soybean Parcel)
        # ---------------------------------------------------------------------
        f_bra_id = created_user_ids["user-farmer-bra-002"]
        farm_bra = (await session.execute(
            select(Farm).where(Farm.id == "farm-bra-sorriso-02")
        )).scalar_one_or_none()
        if not farm_bra:
            farm_bra = Farm(
                id="farm-bra-sorriso-02",
                user_id=f_bra_id,
                farm_name="Fazenda Boa Esperança",
                village_district="Gleba Teles Pires, Sorriso",
                state_province="Mato Grosso",
                country_iso="BRA",
                total_area_hectares=118.5,
            )
            session.add(farm_bra)
            await session.flush()

        field_bra = (await session.execute(
            select(Field).where(Field.id == "field-bra-sorriso-soy-02")
        )).scalar_one_or_none()
        if not field_bra:
            field_bra = Field(
                id="field-bra-sorriso-soy-02",
                farm_id=farm_bra.id,
                field_name="Pivô Central 01 - Soja",
                centroid_lat=-12.5428,
                centroid_lon=-55.7214,
                area_hectares=118.5,
                irrigation_type="sprinkler",
                current_crop="soybean",
                sowing_date=date(2025, 10, 15),
                boundary_geojson={
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-55.7280, -12.5480],
                            [-55.7140, -12.5480],
                            [-55.7140, -12.5370],
                            [-55.7280, -12.5370],
                            [-55.7280, -12.5480],
                        ]
                    ],
                },
            )
            session.add(field_bra)
            await session.flush()

            now = datetime.now(timezone.utc)
            session.add(SatelliteObservation(
                id="sat-bra-sorriso-02",
                field_id=field_bra.id,
                acquisition_date=now - timedelta(days=2),
                satellite_name="Sentinel-2 L2A",
                cloud_cover_pct=5.4,
                mean_ndvi=0.745,
                p10_ndvi=0.680,
                p90_ndvi=0.812,
                mean_ndwi=0.342,
                mean_evi=0.628,
            ))
            session.add(SoilProfile(
                id="soil-bra-sorriso-02",
                field_id=field_bra.id,
                data_source="ISRIC SoilGrids 250m v2.0",
                depth_interval="0-30cm",
                ph_h2o=5.85,
                soil_organic_carbon_g_kg=18.4,
                nitrogen_total_g_kg=1.42,
                cation_exchange_capacity_cmol_kg=12.8,
                clay_pct=42.0,
                sand_pct=48.0,
                silt_pct=10.0,
                bulk_density_cg_cm3=1.22,
                soil_health_score=84,
                plain_language_interpretation="Latossolo Vermelho (Cerrado Oxisol) under established no-till cover cropping (Plantio Direto). Strong aggregate stability and organic carbon density. Advised: Continue Brachiaria cover crop rotation.",
            ))
            session.add(WeatherSnapshot(
                id="weather-bra-sorriso-02",
                field_id=field_bra.id,
                snapshot_date=date.today(),
                temp_min_c=22.1,
                temp_max_c=31.5,
                precipitation_mm=18.6,
                relative_humidity_pct=84.0,
                wind_speed_kmh=8.4,
                rainfall_anomaly_pct=14.2,
                heat_stress_hours=0,
                frost_risk_detected=False,
                drought_spei_index=0.85,
            ))

        # ---------------------------------------------------------------------
        # DEMO FARM 3: SOUTH AFRICA (Bothaville Highveld Maize Parcel)
        # ---------------------------------------------------------------------
        f_zaf_id = created_user_ids["user-farmer-zaf-003"]
        farm_zaf = (await session.execute(
            select(Farm).where(Farm.id == "farm-zaf-bothaville-03")
        )).scalar_one_or_none()
        if not farm_zaf:
            farm_zaf = Farm(
                id="farm-zaf-bothaville-03",
                user_id=f_zaf_id,
                farm_name="Vrystaat Mielies Boerdery",
                village_district="Nala Local Municipality, Bothaville",
                state_province="Free State",
                country_iso="ZAF",
                total_area_hectares=44.8,
            )
            session.add(farm_zaf)
            await session.flush()

        field_zaf = (await session.execute(
            select(Field).where(Field.id == "field-zaf-bothaville-maize-03")
        )).scalar_one_or_none()
        if not field_zaf:
            field_zaf = Field(
                id="field-zaf-bothaville-maize-03",
                farm_id=farm_zaf.id,
                field_name="North Pivot Maize",
                centroid_lat=-27.3812,
                centroid_lon=26.6201,
                area_hectares=44.8,
                irrigation_type="sprinkler",
                current_crop="maize",
                sowing_date=date(2025, 11, 20),
                boundary_geojson={
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [26.6150, -27.3850],
                            [26.6250, -27.3850],
                            [26.6250, -27.3780],
                            [26.6150, -27.3780],
                            [26.6150, -27.3850],
                        ]
                    ],
                },
            )
            session.add(field_zaf)
            await session.flush()

            now = datetime.now(timezone.utc)
            session.add(SatelliteObservation(
                id="sat-zaf-bothaville-03",
                field_id=field_zaf.id,
                acquisition_date=now - timedelta(days=4),
                satellite_name="Sentinel-2 L2A",
                cloud_cover_pct=1.0,
                mean_ndvi=0.512,
                p10_ndvi=0.440,
                p90_ndvi=0.580,
                mean_ndwi=0.154,
                mean_evi=0.384,
            ))
            session.add(SoilProfile(
                id="soil-zaf-bothaville-03",
                field_id=field_zaf.id,
                data_source="ISRIC SoilGrids 250m v2.0",
                depth_interval="0-30cm",
                ph_h2o=6.42,
                soil_organic_carbon_g_kg=8.10,
                nitrogen_total_g_kg=0.72,
                cation_exchange_capacity_cmol_kg=9.4,
                clay_pct=14.5,
                sand_pct=76.2,
                silt_pct=9.3,
                bulk_density_cg_cm3=1.48,
                soil_health_score=72,
                plain_language_interpretation="Hutton / Clovelly Arenosol (sandy loam). Highly permeable with fast infiltration; vulnerable to nitrogen leaching. Advised: Staggered nitrogen applications and retention of maize stover mulch to conserve moisture.",
            ))
            session.add(WeatherSnapshot(
                id="weather-zaf-bothaville-03",
                field_id=field_zaf.id,
                snapshot_date=date.today(),
                temp_min_c=14.2,
                temp_max_c=27.4,
                precipitation_mm=0.0,
                relative_humidity_pct=42.0,
                wind_speed_kmh=16.8,
                rainfall_anomaly_pct=-22.0,
                heat_stress_hours=0,
                frost_risk_detected=False,
                drought_spei_index=-0.82,
            ))

        await session.commit()
        logger.info("Successfully committed all KrishiNet-BRICS seed records!")

        print("\n" + "=" * 80)
        print("  KRISHINET-BRICS - DEMO SEEDING COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"{'Role':<20} | {'Country':<8} | {'Email':<30} | {'Password'}")
        print("-" * 80)
        print(f"{'Farmer (India)':<20} | {'IND':<8} | {'ramesh.patil@krishinet.org':<30} | {'KrishiDemo2026!'}")
        print(f"{'Farmer (Brazil)':<20} | {'BRA':<8} | {'mateus.silva@krishinet.org':<30} | {'KrishiDemo2026!'}")
        print(f"{'Farmer (S. Africa)':<20} | {'ZAF':<8} | {'sipho.nkosi@krishinet.org':<30} | {'KrishiDemo2026!'}")
        print(f"{'Extension Officer':<20} | {'IND':<8} | {'priya.sharma@krishinet.org':<30} | {'KrishiDemo2026!'}")
        print(f"{'Government Admin':<20} | {'IND':<8} | {'rajesh.kumar@krishinet.org':<30} | {'KrishiDemo2026!'}")
        print(f"{'Researcher':<20} | {'BRA':<8} | {'carlos.mendez@krishinet.org':<30} | {'KrishiDemo2026!'}")
        print("=" * 80)
        print("Seeded Farms:")
        print("  1. India: Patil Krishi Farm (Maharashtra, IND) - 3.25 ha (Cotton/Vertisol)")
        print("  2. Brazil: Fazenda Boa Esperança (Mato Grosso, BRA) - 118.5 ha (Soybean/Oxisol)")
        print("  3. South Africa: Vrystaat Mielies Boerdery (Free State, ZAF) - 44.8 ha (Maize/Arenosol)")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(seed())
