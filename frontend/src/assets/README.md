# Assets

Static images, icons, logos, and other media used by the Roadcall frontend.

## Structure

```
assets/
├── images/        # Photos, screenshots, hero images, OG/share images
├── icons/         # SVG icons, favicons, app icons (use lucide-react for inline UI icons)
├── logos/         # Roadcall brand marks, partner/vendor logos
└── illustrations/ # Decorative SVG/PNG illustrations
```

## Two ways to use these in Next.js

### 1. `next/image` import (recommended for optimization)
Put files anywhere under `src/assets/` and import them — Next.js will hash, compress, and serve optimized variants:

```tsx
import Image from "next/image";
import logo from "@/assets/logos/roadcall-mark.svg";

<Image src={logo} alt="Roadcall" width={120} height={32} priority />
```

### 2. `public/` URL (for raw, unhashed files — favicons, OG tags, robots.txt)
Anything that must be reachable at a fixed URL (e.g. `/favicon.ico`, social-share image referenced in `<meta>` tags) belongs in `frontend/public/`, not here.

## Inline UI icons

Don't add Lucide / Heroicon SVGs here — keep using `lucide-react` for inline UI
icons so the bundle stays tree-shakeable. Only drop SVG files here when they
are brand-specific (logos, custom marks) or used as full images.
