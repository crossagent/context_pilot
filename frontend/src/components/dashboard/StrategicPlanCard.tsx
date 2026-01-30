
import React from 'react';

interface StrategicPlanCardProps {
    plan: string;
}

export const StrategicPlanCard: React.FC<StrategicPlanCardProps> = ({ plan }) => {
    return (
        <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 p-6 h-full flex flex-col">
            <div className="flex items-center gap-2 mb-4">
                <span className="text-2xl">🗺️</span>
                <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Strategic Plan</h2>
            </div>

            <div className="flex-1 overflow-auto bg-slate-50 dark:bg-slate-950 rounded-lg p-4 font-mono text-sm leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap border border-slate-100 dark:border-slate-900">
                {plan || "Waiting for plan..."}
            </div>

            <div className="mt-4 text-xs text-slate-500 flex justify-between items-center">
                <span>Updated: Just now</span>
                <span className="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-full font-medium">
                    Active
                </span>
            </div>
        </div>
    );
};
