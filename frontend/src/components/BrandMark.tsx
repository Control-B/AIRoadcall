import Image from "next/image";
import logoSrc from "@/assets/logos/RoadcallLogo.png";

interface BrandMarkProps {
  /** Legacy size prop. Used as height when width/height are omitted. */
  size?: number;
  /** Deprecated: the uploaded logo already includes the wordmark. */
  showWordmark?: boolean;
  /** Deprecated: the uploaded logo already includes the wordmark. */
  wordmarkClassName?: string;
  /** Rendered logo width in pixels. */
  width?: number;
  /** Rendered logo height in pixels. */
  height?: number;
  /** Wrapper class. */
  className?: string;
  /** Mark image as priority (use on header/hero). */
  priority?: boolean;
}

/**
 * Roadcall brand mark — image logo + optional wordmark.
 * Single source of truth so we can swap the logo in one place.
 */
export function BrandMark({
  size = 36,
  width,
  height,
  className = "inline-flex items-center",
  priority = false,
}: BrandMarkProps) {
  const logoHeight = height ?? size;
  const logoWidth = width ?? Math.round(logoHeight * 3.08);

  return (
    <span className={className}>
      <Image
        src={logoSrc}
        alt="Roadcall.ai"
        width={logoWidth}
        height={logoHeight}
        priority={priority}
        className="drop-shadow-[0_12px_24px_rgba(10,132,255,0.20)]"
        style={{ width: logoWidth, height: logoHeight, objectFit: "contain" }}
      />
    </span>
  );
}
