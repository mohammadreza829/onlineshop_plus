# Onlineshop Plus — Spatial Atelier

## Direction

An interactive fashion material study, followed by a clear, usable Persian storefront. Actual 3D is concentrated in the hero; shopping, authentication, order creation and payment remain predictable, keyboard-operable HTML. Depth is not a reason to rotate forms or hide prices.

## Verified inputs and deliberate overrides

- Existing Next App Router, React 19, TypeScript, Tailwind 4, Motion and Persian/RTL API-backed storefront inspected before changes.
- UI UX Pro Max pinned at `d14efff8ed1faa4187f004f79926f428c8074ec7`; design-system queries `fashion ecommerce immersive 3d` and `fashion apparel boutique`, plus the explicit `3d depth perspective` style query and Next/Three.js stack searches were executed.
- Broad engine results (green/orange feature showcase and rose/gold minimalism) were not accepted blindly. Selected the verified **3D & Hyperrealism** and **Dimensional Layering** styles; used the existing semantic theme system rather than a parallel Tailwind palette.
- Kept self-hosted Vazirmatn because Latin font recommendations do not cover Persian typography.
- Kept Next as the BFF/auth/routing shell. Three.js + React Three Fiber supply the rendering architecture; changing the router alone would not improve 3D and would unnecessarily risk existing HttpOnly-session/CSRF/checkout behavior.

## Visual system

- Light canvas `#f5f6f2`, surfaces `#fff`, ink `#172b25`, muted `#5e6b63`, primary `#1d5643`.
- System-dark canvas `#121c18`, surfaces `#1c2922`, ink `#edf3e9`, muted `#b0bfb1`, accent `#c6e79c`.
- Immersive hero intentionally stays dark: `#14231c` + ivory `#eff2e7` + acid/sage `#d1ee9e`. Its contrast pairs are independent of the surrounding system theme.
- 4/8px spacing scale; restrained 12px surfaces; typographic hierarchy; explicit focus rings. Shopping controls remain at least 44px high where practical.
- 21st ibelick Tilt, demo 1448: adapted to installed `motion/react`, restrained pointer-only perspective, coarse-pointer and live reduced-motion safeguards. Attribution and MIT license preserved.
- 21st demo 6563 inspected but rejected for production: fixed-width CSS hallway and raw HTML insertion were not suitable for this real volumetric/RTL storefront. No copied unsafe HTML path or external image dependency.

## True 3D architecture

`features/showroom/showroom.tsx` is the progressive shell and accessible control console; `scene.tsx` is a lazy client-only WebGL module. `cloth.ts` decodes local geometry; `types.ts` defines explicit view commands.

Microsoft SheenCloth (CC0), optimized offline from 115,200 to 13,824 triangles. Original normals/UVs, procedural weave bump, physical sheen, studio lights, real shadows, dimensional stage, live material selection, relative rotation and explicit pose reset. It is **a fabric/form study, not a model of any catalog SKU**.

Rendering is demand-driven, capped at DPR 1.5, paused outside the viewport/hidden tab, and continuous only during allowed auto-rotation. Reduced motion disables automatic scene/camera motion but keeps deliberate button controls. Pause freezes the visible pose. No scroll hijacking. Context loss / no WebGL / asset failure retain an honest static same-model fallback. Save-Data avoids loading the scene. Product data never goes into 21st queries.

## Boundaries

No business APIs, payment callbacks, financial retry behavior, Django models or migrations changed. No credentials, real orders, mock production inventory, promises, testimonials or policy content added. Real 360° product viewing requires separately supplied/approved GLB assets for those products. Legacy Django templates and Django Admin are outside this customer-frontend redesign.
