#!/usr/bin/env python3
"""
KrishiNet-BRICS - Economic Cost Modeling & Cloud Infrastructure Calculator.
Computes estimated monthly and annual operational expenditure (OpEx) across:
1. Compute & Cluster Hosting (Track A Serverless, Track B VPS, Track C Kubernetes)
2. Database & Object Storage (PostGIS, pgvector, MinIO / Cloudflare R2)
3. Generative AI Inference (Google Gemini 1.5 Flash input/output token spend)
4. Mobile Messaging Gateway (WhatsApp Cloud vs Twilio vs Africa's Talking SMS)
"""

import argparse
import json
import sys


def calculate_costs(num_farmers: int, channel: str = "whatsapp", country_iso: str = "IND") -> dict:
    # --------------------------------------------------------------------------
    # Assumptions per Active Farmer per Month
    # --------------------------------------------------------------------------
    advisories_per_month = 4
    diagnoses_per_month = 2
    chat_messages_per_month = 12

    # 1. Gemini AI Token Costs (Gemini 1.5 Flash pricing: $0.075/1M input, $0.30/1M output)
    # Average advisory prompt: 1,500 tokens in, 600 tokens out
    # Average disease report prompt: 800 tokens in, 400 tokens out
    total_input_tokens = num_farmers * (
        (advisories_per_month * 1500) + (diagnoses_per_month * 800)
    )
    total_output_tokens = num_farmers * (
        (advisories_per_month * 600) + (diagnoses_per_month * 400)
    )

    cost_gemini_input = (total_input_tokens / 1_000_000) * 0.075
    cost_gemini_output = (total_output_tokens / 1_000_000) * 0.30
    cost_gemini_monthly = cost_gemini_input + cost_gemini_output

    # 2. Messaging Gateway Costs
    # WhatsApp Meta Cloud API: ~ $0.005 per service conversation (first 1,000 free)
    # Twilio WhatsApp: ~ $0.005 base + $0.005 provider fee = $0.010 per session
    # SMS (India / Africa's Talking): ~ $0.006 per 160-char GSM-7 segment
    if channel == "whatsapp":
        if country_iso == "BRA":
            # Meta Cloud Direct
            billable_conversations = max(0, num_farmers - 1000)
            cost_messaging_monthly = billable_conversations * 0.005
        else:
            # Twilio WhatsApp Business
            cost_messaging_monthly = num_farmers * 0.009
    elif channel == "sms":
        # Average 15 segments/month per farmer
        cost_messaging_monthly = num_farmers * 15 * 0.006
    else: # Hybrid: 60% WhatsApp, 40% SMS
        cost_messaging_monthly = (num_farmers * 0.60 * 0.009) + (num_farmers * 0.40 * 15 * 0.006)

    # 3. Infrastructure & Hosting Tracks
    # Track A: Serverless (Free tier up to ~1,500 farmers, then scales linearly with Neon compute)
    if num_farmers <= 1500:
        cost_infra_track_a = 0.00
    elif num_farmers <= 10000:
        cost_infra_track_a = 25.00 # Neon Pro + Render Team
    else:
        cost_infra_track_a = 150.00

    # Track B: Single VPS (Hetzner / DigitalOcean 4 GB - 16 GB)
    if num_farmers <= 5000:
        cost_infra_track_b = 20.00 # 4 GB VPS
    elif num_farmers <= 25000:
        cost_infra_track_b = 45.00 # 8 GB VPS
    else:
        cost_infra_track_b = 95.00 # 16 GB VPS

    # Track C: Managed Kubernetes (GKE / EKS 3-node cluster + Cloud SQL HA)
    if num_farmers <= 10000:
        cost_infra_track_c = 140.00
    elif num_farmers <= 50000:
        cost_infra_track_c = 280.00
    else:
        cost_infra_track_c = 550.00

    # Storage (Cloudflare R2: $0.015 / GB-month, first 10 GB free)
    # Average leaf photo: 350 KB => 2 photos * 350 KB = 700 KB/farmer-month = 8.4 MB/farmer-year
    storage_gb = (num_farmers * 8.4) / 1024
    cost_storage = max(0.0, storage_gb - 10.0) * 0.015

    total_track_a = cost_gemini_monthly + cost_messaging_monthly + cost_infra_track_a + cost_storage
    total_track_b = cost_gemini_monthly + cost_messaging_monthly + cost_infra_track_b + cost_storage
    total_track_c = cost_gemini_monthly + cost_messaging_monthly + cost_infra_track_c + cost_storage

    return {
        "farmers": num_farmers,
        "channel": channel,
        "country": country_iso,
        "gemini_tokens": {
            "monthly_input_tokens": total_input_tokens,
            "monthly_output_tokens": total_output_tokens,
            "monthly_cost_usd": round(cost_gemini_monthly, 2),
        },
        "messaging": {
            "monthly_cost_usd": round(cost_messaging_monthly, 2),
        },
        "storage": {
            "annual_gb": round(storage_gb, 1),
            "monthly_cost_usd": round(cost_storage, 2),
        },
        "tracks_monthly_total_usd": {
            "track_a_serverless": round(total_track_a, 2),
            "track_b_vps": round(total_track_b, 2),
            "track_c_k8s": round(total_track_c, 2),
        },
        "cost_per_farmer_monthly_cents": {
            "track_a": round((total_track_a / num_farmers) * 100, 2),
            "track_b": round((total_track_b / num_farmers) * 100, 2),
            "track_c": round((total_track_c / num_farmers) * 100, 2),
        },
    }


def print_cost_table():
    print("=" * 80)
    print("🌾 KrishiNet-BRICS — Comprehensive Operational Cost Model (OpEx)")
    print("=" * 80)
    print(f"{'Farmer Cohort':<15} | {'Gemini AI':<10} | {'Messaging':<10} | {'Track A (PaaS)':<14} | {'Track B (VPS)':<13} | {'Track C (K8s)':<13}")
    print("-" * 80)

    cohorts = [1_000, 10_000, 100_000]
    for c in cohorts:
        res = calculate_costs(c, channel="hybrid", country_iso="IND")
        ai = f"${res['gemini_tokens']['monthly_cost_usd']}"
        msg = f"${res['messaging']['monthly_cost_usd']}"
        ta = f"${res['tracks_monthly_total_usd']['track_a_serverless']}/mo"
        tb = f"${res['tracks_monthly_total_usd']['track_b_vps']}/mo"
        tc = f"${res['tracks_monthly_total_usd']['track_c_k8s']}/mo"
        print(f"{c:<15,d} | {ai:<10} | {msg:<10} | {ta:<14} | {tb:<13} | {tc:<13}")

    print("=" * 80)
    print("💡 Cost per Farmer Efficiency:")
    for c in cohorts:
        res = calculate_costs(c, channel="hybrid", country_iso="IND")
        cents = res["cost_per_farmer_monthly_cents"]["track_b"]
        print(f"   - {c:,} Farmers on Track B VPS: {cents:.1f}¢ / farmer / month (~${(cents*12)/100:.2f}/year)")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="KrishiNet-BRICS Cost Calculator")
    parser.add_argument("--farmers", type=int, default=None, help="Number of farmers to model")
    parser.add_argument("--channel", choices=["whatsapp", "sms", "hybrid"], default="hybrid")
    parser.add_argument("--country", default="IND", help="Country ISO (IND, BRA, ZAF)")
    parser.add_argument("--json", action="store_true", help="Output results in raw JSON format")
    args = parser.parse_args()

    if args.farmers:
        data = calculate_costs(args.farmers, channel=args.channel, country_iso=args.country)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"\nCost projection for {args.farmers:,} farmers ({args.country}, {args.channel}):")
            print(f"  - Gemini Flash AI Tokens : ${data['gemini_tokens']['monthly_cost_usd']}/mo")
            print(f"  - Outbound Messaging     : ${data['messaging']['monthly_cost_usd']}/mo")
            print(f"  - Track A (Serverless)   : ${data['tracks_monthly_total_usd']['track_a_serverless']}/mo ({data['cost_per_farmer_monthly_cents']['track_a']}¢/farmer)")
            print(f"  - Track B (Single VPS)   : ${data['tracks_monthly_total_usd']['track_b_vps']}/mo ({data['cost_per_farmer_monthly_cents']['track_b']}¢/farmer)")
            print(f"  - Track C (Kubernetes)   : ${data['tracks_monthly_total_usd']['track_c_k8s']}/mo ({data['cost_per_farmer_monthly_cents']['track_c']}¢/farmer)")
    else:
        print_cost_table()


if __name__ == "__main__":
    main()
