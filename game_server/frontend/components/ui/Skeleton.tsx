'use client';

import { HTMLAttributes } from 'react';

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
}

export function Skeleton({ 
  className = '', 
  variant = 'rectangular',
  width,
  height,
  style,
  ...props 
}: SkeletonProps) {
  const variantClasses = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  };

  return (
    <div
      className={`
        animate-pulse bg-gray-700/50
        ${variantClasses[variant]}
        ${className}
      `}
      style={{
        width: width,
        height: height,
        ...style,
      }}
      {...props}
    />
  );
}

// Pre-built skeleton components
export function SkeletonText({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton 
          key={i} 
          variant="text" 
          className="h-4" 
          style={{ width: i === lines - 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-coup-purple/50 rounded-xl p-4 ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <Skeleton variant="circular" className="w-10 h-10" />
        <div className="flex-1">
          <Skeleton variant="text" className="h-4 w-24 mb-2" />
          <Skeleton variant="text" className="h-3 w-16" />
        </div>
      </div>
      <SkeletonText lines={2} />
    </div>
  );
}

export function SessionCardSkeleton() {
  return (
    <div className="bg-coup-purple/50 border border-gray-700 rounded-xl p-4">
      <div className="flex justify-between items-start mb-3">
        <Skeleton variant="text" className="h-5 w-32" />
        <Skeleton variant="rectangular" className="h-6 w-16 rounded-full" />
      </div>
      <div className="space-y-2">
        <Skeleton variant="text" className="h-4 w-24" />
        <Skeleton variant="text" className="h-4 w-20" />
      </div>
      <div className="mt-4 flex justify-end">
        <Skeleton variant="rectangular" className="h-9 w-20" />
      </div>
    </div>
  );
}
