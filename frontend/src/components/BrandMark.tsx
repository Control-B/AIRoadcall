import Image from "next/image";
import logoSrc from "@/assets/logos/RoadcallLogo.png";

interface BrandMarkProps {
  /** Pixel size of the logo image (square). */
  size?: number;
  /** Show the "Roadcall.ai" wordmark next to the logo. */
  showWordmark?: boolean;
  /** Tailwind text size for the wordmark. */
  wordmarkClassName?: string;
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
  showWordmark = true,
  wordmarkClassName = "text-lg font-bold tracking-tight",
  className = "flex items-center gap-2.5",
  priority = false,
}: BrandMarkProps) {
  return (
    <span className={className}>
      <Image
        src={logoSrc}
        alt="Roadcall.ai"
        width={size}
        height={size}
        priority={priority}
        className="rounded-xl shadow-lg shadow-orange-500/20"
        style={{ width: size, height: size, objectFit: "contain" }}
      />
      {showWordmark && (
        <span className={wordmarkClassName}>
          Roadcall<span className="text-orange-400">.ai</span>
        </span>
      )}
    </span>
  );
}
