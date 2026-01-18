'use client';

import { Button } from '@/components/ui/Button';
import { config } from '@/lib/config';
import { API_ENDPOINTS } from '@/lib/constants';
import log from '@/lib/logger';
import Image from 'next/image';

interface OAuthButtonProps {
  provider: 'discord' | 'slack' | 'google';
  label: string;
  icon: string;
  bgColor: string;
  hoverColor: string;
}

const oauthProviders: OAuthButtonProps[] = [
  {
    provider: 'discord',
    label: 'Continue with Discord',
    icon: '/icons/discord.svg',
    bgColor: 'bg-[#5865F2]',
    hoverColor: 'hover:bg-[#4752C4]',
  },
  {
    provider: 'slack',
    label: 'Continue with Slack',
    icon: '/icons/slack.svg',
    bgColor: 'bg-[#4A154B]',
    hoverColor: 'hover:bg-[#3a1139]',
  },
  {
    provider: 'google',
    label: 'Continue with Google',
    icon: '/icons/google.svg',
    bgColor: 'bg-white',
    hoverColor: 'hover:bg-gray-100',
  },
];

function OAuthButton({ provider, label, icon, bgColor, hoverColor }: OAuthButtonProps) {
  const handleClick = () => {
    log.debug('OAuth redirect:', provider);
    
    const endpoints: Record<string, string> = {
      discord: API_ENDPOINTS.OAUTH_DISCORD,
      slack: API_ENDPOINTS.OAUTH_SLACK,
      google: API_ENDPOINTS.OAUTH_GOOGLE,
    };
    
    const redirectUrl = `${config.apiUrl}${endpoints[provider]}`;
    window.location.href = redirectUrl;
  };

  const isGoogle = provider === 'google';

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`
        w-full flex items-center justify-center gap-3
        px-4 py-2.5 rounded-lg
        font-medium transition-colors duration-200
        ${bgColor} ${hoverColor}
        ${isGoogle ? 'text-gray-700' : 'text-white'}
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-coup-dark focus:ring-coup-gold
      `}
    >
      <Image
        src={icon}
        alt={`${provider} logo`}
        width={20}
        height={20}
        className="flex-shrink-0"
      />
      <span>{label}</span>
    </button>
  );
}

export function OAuthButtons() {
  if (!config.features.oauth) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-600" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-4 bg-coup-dark text-gray-400">
            Or continue with
          </span>
        </div>
      </div>

      <div className="space-y-2">
        {oauthProviders.map((provider) => (
          <OAuthButton key={provider.provider} {...provider} />
        ))}
      </div>
    </div>
  );
}
