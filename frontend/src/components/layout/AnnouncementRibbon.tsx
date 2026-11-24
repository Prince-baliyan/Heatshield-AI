export function AnnouncementRibbon() {
  return (
    <div className="border-b border-violet-300/10 bg-violet-950/30 text-violet-100">
      <div className="hs-page flex min-h-9 items-center justify-between gap-3 py-2 text-[11px] font-semibold uppercase tracking-[0.14em] sm:text-xs">
        <p className="truncate">
          <span className="mr-2 text-cyan-300">ByteForce</span>
          HeatShield AI platform preview
        </p>
        <p className="hidden shrink-0 text-violet-200/70 sm:block">
          Urban heat intelligence
        </p>
      </div>
    </div>
  );
}
