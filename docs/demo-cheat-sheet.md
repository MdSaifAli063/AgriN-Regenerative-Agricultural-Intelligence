# 📋 KrishiNet-BRICS — Demo Reliability Pack & Live Presentation Contingency Guide

> **Purpose**: This document guarantees flawless live presentations, conference demos, and investor/judge walkthroughs for KrishiNet-BRICS under all real-world conditions (including zero-connectivity venues, conference Wi-Fi failures, cloud API outages, or stage technical issues).

---

## 🎬 Part 1: 10-Scene Recorded-Video Shot List

Record these 10 clean, standardized screen captures (1080p60 or 4K30) as high-definition MP4/WebM backups before any high-stakes presentation. If live execution ever freezes or network fails, instantly switch to these video clips without breaking presentation stride.

| # | Scene Name | Primary Tool / UI | Key Message / Narrative | Timestamp Duration | Backup Video Filename |
|---|------------|-------------------|-------------------------|--------------------|-----------------------|
| **1** | **Multilingual WhatsApp Onboarding** | Mobile Screen / `/sim` | Farmer initiates greeting, chooses language (Hindi/Portuguese), reads sovereign data agreement, provides consent, and receives cryptographic receipt code. | 0:00 - 0:45 (45s) | `01_whatsapp_onboarding.mp4` |
| **2** | **AI Leaf Doctor & Biological IPM** | WhatsApp Chat Simulator | Farmer sends photo of pest/disease damage on cotton leaf. System runs Gemini 1.5 Flash + ONNX fallback, detects Bacterial Blight, and delivers biological treatment card (Trichoderma). | 0:45 - 1:30 (45s) | `02_leaf_doctor_diagnosis.mp4` |
| **3** | **Weather Forecast & Spray Window** | WhatsApp / Web Dashboard | Interactive 3-day microclimate forecast showing dynamic spray window calculation (safe wind, zero rain threshold, green/red spray advisory). | 1:30 - 2:10 (40s) | `03_weather_spray_window.mp4` |
| **4** | **Officer Human-in-the-Loop Escalation** | WhatsApp + Extension Web UI | Farmer requests human expert assistance. FSM transfers context to Extension Officer dashboard, assigns ticket number, and notifies officer. | 2:10 - 2:50 (40s) | `04_officer_escalation.mp4` |
| **5** | **Officer Bulk Pest Outbreak Broadcast** | Extension Officer Web Portal | Extension Officer targets 500 cotton farmers in Nagpur circle with high-urgency Fall Armyworm alert, previews recipient count, and dispatches bulk SMS/WhatsApp. | 2:50 - 3:35 (45s) | `05_bulk_broadcast_dispatch.mp4` |
| **6** | **Voice Note Query Transcription** | WhatsApp Audio / Web Sim | Illiterate/vernacular farmer sends a 5-second voice note in Hindi ("Meri fasal pe safed keede hain"). Backend transcribes speech-to-text and answers via audio/text. | 3:35 - 4:15 (40s) | `06_voice_note_transcription.mp4` |
| **7** | **Field Intelligence & Regenerative Map** | Farmer Web PWA (`/fields`) | Polygon boundary map displaying real-time NDVI vegetation index, soil moisture sentinel metrics, and 4-year cover crop rotation plan. | 4:15 - 5:00 (45s) | `07_field_intelligence_map.mp4` |
| **8** | **Data Sovereignty: Delete My Data** | Privacy Settings (`/consents`) | Farmer exercises DPDP/LGPD right-to-be-forgotten. One-click cryptographic shredding anomymizes coordinates, purges sessions, and issues audit receipt. | 5:00 - 5:40 (40s) | `08_delete_my_data_erasure.mp4` |
| **9** | **BRICS Cross-Border Federation Query** | Federation Portal (`/federation`) | Indian node issues an anonymous sovereign query to Brazilian EMBRAPA node for rust-resistant soybean genomics without exporting raw farmer PII. | 5:40 - 6:25 (45s) | `09_brics_federation_query.mp4` |
| **10** | **Chaos-Lite Resiliency & Instant DR** | Terminal + Prometheus/Grafana | Live database disruption simulated. Automatic failover completes with RTO < 0.05 seconds, preserving 100% session integrity. | 6:25 - 7:00 (35s) | `10_chaos_resilience_drill.mp4` |

---

## 📦 Part 2: Static Fallback Build Instructions

When presenting in environments with **strictly zero internet** or when cloud backends cannot be reached, run the pre-rendered static demonstration build. It executes directly in the browser with mock JSON fixtures and zero external network calls.

### 1. Build and Export the Static Web App
```bash
# Set environment variables for zero-network mock mode
export NEXT_PUBLIC_DEMO_MODE=true
export NEXT_PUBLIC_API_URL=http://localhost:3000/api/mock

# Build static HTML/JS export into apps/web/out
cd apps/web
npm run build:static
```

### 2. Run Local Static Web Server (No Python or Backend Required)
Using Node's zero-dependency serve package:
```bash
npx serve@latest out -p 3000
```
Or using standard Python 3:
```bash
python -m http.server 3000 --directory apps/web/out
```

### 3. Verify Offline Mock Endpoints
The static fallback contains built-in responses for all core demonstration user flows:
- `http://localhost:3000/hi/sim` — Full WhatsApp phone simulator with pre-recorded Hindi conversational responses.
- `http://localhost:3000/en/fields` — Pre-loaded Nagpur cotton field with simulated Sentinel-2 NDVI heatmap.
- `http://localhost:3000/en/advisory` — Pre-generated regenerative advisory card with biological pest controls.
- `http://localhost:3000/en/federation` — Mock BRICS node federation topology showing India, Brazil, and South Africa nodes green.

---

## 🛡️ Part 3: Laminated One-Page "If X Breaks, Do Y" Cheat Sheet

Keep this single-page emergency decision matrix printed next to your presentation laptop.

```
====================================================================================================
                        KRISHINET-BRICS — EMERGENCY PRESENTATION CHEAT SHEET
====================================================================================================

SYMPTOM                        ROOT CAUSE                           IMMEDIATE 10-SECOND FIX (DO Y)
----------------------------------------------------------------------------------------------------
1. Backend API (8000) won't    Python process crashed or port       Terminal 1:
   respond / Connection        8000 conflict.                       .venv\Scripts\python -m uvicorn app.main:app --port 8000
   refused                                                          Or kill conflict: npx kill-port 8000

2. WhatsApp Webhook does not   Ngrok expired or Twilio              Switch to local Web Phone Simulator immediately:
   receive incoming message    Cloud Sandbox webhook timeout.       Open browser: http://localhost:3000/en/sim
   from physical phone                                              Or CLI: .venv\Scripts\python scripts/sim_chat.py

3. Gemini 1.5 Flash API        Conference Wi-Fi dropped or          Backend automatically falls back to Edge ONNX model!
   returns 429/500/timeout     Google Cloud AI quota limit.         Ensure DEMO_MODE=true in .env to return instant
                                                                    high-accuracy cached biological treatment cards.

4. Celery / Redis background   Redis service not started or         In .env set: CELERY_TASK_ALWAYS_EAGER=true
   tasks not executing         Docker daemon paused.                This forces all background advisories and notifications
                                                                    to execute synchronously in the FastAPI main thread.

5. Database Locked Error       SQLite concurrent write lock         Run database recovery repair script:
   (sqlite3.OperationalError)  from stale test process.             .venv\Scripts\python scripts/restore_drill.py
                                                                    Or: rm krishinet_dev.db && alembic upgrade head

6. Next.js Web App won't       Node modules lock or webpack         Launch static fallback build:
   compile or crashes on run   hot-reload failure.                  python -m http.server 3000 --directory apps/web/out
                                                                    App is immediately live at http://localhost:3000

7. Voice Transcription fails   Microphone input audio not           The simulator automatically falls back to pre-recorded
   or Whisper model missing    converting to WAV or ffmpeg missing. mock Hindi transcription: "कपास की पत्ती पर धब्बे हैं"
                                                                    (Bacterial blight symptom query).

8. Complete Stage Internet     Conference venue lost all            Set DEMO_MODE=true in both .env and frontend.
   Blackout                    connectivity.                        KrishiNet is designed as an Edge-First sovereign system!
                                                                    Run everything on 127.0.0.1 without touching the internet.
====================================================================================================
```

---

## ⚡ Part 4: Emergency 60-Second Recovery Quick-Keys & Commands

If all running processes need a clean slate before stepping on stage, run this exact 3-step sequence:

```powershell
# 1. Kill any stray dev servers (Windows PowerShell)
Get-Process -Name "python", "node" -ErrorAction SilentlyContinue | Stop-Process -Force

# 2. Run Preflight Check to verify system integrity
.venv\Scripts\python scripts/preflight.py

# 3. Start Backend & Simulator in Demo Mode
$env:DEMO_MODE="true"
Start-Process powershell -ArgumentList ".venv\Scripts\python -m uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList ".venv\Scripts\python scripts/sim_chat.py --auto"
```

You are now 100% stage-ready.
