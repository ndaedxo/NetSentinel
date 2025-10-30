import { useState, KeyboardEvent, useRef } from 'react';
import { X } from 'lucide-react';

interface ScopeTagsInputProps {
  value: string[];
  onChange: (scopes: string[]) => void;
  placeholder?: string;
  className?: string;
}

export default function ScopeTagsInput({
  value,
  onChange,
  placeholder = "Add scope...",
  className = ""
}: ScopeTagsInputProps) {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const addScope = (scope: string) => {
    const trimmed = scope.trim();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
    }
  };

  const removeScope = (scopeToRemove: string) => {
    onChange(value.filter(scope => scope !== scopeToRemove));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      if (inputValue.trim()) {
        addScope(inputValue);
        setInputValue('');
      }
    } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
      removeScope(value[value.length - 1]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleContainerClick = () => {
    inputRef.current?.focus();
  };

  return (
    <div
      className={`flex flex-wrap gap-1 p-2 border border-slate-700 rounded bg-slate-800 min-h-[2.5rem] cursor-text ${className}`}
      onClick={handleContainerClick}
      role="group"
      aria-label="Scope tags input"
      aria-describedby="scope-tags-help"
    >
      {value.map((scope, index) => (
        <span
          key={index}
          className="inline-flex items-center gap-1 px-2 py-1 bg-slate-700 text-slate-200 text-sm rounded"
          role="listitem"
        >
          {scope}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              removeScope(scope);
            }}
            className="hover:bg-slate-600 rounded p-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label={`Remove scope: ${scope}`}
            title={`Remove ${scope}`}
          >
            <X className="w-3 h-3" />
          </button>
        </span>
      ))}
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder={value.length === 0 ? placeholder : ''}
        className="flex-1 min-w-[120px] bg-transparent border-none outline-none text-slate-200 placeholder-slate-400 focus:ring-0"
        role="textbox"
        aria-label="Add scope"
        aria-describedby="scope-tags-instructions"
      />
      <div id="scope-tags-help" className="sr-only">
        Enter a scope and press Enter or comma to add it. Press Backspace to remove the last scope.
      </div>
      <div id="scope-tags-instructions" className="sr-only">
        Type to add new scopes. Use comma or Enter to confirm.
      </div>
    </div>
  );
}
