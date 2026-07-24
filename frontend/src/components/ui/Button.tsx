import React from 'react';

interface ButtonProps {
  variant?: 'outline' | 'primary';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  type?: 'button' | 'submit' | 'reset';
  [key: string]: any; // for other props like className, etc.
}

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  disabled = false,
  children,
  onClick,
  type = 'button',
  ...props
}) => {
  const baseClasses = `inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none`;

  const variantClasses = variant === 'primary'
    ? 'bg-violet-600 text-white hover:bg-violet-700'
    : 'border border-gray-300 bg-white hover:bg-gray-50';

  const sizeClasses = size === 'sm'
    ? 'h-9 px-3 text-sm'
    : size === 'lg'
      ? 'h-11 px-8 text-lg'
      : 'h-10 px-4 text-md'; // md

  return (
    <button
      type={type}
      className={`${baseClasses} ${variantClasses} ${sizeClasses}`}
      disabled={disabled}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;