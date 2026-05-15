
export const Skeleton = () => {
    return (
        <div className="my-5 animate-pulse rounded-[28px] border border-theme-border/40 bg-theme-accent p-6">
    {/* Header */}
    <div className="flex items-start justify-between gap-4">
        <div className="space-y-3">
            <div className="h-3 w-36 rounded-full bg-theme-surface/80" />
            <div className="h-9 w-56 rounded-full bg-theme-surface/60" />
        </div>

        <div className="h-5 w-24 rounded-full bg-theme-surface/80" />
    </div>

    {/* Description */}
    <div className="mt-6 space-y-3">
        <div className="h-4 w-full rounded-full bg-theme-surface/80" />
        <div className="h-4 w-4/5 rounded-full bg-theme-surface/70" />
    </div>

    {/* Tags */}
    <div className="mt-6 flex flex-wrap gap-3">
        {Array.from({ length: 3 }).map((_, index) => (
            <div
                key={index}
                className="h-8 w-28 rounded-full bg-theme-surface/80"
            />
        ))}
    </div>

    {/* Insight Card */}
    <div className="mt-6 rounded-3xl border border-theme-border/30 bg-theme-bg/60 p-5">
        <div className="space-y-4">
            <div className="h-4 w-64 rounded-full bg-theme-surface/80" />

            <div className="space-y-3">
                <div className="h-4 w-full rounded-full bg-theme-surface/80" />
                <div className="h-4 w-5/6 rounded-full bg-theme-surface/70" />
                <div className="h-4 w-3/4 rounded-full bg-theme-surface/60" />
            </div>

            <div className="flex gap-3 pt-2">
                <div className="h-6 w-32 rounded-full bg-theme-surface/80" />
                <div className="h-6 w-40 rounded-full bg-theme-surface/70" />
            </div>

            <div className="pt-3 space-y-2">
                <div className="h-4 w-full rounded-full bg-theme-surface/80" />
                <div className="h-4 w-2/3 rounded-full bg-theme-surface/70" />
            </div>
        </div>
    </div>
</div>
    )
}