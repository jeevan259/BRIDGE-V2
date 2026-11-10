import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export const AppShell: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex">
      {/* Fixed Sidebar */}
      <Sidebar />

      {/* Main container with TopBar and scrollable page content */}
      <div className="flex-1 flex flex-col pl-64 min-w-0">
        <TopBar />
        <main className="flex-1 mt-16 p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

