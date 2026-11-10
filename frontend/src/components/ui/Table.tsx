import React, { HTMLAttributes, ThHTMLAttributes, TdHTMLAttributes } from 'react';

export const Table: React.FC<HTMLAttributes<HTMLTableElement>> = ({
  className = '',
  children,
  ...props
}) => {
  return (
    <div className="w-full overflow-x-auto rounded-lg border border-slate-800">
      <table className={`w-full text-left text-sm text-slate-300 ${className}`} {...props}>
        {children}
      </table>
    </div>
  );
};

export const TableHeader: React.FC<HTMLAttributes<HTMLTableSectionElement>> = ({
  className = '',
  children,
  ...props
}) => {
  return (
    <thead
      className={`bg-slate-900/80 border-b border-slate-800 text-xs uppercase font-medium text-slate-400 tracking-wider ${className}`}
      {...props}
    >
      {children}
    </thead>
  );
};

export const TableBody: React.FC<HTMLAttributes<HTMLTableSectionElement>> = ({
  className = '',
  children,
  ...props
}) => {
  return (
    <tbody className={`divide-y divide-slate-800/60 bg-[#151D2F] ${className}`} {...props}>
      {children}
    </tbody>
  );
};

export const TableRow: React.FC<HTMLAttributes<HTMLTableRowElement>> = ({
  className = '',
  children,
  ...props
}) => {
  return (
    <tr
      className={`hover:bg-slate-800/40 transition-colors ${className}`}
      {...props}
    >
      {children}
    </tr>
  );
};

export const TableHead: React.FC<ThHTMLAttributes<HTMLTableCellElement>> = ({
  className = '',
  children,
  ...props
}) => {
  return (
    <th className={`px-4 py-3 font-semibold ${className}`} {...props}>
      {children}
    </th>
  );
};

export const TableCell: React.FC<TdHTMLAttributes<HTMLTableCellElement>> = ({
  className = '',
  children,
  ...props
}) => {
  return (
    <td className={`px-4 py-3 align-middle ${className}`} {...props}>
      {children}
    </td>
  );
};

