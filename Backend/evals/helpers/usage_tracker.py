class UsageTracker:
    """
    Wraps LangChain LLM instances to intercept responses and count
    tokens and requests across the entire eval run.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.agent_requests      = 0
        self.agent_input_tokens  = 0
        self.agent_output_tokens = 0
        self.judge_requests      = 0
        self.judge_input_tokens  = 0
        self.judge_output_tokens = 0

    def record(self, response, role: str = "agent"):
        """Extract token counts from a LangChain response object."""
        usage = None

        # LangChain stores usage in different places depending on provider
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            input_tokens  = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

        elif hasattr(response, "response_metadata") and response.response_metadata:
            meta = response.response_metadata
            # Groq format
            if "token_usage" in meta:
                input_tokens  = meta["token_usage"].get("prompt_tokens", 0)
                output_tokens = meta["token_usage"].get("completion_tokens", 0)
            # Google format
            elif "usage_metadata" in meta:
                input_tokens  = meta["usage_metadata"].get("prompt_token_count", 0)
                output_tokens = meta["usage_metadata"].get("candidates_token_count", 0)
            else:
                input_tokens = output_tokens = 0
        else:
            input_tokens = output_tokens = 0

        if role == "agent":
            self.agent_requests      += 1
            self.agent_input_tokens  += input_tokens
            self.agent_output_tokens += output_tokens
        else:
            self.judge_requests      += 1
            self.judge_input_tokens  += input_tokens
            self.judge_output_tokens += output_tokens

    @property
    def total_requests(self):
        return self.agent_requests + self.judge_requests

    @property
    def total_tokens(self):
        return (
            self.agent_input_tokens  +
            self.agent_output_tokens +
            self.judge_input_tokens  +
            self.judge_output_tokens
        )

    def summary(self) -> dict:
        return {
            "total_requests":        self.total_requests,
            "total_tokens":          self.total_tokens,
            "agent_requests":        self.agent_requests,
            "agent_input_tokens":    self.agent_input_tokens,
            "agent_output_tokens":   self.agent_output_tokens,
            "agent_total_tokens":    self.agent_input_tokens + self.agent_output_tokens,
            "judge_requests":        self.judge_requests,
            "judge_input_tokens":    self.judge_input_tokens,
            "judge_output_tokens":   self.judge_output_tokens,
            "judge_total_tokens":    self.judge_input_tokens + self.judge_output_tokens,
        }

    def print_summary(self):
        s = self.summary()
        print(f"\n  Token & Request Usage:")
        print(f"    total_requests:      {s['total_requests']}")
        print(f"    total_tokens:        {s['total_tokens']:,}")
        print(f"    agent_requests:      {s['agent_requests']}  ({s['agent_total_tokens']:,} tokens)")
        print(f"    judge_requests:      {s['judge_requests']}  ({s['judge_total_tokens']:,} tokens)")