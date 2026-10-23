# Online Shop Plus — storefront design system

## Direction and scope

Persian RTL apparel storefront, built on the existing Next.js App Router / React / Tailwind stack. The screen's job is to help someone find a garment, compare details, choose a real variant, and confidently continue to purchase. The signature is tactile clothing photography paired with clear blue wayfinding — not decorative lettering or imitation native chrome.

This is a web adaptation of Apple clarity, hierarchy, familiar interaction, and accessibility principles, not a claim of native iOS conformance. Keep Django/BFF contracts, cookies, CSRF, prices, inventory and payment truth unchanged. Do not infer paid status from a URL or clear newly-added cart items after a payment.

## Review before implementation

Rating: **Needs work** (craft and discoverability; no screenshot-only claim of a measured critical accessibility defect).

- **[High] Hero hierarchy** — the previous `frontend/app/page.tsx` placed an oversized rotated “پوشش” in the dominant visual area, not a garment. Why: `layout.md › Visual hierarchy`, “Order content by relative importance.” Fix: editorial apparel image, readable right-hand text and one primary catalog action; verify both narrow and wide layouts.
- **[High] Search discoverability** — the previous header exposed a search icon linking into the catalog, rather than direct query entry. Why: practical web shopping judgment, not a quoted Apple requirement. Fix: labelled GET search in desktop and mobile headers; verify submitted query and URL.
- **[Medium] Inconsistent shopping/account surfaces** — previous styles mixed editorial headings, separate panel treatments and sparse account navigation. Why: `typography.md › Conveying hierarchy`, “Minimize the number of typefaces you use”. Fix: one self-hosted family, shared roles, fields, panels, action hierarchy and icon vocabulary.
- **[Medium] Technical payment copy** — implementation details such as Django/API appeared in customer-facing explanations. Why: content judgment. Fix: explain the next action plainly while retaining the actual callback limitation and verified server state.

What worked and was preserved: real variant identity in the cart, actual API-backed stock and prices, URL filters, OTP error handling, safe redirects, Radix dialog focus/scroll locking, and honest empty/missing-image states.

## Tokens

Six principal roles are background, surface, text, muted, accent and input-border. Status colors remain semantic rather than decorative. `frontend/app/globals.css` is the canonical implementation; this file records the decisions, not a parallel runtime token system.

| Role | Light | Dark |
| --- | --- | --- |
| `background` | `#f6f7fa` | `#111722` |
| `surface` | `#ffffff` | `#1a2231` |
| `text` | `#182236` | `#f1f4fa` |
| `muted` | `#566176` | `#b0bdd0` |
| `accent` | `#2155cd` | `#a5bfff` |
| `accent-soft` | `#eaf0ff` | `#253757` |
| `on-accent` | `#ffffff` | `#132346` |
| `input-border` | `#8590a3` | `#77869f` |
| `danger` | `#b4233c` | `#ffacb8` |

Computed WCAG relative-luminance ratios (opaque sRGB, rounded):

| Foreground / background | Light | Dark |
| --- | --- | --- |
| text / surface | 15.90:1 | 14.47:1 |
| muted / surface | 6.24:1 | 8.38:1 |
| muted / background | 5.82:1 | 9.44:1 |
| accent / surface | 6.47:1 | 8.73:1 |
| on-accent / accent | 6.47:1 | 8.47:1 |
| accent / accent-soft | 5.67:1 | 6.52:1 |
| input-border / surface | 3.22:1 | 4.32:1 |
| danger / surface | 6.47:1 | 8.99:1 |

Body text uses the text/muted pairs, never the subtle decorative divider as text. Input boundaries target 3:1; decorative panel borders are not used as the sole control affordance. Disabled controls are visibly unavailable, not active low-contrast actions. Focus uses a visible 3px accent outline with offset.

## Typography and layout

- Existing self-hosted Vazirmatn, weights 400/500/700; no remote font requests.
- Body 1rem with comfortable Persian leading, supporting labels generally .875rem; display uses a fluid clamp, data uses tabular numerals. The small Latin wordmark is supplementary branding, not essential content.
- Shared container, spacious hero, 2-column compact product grid / up to 4 columns wide, filters in a desktop sidebar and mobile dialog. A sparse real inventory remains sparse; do not fill production with invented products.
- Controls generally 44–52 CSS pixels high; this is a usability choice, not an assertion that WCAG universally requires 44px. Labelled icons, real form controls, logical RTL alignment, LTR phone/order isolates.

Regular-width wireframe (left to right in this diagram):

```text
[cart/account]       [search]            [brand]
[navigation / categories]
[editorial clothing photo] [headline + catalog CTA]
[helpful shopping features]
[real categories]
[real product cards]
[account invitation]
[footer navigation]
```

Compact wireframe:

```text
[cart/account] [brand] [menu]
[search]
[headline + CTA]
[editorial photo + honest caption]
[stacked feature explanations]
[categories]
[product] [product]
[account invitation]
[footer groups]
```

## Interaction and restraint

Native scrolling replaces the former home-only Lenis wrapper. No parallax, glass, forced momentum or scroll storytelling: browsing should not compete with the garments. Preserve useful dialog opening/closing feedback, disable transitions under reduced motion, retain semantic state independently of animation. No decorative animation was added. Removing the giant vertical word and smooth-scroll wrapper is the explicit second-pass restraint decision.

The business trade-off is a more restrained conversion-oriented store instead of an expressive poster. Search and variant clarity are prioritized; editorial character comes from the fabric image rather than extra badges. Do not advertise free shipping, returns, discounts or guarantees without actual policy data.

## Assets

`frontend/assets/wardrobe-editorial.webp.b64` is the text-transportable source for an AI-generated editorial illustration created for this redesign. `npm ci` / prebuild reconstructs `public/images/wardrobe-editorial.webp` locally through the existing asset-preparation script; no CDN or runtime download. The generated binary is ignored. SHA-256: `8d3ef1ffdae6d087fe17d10284d5b9886544bb8e2f7211462ac584a6a225daf3`.

The hero caption explicitly says it is inspiration, not inventory. Never use it as a missing product's actual image. Actual products retain their true photos or the honest “تصویر ثبت نشده” state. Next Image uses a sized fill container and priority for the above-fold hero.

## Pinned sources and limits

- UI UX Pro Max `d14efff8ed1faa4187f004f79926f428c8074ec7`: hand-authored workflow, full local rule index, command reference and actual search scripts read/used. Initial fashion design-system search suggested scroll storytelling/pink-gold; follow-up landing matches were off-topic or empty. **Those outputs were not adopted or persisted as verified recommendations.** The product-first arrangement and palette here are explicit design judgment. Separate Next.js search returned relevant image sizing/priority guidance, applied where compatible with the detected version.
- Apple design skill `914b6a377c22755597e4405e54911b996de822d7`: full SKILL, AGENTS and lookup, cross-platform/code-audit plus accessibility, layout, typography, color, designing-for-ios, buttons, collections, right-to-left and entering-data references read. Native units/SDK conventions were not imposed on web.
- Opened reference: [layout.md — Visual hierarchy](https://github.com/dickwu/apple-design-skill/blob/914b6a377c22755597e4405e54911b996de822d7/references/hig/layout.md#visual-hierarchy).
- Opened reference: [typography.md — Conveying hierarchy](https://github.com/dickwu/apple-design-skill/blob/914b6a377c22755597e4405e54911b996de822d7/references/hig/typography.md#conveying-hierarchy).
- Apple owns reproduced guideline text; this project/repository is not affiliated with Apple. No upstream source code or datasets are redistributed in this application.

## Verification

See `frontend/REDESIGN_QA.md` for executed checks and release limitations. Automated accessibility checks are useful regression coverage, not full screen-reader or WCAG certification.
