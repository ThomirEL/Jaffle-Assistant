from evals.eval_configs.prompt_variants import ANALYTICAL_PROMPT, STEP_PROMPT, CONCISE_PROMPT, BASELINE_PROMPT, UPDATED_BASELINE_PROMPT, SQL_UPDATED_BASELINE_PROMPT
from evals.eval_configs.agent_variants import REASONING_PROMPT

AGENT_VARIANTS = [
    {
        "name": "baseline",
        "agent_type": "single",
        "description": "Single agent with standard business-assistant prompt",
        "system_prompt": BASELINE_PROMPT,
    },
    {
        "name": "reasoning",
        "agent_type": "single",
        "description": "Single agent with structured <thinking> reasoning protocol",
        "system_prompt": REASONING_PROMPT,
    },
    {
        "name": "multi_agent",
        "agent_type": "multi",
        "description": "Three sub-agents: SQL specialist, chart specialist, insight specialist",
        "system_prompt": None,
    },
    {
        "name": "reasoning_multi_agent",
        "agent_type": "reasoning_multi",
        "description": "Three sub-agents, each with <thinking> reasoning before acting",
        "system_prompt": None,
    },
]

PROMPT_VARIANTS = [
    {
        "name": "analytical",
        "agent_type": "single",
        "description": "Baseline prompt with more emphasis on analytical thinking and insights",
        "system_prompt": ANALYTICAL_PROMPT,
    },
    {
        "name": "step_by_step",
        "agent_type": "single",
        "description": "Baseline prompt with explicit step-by-step reasoning instructions",
        "system_prompt": STEP_PROMPT,
    },
    {
        "name": "concise",
        "agent_type": "single",
        "description": "Baseline prompt with instructions to be concise and avoid unnecessary text",
        "system_prompt": CONCISE_PROMPT,
    },
    {
        "name": "baseline",
        "agent_type": "single",
        "description": "Original prompt with no modifications",
        "system_prompt": BASELINE_PROMPT
    }
]

UPDATED_BASELINE = [
    {
        "name": "updated_baseline",
        "agent_type": "single",
        "description": "Baseline prompt with minor updates to improve clarity and instructions",
        "system_prompt": UPDATED_BASELINE_PROMPT,
    }
]

SQL_UPDATED_BASELINE_PROMPT = [
    {
        "name": "sql_updated_baseline",
        "agent_type": "single",
        "description": "Updated baseline prompt with additional instructions to avoid SQL errors",
        "system_prompt": SQL_UPDATED_BASELINE_PROMPT,
    }
]