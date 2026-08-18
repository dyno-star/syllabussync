// The SVG filter that gives the stamp its rough, hand-inked edge. Defined
// once globally (invisible, zero-size) since multiple <Stamp> instances can
// share the same filter definition via url(#ink-roughen).
export function StampFilterDefs() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <filter id="ink-roughen">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" result="noise" />
        <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.2" />
      </filter>
    </svg>
  );
}

export default function Stamp({ label, variant = "review", animate = false }) {
  const className = ["stamp", animate ? "stamp-animate" : ""].filter(Boolean).join(" ");

  return (
    <span className={className}>
      <span className={`stamp-inner ${variant === "verified" ? "stamp--verified" : ""}`}>
        {label}
      </span>
    </span>
  );
}
