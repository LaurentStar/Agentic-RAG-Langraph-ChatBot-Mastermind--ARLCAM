import { SessionCardSkeleton } from '@/components/ui/Skeleton';

export default function SessionsLoading() {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header Skeleton */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <div className="h-9 w-48 bg-gray-700/50 rounded animate-pulse mb-2" />
            <div className="h-5 w-64 bg-gray-700/50 rounded animate-pulse" />
          </div>
          <div className="flex gap-3">
            <div className="h-10 w-32 bg-gray-700/50 rounded-lg animate-pulse" />
            <div className="h-10 w-24 bg-gray-700/50 rounded-lg animate-pulse" />
          </div>
        </div>

        {/* Sessions Skeleton */}
        <div className="grid gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <SessionCardSkeleton key={i} />
          ))}
        </div>
      </div>
    </main>
  );
}
