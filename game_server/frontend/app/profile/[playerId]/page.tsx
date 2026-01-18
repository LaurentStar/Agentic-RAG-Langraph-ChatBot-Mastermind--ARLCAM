import { getPlayer } from '@/lib/api/players';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ROUTES } from '@/lib/constants';
import Link from 'next/link';

interface ProfilePageProps {
  params: { playerId: string };
}

export default async function ProfilePage({ params }: ProfilePageProps) {
  let player;
  let error: string | null = null;

  try {
    player = await getPlayer(params.playerId);
  } catch (err) {
    error = err instanceof Error ? err.message : 'Failed to load player';
  }

  if (error || !player) {
    return (
      <main className="min-h-screen flex items-center justify-center p-4">
        <Card className="max-w-md w-full text-center">
          <CardContent>
            <div className="text-6xl mb-4">😕</div>
            <h1 className="text-xl font-semibold text-white mb-2">
              Player Not Found
            </h1>
            <p className="text-gray-400 mb-6">
              {error || `Could not find player "${params.playerId}"`}
            </p>
            <Link href={ROUTES.SESSIONS}>
              <Button variant="primary">Go to Sessions</Button>
            </Link>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link 
            href={ROUTES.SESSIONS}
            className="text-coup-gold hover:underline text-sm mb-4 inline-block"
          >
            ← Back to Sessions
          </Link>
        </div>

        {/* Profile Card */}
        <Card variant="elevated" padding="lg">
          <div className="flex items-start gap-6">
            {/* Avatar */}
            <div className="flex-shrink-0">
              <div className="w-24 h-24 bg-coup-gold/20 rounded-full flex items-center justify-center">
                <span className="text-4xl">
                  {player.player_type === 'llm_agent' ? '🤖' : '👤'}
                </span>
              </div>
            </div>

            {/* Info */}
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-white mb-1">
                {player.display_name}
              </h1>
              <p className="text-gray-400 capitalize mb-4">
                {player.player_type.replace('_', ' ')}
              </p>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-coup-dark/50 rounded-lg p-3">
                  <div className="text-2xl font-bold text-coup-gold">
                    {player.coins}
                  </div>
                  <div className="text-sm text-gray-400">Coins</div>
                </div>
                <div className="bg-coup-dark/50 rounded-lg p-3">
                  <div className="text-2xl font-bold">
                    {player.is_alive ? (
                      <span className="text-green-400">Active</span>
                    ) : (
                      <span className="text-red-400">Eliminated</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-400">Status</div>
                </div>
              </div>
            </div>
          </div>

          {/* Connected Platforms */}
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-white mb-3">
              Connected Platforms
            </h2>
            <div className="flex flex-wrap gap-2">
              {player.social_media_platforms.length > 0 ? (
                player.social_media_platforms.map((platform) => (
                  <span
                    key={platform}
                    className="px-3 py-1 bg-coup-accent/50 rounded-full text-sm text-gray-300 capitalize"
                  >
                    {platform}
                  </span>
                ))
              ) : (
                <span className="text-gray-400 text-sm">
                  No platforms connected
                </span>
              )}
            </div>
          </div>

          {/* Current Session */}
          <div className="mt-6">
            <h2 className="text-lg font-semibold text-white mb-3">
              Current Session
            </h2>
            {player.session_id ? (
              <Link href={ROUTES.GAME(player.session_id)}>
                <div className="bg-coup-dark/50 rounded-lg p-4 hover:bg-coup-dark/70 transition-colors">
                  <p className="text-coup-gold font-medium">
                    Session: {player.session_id}
                  </p>
                  <p className="text-sm text-gray-400 mt-1">
                    Click to view game
                  </p>
                </div>
              </Link>
            ) : (
              <p className="text-gray-400 text-sm">
                Not currently in a game session
              </p>
            )}
          </div>
        </Card>
      </div>
    </main>
  );
}
