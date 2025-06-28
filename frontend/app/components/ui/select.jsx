'use client';

import React, { createContext, useContext, useState } from 'react';

const SelectContext = createContext();

const Select = ({ children, value, onValueChange, ...props }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedValue, setSelectedValue] = useState(value || '');

  const handleValueChange = (newValue) => {
    setSelectedValue(newValue);
    setIsOpen(false);
    if (onValueChange) {
      onValueChange(newValue);
    }
  };

  return (
    <SelectContext.Provider value={{ 
      isOpen, 
      setIsOpen, 
      selectedValue, 
      handleValueChange 
    }}>
      <div className="relative" {...props}>
        {children}
      </div>
    </SelectContext.Provider>
  );
};

const SelectTrigger = React.forwardRef(({ className = '', children, ...props }, ref) => {
  const { isOpen, setIsOpen } = useContext(SelectContext);
  
  return (
    <button
      ref={ref}
      type="button"
      onClick={() => setIsOpen(!isOpen)}
      className={`flex h-10 w-full items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm ring-offset-background placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
      <svg
        className={`h-4 w-4 opacity-50 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <polyline points="6,9 12,15 18,9"></polyline>
      </svg>
    </button>
  );
});
SelectTrigger.displayName = 'SelectTrigger';

const SelectValue = ({ placeholder = 'Select...', className = '', ...props }) => {
  const { selectedValue } = useContext(SelectContext);
  
  return (
    <span className={className} {...props}>
      {selectedValue || placeholder}
    </span>
  );
};

const SelectContent = ({ className = '', children, ...props }) => {
  const { isOpen } = useContext(SelectContext);
  
  if (!isOpen) return null;
  
  return (
    <div
      className={`absolute z-50 top-full mt-1 w-full min-w-[8rem] overflow-hidden rounded-md border bg-white text-gray-950 shadow-md animate-in fade-in-0 zoom-in-95 ${className}`}
      {...props}
    >
      <div className="max-h-96 overflow-auto p-1">
        {children}
      </div>
    </div>
  );
};

const SelectItem = React.forwardRef(({ className = '', children, value, ...props }, ref) => {
  const { handleValueChange, selectedValue } = useContext(SelectContext);
  
  return (
    <div
      ref={ref}
      onClick={() => handleValueChange(value)}
      className={`relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none hover:bg-gray-100 focus:bg-gray-100 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 ${selectedValue === value ? 'bg-gray-100' : ''} ${className}`}
      {...props}
    >
      {selectedValue === value && (
        <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        </span>
      )}
      {children}
    </div>
  );
});
SelectItem.displayName = 'SelectItem';

export { Select, SelectContent, SelectItem, SelectTrigger, SelectValue };