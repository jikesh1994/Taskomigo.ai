const REASONS = [
  "Python required: 7 years on your profile",
  "Django required: on your profile",
  "5+ years required: you have 7",
  "Remote: matches your preference",
];

/** Illustration of an explained match, mirroring how the matching engine reports results. */
export function MatchPreview() {
  return (
    <figure className="glass rounded-2xl p-6 sm:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-medium">Senior Python Developer</p>
          <p className="text-sm text-muted">ABC Technologies · Remote</p>
        </div>
        <div className="text-right">
          <p className="text-grad text-4xl font-semibold">86</p>
          <p className="text-xs text-muted">match</p>
        </div>
      </div>
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-surface-2" aria-hidden>
        <div className="h-full w-[86%] rounded-full bg-[image:var(--grad)]" />
      </div>
      <p className="mt-5 text-xs font-medium tracking-wide text-muted uppercase">Included because</p>
      <ul className="mt-2 space-y-2 text-sm">
        {REASONS.map((reason) => (
          <li key={reason} className="flex gap-2">
            <span aria-hidden className="text-success">
              ✓
            </span>
            {reason}
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs font-medium tracking-wide text-muted uppercase">Worth knowing</p>
      <p className="mt-2 flex gap-2 text-sm">
        <span aria-hidden className="text-warning">
          !
        </span>
        Kubernetes is preferred, and it isn’t on your profile yet
      </p>
      <figcaption className="mt-5 border-t border-line pt-3 text-xs text-muted">
        Scores explain fit. They never predict whether you’ll be hired.
      </figcaption>
    </figure>
  );
}
