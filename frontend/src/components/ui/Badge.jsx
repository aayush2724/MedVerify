import React from 'react';

export default function Badge({ status }) {
  let styles = "bg-gray-100 text-gray-800";
  
  if (status === 'GENUINE') {
    styles = "bg-teal-50 text-[var(--accent-teal)] border border-teal-200/50";
  } else if (status === 'SUSPICIOUS') {
    styles = "bg-amber-50 text-[var(--accent-amber)] border border-amber-200/50";
  } else if (status === 'FAKE') {
    styles = "bg-red-50 text-[var(--accent-red)] border border-red-200/50";
  }

  return (
    <span className={`px-3 py-1 text-xs font-semibold rounded-full uppercase tracking-wider ${styles}`}>
      {status}
    </span>
  );
}
