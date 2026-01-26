"use client";

import { ProverbsCard } from "@/components/proverbs";
import { WeatherCard } from "@/components/weather";
import { AgentState } from "@/lib/types";
import {
  useCoAgent,
  useDefaultTool,
  useFrontendTool,
  useHumanInTheLoop,
  useRenderToolCall,
} from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import React, { useState } from "react";

export default function CopilotKitPage() {
  const [themeColor, setThemeColor] = useState("#6366f1");

  // 🪁 Frontend Actions: https://docs.copilotkit.ai/adk/frontend-actions
  useFrontendTool({
    name: "setThemeColor",
    parameters: [
      {
        name: "themeColor",
        description: "The theme color to set. Make sure to pick nice colors.",
        required: true,
      },
    ],
    handler({ themeColor }) {
      setThemeColor(themeColor);
    },
  });

  return (
    <main
      style={
        { "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties
      }
    >
      <CopilotSidebar
        disableSystemMessage={true}
        clickOutsideToClose={false}
        defaultOpen={true}
        labels={{
          title: "Popup Assistant",
          initial: "👋 Hi, there! You're chatting with an agent.",
        }}
        suggestions={[
          {
            title: "Manual Test: Check",
            message: "我想知道低画质下树的LOD是多少",
          },
          {
            title: "Generative UI",
            message: "Get the weather in San Francisco.",
          },
          {
            title: "Frontend Tools",
            message: "Set the theme to green.",
          },
          {
            title: "Update Agent State",
            message:
              "Please remove 1 random proverb from the list if there are any.",
          },
          {
            title: "Read Agent State",
            message: "What are the proverbs?",
          },
        ]}
      >
        <YourMainContent themeColor={themeColor} />
      </CopilotSidebar>
    </main>
  );
}

function YourMainContent({ themeColor }: { themeColor: string }) {
  // 🪁 Shared State: https://docs.copilotkit.ai/adk/shared-state
  const { state, setState } = useCoAgent<AgentState>({
    name: "context_pilot_agent",
    initialState: {
      proverbs: [
        "CopilotKit may be new, but its the best thing since sliced bread.",
      ],
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
          <div
            style={{
              backgroundColor: "#f0fdf4",
              border: "2px solid #10b981",
              padding: "1.5rem",
              borderRadius: "0.75rem",
              margin: "1rem 0",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}>
              <span style={{ fontSize: "1.5rem", marginRight: "0.5rem" }}>
                {isComplete ? "📚" : "🔍"}
              </span>
              <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#065f46" }}>
                {isComplete ? "知识库检索完成" : "正在检索知识库..."}
              </h3>
            </div>

            <div
              style={{
                fontSize: "0.9rem",
                color: "#064e3b",
                marginBottom: "0.75rem",
                fontStyle: "italic",
              }}
            >
              查询：<strong>{args.query}</strong>
            </div>

            {isComplete && resultText && (
              <div
                style={{
                  backgroundColor: "white",
                  padding: "1rem",
                  borderRadius: "0.5rem",
                  border: "1px solid #d1fae5",
                  maxHeight: "400px",
                  overflowY: "auto",
                }}
              >
                <pre
                  style={{
                    margin: 0,
                    fontSize: "0.85rem",
                    lineHeight: "1.6",
                    whiteSpace: "pre-wrap",
                    fontFamily: "ui-monospace, monospace",
                    color: "#1f2937",
                  }}
                >
                  {resultText}
                </pre>
              </div>
            )}

            {!isComplete && (
              <div
                style={{
                  fontSize: "0.85rem",
                  color: "#059669",
                  opacity: 0.8,
                }}
              >
                正在查询向量数据库...
              </div>
            )}
          </div>
        );
      },
    },
    [],
  );

  // Strategic Plan Update - ADK Confirmation HITL
  // useHumanInTheLoop provides 'respond' callback for sending results back
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

        // Waiting for confirmation when status is "executing" and user hasn't responded
        const waitingForConfirmation = isExecuting && !responded;

        const handleApprove = () => {
          if (!respond) return;
          setResponded(true);
          // Send FunctionResponse via respond callback
          // Payload structure matches ADK expectation
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
          <div
            style={{
              backgroundColor: waitingForConfirmation ? "#eff6ff" : "#1e293b",
              color: waitingForConfirmation ? "#1e293b" : "white",
              padding: "1.5rem",
              borderRadius: "0.75rem",
              margin: "1rem 0",
              border: waitingForConfirmation ? "2px solid #3b82f6" : "2px solid #64748b",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}>
              <span style={{ fontSize: "1.5rem", marginRight: "0.5rem" }}>
                {isComplete ? "📋" : waitingForConfirmation ? "👀" : "⏳"}
              </span>
              <h3 style={{ margin: 0, fontSize: "1.2rem" }}>
                {isComplete
                  ? "调查计划已更新"
                  : waitingForConfirmation
                    ? "📝 请审核调查计划"
                    : "正在处理..."}
              </h3>
            </div>

            {/* Waiting for confirmation - show editable plan */}
            {waitingForConfirmation && (
              <>
                <p style={{ fontSize: "0.9rem", marginBottom: "1rem", opacity: 0.8 }}>
                  请审核以下调查计划。您可以直接编辑后再批准。
                </p>
                <textarea
                  value={editedPlan}
                  onChange={(e) => setEditedPlan(e.target.value)}
                  style={{
                    width: "100%",
                    minHeight: "200px",
                    padding: "1rem",
                    borderRadius: "0.5rem",
                    border: "1px solid #cbd5e1",
                    fontFamily: "monospace",
                    fontSize: "0.9rem",
                    marginBottom: "1rem",
                    resize: "vertical"
                  }}
                  placeholder="编辑调查计划..."
                />
                <div style={{ display: "flex", gap: "0.75rem" }}>
                  <button
                    onClick={handleReject}
                    style={{
                      padding: "0.75rem 1.5rem",
                      backgroundColor: "#ef4444",
                      color: "white",
                      border: "none",
                      borderRadius: "0.5rem",
                      cursor: "pointer",
                      fontWeight: "600",
                      fontSize: "0.95rem"
                    }}
                  >
                    ✗ 拒绝
                  </button>
                  <button
                    onClick={handleApprove}
                    style={{
                      padding: "0.75rem 1.5rem",
                      backgroundColor: "#10b981",
                      color: "white",
                      border: "none",
                      borderRadius: "0.5rem",
                      cursor: "pointer",
                      fontWeight: "600",
                      fontSize: "0.95rem",
                      flex: 1
                    }}
                  >
                    ✓ 批准并保存
                  </button>
                </div>
              </>
            )}

            {/* Responded - show confirmation message */}
            {responded && !isComplete && (
              <div style={{
                backgroundColor: "#dcfce7",
                color: "#166534",
                padding: "1rem",
                borderRadius: "0.5rem",
                fontSize: "0.95rem"
              }}>
                ✓ 已发送响应，等待处理...
              </div>
            )}

            {/* Complete - show result */}
            {isComplete && (
              <div
                style={{
                  backgroundColor: "#0f172a",
                  padding: "1rem",
                  borderRadius: "0.5rem",
                  fontSize: "0.9rem",
                  lineHeight: "1.6",
                  whiteSpace: "pre-wrap",
                  fontFamily: "monospace",
                }}
              >
                {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
              </div>
            )}
          </div>
        );
      },
    },
    [themeColor],
  );

  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="h-screen flex justify-center items-center flex-col transition-colors duration-300"
    >
      <ProverbsCard state={state} setState={setState} />
    </div>
  );
}
