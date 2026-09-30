# KrishiNet-BRICS Green & White Design System

The KrishiNet-BRICS user interface is built on a strict **Green & White** visual identity designed for clarity, trust, and usability on low-power mobile devices and high-resolution desktop control centers.

---

## 1. Core Principles

1. **White Surfaces**: Clean, airy background (`--background: #FFFFFF`) and soft tinted cards (`--surface-soft: #F4FAF5`).
2. **Single Brand Color (Green)**: The green palette signifies life, regenerative soil, and sovereign public infrastructure.
   - Primary: `#16A34A` (Solid buttons, key highlights)
   - Primary Dark: `#166534` (Headings, primary button hovers)
   - Primary Deep: `#14532D` (Officer sidebar, high contrast emphasis)
   - Primary Light: `#DCFCE7` (Hero tints, badges, subtle selections)
3. **Generous Whitespace & Rounded Radii**:
   - Cards: `16px` radius (`rounded-card`), 1px border (`--border: #DCEBDD`), soft green-tinted shadows.
   - Action Buttons: `12px` radius (`rounded-btn`), minimum `48px` touch target height.
4. **No Gratuitous Colors**:
   - Amber (`#F59E0B`), Red (`#DC2626`), and Blue (`#0EA5E9`) are reserved strictly for semantic health status (healthy, watch, risk, info).
   - All charts use monochromatic green progressions; amber/red are invoked only when crossing alert thresholds.
5. **NDVI & Heatmap Scale**:
   - `0.0`: `#DC2626` (Bare soil / drought stress)
   - `0.2`: `#F59E0B` (Sparse canopy)
   - `0.4`: `#FDE047` (Moderate growth)
   - `0.6`: `#86EFAC` (Healthy biomass)
   - `0.8`: `#16A34A` (Dense healthy canopy)
   - `1.0`: `#14532D` (Peak vegetative vigour)

---

## 2. Accessibility & Low-Literacy Rules

- **WCAG AA Compliance**: All text achieves a 4.5:1 contrast ratio against its background. White text is displayed only over `#16A34A` or darker.
- **Never Color Alone**: Status is always communicated through a three-factor triad: **Color + Icon + Text Label**.
- **Touch Target Floor**: 48×48px minimum touch surface for all interactive triggers.
- **Typography Sizing Toggles**: Dynamic font scale toggles (`A`, `A+`, `A++`) support visual impairment in field conditions.
- **RTL Logical Properties**: Support for Arabic (`ar`) and Persian (`fa`) via CSS logical properties (`ms-*`, `me-*`, `ps-*`, `pe-*`, `start`, `end`).
- **High Contrast Toggle**: Sharp monochrome mode with `#000000` text and darkened green borders.
- **Voice-First Guidance**: Text-to-speech triggers accompany all core actionable advisories.
