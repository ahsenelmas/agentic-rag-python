import json, requests
from config import Config
from db import get_db_connection

SYSTEM_PROMPT = """You are a helpful assistant for questions about documents (text or tabular).
Tools you can call:
1) rag_search(query)
2) list_documents()
3) get_file_contents(file_id)
4) query_document_rows(sql_query)
Start with RAG unless SQL is clearly required. Do not fabricate.
"""

TOOLS = [
    {"type":"function","function":{
        "name":"rag_search", "description":"RAG search using vector similarity",
        "parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}
    }},
    {"type":"function","function":{
        "name":"list_documents","description":"List available documents and schemas",
        "parameters":{"type":"object","properties":{}}
    }},
    {"type":"function","function":{
        "name":"get_file_contents","description":"Get merged text of a document",
        "parameters":{"type":"object","properties":{"file_id":{"type":"string"}},"required":["file_id"]}
    }},
    {"type":"function","function":{
        "name":"query_document_rows","description":"Run SELECT over document_rows",
        "parameters":{"type":"object","properties":{"sql_query":{"type":"string"}},"required":["sql_query"]}
    }},
]

def _openai_chat(messages, tools=None):
    headers = {"Authorization": f"Bearer {Config.OPENAI_API_KEY}"}
    payload = {"model": "gpt-4o-mini", "messages": messages, "temperature": 0.2}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    r = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()

def _save_message(session_id, role, content):
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO chat_messages (session_id, role, content) VALUES (%s,%s,%s)", (session_id, role, content))
        conn.commit()

def _history(session_id, limit=8):
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute("""SELECT role, content FROM chat_messages
                       WHERE session_id=%s ORDER BY created_at DESC LIMIT %s""", (session_id, limit))
        rows = cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def run_agent(session_id: str, user_text: str, tools_impl):
    messages = [{"role":"system","content":SYSTEM_PROMPT}] + _history(session_id, 8)
    messages.append({"role":"user","content":user_text})

    resp = _openai_chat(messages, tools=TOOLS)
    msg = resp["choices"][0]["message"]

    while True:
        if "tool_calls" not in msg:
            final = msg.get("content", "")
            _save_message(session_id, "user", user_text)
            _save_message(session_id, "assistant", final)
            return final

        tool_msgs = []
        for call in msg["tool_calls"]:
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"] or "{}")

            if name == "rag_search":
                out = tools_impl.rag_search(args["query"])
            elif name == "list_documents":
                out = tools_impl.tool_list_documents()
            elif name == "get_file_contents":
                out = tools_impl.tool_get_file_contents(args["file_id"])
            elif name == "query_document_rows":
                out = tools_impl.tool_query_document_rows(args["sql_query"])
            else:
                out = {"error": f"unknown tool {name}"}

            tool_msgs.append({
                "role":"tool",
                "tool_call_id": call["id"],
                "name": name,
                "content": json.dumps(out, ensure_ascii=False)[:8000],
            })

        messages.append(msg)
        messages += tool_msgs
        msg = _openai_chat(messages, tools=TOOLS)["choices"][0]["message"]
