import { forwardRef } from 'react';

const Input = forwardRef(({
  type = 'text',
  placeholder,
  value,
  onChange,
  icon: Icon,
  label,
  required = false,
  minLength,
  error,
}, ref) => {
  return (
    <div className="space-y-1">
      {label && (
        <label className="text-xs font-medium text-gray-300 ml-1">
          {label}
        </label>
      )}
      <div className="relative">
        {Icon && (
          <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
        )}
        <input
          ref={ref}
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          required={required}
          minLength={minLength}
          className={`input-field ${Icon ? 'pl-10' : ''} ${error ? 'border-red-500' : ''}`}
        />
      </div>
      {error && (
        <p className="text-xs text-red-400 ml-1">{error}</p>
      )}
    </div>
  );
});

Input.displayName = 'Input';
export default Input;