/** Fixed aurora glow behind the whole landing page. */
export function Aurora() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
      <div className="aurora-blob top-[-15%] left-[-10%] size-[55vw] bg-[#7c3aed]" />
      <div className="aurora-blob top-[20%] right-[-15%] size-[45vw] bg-[#ec4899]" style={{ animationDelay: "-7s" }} />
      <div className="aurora-blob bottom-[-20%] left-[20%] size-[50vw] bg-[#2563eb]" style={{ animationDelay: "-14s", opacity: 0.4 }} />
      <div className="aurora-blob top-[55%] left-[-12%] size-[30vw] bg-[#fb923c]" style={{ animationDelay: "-4s", opacity: 0.25 }} />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_30%,var(--canvas)_85%)]" />
    </div>
  );
}

interface AmigoAnchorProps {
  className?: string;
  /** Size multiplier relative to the anchor box. */
  scale?: number;
  /** Extra head turn in radians, e.g. to look towards nearby content. */
  turn?: number;
}

/**
 * An invisible box the flying 3D amigo moves to while its section is centred in the
 * viewport. Layout decides where the mascot goes, so it adapts to every screen size.
 */
export function AmigoAnchor({ className, scale = 1, turn = 0 }: AmigoAnchorProps) {
  return (
    <div
      aria-hidden
      data-amigo-anchor=""
      data-amigo-scale={scale}
      data-amigo-turn={turn}
      className={`pointer-events-none ${className ?? ""}`}
    />
  );
}
