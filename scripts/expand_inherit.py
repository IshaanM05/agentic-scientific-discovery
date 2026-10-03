"""One-off: replace `tools: {x: inherit}` in sub-agents of agents/planner.yaml with explicit function
declarations (omnigent 0.16 on Windows: `inherit` did not reach sub-agents in a live run)."""
import re

s = open("agents/planner.yaml").read()
top = s.split("tools:\n", 1)[1].split("  literature:\n", 1)[0]
defs = {}
for line in top.splitlines():
    m = re.match(r"  (\w+): \{type: function", line)
    if m:
        defs[m.group(1)] = line.strip()[len(m.group(1)) + 2:]


def block(names):
    return "    tools:\n" + "".join(f"      {n}: {defs[n]}\n" for n in names)


PLAN = {"literature": ["literature_search", "record_step"],
        "insight": ["get_features", "propose_hypothesis", "record_step"],
        "analysis": ["analyze_result", "select_next", "record_step"],
        "safety": ["flag_risk", "record_step"]}
for agent, names in PLAN.items():
    s = re.sub(r"(  %s:\n(?:    .*\n)*?)    tools: \{[^\n]*\}\n" % agent,
               lambda m: m.group(1) + block(names), s, count=1)
open("agents/planner.yaml", "w").write(s)
