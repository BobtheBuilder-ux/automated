import React from 'react';

const badgeVariants = {
  default: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200',
  destructive: 'bg-red-600 text-white hover:bg-red-700',
  outline: 'border border-gray-300 text-gray-700'
};

const Badge = React.forwardRef(({ className = '', variant = 'default', ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 ${badgeVariants[variant]} ${className}`}
      {...props}
    />
  );
});
Badge.displayName = 'Badge';

export { Badge };