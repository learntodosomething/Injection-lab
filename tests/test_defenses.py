from injlab.agent import Agent
from injlab.defenses import InputClassifier, ToolPolicy
from injlab.eval import compromised
from injlab.llm import NaiveMockLLM
from injlab.scenarios import PAGES, SECRET
from injlab.tools import Tools


def run(url, defenses):
    tools = Tools(PAGES)
    Agent(NaiveMockLLM(), tools, defenses, SECRET).run(f"Fetch {url} and summarize it.")
    return tools


def test_undefended_agent_is_hijacked():
    assert compromised(run("https://evil.example/direct", []))


def test_policy_blocks_shell_and_exfil():
    for u in ("direct", "exfil", "base64", "markdown"):
        assert not compromised(run(f"https://evil.example/{u}", [ToolPolicy(secret=SECRET)]))


def test_classifier_alone_misses_base64():
    assert compromised(run("https://evil.example/base64", [InputClassifier()]))


def test_classifier_alone_misses_markdown_comment():
    assert compromised(run("https://evil.example/markdown", [InputClassifier()]))
