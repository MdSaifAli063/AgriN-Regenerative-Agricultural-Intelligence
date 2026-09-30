import { http, HttpResponse } from "msw";

export const handlers = [
  // 1. Health & Demo Mode
  http.get("*/health/demo-mode", () => {
    return HttpResponse.json({
      demo_mode: true,
      dev_auth_bypass: true,
      node_id: "node-in-01",
      country: "IND",
      node_country: "IND",
      fallback_providers: [
        "Copernicus Sentinel-2 STAC Mock Layer",
        "ISRIC SoilGrids Deterministic Chemistry Engine",
        "Open-Meteo & NASA POWER 7-Day Resilient Forecasts",
        "Gemini 1.5/2.0 Grounded Agronomy Fallback Generator",
      ],
    });
  }),

  http.get("*/health/live", () => {
    return HttpResponse.json({ status: "alive", service: "KrishiNet-BRICS API" });
  }),

  http.get("*/health/ready", () => {
    return HttpResponse.json({
      status: "ready",
      demo_mode: true,
      components: { database: true, redis: true, minio: true, keycloak: true },
    });
  }),

  // 2. Auth & RBAC
  http.post("*/auth/dev-login", async ({ request }) => {
    const body = (await request.json()) as any;
    return HttpResponse.json({
      access_token: `mock-jwt-${body?.role || "farmer"}-${Date.now()}`,
      token_type: "bearer",
      role: body?.role || "farmer",
      expires_in_minutes: 1440,
    });
  }),

  http.get("*/auth/me", () => {
    return HttpResponse.json({
      id: "demo-farmer-001",
      full_name: "Ramesh Patel",
      phone_number: "+919876543210",
      country_iso: "IND",
      role: "farmer",
      roles: ["farmer"],
    });
  }),

  http.get("*/auth/roles", () => {
    return HttpResponse.json({
      roles: ["farmer", "extension_officer", "government_admin", "researcher"],
    });
  }),

  // 3. Onboarding & Fields
  http.post("*/onboarding", async ({ request }) => {
    const body = (await request.json()) as any;
    return HttpResponse.json({
      field_id: "fld-mock-2026",
      farmer_id: "demo-farmer-001",
      field_name: body?.field_name || "Demo Plot",
      crop_type: body?.crop_type || "Cotton",
      area_ha: body?.area_ha || 1.45,
      status: "created",
      message: "Field successfully onboarded with baseline satellite indexing.",
    });
  }),

  http.get("*/fields", () => {
    return HttpResponse.json([
      {
        id: "fld-001",
        farmer_id: "demo-farmer-001",
        name: "North Well Plot",
        crop_type: "Cotton",
        area_ha: 1.85,
        centroid_lat: 20.7453,
        centroid_lon: 78.5982,
        health_status: "healthy",
        latest_ndvi: 0.72,
        soil_health_score: 84,
        created_at: new Date().toISOString(),
      },
      {
        id: "fld-002",
        farmer_id: "demo-farmer-001",
        name: "Canal Terrace",
        crop_type: "Soybean",
        area_ha: 0.95,
        centroid_lat: 20.7481,
        centroid_lon: 78.6014,
        health_status: "watch",
        latest_ndvi: 0.45,
        soil_health_score: 68,
        created_at: new Date().toISOString(),
      },
    ]);
  }),

  // 4. Advisory
  http.get("*/advisories/current", () => {
    return HttpResponse.json({
      id: "adv-mock-01",
      field_id: "fld-001",
      confidence_level: "high",
      confidence_score: 0.88,
      needs_expert_escalation: false,
      what_to_do_today: {
        headline: "Apply Neem Biopesticide Before Morning Dew Clears",
        summary:
          "High relative humidity (84%) combined with daytime warmth has created conditions for fungal spore germination. Organic foliar spray is recommended.",
        urgency: "urgent",
        recommended_actions: [
          "Mix 5ml neem oil with 1 litre of water and organic soap surfactant",
          "Spray undersides of leaves where early lesions concentrate",
          "Avoid spraying during peak noon heat to prevent foliar scorching",
        ],
        read_aloud_text:
          "Today's advice: Apply neem biopesticide before morning dew clears to stop fungal spore germination.",
      },
      crop_recommendations: [
        {
          crop_name: "Cotton (Desi Organic)",
          suitability_score: 92,
          yield_estimate_range: "1.8 - 2.2 tonnes/ha",
          water_need_mm: 650,
          climate_risk_level: "low",
        },
        {
          crop_name: "Soybean (Intercrop)",
          suitability_score: 85,
          yield_estimate_range: "2.1 - 2.6 tonnes/ha",
          water_need_mm: 520,
          climate_risk_level: "low",
        },
      ],
      regenerative_practices: [
        {
          id: "rp-1",
          title: "Neem Cake Soil Amendment",
          summary: "Improves nitrogen retention and suppresses parasitic root-knot nematodes.",
          cost_level: "low",
          benefit_category: "soil_organic_matter",
          difficulty: "easy",
          verified_indigenous: true,
        },
      ],
      timeline_30d: [
        {
          id: "tl-1",
          day_offset: 1,
          date_iso: new Date().toISOString(),
          action_text: "Foliar neem biopesticide spray",
          category: "pest_scouting",
          is_completed: false,
          urgency: "urgent",
        },
        {
          id: "tl-2",
          day_offset: 4,
          date_iso: new Date().toISOString(),
          action_text: "Targeted drip irrigation run: 18mm",
          category: "irrigation",
          is_completed: false,
          urgency: "normal",
        },
      ],
      explainability: {
        signals_used: [
          { name: "Relative Humidity", value: "84%", support: "supports" },
          { name: "NDVI Anomaly", value: "+0.08", support: "supports" },
        ],
        top_drivers: [
          {
            feature: "Soil Moisture Deficit",
            impact: "positive",
            magnitude: 0.35,
            description: "Drip efficiency prevents waterlogging.",
          },
        ],
        sources: [
          {
            id: "cit-1",
            title: "ICAR Integrated Pest Management in Cotton",
            source: "Indian Council of Agricultural Research",
          },
        ],
        counterfactual:
          "If humidity dropped below 60%, biopesticide spray would be optional.",
      },
      provenance: {
        source: "KrishiNet-BRICS Advisory Engine",
        mode: "demo",
        fetched_at: new Date().toISOString(),
        ttl: 3600,
        confidence: 0.88,
      },
    });
  }),

  // 5. Disease Diagnosis
  http.post("*/disease/diagnose", () => {
    return HttpResponse.json({
      detection_id: "det-mock-2026",
      primary_disease_name: "Rice Blast",
      primary_disease_label: "rice_blast",
      canonical_name: "Rice Blast (Magnaporthe oryzae)",
      fao_agrovoc_uri: "http://aims.fao.org/aos/agrovoc/c_25344",
      severity_level: "moderate",
      spread_risk_score: "moderate",
      top_3_predictions: [
        { label: "rice_blast", confidence: 0.82, canonical_name: "Rice Blast" },
        { label: "brown_spot", confidence: 0.12, canonical_name: "Brown Spot" },
        { label: "healthy", confidence: 0.06, canonical_name: "Healthy" },
      ],
      ensemble_confidence: 0.82,
      organic_treatment:
        "Foliar application of Pseudomonas fluorescens (20g/L) or neem leaf extract.",
      chemical_treatment:
        "Tricyclazole 75% WP @ 0.6g/L water in case of severe threshold breaches.",
      chemical_safety_warning:
        "Mandatory Safety Notice: Wear protective mask and gloves. Observe 14-day pre-harvest interval.",
      prevention_measures: [
        "Avoid excessive nitrogenous fertiliser application.",
        "Ensure field drainage to reduce prolonged leaf wetness.",
        "Use certified blast-resistant seed varieties.",
      ],
      weather_risk_amplified: true,
      weather_risk_factors: ["High relative humidity > 80% with night chill"],
      visual_reasoning:
        "Diamond-shaped elliptical spindle lesions with greyish center visible on leaf blade.",
      is_healthy: false,
      confidence_sufficient: true,
      confidence_guard_threshold: 0.42,
      fusion_strategy: "weighted_sum",
      edge_weight: 0.55,
      gemini_weight: 0.45,
      ood_rejected: false,
      model_version: "demo_v1",
      created_at: new Date().toISOString(),
    });
  }),

  // 6. Outbreak Feeds
  http.get("*/disease/outbreak/feed", () => {
    return HttpResponse.json({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [78.6, 20.7] },
          properties: {
            h3_index: "86618844fffffff",
            disease_label: "rice_blast",
            disease_name: "Rice Blast",
            reported_cases: 12,
            severity: "high",
            is_spike: true,
            period_start: new Date(Date.now() - 604800000).toISOString(),
            period_end: new Date().toISOString(),
          },
        },
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [-47.9, -15.8] },
          properties: {
            h3_index: "86618840fffffff",
            disease_label: "soybean_rust",
            disease_name: "Soybean Rust",
            reported_cases: 7,
            severity: "medium",
            is_spike: false,
            period_start: new Date(Date.now() - 604800000).toISOString(),
            period_end: new Date().toISOString(),
          },
        },
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [28.0473, -26.2041] },
          properties: {
            h3_index: "86618843fffffff",
            disease_label: "maize_gray_leaf_spot",
            disease_name: "Gray Leaf Spot (Cercospora zeae-maydis)",
            reported_cases: 19,
            severity: "medium",
            is_spike: false,
            period_start: new Date(Date.now() - 604800000).toISOString(),
            period_end: new Date().toISOString(),
          },
        },
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [116.4074, 39.9042] },
          properties: {
            h3_index: "86618849fffffff",
            disease_label: "wheat_rust_yellow",
            disease_name: "Stripe Rust (Puccinia striiformis)",
            reported_cases: 31,
            severity: "high",
            is_spike: true,
            period_start: new Date(Date.now() - 604800000).toISOString(),
            period_end: new Date().toISOString(),
          },
        },
      ],
    });
  }),

  // 7. Disease History & Offline Sync
  http.get("*/disease/history", () => {
    return HttpResponse.json([
      {
        detection_id: "det-001",
        field_id: "fld-001",
        crop: "Cotton",
        disease_name: "Cotton Leaf Curl Disease (CLCuD)",
        severity_level: "moderate",
        ensemble_confidence: 0.84,
        image_s3_uri: "/images/leaf-curl-demo.jpg",
        created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
        is_healthy: false,
      },
      {
        detection_id: "det-002",
        field_id: "fld-001",
        crop: "Cotton",
        disease_name: "Healthy Plant Tissue",
        severity_level: "mild",
        ensemble_confidence: 0.94,
        image_s3_uri: "/images/healthy-cotton.jpg",
        created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
        is_healthy: true,
      },
      {
        detection_id: "det-003",
        field_id: "fld-002",
        crop: "Soybean",
        disease_name: "Asian Soybean Rust",
        severity_level: "severe",
        ensemble_confidence: 0.89,
        image_s3_uri: "/images/soy-rust.jpg",
        created_at: new Date(Date.now() - 86400000 * 10).toISOString(),
        is_healthy: false,
      },
    ]);
  }),

  http.post("*/disease/offline/sync", async ({ request }) => {
    const body = (await request.json()) as any;
    const items = body?.items || [];
    return HttpResponse.json({
      synced_count: items.length,
      errors_count: 0,
      results: items.map((it: any) => ({
        client_id: it.client_id,
        detection_id: `det-sync-${Date.now()}`,
        status: "synced",
      })),
    });
  }),

  // 8. Phase 7 BRICS Federation, Model Hub & Sovereign Governance
  http.get("*/federation/impact/summary", () => {
    return HttpResponse.json({
      total_brics_hectares_regenerated: 1425800,
      total_brics_farmers_reached: 512400,
      total_brics_water_saved_megalitres: 8940,
      total_brics_co2e_sequestered_tonnes: 218500,
      participating_countries_count: 9,
      methodology: "IPCC Tier 1 Default Factors (2019 Refinement) + Empirical Drip & Agroforestry Trials",
      generated_at: new Date().toISOString(),
    });
  }),

  http.get("*/nodes", () => {
    return HttpResponse.json([
      {
        node_id: "node-ind-01",
        country_code: "IND",
        country_name: "India (ICAR / KrishiNet)",
        organisation_name: "Indian Council of Agricultural Research",
        is_active: true,
        farmers_count: 248000,
        hectares_regenerated: 680000,
        water_saved_megalitres: 4200,
        co2e_sequestered_tonnes: 104000,
      },
      {
        node_id: "node-bra-01",
        country_code: "BRA",
        country_name: "Brazil (Embrapa)",
        organisation_name: "Empresa Brasileira de Pesquisa Agropecuária",
        is_active: true,
        farmers_count: 142000,
        hectares_regenerated: 490000,
        water_saved_megalitres: 3100,
        co2e_sequestered_tonnes: 76000,
      },
      {
        node_id: "node-zaf-01",
        country_code: "ZAF",
        country_name: "South Africa (ARC)",
        organisation_name: "Agricultural Research Council",
        is_active: true,
        farmers_count: 48000,
        hectares_regenerated: 135000,
        water_saved_megalitres: 920,
        co2e_sequestered_tonnes: 21000,
      },
      {
        node_id: "node-chn-01",
        country_code: "CHN",
        country_name: "China (CAAS)",
        organisation_name: "Chinese Academy of Agricultural Sciences",
        is_active: true,
        farmers_count: 56000,
        hectares_regenerated: 98000,
        water_saved_megalitres: 580,
        co2e_sequestered_tonnes: 14500,
      },
      {
        node_id: "node-rus-01",
        country_code: "RUS",
        country_name: "Russia (VIGRR)",
        organisation_name: "All-Russian Institute of Plant Genetic Resources",
        is_active: true,
        farmers_count: 18400,
        hectares_regenerated: 22800,
        water_saved_megalitres: 140,
        co2e_sequestered_tonnes: 3000,
      },
    ]);
  }),

  http.get("*/models/catalog", () => {
    return HttpResponse.json([
      {
        id: "mdl-001",
        model_name: "MobileNetV3-BRICS-Disease-Int8",
        version: "2.4.0",
        crop_coverage: ["Cotton", "Rice", "Wheat", "Tomato", "Soybean", "Maize"],
        accuracy_score: 0.912,
        quantization: "int8",
        size_mb: 4.8,
        license_type: "Apache 2.0 / BRICS Open Science",
        download_count: 12400,
        download_url: "/models/mobilenetv3_brics_disease_int8.onnx",
        weights_sha256: "a4f89d38c20173e4b780df294bb89e623c0f49c0d127ef8c0a370e7a884e62a1",
      },
      {
        id: "mdl-002",
        model_name: "ResNet50-SoilCarbon-Predictor",
        version: "1.2.0",
        crop_coverage: ["Soil Organic Carbon", "Bulk Density", "Moisture Capacity"],
        accuracy_score: 0.885,
        quantization: "fp16",
        size_mb: 42.1,
        license_type: "CC-BY 4.0",
        download_count: 3820,
        download_url: "/models/resnet50_soil_carbon_fp16.onnx",
        weights_sha256: "7f920dae5033c4bc08d810f69bc43891040523f46f3918da8c340dfa16631c0e",
      },
      {
        id: "mdl-003",
        model_name: "CropET-HighRes-WaterBalance",
        version: "3.0.1",
        crop_coverage: ["Drip Irrigation", "Canopy Evapotranspiration", "Stress Index"],
        accuracy_score: 0.934,
        quantization: "int8",
        size_mb: 3.2,
        license_type: "BRICS Multi-Lateral Data Exchange",
        download_count: 8900,
        download_url: "/models/crop_et_water_balance_int8.onnx",
        weights_sha256: "c98321af4320e8b19a93ef092147fceb5a837492c10b48a129df83921bca9082",
      },
    ]);
  }),

  http.get("*/federation/climate-analogues", () => {
    return HttpResponse.json([
      {
        source_region: "Vidarbha, Maharashtra",
        source_country: "India",
        analogue_region: "Cerrado Biosphere, Bahia / Mato Grosso",
        analogue_country: "Brazil",
        similarity_index: 0.89,
        successful_regenerative_practices: [
          "No-till multi-species cover cropping with Pigeonpea + Sunn Hemp",
          "Neem seed cake in-furrow amendment for moisture barrier",
          "Micro-swales and contour terracing reducing runoff by 43%",
        ],
      },
      {
        source_region: "Free State Highveld",
        source_country: "South Africa",
        analogue_region: "Malwa Plateau, Madhya Pradesh",
        analogue_country: "India",
        similarity_index: 0.84,
        successful_regenerative_practices: [
          "Windbreak agroforestry with indigenous Acacia and Moringa",
          "Biochar and gypsum combined amendment restoring calcium-sodium balance",
          "Deficit drip scheduling tuned to critical vegetative flowering",
        ],
      },
      {
        source_region: "Northeast Plain, Heilongjiang",
        source_country: "China",
        analogue_region: "Volga Black Soil Basin",
        analogue_country: "Russia",
        similarity_index: 0.92,
        successful_regenerative_practices: [
          "Strip-tillage leaving 60% residue mulch on soil surface",
          "Cold-tolerant mycorrhizal inoculants increasing root nutrient uptake",
          "Snow-trapping stubble management preserving 80mm meltwater",
        ],
      },
    ]);
  }),

  http.post("*/federation/rounds/simulate", async () => {
    return HttpResponse.json({
      simulation_id: "sim-fl-test-01",
      model_name: "KrishiNet-BRICS-YieldPredictor",
      rounds_executed: 3,
      participating_nodes: ["node-ind-01", "node-bra-01", "node-zaf-01"],
      initial_accuracy: 0.898,
      final_accuracy: 0.924,
      accuracy_delta: 0.026,
      final_loss: 0.284,
      total_epsilon_consumed: 0.50,
      zero_raw_data_transferred: true,
      byzantine_attacks_defended: 1,
      candidate_version: "v2.5.0-rc1",
      status: "converged",
    });
  }),

  http.get("*/federation/egress/report", () => {
    return HttpResponse.json({
      node_id: "node-ind-01",
      country_iso: "IND",
      generated_at: new Date().toISOString(),
      total_egress_events: 184,
      passed_events_count: 184,
      blocked_events_count: 0,
      zero_pii_confirmed: true,
      active_sharing_agreements_count: 3,
      scope_breakdown: {
        outbreak_aggregates: 120,
        impact_aggregates: 38,
        model_exchange: 26,
      },
      recent_audit_records: [
        {
          id: "aud-001",
          destination_type: "registry",
          destination_id: "brics-commons-registry-01",
          scope: "outbreak_aggregates",
          payload_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          payload_summary: { features: 12, k_anonymity: 5, resolution: "H3-Res6" },
          passed_egress_gate: true,
          timestamp: new Date().toISOString(),
        },
      ],
    });
  }),

  http.get("*/consents/ledger", () => {
    return HttpResponse.json([
      {
        block_index: 2,
        prev_hash: "9b3c4f728362842104a09dfbaec3081e74b88939c0490b411d9482f0c788c034",
        user_id: "farmer-anon-014",
        action: "UPDATE",
        scopes: {
          share_anonymized_soil: true,
          share_outbreak_telemetry: true,
          participate_in_federated_learning: true,
        },
        reason: "Farmer joined federated model improvement cohort",
        timestamp: new Date().toISOString(),
        receipt_id: "rec-8402-9472",
        block_hash: "a4f89d38c20173e4b780df294bb89e623c0f49c0d127ef8c0a370e7a884e62a1",
      },
      {
        block_index: 1,
        prev_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        user_id: "farmer-anon-009",
        action: "REVOKE",
        scopes: {
          share_anonymized_soil: true,
          share_outbreak_telemetry: true,
          participate_in_federated_learning: false,
        },
        reason: "Farmer opted out of federated training (instant cohort purge)",
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        receipt_id: "rec-1940-5831",
        block_hash: "9b3c4f728362842104a09dfbaec3081e74b88939c0490b411d9482f0c788c034",
      },
    ]);
  }),

  http.get("*/consents/verify-ledger", () => {
    return HttpResponse.json({
      is_valid: true,
      total_blocks: 3,
      integrity_status: "VERIFIED_TAMPER_EVIDENT",
    });
  }),
];


