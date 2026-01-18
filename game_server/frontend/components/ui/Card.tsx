'use client';

import { HTMLAttributes, forwardRef } from 'react';
import { motion } from 'framer-motion';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'outlined';
  hoverable?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const variants = {
  default: 'bg-coup-purple/50 border border-gray-700',
  elevated: 'bg-coup-purple/70 shadow-lg shadow-black/20',
  outlined: 'bg-transparent border-2 border-coup-gold/30',
};

const paddings = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ 
    className = '', 
    variant = 'default', 
    hoverable = false, 
    padding = 'md',
    children, 
    ...props 
  }, ref) => {
    const Component = hoverable ? motion.div : 'div';
    const hoverProps = hoverable 
      ? { 
          whileHover: { scale: 1.02, y: -2 },
          transition: { duration: 0.2 }
        } 
      : {};

    return (
      <Component
        ref={ref}
        className={`
          rounded-xl
          ${variants[variant]}
          ${paddings[padding]}
          ${hoverable ? 'cursor-pointer' : ''}
          ${className}
        `}
        {...hoverProps}
        {...props}
      >
        {children}
      </Component>
    );
  }
);

Card.displayName = 'Card';

// Card sub-components
export const CardHeader = ({ className = '', children, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={`mb-4 ${className}`} {...props}>
    {children}
  </div>
);

export const CardTitle = ({ className = '', children, ...props }: HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={`text-lg font-semibold text-white ${className}`} {...props}>
    {children}
  </h3>
);

export const CardDescription = ({ className = '', children, ...props }: HTMLAttributes<HTMLParagraphElement>) => (
  <p className={`text-sm text-gray-400 ${className}`} {...props}>
    {children}
  </p>
);

export const CardContent = ({ className = '', children, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={className} {...props}>
    {children}
  </div>
);

export const CardFooter = ({ className = '', children, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={`mt-4 pt-4 border-t border-gray-700 ${className}`} {...props}>
    {children}
  </div>
);
