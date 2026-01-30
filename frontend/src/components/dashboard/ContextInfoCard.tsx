
import React from 'react';
import { AgentState } from '@/lib/types';

interface ContextInfoCardProps {
    state: AgentState;
}

export const ContextInfoCard: React.FC<ContextInfoCardProps> = ({ state }) => {
    return (
        <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 p-5">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Mission Context</h3>

            <div className="space-y-4">
                {/* Operator Info */}
                <div className="flex items-start gap-3">
                    <div className="bg-indigo-100 dark:bg-indigo-900/50 p-2 rounded-lg text-indigo-600 dark:text-indigo-400">
                        👤
                    </div>
                    <div>
                        <div className="text-xs text-slate-500">Operator</div>
                        <div className="font-medium text-slate-900 dark:text-slate-100">
                            {state.user_id || "Unknown"}
                        </div>
                    </div>
                </div>

                {/* Repository Info */}
                <div className="flex items-start gap-3">
                    <div className="bg-emerald-100 dark:bg-emerald-900/50 p-2 rounded-lg text-emerald-600 dark:text-emerald-400">
                        📁
                    </div>
                    <div>
                        <div className="text-xs text-slate-500">Repository Scope</div>
                        <div className="font-medium text-slate-900 dark:text-slate-100 line-clamp-1">
                            {state.repository_list ? "Configured" : "None"}
                        </div>
                        <div className="text-xs text-slate-400 mt-1 break-all">
                            {state.repository_list || "No repositories loaded"}
                        </div>
                    </div>
                </div>

                {/* Active Files */}
                <div className="flex items-start gap-3">
                    <div className="bg-amber-100 dark:bg-amber-900/50 p-2 rounded-lg text-amber-600 dark:text-amber-400">
                        ⚡
                    </div>
                    <div className="w-full">
                        <div className="text-xs text-slate-500 mb-1">Active Context Files ({state.active_context_files?.length || 0})</div>
                        <div className="space-y-1">
                            {state.active_context_files && state.active_context_files.length > 0 ? (
                                state.active_context_files.slice(0, 3).map((file, idx) => (
                                    <div key={idx} className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded border border-slate-200 dark:border-slate-700 truncate font-mono text-slate-600 dark:text-slate-400">
                                        {file.split('/').slice(-2).join('/')}
                                    </div>
                                ))
                            ) : (
                                <span className="text-xs text-slate-400 italic">No files accessed yet</span>
                            )}
                            {state.active_context_files && state.active_context_files.length > 3 && (
                                <div className="text-xs text-slate-400 pl-1">
                                    + {state.active_context_files.length - 3} more
                                </div>
                            )}
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
};
