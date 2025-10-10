/**
 * Skeleton loader components for various content types
 * Provides visual feedback during data loading with animated placeholders
 */

interface SkeletonProps {
  className?: string;
}

// Base skeleton with shimmer effect
function SkeletonBase({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:200%_100%] rounded ${className}`}
      style={{ animation: 'shimmer 2s ease-in-out infinite' }}
    />
  );
}

// Material Request Card Skeleton
export function MaterialRequestSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3 flex-1">
          <SkeletonBase className="w-12 h-12 rounded-lg" />
          <div className="flex-1 space-y-2">
            <SkeletonBase className="h-5 w-3/4" />
            <SkeletonBase className="h-4 w-1/2" />
          </div>
        </div>
        <SkeletonBase className="w-16 h-6 rounded-full" />
      </div>

      <div className="border-t border-gray-100 pt-3 space-y-2">
        <div className="flex justify-between">
          <SkeletonBase className="h-4 w-24" />
          <SkeletonBase className="h-4 w-16" />
        </div>
        <SkeletonBase className="h-2 w-full rounded-full" />
      </div>
    </div>
  );
}

// Item Group Card Skeleton
export function ItemGroupSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3 flex-1">
          <SkeletonBase className="w-10 h-10 rounded-lg" />
          <div className="flex-1 space-y-2">
            <SkeletonBase className="h-5 w-2/3" />
            <SkeletonBase className="h-3 w-1/3" />
          </div>
        </div>
        <SkeletonBase className="w-4 h-4 rounded" />
      </div>

      <SkeletonBase className="h-2 w-full rounded-full mb-3" />

      <div className="border-t border-gray-100 pt-3">
        <SkeletonBase className="h-3 w-16 mb-2" />
        <div className="flex gap-2">
          <SkeletonBase className="h-7 w-20 rounded-md" />
          <SkeletonBase className="h-7 w-20 rounded-md" />
          <SkeletonBase className="h-7 w-20 rounded-md" />
        </div>
      </div>
    </div>
  );
}

// List of skeletons (for multiple items)
export function MaterialRequestListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <MaterialRequestSkeleton key={i} />
      ))}
    </div>
  );
}

export function ItemGroupListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <ItemGroupSkeleton key={i} />
      ))}
    </div>
  );
}

// Generic card skeleton
export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 animate-pulse space-y-4">
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="space-y-2">
            <SkeletonBase className="h-4 w-24" />
            <SkeletonBase className="h-6 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

// Table skeleton
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 border-b border-gray-200 p-4">
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
          {Array.from({ length: cols }).map((_, i) => (
            <SkeletonBase key={i} className="h-4" />
          ))}
        </div>
      </div>

      {/* Rows */}
      <div className="divide-y divide-gray-200">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="p-4">
            <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
              {Array.from({ length: cols }).map((_, colIndex) => (
                <SkeletonBase key={colIndex} className="h-5" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Page with header and content
export function PageSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header skeleton */}
      <div className="bg-white border-b border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            <SkeletonBase className="w-8 h-8 rounded" />
            <div className="space-y-2 flex-1">
              <SkeletonBase className="h-6 w-64" />
              <SkeletonBase className="h-4 w-40" />
            </div>
          </div>
        </div>
      </div>

      {/* Content skeleton */}
      <div className="p-6 space-y-4">
        <MaterialRequestListSkeleton count={4} />
      </div>
    </div>
  );
}

// Add shimmer animation styles
export function SkeletonStyles() {
  return (
    <style dangerouslySetInnerHTML={{
      __html: `
        @keyframes shimmer {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }
      `
    }} />
  );
}

// Export base for custom use
export { SkeletonBase };
