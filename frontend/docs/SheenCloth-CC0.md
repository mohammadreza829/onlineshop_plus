# SheenCloth — source and license

- Original: Microsoft, 2020. Donated to Khronos for glTF testing.
- Source: https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/SheenCloth
- License: Creative Commons Zero v1.0 Universal (CC0).
- Legal text: https://creativecommons.org/publicdomain/zero/1.0/legalcode

To the extent possible under law, Microsoft has waived all copyright and related or neighboring rights to this asset.

## Local derivative

Geometry only, reduced offline with meshoptimizer from 115,200 to 13,824 triangles (7,393 vertices, 319,528 bytes; simplification error 0.000897). Original normals and UVs preserved. Original textures are not redistributed. The weave texture, lighting, stage, interactions and color variants are original.

`assets/cloth.mesh.base64` is the deterministic source. `prepare-assets.mjs` verifies SHA-256 and restores `public/models/cloth.mesh` without network access. Runtime fetch is same-origin and lazy. This is a material study, not a catalog garment or an accurate product digital twin. No catalog inventory is fabricated.
