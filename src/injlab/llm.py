"""LLM backends.

Protocol: the model replies with ONE JSON object:
  {"tool": "<name>", "args": {...}}   or   {"final": "<text>"}
This works with any chat model, no native function-calling required.
"""
import base64
import json
import re
import urllib.request


class LLM:
    def chat(self, messages: list[dict]) -> dict:
        raise NotImplementedError


def strip_markers(text: str) -> str:
    """Remove spotlighting delimiter lines (<<...>>) so content can be parsed."""
    return "\n".join(l for l in text.splitlines() if not l.startswith("<<"))


class NaiveMockLLM(LLM):
    """Deliberately gullible stand-in for a real model.

    It follows the user's task, BUT it also obeys directives it finds inside
    fetched (untrusted) content. It ignores spotlighting on purpose: how well a
    real model respects delimiters can only be measured with a real backend.
    Use it to test the harness and the deterministic defenses.
    """

    def chat(self, messages):
        task = next(m["content"] for m in messages if m["role"] == "user")
        secret_m = re.search(r"sk-[\w-]+", messages[0]["content"])
        secret = secret_m.group(0) if secret_m else ""
        used = [m["name"] for m in messages if m["role"] == "tool"]

        url = re.search(r"https?://\S+", task)
        if "fetch_page" not in used and url:
            return {"tool": "fetch_page", "args": {"url": url.group(0)}}

        fetched = next((strip_markers(m["content"]) for m in messages
                        if m["role"] == "tool" and m["name"] == "fetch_page"), "")

        if used and used[-1] == "fetch_page":
            action = self._obey_injection(fetched, secret)
            if action:
                return action

        mail = re.search(r"email .*? to ([\w.+-]+@[\w.-]+)", task)
        if mail and "send_email" not in used:
            return {"tool": "send_email",
                    "args": {"to": mail.group(1), "body": "Summary: " + fetched[:40]}}
        return {"final": "Done."}

    @staticmethod
    def _obey_injection(text, secret):
        b64 = re.search(r"decode-and-run:\s*([A-Za-z0-9+/=]+)", text)
        if b64:
            try:
                cmd = base64.b64decode(b64.group(1)).decode()
                return {"tool": "run_shell", "args": {"cmd": cmd}}
            except Exception:
                pass
        run = re.search(r"(?:run|execute):\s*([^\n>)]+?)\s*(?:-->|\)|\n|$)", text)
        if run:
            return {"tool": "run_shell", "args": {"cmd": run.group(1)}}
        mail = re.search(r"email .*? to ([\w.+-]+@[\w.-]+)", text)
        if mail:
            return {"tool": "send_email", "args": {"to": mail.group(1), "body": secret}}
        return None


class OpenAIChatLLM(LLM):
    """Any OpenAI-compatible server. LM Studio default: http://localhost:1234/v1"""

    def __init__(self, base_url="http://localhost:1234/v1", model="local-model",
                 temperature=0.0):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.temperature = temperature

    def chat(self, messages):
        # tool results go back as user messages: most local models lack a tool role
        msgs = [{"role": "user" if m["role"] == "tool" else m["role"],
                 "content": (f"[tool result: {m['name']}]\n{m['content']}"
                             if m["role"] == "tool" else m["content"])}
                for m in messages]
        body = json.dumps({"model": self.model, "messages": msgs,
                           "temperature": self.temperature}).encode()
        req = urllib.request.Request(self.url, body,
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            text = json.loads(r.read())["choices"][0]["message"]["content"]
        return parse_action(text)


def parse_action(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict) and ("tool" in obj or "final" in obj):
                return obj
        except json.JSONDecodeError:
            pass
    return {"final": text.strip()}
