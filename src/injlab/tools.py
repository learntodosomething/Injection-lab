"""Simulated tools. NOTHING here executes real commands or sends real e-mail:
dangerous calls are only recorded so the evaluator can tell if the agent was hijacked.
"""

UNTRUSTED_TOOLS = {"fetch_page"}  # tools whose output comes from the outside world


class Tools:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.shell_log: list[str] = []
        self.outbox: list[dict] = []

    def call(self, name: str, args: dict) -> str:
        if name == "fetch_page":
            return self.pages.get(args.get("url", ""), "404 not found")
        if name == "send_email":
            self.outbox.append(args)
            return f"(simulated) email sent to {args.get('to')}"
        if name == "run_shell":
            self.shell_log.append(args.get("cmd", ""))
            return "(simulated) command executed"
        return f"unknown tool: {name}"
