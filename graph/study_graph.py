import json
import re
from langgraph.graph import StateGraph, END
from llm import get_llm
from planner_prompt import get_planner_prompt
from rag.chroma_store import rag_search

llm = get_llm()


def extract_json_array(text: str):
    """
    Extracts JSON array from LLM output safely.
    Works even if LLM adds extra text before/after JSON.
    """
    # Find first JSON array in response
    match = re.search(r"\[\s*\{.*?\}\s*\]", text, re.DOTALL)

    if not match:
        # fallback: try any [...]
        match = re.search(r"\[.*\]", text, re.DOTALL)

    if not match:
        raise ValueError("❌ LLM response does not contain a JSON array.")

    json_str = match.group().strip()

   
    if json_str.startswith('"') and json_str.endswith('"'):
        json_str = json.loads(json_str)

    return json.loads(json_str)


def planner_node(state):
    #RAG from syllabus
    query = " ".join(state["subjects"]) + " syllabus units modules important topics"
    retrieved = rag_search(query, top_k=6)

    rag_context = "\n\n".join(
        [f"[Chunk {i+1}] {r['text']}" for i, r in enumerate(retrieved)]
    ) if retrieved else "No syllabus context found."

    prompt = get_planner_prompt(
        subjects=state["subjects"],
        exam_date=state["exam_date"],
        hours_per_day=state["hours_per_day"],
        rag_context=rag_context
    )

    #Try 3 attempts
    for attempt in range(3):
        response = llm.invoke(prompt).content
        print(f"\n🔍 LLM RESPONSE Attempt {attempt+1}:\n{response}\n")

        try:
            plan = extract_json_array(response)
            break
        except Exception:
            #Repair prompt (force JSON only)
            prompt = prompt + """
            
IMPORTANT FINAL WARNING:
Return ONLY JSON ARRAY.
No markdown, no explanation, no text.
Only output like:
[
  {"subject":"...","topic":"...","date":"YYYY-MM-DD","hours":2}
]
"""

            if attempt == 2:
                raise ValueError(
                    " Groq did not return valid JSON even after retries. Check terminal LLM output."
                )

    #output
    cleaned_plan = []
    for item in plan:
        cleaned_plan.append({
            "subject": item.get("subject", "Unknown"),
            "topic": item.get("topic", "Topic Missing"),
            "date": item.get("date", state["exam_date"]),
            "hours": float(item.get("hours", 1))
        })

    state["plan"] = cleaned_plan
    return state


workflow = StateGraph(dict)
workflow.add_node("planner", planner_node)
workflow.set_entry_point("planner")
workflow.add_edge("planner", END)

study_graph = workflow.compile()
