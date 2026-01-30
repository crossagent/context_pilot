// State of the agent, make sure this aligns with your agent's state.
export type AgentState = {
  proverbs?: string[];
  strategic_plan?: string;
  user_id?: string;
  repository_list?: string;
  active_context_files?: string[];
  last_rag_query?: string;
  cur_date_time?: string;
  current_os?: string;
  total_estimated_cost?: number;
}