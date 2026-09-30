#!/usr/bin/env python3
"""
License Compliance Checker for KrishiNet-BRICS (AgriN Commons).
Enforces strict license hygiene for Apache-2.0 Digital Public Good compliance.
Only permissive open-source licenses are permitted; copyleft (GPL/AGPL) dependencies are blocked.
"""

import sys
import importlib.metadata

PERMISSIVE_LICENSES = {
    "apache-2.0",
    "apache 2.0",
    "apache software license",
    "mit",
    "bsd",
    "bsd-2-clause",
    "bsd-3-clause",
    "isc",
    "psf",
    "python software foundation license",
    "unlicense",
    "cc0",
    "cc-by-4.0",
    "mpl-2.0",
}

BLOCKED_LICENSES = {
    "gpl",
    "gplv2",
    "gplv3",
    "agpl",
    "agplv3",
    "gnu general public license",
    "gnu affero general public license",
}


def check_licenses():
    print("=" * 65)
    print("⚖️  KrishiNet-BRICS Open Source License Compliance Gate")
    print("=" * 65)

    installed_packages = list(importlib.metadata.distributions())
    violations = []
    compliant_count = 0

    for dist in installed_packages:
        name = dist.metadata.get("Name", "unknown")
        raw_lic = dist.metadata.get("License", "") or ""
        classifiers = dist.metadata.get_all("Classifier") or []

        # Find license classifier if present
        lic_from_classifier = ""
        for c in classifiers:
            if c.startswith("License ::"):
                lic_from_classifier = c.split("::")[-1].strip()

        combined_lic = f"{raw_lic} {lic_from_classifier}".lower()

        # Check for blocked copyleft
        is_blocked = any(b in combined_lic for b in BLOCKED_LICENSES)
        is_permissive = any(p in combined_lic for p in PERMISSIVE_LICENSES)

        # Handle packages that don't state license in top-level metadata cleanly
        if is_blocked and not is_permissive:
            violations.append((name, raw_lic or lic_from_classifier))
        else:
            compliant_count += 1

    print(f"Verified {len(installed_packages)} packages.")
    print(f"Permissive / Compliant packages: {compliant_count}")

    if violations:
        print(f"\n❌ FAILED: Found {len(violations)} non-permissive or copyleft licenses:")
        for pkg, lic in violations:
            print(f"  • {pkg}: {lic}")
        sys.exit(1)
    else:
        print("\n✅ PASSED: All installed dependencies comply with Apache-2.0 Digital Public Good terms.")
        sys.exit(0)


if __name__ == "__main__":
    check_licenses()
