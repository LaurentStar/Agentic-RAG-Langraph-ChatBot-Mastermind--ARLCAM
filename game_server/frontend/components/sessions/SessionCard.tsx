'use client';

import { motion } from 'framer-motion';
import { Session } from '@/types';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ROUTES, UI } from '@/lib/constants';
import { useRouter } from 'next/navigation';
import log from '@/lib/logger';

interface SessionCardProps {
  session: Session;
  onJoin?: (sessionId: string) => Promise<void>;
  isJoining?: boolean;
  index?: number;
}

const statusColors: Record<string, string> = {
  waiting: 'bg-green-500/20 text-green-400 border-green-500/30',
  active: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  paused: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  ended: 'bg-red-500/20 text-red-400 border-red-500/30',
};

const statusLabels: Record<string, string> = {
  waiting: 'Waiting',
  active: 'In Progress',
  paused: 'Paused',
  ended: 'Ended',
};

export function SessionCard({ session, onJoin, isJoining, index = 0 }: SessionCardProps) {
  const router = useRouter();
  const canJoin = session.status === 'waiting' && session.player_count < session.max_players;

  const handleJoin = async () => {
    if (onJoin) {
      log.debug('Joining session:', session.session_id);
      await onJoin(session.session_id);
    }
  };

  const handleView = () => {
    router.push(ROUTES.GAME(session.session_id));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
    >
      <Card 
        variant="default" 
        hoverable 
        className="transition-all duration-200"
      >
        <div className="flex justify-between items-start mb-3">
          <h3 className="text-lg font-semibold text-white truncate pr-2">
            {session.session_name}
          </h3>
          <span className={`
            px-2 py-1 rounded-full text-xs font-medium border
            ${statusColors[session.status] || statusColors.waiting}
          `}>
            {statusLabels[session.status] || session.status}
          </span>
        </div>

        <div className="space-y-2 text-sm text-gray-400">
          <div className="flex items-center gap-2">
            <svg 
              className="w-4 h-4" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" 
              />
            </svg>
            <span>
              {session.player_count} / {session.max_players} players
            </span>
          </div>

          {session.current_phase && (
            <div className="flex items-center gap-2">
              <svg 
                className="w-4 h-4" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" 
                />
              </svg>
              <span className="capitalize">
                {session.current_phase.replace(/_/g, ' ')}
              </span>
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-end gap-2">
          {session.status !== 'ended' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleView}
            >
              View
            </Button>
          )}
          
          {canJoin && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleJoin}
              isLoading={isJoining}
            >
              Join Game
            </Button>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
