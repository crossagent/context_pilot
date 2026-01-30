
import React from 'react';

interface KnowledgeStateCardProps {
    lastQuery?: string;
}

export const KnowledgeStateCard: React.FC<KnowledgeStateCardProps> = ({ lastQuery }) => {
    return (
        <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 p-5">
            <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">🧠</span>
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Active Recall</h3>
            </div>

            {lastQuery ? (
                <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800/30 rounded-lg p-3">
                    <div className="text-xs text-purple-600 dark:text-purple-400 font-semibold mb-1">
                        Last Memory Access
                    </div>
                    <div className="text-sm text-slate-700 dark:text-slate-300 italic">
                        "{lastQuery}"
                    </div>
                </div>
            ) : (
                <div className="text-sm text-slate-400 italic p-2">
                    Agent has not accessed internal knowledge base yet.
                </div>
            )}
        </div>
    );
};
