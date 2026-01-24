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
import { CopilotKitCSSProperties, CopilotChat } from "@copilotkit/react-ui";
import { useState } from "react";

export default function CopilotKitPage() {
  const [themeColor, setThemeColor] = useState("#6366f1");

  // 🪁 Shared State: https://docs.copilotkit.ai/adk/shared-state
  const { state, setState } = useCoAgent<AgentState>({
    name: "context_pilot_app",
    initialState: {
      proverbs: [
        "CopilotKit may be new, but its the best thing since sliced bread.",
      ],
    },
  });

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

  //🪁 Generative UI: https://docs.copilotkit.ai/adk/generative-ui
  useRenderToolCall(
    {
      name: "get_weather",
      description: "Get the weather for a given location.",
      parameters: [{ name: "location", type: "string", required: true }],
      render: ({ args, result }) => {
        return <WeatherCard location={args.location} themeColor={themeColor} />;
      },
    },
    [themeColor],
  );

  return (
    <main
      style={
        { "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties
      }
      className="h-screen"
    >
      <CopilotChat
        labels={{
          title: "ContextPilot Assistant",
          initial: "👋 您好！我是 ContextPilot，您的智能工程领航员。",
        }}
        instructions="You are a helpful assistant that can help with various tasks."
        suggestions={[
          {
            title: "开始使用",
            message: "帮我分析一下当前项目的结构",
          },
        ]}
      />
    </main>
  );
}
