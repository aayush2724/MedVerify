import React from 'react';

export default function Card({ children, className = '', ...props }) {
  return (
    <div 
      className={`bg-[var(--surface)] border border-[var(--border)] p-6 rounded-[var(--radius)] shadow-[var(--shadow-sm)] ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
