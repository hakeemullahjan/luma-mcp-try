# 🗼 Paris Events Agent with Luma.com MCP & Google Gemini

An educational AI engineering project demonstrating how to connect an AI Agent powered by **Google Gemini** to **Luma.com (lu.ma)** using the **Model Context Protocol (MCP)**.

---

## 🎯 What You Will Learn
1. **Model Context Protocol (MCP)**: How an LLM client dynamically discovers tools exposed by an MCP server over standard I/O (`stdio`).
2. **Decoupled Architecture**: The MCP server (`luma_mcp_server.py`) handles all API interactions with Lu.ma, while the Agent (`agent.py`) communicates with Gemini and orchestrates tool calling.
3. **Autonomous Agent Loop**: How Gemini decides when to call Luma tools, inspects arguments, receives results from MCP, and synthesizes answers for the user.

---

## 🏗️ Architecture

```
User Query ("What AI events are happening in Paris?")
       │
       ▼
┌──────────────┐      stdio (MCP)      ┌─────────────────────────┐
│   agent.py   │ ◄───────────────────► │   luma_mcp_server.py    │
│  (Gemini +   │                       │      (MCP Server)       │
│  MCP Client) │                       └────────────┬────────────┘
└──────┬───────┘                                    │ REST API
       │ Function Call / Response                   ▼
       ▼                                     ┌─────────────┐
┌──────────────┐                             │  luma.com   │
│Google Gemini │                             │  (Lu.ma)    │
│(flash-lite)  │                             └─────────────┘
└──────────────┘
```

---

## 🛠️ MCP Tools Provided by the Server

| Tool Name | Description | Arguments |
|-----------|-------------|-----------|
| `get_paris_events` | Retrieves upcoming events in Paris with optional category filtering (`ai`, `tech`, `crypto`, etc.) | `category` (string, optional), `limit` (int) |
| `search_paris_events` | Keyword search across upcoming Paris events (titles, hosts, calendars) | `keyword` (string), `limit` (int) |
| `get_event_details` | Fetches full event descriptions, location, and ticket options | `event_api_id` (string) |

---

## 🚀 Quickstart

### 1. Setup Environment

The Python virtual environment is already prepared in `.venv`. If you ever need to recreate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Your Gemini Key

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Open `.env` and set your key from [Google AI Studio](https://aistudio.google.com/):

```env
GEMINI_API_KEY=AIzaSy...your_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Run the Agent

#### Interactive Chat Mode:
```bash
.venv/bin/python3 agent.py
```

#### Single Query Mode:
```bash
.venv/bin/python3 agent.py "What AI and tech events are happening in Paris this week?"
```

---

## 💬 Example Queries to Try

- *"What AI events are happening in Paris?"*
- *"Are there any hackathons or co-working sessions in Paris right now?"*
- *"Find me free networking events in Paris."*
- *"Tell me more details about event evt-..."*
- *"Quels sont les événements tech à Paris cette semaine ?"* (The agent also supports French!)
