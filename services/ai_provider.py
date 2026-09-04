import json
import streamlit as st


# =========================================================
# CONFIG
# =========================================================

AI_PROVIDER = "openrouter"
# pilihan:
# "gemini"
# "openrouter"
# "claude"


# =========================================================
# MAIN FUNCTION
# =========================================================

def ask_ai(system_prompt, user_message, conversation_history=None):
    # FIX #004: mutable default argument — each call gets its own list
    if conversation_history is None:
        conversation_history = []

    if AI_PROVIDER == "gemini":
        return _ask_gemini(system_prompt, user_message, conversation_history)

    elif AI_PROVIDER == "openrouter":
        return _ask_openrouter(system_prompt, user_message, conversation_history)

    elif AI_PROVIDER == "claude":
        return _ask_claude(system_prompt, user_message, conversation_history)

    else:
        return {
            "answer": "❌ Provider AI tidak dikenali",
            "sql": None,
            "chart_type": "none",
            "chart_config": {},
            "insights": [],
            "followup": [],
        }


# =========================================================
# GEMINI
# =========================================================

def _ask_gemini(system_prompt, user_message, conversation_history):

    import google.generativeai as genai

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

    model = genai.GenerativeModel("gemini-1.5-flash")

    history = ""

    for h in conversation_history[-10:]:
        history += f"{h['role']}: {h['content']}\n"

    prompt = f"""
{system_prompt}

History:
{history}

User:
{user_message}

WAJIB JSON VALID.
"""

    response = model.generate_content(prompt)

    raw = response.text.strip()

    raw = raw.replace("```json", "")
    raw = raw.replace("```", "")

    return json.loads(raw)


# =========================================================
# OPENROUTER
# =========================================================

def _ask_openrouter(system_prompt, user_message, conversation_history):

    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=st.secrets["OPENROUTER_API_KEY"]
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    for h in conversation_history[-10:]:
        messages.append({
            "role": h["role"],
            "content": h["content"]
        })

    messages.append({
        "role": "user",
        "content": user_message
    })

    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=messages,
        temperature=0.2,
        max_tokens=1200,
    )

    raw = completion.choices[0].message.content.strip()

    raw = raw.replace("```json", "")
    raw = raw.replace("```", "")

    return json.loads(raw)


# =========================================================
# CLAUDE
# =========================================================

def _ask_claude(system_prompt, user_message, conversation_history):

    import requests

    messages = []

    for h in conversation_history[-10:]:
        messages.append({
            "role": h["role"],
            "content": h["content"]
        })

    messages.append({
        "role": "user",
        "content": user_message
    })

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": st.secrets["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 1500,
            "system": system_prompt,
            "messages": messages,
        },
        timeout=30,
    )

    data = response.json()

    raw = ""

    for block in data.get("content", []):
        if block.get("type") == "text":
            raw += block["text"]

    raw = raw.replace("```json", "")
    raw = raw.replace("```", "")

    return json.loads(raw)