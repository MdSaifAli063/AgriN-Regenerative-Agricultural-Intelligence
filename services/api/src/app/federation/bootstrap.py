"""
KrishiNet-BRICS - Node Federation Bootstrap CLI.
Automates country onboarding in under one day:
1. Generates sovereign Ed25519 keypair
2. Assembles node passport & capabilities
3. Performs cryptographic handshake with the BRICS Commons Registry
4. Writes local node configuration
"""

import argparse
import json
import os
import sys
from pathlib import Path
import httpx
from app.federation.identity import NodeIdentity


def bootstrap_node(
    country_code: str,
    org_name: str,
    registry_url: str,
    api_base_url: str,
    node_id: str,
    contact_email: str,
    keys_dir: Path,
    config_output: Path,
) -> bool:
    print(f"\n==================================================================")
    print(f"  KRISHINET-BRICS: SOVEREIGN NODE BOOTSTRAP INITIALIZATION")
    print(f"==================================================================")
    print(f"[*] Target Country       : {country_code.upper()}")
    print(f"[*] Sovereign Institution: {org_name}")
    print(f"[*] Node ID              : {node_id}")
    print(f"[*] Registry Endpoint    : {registry_url}")
    print(f"[*] Node API URL         : {api_base_url}")
    print(f"[*] Key Storage Dir      : {keys_dir}")

    # 1. Generate or load Ed25519 keypair
    print("\n[1/4] Generating Sovereign Ed25519 Cryptographic Identity...")
    identity = NodeIdentity.load_or_create(keys_dir, node_id)
    pub_b64 = identity.public_key_b64
    print(f"      Ed25519 Public Key: {pub_b64[:16]}...{pub_b64[-8:]} (32 bytes)")

    # 2. Prepare Registration Payload
    print("\n[2/4] Assembling Zero-PII Node Registration Handshake...")
    capabilities = [
        "stac-1.0.0",
        "geojson-rfc7946",
        "jsonld-agrovoc",
        "flower-fl-grpc",
        "mobilenetv3-disease-edge",
    ]

    payload = {
        "node_id": node_id,
        "country_code": country_code.upper(),
        "organisation_name": org_name,
        "public_key": pub_b64,
        "capabilities": capabilities,
        "api_base_url": api_base_url,
        "version": "1.0.0",
        "contact_email": contact_email,
    }

    # 3. Contact Registry Handshake
    print(f"\n[3/4] Handshaking with BRICS Commons Registry ({registry_url})...")
    register_endpoint = f"{registry_url.rstrip('/')}/registry/v1/nodes/register"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(register_endpoint, json=payload)
            if resp.status_code == 201:
                data = resp.json()
                print(f"      [SUCCESS] Node registered! Status: {data.get('status').upper()}")
                print(f"      Message: {data.get('message')}")
            elif resp.status_code == 409:
                print(f"      [INFO] Node '{node_id}' is already registered with Registry. Verifying status...")
                get_node_endpoint = f"{registry_url.rstrip('/')}/registry/v1/nodes/{node_id}"
                check_resp = client.get(get_node_endpoint)
                if check_resp.status_code == 200:
                    node_data = check_resp.json()
                    print(f"      [OK] Verified existing node registration. Current Status: {node_data.get('status').upper()}")
                else:
                    print(f"      [WARNING] Could not verify existing status: {check_resp.text}")
            else:
                print(f"      [ERROR] Registration rejected by Registry (HTTP {resp.status_code}): {resp.text}")
                return False
    except Exception as e:
        print(f"      [WARNING] Registry connection failed ({e}).")
        print("      Operating in Offline Sovereign Standalone mode. Registration will be retried via background worker.")

    # 4. Save Node Configuration File
    print(f"\n[4/4] Writing Sovereign Node Configuration ({config_output})...")
    config_data = {
        "node_id": node_id,
        "country_code": country_code.upper(),
        "organisation_name": org_name,
        "api_base_url": api_base_url,
        "registry_url": registry_url,
        "public_key": pub_b64,
        "capabilities": capabilities,
        "keys_dir": str(keys_dir),
    }

    config_output.parent.mkdir(parents=True, exist_ok=True)
    with open(config_output, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    print("      Configuration saved successfully.")
    print("\n==================================================================")
    print("  SOVEREIGN NODE ONBOARDING COMPLETED SUCCESSFULLY!")
    print("  Next Steps for Country Administrator:")
    print("  1. Verify data residency boundaries in docker-compose.yml")
    print("  2. Start national node services: docker compose up -d")
    print("  3. Check health: curl http://localhost:8000/api/v1/health/ready")
    print("==================================================================\n")
    return True


def main():
    parser = argparse.ArgumentParser(description="KrishiNet Sovereign Node Bootstrap CLI")
    parser.add_argument("--country", required=True, help="ISO-3166 country code (e.g. BR, ZA, IN)")
    parser.add_argument("--name", required=True, help="Institution name (e.g. 'Embrapa Brazil')")
    parser.add_argument("--node-id", default=None, help="Unique node identifier")
    parser.add_argument("--registry-url", default="http://localhost:8001", help="BRICS Commons Registry URL")
    parser.add_argument("--api-base-url", default="http://localhost:8000", help="This node's public API URL")
    parser.add_argument("--email", default="admin@krishinet.org", help="Node security contact email")
    parser.add_argument("--keys-dir", default="./data/keys", help="Directory to store Ed25519 keypair")
    parser.add_argument("--config-output", default="./data/node_config.json", help="Path to write node_config.json")

    args = parser.parse_args()

    country = args.country.upper()
    node_id = args.node_id or f"node-{country.lower()}-{args.name.lower().split()[0]}-01"

    success = bootstrap_node(
        country_code=country,
        org_name=args.name,
        registry_url=args.registry_url,
        api_base_url=args.api_base_url,
        node_id=node_id,
        contact_email=args.email,
        keys_dir=Path(args.keys_dir),
        config_output=Path(args.config_output),
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
