# Operational Runbook: SoilGrids / External Telemetry Outage

## 1. Alert Trigger
- **Alert**: `SoilGridsUnreachable` or HTTP 504 Gateway Timeout from `rest.isric.org`.
- **Impact**: Automatic soil profile fetching for newly registered fields is stalled.

## 2. Automated System Behavior
1. Cached soil profiles in PostgreSQL table `soil_profiles` serve all existing fields with zero external calls.
2. For un-cached coordinates, `ExternalServiceGuard` invokes the regional soil baseline fallback database (`data/soil_benchmarks/`).
3. Advisory pipeline applies the nearest agro-ecological zone default values (e.g. Vertisol/Clay for Vidarbha Cotton, Ferralsol for Mato Grosso Soybean).
4. Advisory output flags: `soil_data_source: "regional_agro_ecological_default"`.

## 3. Operator Action Steps
1. Verify endpoint latency:
   ```bash
   curl -I https://rest.isric.org/soilgrids/v2.0/properties/query
   ```
2. Enable Soil Telemetry Fallback Cache:
   Ensure `USE_REGIONAL_SOIL_FALLBACK=true` in deployment environment variables.
3. Review advisory logs for any unhandled telemetry ingestion errors.
