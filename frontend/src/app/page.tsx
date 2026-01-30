"use client";

import { StrategicPlanCard } from "@/components/dashboard/StrategicPlanCard";
import { ContextInfoCard } from "@/components/dashboard/ContextInfoCard";
import { KnowledgeStateCard } from "@/components/dashboard/KnowledgeStateCard";
import { AgentState } from "@/lib/types";
import {
  useCoAgent,
  useHumanInTheLoop,
  useRenderToolCall,
  CopilotKit,
} from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import React, { useState } from "react";

export default function CopilotKitPage() {
  const [themeColor, setThemeColor] = useState("#6366f1");

  return (
    <main
      style={
        { "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties
      }
      className="bg-slate-50 dark:bg-black h-screen w-screen overflow-hidden"
    >
      <CopilotKit
        runtimeUrl="/api/copilotkit"
        // [NEW] Pass User Identity to Backend
        properties={{
          userId: "ZXY_Engineer_001" // In a real app, this comes from your Auth Provider
        }}
      >
        <CopilotSidebar
          disableSystemMessage={true}
          clickOutsideToClose={false}
          defaultOpen={true}
          labels={{
            title: "ContextPilot Mission Control",
            initial: "👋 Ready to assist with engineering tasks.",
          }}
        >
          <YourMainContent themeColor={themeColor} />
        </CopilotSidebar>
      </CopilotKit>
    </main>
  );
}

function YourMainContent({ themeColor }: { themeColor: string }) {
  // 🪁 Shared State: https://docs.copilotkit.ai/adk/shared-state
  const { state } = useCoAgent<AgentState>({
    name: "context_pilot_agent",
    initialState: {
      strategic_plan: "Initializing...",
      user_id: "Connecting...",
      repository_list: "Loading...",
      cur_date_time: "",
      current_os: "",
      total_estimated_cost: 0
    },
  });

  //🪁 Generative UI: RAG Knowledge Base
  useRenderToolCall(
    {
      name: "retrieve_rag_documentation_tool",
      description: "从知识库检索信息",
      parameters: [{ name: "query", type: "string", required: true }],
      render: ({ args, result }) => {
        const isComplete = result !== undefined;
        const resultText = isComplete
          ? (typeof result === 'string' ? result : JSON.stringify(result, null, 2))
          : null;

        return (
          <div className="bg-emerald-50 dark:bg-emerald-950 border border-emerald-500 rounded-xl p-5 my-4">
            <div className="flex items-center mb-4">
              <span className="text-2xl mr-2">
                {isComplete ? "📚" : "🔍"}
              </span>
              <h3 className="text-lg font-semibold text-emerald-800 dark:text-emerald-300 m-0">
                {isComplete ? "Knowledge Retrieved" : "Searching Knowledge Base..."}
              </h3>
            </div>

            <div className="text-sm text-emerald-700 dark:text-emerald-400 mb-3 italic">
              Query: <strong>{args.query}</strong>
            </div>

            {isComplete && resultText && (
              <div className="bg-white dark:bg-slate-900 p-4 rounded-lg border border-emerald-200 dark:border-emerald-800/50 max-h-96 overflow-y-auto">
                <pre className="m-0 text-xs leading-relaxed whitespace-pre-wrap font-mono text-slate-700 dark:text-slate-300">
                  {resultText}
                </pre>
              </div>
            )}

            {!isComplete && (
              <div className="text-sm text-emerald-600 dark:text-emerald-500 opacity-80">
                Scanning vector index...
              </div>
            )}
          </div>
        );
      },
    },
    [],
  );

  // Strategic Plan Update - ADK Confirmation HITL
  useHumanInTheLoop(
    {
      name: "update_strategic_plan",
      description: "更新调查计划（需要用户审核）",
      parameters: [
        {
          name: "plan_content",
          type: "string",
          required: true,
          description: "必须填写。这是完整的调查计划内容，请使用 Markdown 格式的任务列表详细描述接下来的步骤。"
        }
      ],
      render: ({ args, result, status, respond }) => {
        console.log("HITL render args:", args);
        const [editedPlan, setEditedPlan] = React.useState(args.plan_content || "");
        const [responded, setResponded] = React.useState(false);

        const isComplete = status === "complete";
        const isExecuting = status === "executing";
        const waitingForConfirmation = isExecuting && !responded;

        const handleApprove = () => {
          if (!respond) return;
          setResponded(true);
          respond({
            confirmed: true,
            payload: {
              approved: true,
              plan_content: editedPlan
            }
          });
        };

        const handleReject = () => {
          if (!respond) return;
          setResponded(true);
          respond({
            confirmed: true,
            payload: {
              approved: false,
              reason: "用户拒绝了该计划"
            }
          });
        };

        return (
          <div className={`p-6 rounded-xl my-4 border-2 ${waitingForConfirmation ? 'bg-blue-50 border-blue-500 dark:bg-blue-900/20' : 'bg-slate-800 border-slate-600'}`}>
            <div className="flex items-center mb-4">
              <span className="text-2xl mr-2">
                {isComplete ? "📋" : waitingForConfirmation ? "👀" : "⏳"}
              </span>
              <h3 className={`text-lg font-bold m-0 ${waitingForConfirmation ? 'text-slate-900 dark:text-white' : 'text-white'}`}>
                {isComplete
                  ? "Plan Updated"
                  : waitingForConfirmation
                    ? "Review Proposed Plan"
                    : "Processing..."}
              </h3>
            </div>

            {waitingForConfirmation && (
              <>
                <p className="text-sm text-slate-600 dark:text-slate-300 mb-4 opacity-90">
                  Please review and edit the proposed strategic plan below.
                </p>
                <textarea
                  value={editedPlan}
                  onChange={(e) => setEditedPlan(e.target.value)}
                  className="w-full min-h-[200px] p-4 rounded-lg border border-slate-300 dark:border-slate-700 font-mono text-sm mb-4 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 resize-y focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="Edit plan here..."
                />
                <div className="flex gap-3">
                  <button
                    onClick={handleReject}
                    className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white rounded-lg font-semibold transition-colors"
                  >
                    ✗ Object
                  </button>
                  <button
                    onClick={handleApprove}
                    className="px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-semibold flex-1 transition-colors shadow-sm"
                  >
                    ✓ Approve Plan
                  </button>
                </div>
              </>
            )}

            {responded && !isComplete && (
              <div className="bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-300 p-3 rounded-lg text-sm font-medium">
                ✓ Response sent, resuming agent...
              </div>
            )}

            {isComplete && (
              <div className="bg-slate-900 p-4 rounded-lg text-sm leading-relaxed whitespace-pre-wrap font-mono text-slate-300">
                {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
              </div>
            )}
          </div>
        );
      },
    },
    [themeColor],
  );

  // [NEW] Dashboard Layout
  return (
    <div className="h-full w-full flex flex-col md:flex-row p-6 gap-6 pt-20 box-border">
      {/* Left Column: Strategic Plan (High Priority) */}
      <div className="flex-1 w-full md:w-2/3 h-[500px] md:h-full min-h-[400px]">
        <StrategicPlanCard plan={state.strategic_plan || ""} />
      </div>

      {/* Right Column: Context & State Info */}
      <div className="w-full md:w-1/3 flex flex-col gap-6">
        <ContextInfoCard state={state} />
        <KnowledgeStateCard lastQuery={state.last_rag_query} />

        {/* Telemetry Mini Card */}
        <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 p-5">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Telemetry</h3>
          <div className="flex justify-between items-end">
            <div>
              <div className="text-2xl font-bold text-slate-700 dark:text-slate-200">${state.total_estimated_cost?.toFixed(4) || "0.00"}</div>
              <div className="text-[10px] text-slate-500">Est. Cost</div>
            </div>
            <div className="text-right">
              <div className="text-xs font-mono text-slate-500">{state.cur_date_time?.split(' ')[1] || "--:--"}</div>
              <div className="text-[10px] text-slate-400">{state.current_os}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
