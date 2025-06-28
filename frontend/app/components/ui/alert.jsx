import React from 'react';

const alertVariants = {
  default: 'bg-white border-gray-200',
  destructive: 'bg-red-50 border-red-200 text-red-800'
};

const Alert = React.forwardRef(({ className = '', variant = 'default', ...props }, ref) => {
  return (
    <div
      ref={ref}
      role="alert"
      className={`relative w-full rounded-lg border p-4 ${alertVariants[variant]} ${className}`}
      {...props}
    />
  );
});
Alert.displayName = 'Alert';

const AlertDescription = React.forwardRef(({ className = '', ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={`text-sm [&_p]:leading-relaxed ${className}`}
      {...props}
    />
  );
});
AlertDescription.displayName = 'AlertDescription';

export { Alert, AlertDescription };