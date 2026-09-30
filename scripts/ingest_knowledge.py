"""
KrishiNet-BRICS - Knowledge Base Ingestion & Embedding Precomputation Script.

Writes 28 original open agronomic guidance notes into data/seed/knowledge/
and idempotently indexes them into the database with precomputed embeddings.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, List

# Ensure services/api/src is on module path
current_dir = os.path.dirname(os.path.abspath(__file__))
api_src = os.path.abspath(os.path.join(current_dir, "..", "services", "api", "src"))
if api_src not in sys.path:
    sys.path.insert(0, api_src)

from app.db.session import AsyncSessionLocal
from app.services.rag.embedding import embedding_service
from app.services.rag.ingestion import ingestion_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("krishinet.ingest")

SEED_KNOWLEDGE_DIR = os.path.abspath(os.path.join(current_dir, "..", "data", "seed", "knowledge"))

SEED_NOTES: List[Dict[str, str]] = [
    {
        "filename": "01_cotton_rainfed_vertisol.md",
        "title": "Rainfed Cotton Management on Deep Black Vertisols",
        "crop": "cotton",
        "region": "India-Vertisol, semi-arid",
        "practice": "water_harvesting",
        "content": """---
title: Rainfed Cotton Management on Deep Black Vertisols
crop: cotton
region: India-Vertisol
practice: water_harvesting
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Rainfed Cotton Management on Deep Black Vertisols

## Soil Characteristics and Moisture Dynamics
Deep black soils (Vertisols) possess high montmorillonite clay fractions (40-60%) that expand upon wetting and contract upon drying. In rainfed semi-arid zones like Vidarbha, Vertisols provide extensive capillary water retention but suffer from severe waterlogging during intense monsoons and deep shrinkage cracks during dry spells.

## Broad Bed and Furrow (BBF) Cultivation
Constructing Broad Bed and Furrow (BBF) systems spaced at 1.5 m intervals (1 m wide raised bed flanked by 50 cm furrows on a 0.2-0.4% grade) solves both drainage and drought constraints. During heavy rainfall events exceeding 50 mm/day, furrows safely channel excess runoff without soil crusting. During dry intervals, in-situ moisture retention increases by 25-30% compared to flat sowing.

## Organic Mulching and Residue Management
Applying 3.0-4.0 t/ha of cotton stalks or sunn hemp residues as surface mulch after post-emergence weeding reduces evaporative losses by up to 35%, moderates rhizosphere temperatures, and promotes beneficial microbial biomass.
""",
    },
    {
        "filename": "02_cotton_pink_bollworm_ipm.md",
        "title": "Integrated Pest Management for Pink Bollworm in Cotton",
        "crop": "cotton",
        "region": "India-Vertisol, global cotton",
        "practice": "integrated_pest_management",
        "content": """---
title: Integrated Pest Management for Pink Bollworm in Cotton
crop: cotton
region: India-Vertisol
practice: integrated_pest_management
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Integrated Pest Management for Pink Bollworm in Cotton

## Early Detection and Monitoring
Pink bollworm (Pectinophora gossypiella) threatens cotton flowering and boll development. Install delta pheromone traps baited with gossyplure at a density of 5 traps per hectare starting 45 days after sowing. The economic threshold level (ETL) is 8 moths per trap per night for three consecutive nights, or 10% rosette flowers.

## Biological Control and Pheromone Mating Disruption
Release Trichogramma bactrae egg parasitoids at 150,000 parasitoids/ha weekly starting from early squaring. Implement mating disruption using PB Rope dispensers or microencapsulated pheromone formulations applied at peak moth emergence to suppress mating without toxic residues.

## Botanical Interventions and Resistance Management
Spray 5% neem seed kernel extract (NSKE) or azadirachtin 10,000 ppm at 2 ml/L during initial square formation as an oviposition deterrent. Avoid broad-spectrum synthetic pyrethroids during early stages to conserve predatory green lacewings and ladybird beetles.
""",
    },
    {
        "filename": "03_cotton_high_density_canopy.md",
        "title": "High Density Planting System (HDPS) for Rainfed Cotton",
        "crop": "cotton",
        "region": "India-Vertisol, rainfed",
        "practice": "crop_rotation",
        "content": """---
title: High Density Planting System (HDPS) for Rainfed Cotton
crop: cotton
region: India-Vertisol
practice: crop_rotation
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# High Density Planting System (HDPS) for Rainfed Cotton

## Agronomic Rationale and Density
Traditional hybrid cotton planted at 90x60 cm often suffers from prolonged vegetative growth and boll rot in late season rains. HDPS utilizes compact, semi-determinate cotton varieties planted at 60x10 cm or 45x10 cm (yielding 166,000 to 222,000 plants/ha).

## Synchronized Boll Maturation and Drought Escape
HDPS concentrates boll production onto fewer sympodial branches per plant, allowing the crop to finish within 130-150 days compared to 180-210 days for long-duration hybrids. This short duration minimizes exposure to terminal drought and late-season bollworm attacks.

## Canopy Pruning and Deficit Nutrition
Apply mepiquat chloride (growth regulator) at 45 and 65 days after sowing (20-25 g a.i./ha) to restrict excessive vegetative expansion and direct assimilates into square and boll retention.
""",
    },
    {
        "filename": "04_soybean_cerrado_inoculation.md",
        "title": "Biological Nitrogen Fixation and Inoculation in Cerrado Soybean",
        "crop": "soybean",
        "region": "Brazil-Cerrado, tropical Oxisol",
        "practice": "cover_cropping",
        "content": """---
title: Biological Nitrogen Fixation and Inoculation in Cerrado Soybean
crop: soybean
region: Brazil-Cerrado
practice: cover_cropping
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Biological Nitrogen Fixation and Inoculation in Cerrado Soybean

## Rhizobial Inoculation Protocol
In highly weathered Cerrado Oxisols (Latossolos), commercial soybean requires 300-350 kg N/ha for high yields (3.5-4.5 t/ha). Inoculating seed or furrow with selected Bradyrhizobium strains (B. japonicum SEMIA 5079 and B. elkanii SEMIA 5019) completely eliminates the need for synthetic nitrogen fertilizers.

## Co-Inoculation with Azospirillum brasilense
Co-inoculation combining Bradyrhizobium with Azospirillum brasilense (strains Ab-V5 and Ab-V6) stimulates auxin synthesis, resulting in 20-30% greater root surface area and improved water and phosphorus acquisition in low-fertility soils.

## Micronutrient Synergies (Cobalt and Molybdenum)
Apply cobalt (2-3 g/ha) and molybdenum (12-25 g/ha) via seed treatment or early foliar spray at V3 stage. Molybdenum is the vital cofactor for nitrogenase enzyme, while cobalt is required for rhizobial cobalamin synthesis.
""",
    },
    {
        "filename": "05_soybean_notill_mulch.md",
        "title": "No-Till Conservation Agriculture on Tropical Oxisols",
        "crop": "soybean",
        "region": "Brazil-Cerrado, tropical Oxisol",
        "practice": "no_till",
        "content": """---
title: No-Till Conservation Agriculture on Tropical Oxisols
crop: soybean
region: Brazil-Cerrado
practice: no_till
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# No-Till Conservation Agriculture on Tropical Oxisols

## Direct Seeding on Permanent Straw Cover (Plantio Direto)
Zero-tillage direct seeding into 6-10 t/ha of Brachiaria ruziziensis or millet stubble is the foundation of regenerative agriculture in the Brazilian Cerrado. Soil surface temperature drops by 8-12°C compared to conventional tillage, avoiding seedling heat death.

## Erosion Control and Macro-Porosity
Heavy tropical downpours exceeding 80 mm/hour cause catastrophic sheet erosion in conventionally tilled soils. A permanent residue mat retains kinetic raindrop energy, preserves biopores formed by decaying roots and earthworms, and raises infiltration rates fivefold.

## Organic Matter Accumulation in Tropical Conditions
Continuous no-till over 5-8 years increases soil organic carbon in the 0-10 cm layer from 1.2% to 2.8%, doubling effective cation exchange capacity (CEC) in kaolinitic soils.
""",
    },
    {
        "filename": "06_soybean_maize_rotation.md",
        "title": "Soybean and Safrinha Maize Double-Cropping Rotation",
        "crop": "soybean",
        "region": "Brazil-Cerrado",
        "practice": "crop_rotation",
        "content": """---
title: Soybean and Safrinha Maize Double-Cropping Rotation
crop: soybean
region: Brazil-Cerrado
practice: crop_rotation
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Soybean and Safrinha Maize Double-Cropping Rotation

## Crop Succession Dynamics
Planting early-maturing soybean (relative maturity group 7.8-8.2) in October allows harvest by mid-February, enabling immediate direct drilling of second-crop (Safrinha) maize intercropped with Brachiaria grass before the dry winter season begins.

## Nutrient Recycling and Carbon Pumping
Deep fibrous root systems of Safrinha maize and Brachiaria penetrate 1.5-2.0 m depth, recycling leached potassium and nitrate back to the soil surface while producing 8-12 t/ha of high C:N dry matter that protects the soil through the dry winter.

## Pest and Disease Break
Rotating legume soybean with C4 grass cereal breaks the reproductive cycles of soil-borne fungi (Macrophomina phaseolina, Sclerotinia sclerotiorum) and soybean cyst nematodes (Heterodera glycines).
""",
    },
    {
        "filename": "07_soybean_rust_monitoring.md",
        "title": "Asian Soybean Rust Agro-Climatic Warning and Management",
        "crop": "soybean",
        "region": "Brazil-Cerrado, tropical humid",
        "practice": "integrated_pest_management",
        "content": """---
title: Asian Soybean Rust Agro-Climatic Warning and Management
crop: soybean
region: Brazil-Cerrado
practice: integrated_pest_management
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Asian Soybean Rust Agro-Climatic Warning and Management

## Pathogen Ecology and Microclimate Drivers
Asian soybean rust (Phakopsora pachyrhizi) is an airborne fungal pathogen that spreads rapidly during periods of leaf wetness exceeding 6 hours combined with temperatures between 18°C and 28°C and relative humidity above 75%.

## Sanitised Sanitary Void (Vazio Sanitário)
Compliance with the national 90-day sanitary void (June to September) prevents living soybean volunteer hosts between seasons, starving fungal inocula and delaying first field infections in the summer crop.

## Preventive Multi-Site Fungicide Strategy
Apply protective multisite fungicides (mancozeb, copper oxychloride, or chlorothalonil) combined with site-specific triazoles or strobilurins at R1 (flowering) prior to canopy closure, rotating chemical groups to prevent single-site target resistance.
""",
    },
    {
        "filename": "08_maize_freestate_conservation.md",
        "title": "Conservation Agriculture for Rainfed Maize in the Free State",
        "crop": "maize",
        "region": "South Africa-Free State, Highveld",
        "practice": "no_till",
        "content": """---
title: Conservation Agriculture for Rainfed Maize in the Free State
crop: maize
region: South Africa-Free State
practice: no_till
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Conservation Agriculture for Rainfed Maize in the Free State

## Agro-Ecology of the Highveld Sandy Loam
The Free State Highveld is characterized by sandy loam Arenosols (low clay <15%, high sand >70%) with rapid percolation, low water storage capacity, and high susceptibility to wind erosion and plough-pan compaction.

## Stubble Retention and Wind Erosion Defense
Retaining at least 30% maize crop residue cover on the soil surface reduces spring wind erosion by up to 90%, preventing loss of nutrient-rich silt fractions and protecting emerging maize seedlings from sandblasting damage.

## Controlled Traffic Farming
Confining all heavy machinery wheel traffic to permanent tramlines avoids re-compacting the seedling zone. This increases effective root rooting depth from 25 cm to over 90 cm, unlocking deep subsoil moisture reserves during mid-summer heat waves.
""",
    },
    {
        "filename": "09_maize_pivot_irrigation_deficit.md",
        "title": "Center-Pivot Deficit Irrigation Scheduling for Maize",
        "crop": "maize",
        "region": "South Africa-Free State, commercial",
        "practice": "water_harvesting",
        "content": """---
title: Center-Pivot Deficit Irrigation Scheduling for Maize
crop: maize
region: South Africa-Free State
practice: water_harvesting
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Center-Pivot Deficit Irrigation Scheduling for Maize

## Critical Phenological Growth Stages
Maize water sensitivity varies dramatically across growth stages. Moderate water deficit during vegetative stages (V3-V8) encourages deep taproot exploration with minimal yield penalty. In contrast, water stress during silking and grain fill (VT-R2) causes pollination failure, kernel abortion, and yield losses up to 7% per day of stress.

## FAO-56 Evapotranspiration Deficit Scheduling
Calculate daily crop water demand using FAO-56 Penman-Monteith reference ET (ETo) multiplied by crop coefficient (Kc): V6 (Kc 0.7), Tasseling/Silking (Kc 1.2), Grain Fill (Kc 1.15), Maturity (Kc 0.6). Schedule center-pivot applications to maintain rhizosphere soil moisture between 60% and 85% of plant available water (PAW).

## Low-Energy Precision Application (LEPA)
Equipping pivots with flexible drop nozzles discharging water 30-50 cm above soil surface directly into furrows reduces wind drift and droplet evaporation losses by 15-20% compared to high-pressure overhead impact sprinklers.
""",
    },
    {
        "filename": "10_maize_fall_armyworm_ipm.md",
        "title": "Ecological Management of Fall Armyworm in Maize",
        "crop": "maize",
        "region": "South Africa-Free State, pan-African",
        "practice": "integrated_pest_management",
        "content": """---
title: Ecological Management of Fall Armyworm in Maize
crop: maize
region: South Africa-Free State
practice: integrated_pest_management
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Ecological Management of Fall Armyworm in Maize

## Scouting Protocol and Damage Thresholds
Fall armyworm (Spodoptera frugiperda) lays egg masses on lower leaf surfaces. Scout 20 consecutive plants in 5 representative locations per field twice weekly. The action threshold is 20% infested plants with fresh frass in vegetative stages (V3-V6) and 40% in late vegetative stages (V7-V12).

## Push-Pull Habitat Management
Intercropping maize with silverleaf desmodium (Desmodium uncinatum) acts as a repellent ("push"), emitting volatile semiochemicals that deter adult moth oviposition. Planting Napier grass (Pennisetum purpureum) or Brachiaria around field boundaries acts as a trap crop ("pull"), attracting moths away from maize.

## Biological Interventions in the Leaf Whorl
Apply Bacillus thuringiensis (Bt subsp. kurstaki) or Metarhizium rileyi biopesticides directed into the central leaf whorl where young larvae feed. Placing a pinch of dry wood ash or sand mixed with fine neem powder into the whorl causes physical desiccation and feeding deterrence in smallholder plots.
""",
    },
    {
        "filename": "11_cover_crops_biomass.md",
        "title": "Multi-Species Cover Crops for Soil Regeneration",
        "crop": "general",
        "region": "global, BRICS",
        "practice": "cover_cropping",
        "content": """---
title: Multi-Species Cover Crops for Soil Regeneration
crop: general
region: global
practice: cover_cropping
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Multi-Species Cover Crops for Soil Regeneration

## The Power of Diverse Functional Groups
Monoculture cover crops produce single-dimension benefits. Cocktail mixes combining at least three functional plant groups—grasses (e.g. sorghum-sudan, black oat), legumes (e.g. cowpea, sunn hemp, hairy vetch), and brassicas (e.g. tillage radish, mustard)—maximize soil ecological functions.

## Synergistic Below-Ground Root Architecture
Fibrous grass roots build aggregate stability in the top 15 cm; deep brassica taproots puncture compacted subsoil pans down to 1.2 m; legume roots host nitrogen-fixing nodules. Exudate diversity stimulates diverse mycorrhizal fungal networks that accelerate humus synthesis.

## Biomass Termination Methods
Terminate cover crop cocktails at 50% flowering using a roller-crimper or knife roller on sunny days. This forms a permanent, weed-suppressing mulch mat without herbicide dependency.
""",
    },
    {
        "filename": "12_intercropping_legume_cereal.md",
        "title": "Cereal-Legume Intercropping Systems for Nutrient Efficiency",
        "crop": "general",
        "region": "global, semi-arid",
        "practice": "intercropping",
        "content": """---
title: Cereal-Legume Intercropping Systems for Nutrient Efficiency
crop: general
region: global
practice: intercropping
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Cereal-Legume Intercropping Systems for Nutrient Efficiency

## Land Equivalent Ratio (LER) and Yield Stability
Intercropping cereals (maize, sorghum, pearl millet) with grain legumes (pigeon pea, cowpea, groundnut) regularly achieves a Land Equivalent Ratio (LER) of 1.25 to 1.50, meaning a monoculture would require 25-50% more land to produce identical total output.

## Nitrogen Facilitation and Direct Transfer
Legumes fix atmospheric nitrogen via rhizobial symbiosis. Part of this fixed nitrogen is directly transferred to the companion cereal crop through mycorrhizal fungal bridges and root exudate diffusion, reducing required synthetic N by 30-50 kg/ha.

## Temporal and Spatial Niche Differentiation
Planting combinations with staggered growth peaks (e.g. fast-canopy cowpea followed by tall, slow-maturing pigeon pea) optimizes sunlight interception, reduces surface water evaporation, and smothers weed flushes.
""",
    },
    {
        "filename": "13_crop_rotation_soil_nitrogen.md",
        "title": "Strategic Crop Rotation for Soil Carbon and Nitrogen Balancing",
        "crop": "general",
        "region": "global",
        "practice": "crop_rotation",
        "content": """---
title: Strategic Crop Rotation for Soil Carbon and Nitrogen Balancing
crop: general
region: global
practice: crop_rotation
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Strategic Crop Rotation for Soil Carbon and Nitrogen Balancing

## Breaking Monoculture Depletion
Monocropping depletes specific soil nutrient strata, accelerates soil-borne pathogen accumulation (e.g. Fusarium, Rhizoctonia), and limits the diversity of soil microbial communities. A 3-to-4 year diverse rotation restores biological equilibrium.

## Balancing C:N Ratios for Humus Synthesis
High C:N crops like maize and sorghum residues (C:N 60:1 to 80:1) break down slowly and provide durable surface cover. Low C:N legume residues (C:N 15:1 to 25:1) release mineral nitrogen rapidly. Alternating high and low C:N species sustains microbial carbon consumption and stable humic acid formation.

## Pest and Weed Lifecycle Disruption
Alternating broadleaf crops with grass crops allows mechanical, biological, and timing-based weed suppression, effectively breaking herbicide resistance cycles in problematic weeds.
""",
    },
    {
        "filename": "14_notill_soil_structure.md",
        "title": "Soil Structure and Aggregation Under Zero-Tillage",
        "crop": "general",
        "region": "global",
        "practice": "no_till",
        "content": """---
title: Soil Structure and Aggregation Under Zero-Tillage
crop: general
region: global
practice: no_till
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Soil Structure and Aggregation Under Zero-Tillage

## The Micro-Architecture of Healthy Soil
Mechanical inversion ploughing pulverizes soil macro-aggregates (>2 mm), exposes protected organic carbon to rapid oxidation by aerobic bacteria, and releases carbon dioxide into the atmosphere.

## Glomalin Production by Arbuscular Mycorrhizal Fungi
Under undisturbed zero-tillage, living root systems establish dense associations with Arbuscular Mycorrhizal Fungi (AMF). AMF hyphae secrete glomalin—an insoluble, hydrophobic glycoprotein that acts as biological mortar, cementing sand, silt, and clay particles into resilient water-stable aggregates.

## Infiltration and Internal Drainage
Intact vertical macropores created by earthworms (anecic species) and decayed root channels remain continuous from surface to subsoil. During sudden cloudbursts, water infiltrates downward by gravity rather than pooling and eroding valuable topsoil.
""",
    },
    {
        "filename": "15_composting_farmyard_manure.md",
        "title": "Aerobic Thermal Composting and Enriched Farmyard Manure",
        "crop": "general",
        "region": "global",
        "practice": "composting",
        "content": """---
title: Aerobic Thermal Composting and Enriched Farmyard Manure
crop: general
region: global
practice: composting
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Aerobic Thermal Composting and Enriched Farmyard Manure

## The 30:1 Carbon to Nitrogen Ratio
Aerobic composting requires blending brown, carbon-rich materials (straw, dry stalks, sawdust) with green, nitrogen-rich materials (cattle dung, poultry manure, green weeds) to achieve an initial C:N ratio near 25:1 to 30:1 with 50-60% moisture content.

## Thermophilic Pathogen Destruction
Turn compost windrows every 10-14 days. Internal pile temperatures must reach 55-65°C for at least 72 hours. This thermophilic phase destroys weed seeds, insect larvae, and plant pathogens while preserving beneficial spore-forming Bacillus and Trichoderma strains.

## Bio-Enrichment with Rock Phosphate and Microbes
Enrich maturing compost piles by adding 2-5% finely ground rock phosphate and microbial inoculants (Phosphate Solubilizing Bacteria and Trichoderma viride). The organic acids generated during organic matter maturation solubilize insoluble phosphates into plant-available orthophosphate.
""",
    },
    {
        "filename": "16_biochar_carbon_permanence.md",
        "title": "Biochar Application for Long-Term Carbon Sequestration and Soil CEC",
        "crop": "general",
        "region": "global",
        "practice": "biochar",
        "content": """---
title: Biochar Application for Long-Term Carbon Sequestration and Soil CEC
crop: general
region: global
practice: biochar
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Biochar Application for Long-Term Carbon Sequestration and Soil CEC

## Recalcitrant Aromatic Carbon Structure
Biochar produced through slow pyrolysis (350-550°C in an oxygen-limited atmosphere) of agricultural residues (cotton stalks, maize cobs, coconut shells) possesses a polycyclic aromatic carbon backbone resistant to microbial degradation for hundreds of years.

## High Porosity and Specific Surface Area
Biochar provides an internal surface area of 200-400 m²/g. This vast labyrinth of micropores serves as a permanent habitat for beneficial soil bacteria and mycorrhizal hyphae while dramatically increasing soil water holding capacity in sandy soils.

## Inoculation ('Charging') Before Application
Raw biochar can initially immobilize soil nitrogen if applied uncharged. Mix biochar with animal manure, compost, or microbial tea at a 1:4 ratio for 2-3 weeks prior to field application. Apply at 2.5-5.0 t/ha to achieve permanent increases in cation exchange capacity (CEC).
""",
    },
    {
        "filename": "17_mulching_thermoregulation.md",
        "title": "Residue Mulching for Soil Moisture Conservation and Temperature Control",
        "crop": "general",
        "region": "global, semi-arid",
        "practice": "mulching",
        "content": """---
title: Residue Mulching for Soil Moisture Conservation and Temperature Control
crop: general
region: global
practice: mulching
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Residue Mulching for Soil Moisture Conservation and Temperature Control

## Evaporative Moisture Suppression
In semi-arid tropical and subtropical regions, bare soil loses up to 60-70% of received rainwater to direct soil evaporation. A 5-8 cm layer of dry crop residues (straw, shredded stalks, stubble) creates a boundary layer that suppresses vapor loss by 30-45%.

## Thermal Buffering of the Rhizosphere
Extreme surface temperatures exceeding 42°C denature root enzymes and halt mycorrhizal nutrient transport. Organic mulch maintains topsoil temperatures in the optimal 24-30°C zone during midday heat spikes.

## Weed Seed Germination Suppression
Depriving emerging weed seedlings of light suppresses germination of photoblastic annual weeds by 70-85%, drastically lowering hand-weeding labor and chemical herbicide reliance.
""",
    },
    {
        "filename": "18_agroforestry_boundary_windbreaks.md",
        "title": "Boundary Agroforestry and Microclimate Windbreaks",
        "crop": "general",
        "region": "global",
        "practice": "agroforestry",
        "content": """---
title: Boundary Agroforestry and Microclimate Windbreaks
crop: general
region: global
practice: agroforestry
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Boundary Agroforestry and Microclimate Windbreaks

## Wind Speed Reduction and Evapotranspiration
Multi-tier tree shelterbelts established along prevailing windward boundaries reduce field wind velocities by 40-60% across a distance equal to 15-20 times the tree height. This substantially lowers crop evapotranspiration (ET) demand and prevents crop lodging.

## Deep Subsoil Nutrient Safety Net
Deep-rooted multipurpose trees (e.g. Faidherbia albida, Gliricidia sepium, Acacia nilotica) capture nitrates and sulfates that have leached below annual crop root zones. When tree foliage is pruned as green leaf manure, these nutrients are recycled to surface soils.

## Biodiversity Reservoirs for Natural Predators
Perennial boundary hedgerows provide stable overwintering habitats, nectar, and pollen for beneficial predators (syrphid flies, parasitic wasps, predatory mites) that maintain natural pest suppression in adjoining crop fields.
""",
    },
    {
        "filename": "19_ipm_biological_thresholds.md",
        "title": "Integrated Pest Management and Biological Scouting",
        "crop": "general",
        "region": "global",
        "practice": "integrated_pest_management",
        "content": """---
title: Integrated Pest Management and Biological Scouting
crop: general
region: global
practice: integrated_pest_management
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Integrated Pest Management and Biological Scouting

## The Economic Injury Level (EIL) Concept
Chemical sprays must never be applied according to fixed calendar dates. Sprays are only justified when pest populations cross the Economic Threshold (ETL)—the density at which control costs equal potential crop damage.

## Conservation of Natural Enemies
Preserving generalist predators (spiders, predatory stink bugs, coccinellid beetles, chrysopids) prevents secondary pest outbreaks. Spraying broad-spectrum pyrethroids frequently destroys natural enemies, triggering severe resurgence of mites, aphids, and whiteflies.

## Pheromones, Colored Sticky Traps, and Biocontrol
Install yellow sticky traps for whiteflies and aphids; blue sticky traps for thrips. Utilize targeted bio-pesticides (Bacillus thuringiensis, Beauveria bassiana, Trichoderma) that kill target insect orders without bioaccumulating in human food chains or aquatic ecosystems.
""",
    },
    {
        "filename": "20_water_harvesting_contour_bunds.md",
        "title": "In-Situ Water Harvesting and Contour Bunding",
        "crop": "general",
        "region": "global, drylands",
        "practice": "water_harvesting",
        "content": """---
title: In-Situ Water Harvesting and Contour Bunding
crop: general
region: global
practice: water_harvesting
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# In-Situ Water Harvesting and Contour Bunding

## Contour Bunds and Stone Terracing
On slopes between 1% and 6%, constructing earth or stone bunds along true elevation contours prevents runoff velocity from reaching erosive thresholds. Water ponds shallowly behind bunds, infiltrating into subsoil profiles.

## Continuous Contour Trenches (CCT) and Farm Ponds
Staggered contour trenches (50 cm wide x 30 cm deep) catch seasonal cloudburst runoff on upper catchments. Constructing lined on-farm collection ponds (krishi ponds) captures surplus peak monsoon runoff to provide 1-2 critical lifesaving supplemental irrigations during dry spells.

## Furrow Diking and Tied Ridges
In rainfed crop rows, placing small earth dams ('dikes') every 2-3 meters along furrows transforms each row into a series of micro-basins, holding all rainfall directly on the field where it falls.
""",
    },
    {
        "filename": "21_soil_acidity_liming_dolomite.md",
        "title": "Management of Acidic Soils and Liming with Dolomite",
        "crop": "general",
        "region": "Brazil-Cerrado, tropical humid",
        "practice": "composting",
        "content": """---
title: Management of Acidic Soils and Liming with Dolomite
crop: general
region: Brazil-Cerrado
practice: composting
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Management of Acidic Soils and Liming with Dolomite

## Aluminum Toxicity in Low pH Soils
When soil pH drops below 5.2, trivalent aluminum ions (Al3+) solubilize into the soil solution, severely poisoning root tips, causing stubby root syndrome, and permanently fixing applied phosphorus into insoluble aluminum phosphates.

## Dolomitic Limestone Application
Apply finely ground agricultural limestone or dolomitic limestone (containing both CaCO3 and MgCO3 with PRNT >80%) to neutralize active and exchangeable acidity. In no-till systems, apply lime uniformly over the surface 3-6 months before sowing; soluble humic substances facilitate gradual downward calcium transport.

## Agricultural Gypsum (Phosphogypsum) for Subsoil Acidity
Unlike limestone, agricultural gypsum (CaSO4.2H2O) does not alter soil pH but possesses 200-fold greater water solubility. Gypsum leaches rapidly into deep subsoil layers (20-60 cm), precipitating toxic aluminum into neutral complexes and supplying calcium to stimulate deep taproot expansion.
""",
    },
    {
        "filename": "22_low_soc_green_manuring.md",
        "title": "Restoring Depleted Soil Organic Carbon through Green Manuring",
        "crop": "general",
        "region": "global",
        "practice": "cover_cropping",
        "content": """---
title: Restoring Depleted Soil Organic Carbon through Green Manuring
crop: general
region: global
practice: cover_cropping
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Restoring Depleted Soil Organic Carbon through Green Manuring

## The Critical Threshold of 1.0% Soil Organic Carbon
Soils with SOC below 0.7-1.0% suffer from structural collapse, aggregate slaking, low water holding capacity, and rapid nutrient leaching. Restoring active carbon is prerequisite to achieving sustainable crop response from applied fertilizers.

## Fast-Growing Leguminous Green Manures
Broadcast sunn hemp (Crotalaria juncea) or Sesbania (Sesbania aculeata) at 25-30 kg/ha at the onset of early pre-monsoon rains. Within 45-50 days, these legumes accumulate 15-20 t/ha of green biomass containing 80-120 kg N/ha fixed from the atmosphere.

## Shallow Incorporation at Succulent Stage
Incorporate green manure crops into the top 10-15 cm while stems are still soft and succulent (at early flowering stage). Rapid microbial breakdown releases plant-available ammonium and organic acids that condition the soil for the subsequent cash crop.
""",
    },
    {
        "filename": "23_saline_sodic_gypsum_drainage.md",
        "title": "Reclamation of Saline and Sodic Soils with Gypsum and Drainage",
        "crop": "general",
        "region": "global, arid & semi-arid",
        "practice": "water_harvesting",
        "content": """---
title: Reclamation of Saline and Sodic Soils with Gypsum and Drainage
crop: general
region: global
practice: water_harvesting
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Reclamation of Saline and Sodic Soils with Gypsum and Drainage

## Distinguishing Saline from Sodic Soils
Saline soils contain high concentrations of neutral soluble salts (EC >4 dS/m, pH <8.5, ESP <15%), causing osmotic physiological drought. Sodic soils contain excessive exchangeable sodium (ESP >15%, pH >8.5), causing clay dispersion, severe surface crusting, and impermeability to water.

## Gypsum Requirement for Sodic Replacement
Apply mineral agricultural gypsum based on soil lab analysis (typically 3-8 t/ha). Calcium (Ca2+) replaces exchangeable sodium (Na+) on clay colloids. The displaced sodium sulfate must then be leached below the root zone via irrigation or heavy rains.

## Subsurface Drainage and Leaching Fraction
Reclamation fails without adequate drainage. Install deep field ditches or perforated sub-surface tile drains at 1.0-1.2 m depth to evacuate leached salts away from farm boundaries.
""",
    },
    {
        "filename": "24_drought_heat_stress_mitigation.md",
        "title": "Agro-Techniques for Mitigating Heat Waves and Drought Spikes",
        "crop": "general",
        "region": "global",
        "practice": "mulching",
        "content": """---
title: Agro-Techniques for Mitigating Heat Waves and Drought Spikes
crop: general
region: global
practice: mulching
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Agro-Techniques for Mitigating Heat Waves and Drought Spikes

## Physiological Impacts of Extreme Heat (>35°C)
Temperatures above 35°C during reproductive stages reduce pollen viability, cause flower abortion, inactivate photosynthetic enzymes, and induce severe stomatal closure that halts assimilate accumulation.

## Foliar Kaolin Clay Film Sprays
Spraying a 3-5% suspension of processed kaolin clay forms a reflective, white mineral barrier film on leaves. This film reflects infrared and excessive ultraviolet radiation, lowering canopy temperatures by 3-5°C while allowing photosynthetically active radiation (PAR) to penetrate.

## Potassium and Soluble Silicon Nutrition
Foliar applications of 1% potassium nitrate (KNO3) or soluble potassium silicate prior to forecast heat spikes maintain stomatal guard cell turgor and enhance antioxidant enzyme activity (SOD, catalase), protecting cellular membranes from lipid peroxidation.
""",
    },
    {
        "filename": "25_frost_protection_orchards_field.md",
        "title": "Passive and Active Frost Protection for Field Crops",
        "crop": "general",
        "region": "South Africa-Highveld, temperate",
        "practice": "water_harvesting",
        "content": """---
title: Passive and Active Frost Protection for Field Crops
crop: general
region: South Africa-Highveld
practice: water_harvesting
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Passive and Active Frost Protection for Field Crops

## Radiation vs. Advective Frost Events
Radiation frosts occur on clear, windless nights when heat radiates from ground into the atmosphere, creating a thermal inversion where coldest air pools in low-lying landscape pockets. Advective frosts occur when massive cold polar air masses move into a region.

## Soil Moisture Thermal Massing
Wet, firm soil conducts and stores 3-4 times more solar heat during daylight hours than dry, fluffed-up soil. Irrigating field plots 24-48 hours prior to an anticipated radiation frost creates a thermal heat reservoir that radiates upward overnight, elevating ground-level temperatures by 1.5-2.5°C.

## Cold Air Drainage Corridors
Avoid establishing frost-sensitive annual crops in low-lying concave hollows ('frost pockets'). Ensure field boundary hedgerows do not block down-slope cold air drainage routes.
""",
    },
    {
        "filename": "26_organic_first_fertiliser_planning.md",
        "title": "Organic-First Nutrient Management and Bio-Fertilisers",
        "crop": "general",
        "region": "global",
        "practice": "composting",
        "content": """---
title: Organic-First Nutrient Management and Bio-Fertilisers
crop: general
region: global
practice: composting
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Organic-First Nutrient Management and Bio-Fertilisers

## The Organic-First Hierarchy
1. Establish base biological fertility using 5-10 t/ha of well-rotted farmyard manure, vermicompost, or green manure.
2. Inoculate seeds and root zones with beneficial microbial biofertilizers (Azotobacter/Rhizobium for N, Bacillus megaterium for P, Frateuria aurantia for K).
3. Apply mineral supplements only to satisfy specific agronomic nutrient deficits indicated by soil testing.

## Phosphorus Solubilization in Alkaline and Acid Soils
Phosphate ions bind tenaciously to calcium in alkaline soils and to iron/aluminum in acid soils. Co-applying rock phosphate or single superphosphate blended into organic compost prevents direct soil fixation and increases phosphorus efficiency by 40%.

## Split Application and Placement Precision
When supplementary mineral fertilizers are required, split nitrogen into 2-3 applications timed to peak crop demand stages rather than broadcasting all upfront. Band fertilizer 5 cm below and 5 cm to the side of the seed line to avoid seedling salt burn.
""",
    },
    {
        "filename": "27_safe_pesticide_use_ppe_drift.md",
        "title": "Safe Pesticide Handling, Drift Management and Buffer Zones",
        "crop": "general",
        "region": "global",
        "practice": "integrated_pest_management",
        "content": """---
title: Safe Pesticide Handling, Drift Management and Buffer Zones
crop: general
region: global
practice: integrated_pest_management
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Safe Pesticide Handling, Drift Management and Buffer Zones

## Personal Protective Equipment (PPE) Essentials
Chemical pesticides are hazardous substances. Operators must wear chemical-resistant nitrile gloves, vapor respirators, eye goggles, and protective overalls during chemical measuring, mixing, and spraying. Never blow out clogged nozzles with the mouth.

## Spray Windows and Wind Drift Mitigation
Spray strictly during calm hours when wind speeds are between 3 km/h and 10 km/h. Do not spray during thermal inversions (early morning fog or dead calm) where ultra-fine droplets float horizontally for kilometers. Utilize air-induction low-drift nozzles operating at appropriate hydraulic pressure.

## Riparian Buffer Zones and Withholding Periods
Maintain an unsprayed buffer zone of at least 15-30 meters around rivers, ponds, and residential dwellings. Strictly respect the pre-harvest interval (PHI) / withholding period listed on product labels to guarantee zero chemical residues on harvested food.
""",
    },
    {
        "filename": "28_soil_compaction_subsoiling_radish.md",
        "title": "Remediating Soil Compaction with Deep Rippers and Bio-Drilling Radishes",
        "crop": "general",
        "region": "global",
        "practice": "no_till",
        "content": """---
title: Remediating Soil Compaction with Deep Rippers and Bio-Drilling Radishes
crop: general
region: global
practice: no_till
language: en
licence: CC-BY-4.0
source: KrishiNet seed note, summarised from open agronomy practice (FAO/ICAR/EMBRAPA-style)
---

# Remediating Soil Compaction with Deep Rippers and Bio-Drilling Radishes

## Identifying Subsoil Plough Pans
Years of heavy tractor traffic and shallow disc plowing form a dense, impervious plough pan at 15-25 cm depth (bulk density >1.55 g/cm³), physically blocking root penetration and creating perched water tables that drown crop roots.

## Biological Drilling with Tillage Radish (Raphanus sativus)
Planting deep-rooting forage/tillage radish at 6-8 kg/ha produces thick taproots that exert up to 2.5 MPa of downward pressure, punching through compacted subsoil pans down to 70-90 cm. When radishes decompose in winter, they leave continuous, open root channels that subsequent crop roots follow deep into the profile.

## Non-Inversion Subsoiling (Chisel Ripping)
When severe mechanical compaction requires rapid intervention, operate a non-inversion subsoil ripper spaced at 60 cm intervals 5-10 cm beneath the compacted layer during dry soil conditions to shatter the pan without bringing unweathered subsoil to the surface.
""",
    },
]


async def generate_and_ingest():
    """Writes all 28 seed notes and indexes them into the database with embeddings."""
    os.makedirs(SEED_KNOWLEDGE_DIR, exist_ok=True)
    logger.info(f"Writing {len(SEED_NOTES)} seed notes to {SEED_KNOWLEDGE_DIR}...")

    file_paths = []
    for note in SEED_NOTES:
        path = os.path.join(SEED_KNOWLEDGE_DIR, note["filename"])
        with open(path, "w", encoding="utf-8") as f:
            f.write(note["content"].strip() + "\n")
        file_paths.append(path)

    logger.info("Ingesting notes into database...")
    async with AsyncSessionLocal() as session:
        for path in file_paths:
            await ingestion_service.ingest_file(db=session, file_path=path)

    # Save embeddings to data/seed/knowledge_embeddings.json
    embedding_service.save_cache()
    logger.info("Successfully ingested all seed notes and saved embedding cache!")


if __name__ == "__main__":
    asyncio.run(generate_and_ingest())
