'use client';

import useSound from 'use-sound';
import { config } from '@/lib/config';

interface GameSounds {
  playCoin: () => void;
  playCardFlip: () => void;
  playChallenge: () => void;
  playSuccess: () => void;
  playFail: () => void;
}

export function useGameSounds(): GameSounds {
  const soundEnabled = config.features.soundEffects;

  const [playCoin] = useSound('/audio/sfx/coin.mp3', { 
    volume: 0.5,
    soundEnabled,
  });
  
  const [playCardFlip] = useSound('/audio/sfx/card-flip.mp3', { 
    volume: 0.5,
    soundEnabled,
  });
  
  const [playChallenge] = useSound('/audio/sfx/challenge.mp3', { 
    volume: 0.5,
    soundEnabled,
  });
  
  const [playSuccess] = useSound('/audio/sfx/success.mp3', { 
    volume: 0.5,
    soundEnabled,
  });
  
  const [playFail] = useSound('/audio/sfx/fail.mp3', { 
    volume: 0.5,
    soundEnabled,
  });

  return {
    playCoin,
    playCardFlip,
    playChallenge,
    playSuccess,
    playFail,
  };
}
