'use client';

import { useEffect, useState } from 'react';
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { useIntersectionObserver } from '@/hooks/useIntersectionObserver';
import { getSessionsPaginated, joinSession, createSession } from '@/lib/api/sessions';
import { SessionCard } from '@/components/sessions/SessionCard';
import { SessionCardSkeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { useAuthStore } from '@/stores/authStore';
import { ROUTES } from '@/lib/constants';
import log from '@/lib/logger';

export default function SessionsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, user, logout, isLoading: authLoading, isHydrated } = useAuthStore();
  const { ref, isVisible } = useIntersectionObserver();
  
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [joiningSessionId, setJoiningSessionId] = useState<string | null>(null);

  // Redirect to login if not authenticated (after hydration and session check)
  useEffect(() => {
    if (isHydrated && !authLoading && !isAuthenticated) {
      router.push(ROUTES.HOME);
    }
  }, [isAuthenticated, isHydrated, authLoading, router]);

  // Infinite scroll query
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
  } = useInfiniteQuery({
    queryKey: ['sessions'],
    queryFn: ({ pageParam = 1 }) => getSessionsPaginated(pageParam),
    getNextPageParam: (lastPage) => lastPage.nextPage ?? undefined,
    initialPageParam: 1,
  });

  // Auto-fetch when scroll sentinel becomes visible
  useEffect(() => {
    if (isVisible && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [isVisible, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Join session mutation
  const joinMutation = useMutation({
    mutationFn: joinSession,
    onSuccess: (session) => {
      log.info('Joined session:', session.session_id);
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      router.push(ROUTES.GAME(session.session_id));
    },
    onError: (err) => {
      log.error('Failed to join session:', err);
    },
  });

  // Create session mutation
  const createMutation = useMutation({
    mutationFn: createSession,
    onSuccess: (session) => {
      log.info('Created session:', session.session_id);
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      setShowCreateModal(false);
      setNewSessionName('');
      router.push(ROUTES.GAME(session.session_id));
    },
    onError: (err) => {
      log.error('Failed to create session:', err);
    },
  });

  const handleJoin = async (sessionId: string) => {
    setJoiningSessionId(sessionId);
    try {
      await joinMutation.mutateAsync(sessionId);
    } finally {
      setJoiningSessionId(null);
    }
  };

  const handleCreateSession = () => {
    if (!newSessionName.trim()) return;
    createMutation.mutate({
      session_name: newSessionName.trim(),
      max_players: 6,
    });
  };

  const handleLogout = async () => {
    await logout();
    router.push(ROUTES.HOME);
  };

  // Show loading while checking session
  if (!isHydrated || authLoading) {
    return (
      <main className="min-h-screen p-8">
        <div className="max-w-4xl mx-auto">
          <div className="grid gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <SessionCardSkeleton key={i} />
            ))}
          </div>
        </div>
      </main>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect
  }

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Game Sessions</h1>
            {user && (
              <p className="text-gray-400 mt-1">
                Welcome back, <span className="text-coup-gold">{user.display_name}</span>
              </p>
            )}
          </div>
          <div className="flex gap-3">
            <Button
              variant="primary"
              onClick={() => setShowCreateModal(true)}
            >
              Create Session
            </Button>
            <Button
              variant="ghost"
              onClick={handleLogout}
            >
              Logout
            </Button>
          </div>
        </div>

        {/* Create Session Modal */}
        {showCreateModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowCreateModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              onClick={(e) => e.stopPropagation()}
            >
              <Card variant="elevated" padding="lg" className="w-full max-w-md">
                <h2 className="text-xl font-semibold text-white mb-4">
                  Create New Session
                </h2>
                <div className="space-y-4">
                  <Input
                    label="Session Name"
                    value={newSessionName}
                    onChange={(e) => setNewSessionName(e.target.value)}
                    placeholder="Enter session name"
                    disabled={createMutation.isPending}
                  />
                  {createMutation.isError && (
                    <p className="text-coup-red text-sm">
                      {createMutation.error instanceof Error 
                        ? createMutation.error.message 
                        : 'Failed to create session'}
                    </p>
                  )}
                  <div className="flex gap-3 justify-end">
                    <Button
                      variant="ghost"
                      onClick={() => setShowCreateModal(false)}
                      disabled={createMutation.isPending}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      onClick={handleCreateSession}
                      isLoading={createMutation.isPending}
                      disabled={!newSessionName.trim()}
                    >
                      Create
                    </Button>
                  </div>
                </div>
              </Card>
            </motion.div>
          </motion.div>
        )}

        {/* Error State */}
        {isError && (
          <Card className="text-center py-8">
            <div className="text-4xl mb-4">😕</div>
            <p className="text-gray-400">
              {error instanceof Error ? error.message : 'Failed to load sessions'}
            </p>
            <Button
              variant="primary"
              className="mt-4"
              onClick={() => queryClient.invalidateQueries({ queryKey: ['sessions'] })}
            >
              Retry
            </Button>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="grid gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <SessionCardSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Sessions List */}
        {!isLoading && !isError && (
          <>
            {data?.pages.flatMap((page) => page.sessions).length === 0 ? (
              <Card className="text-center py-12">
                <div className="text-6xl mb-4">🎮</div>
                <h2 className="text-xl font-semibold text-white mb-2">
                  No Sessions Yet
                </h2>
                <p className="text-gray-400 mb-6">
                  Be the first to create a game session!
                </p>
                <Button
                  variant="primary"
                  onClick={() => setShowCreateModal(true)}
                >
                  Create Session
                </Button>
              </Card>
            ) : (
              <div className="grid gap-4">
                {data?.pages.flatMap((page, pageIndex) =>
                  page.sessions.map((session, sessionIndex) => (
                    <SessionCard
                      key={session.session_id}
                      session={session}
                      index={pageIndex * 10 + sessionIndex}
                      onJoin={handleJoin}
                      isJoining={joiningSessionId === session.session_id}
                    />
                  ))
                )}
              </div>
            )}

            {/* Scroll sentinel - triggers next page load */}
            <div ref={ref} className="h-10 mt-4 flex items-center justify-center">
              {isFetchingNextPage && <SessionCardSkeleton />}
              {!hasNextPage && data?.pages.flatMap((p) => p.sessions).length! > 0 && (
                <p className="text-gray-500 text-sm">No more sessions</p>
              )}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
