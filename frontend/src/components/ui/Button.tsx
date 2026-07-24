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
  const baseClasses = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';

  const variantClasses = variant === 'primary'
    ? 'bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-indigo-500'
    : 'border border-gray-600 bg-transparent text-gray-300 hover:bg-gray-800 hover:text-white focus:ring-gray-500';

  const sizeClasses = size === 'sm'
    ? 'px-3 py-1.5 text-sm'
    : size === 'lg'
      ? 'px-5 py-2.5 text-lg'
      : 'px-4 py-2 text-md'; // md

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