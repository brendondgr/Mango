# Project Plan: Local-First Autonomous Agent System

## 1. Project Overview
A modular, multi-agent system orchestrated by a central Controller. The system runs on a Django backend, utilizing a local GPT-OSS 20B model for inference, LangGraph for state management, and Celery for asynchronous task execution.

## 2. Technology Stack

### Backend & Infrastructure
* **Web Framework:** Django 5.x (Python)
* **Asynchronous Tasks:** Celery + Redis (Message Broker)
* **Database:** PostgreSQL (User data + Persistent Agent State)

### Artificial Intelligence
* **Inference Engine:** Llama-CPP Server (Hosting GPT-OSS 20B GGUF)
* **Orchestration:** LangGraph (State machines and cyclic graphs)
* **LLM Integration:** Custom Python Library (connecting to Llama-CPP)

### Agent Capabilities (Tools)
* **Email Agent:** Gmail API + Microsoft Graph API (Outlook)
* **Research Agent:** Tavily API or DuckDuckGo Search (via LangChain Community)
* **Controller:** Logic-only (Routing & Decision Making)

---

## 3. High-Level Architecture

**The Hub-and-Spoke Model:**
1.  **Input:** User interacts via Django Web Interface.
2.  **Queue:** Request is offloaded to Celery (preventing timeout).
3.  **Controller:** The "Brain" analyzes the request.
    * *Route A:* Triggers Research Sub-Graph.
    * *Route B:* Triggers Email Sub-Graph.
    * *Route C:* Handles general chat directly.
4.  **Action:** Sub-agents execute tools (Search/API calls).
5.  **Output:** Final response is saved to Postgres and pushed to the UI.

---

## 4. Project File Structure

```text
project_root/
├── manage.py                   # Django CLI entry point
├── requirements.txt            # Python dependencies
├── .env                        # Secrets (API Keys, DB Creds, Model Config)
├── README.md                   # Setup documentation
│
├── config/                     # Core Django Configuration
│   ├── __init__.py
│   ├── settings.py             # Global settings (Installs Apps, Celery Config)
│   ├── urls.py                 # Main URL routing
│   ├── asgi.py                 # Async server config (optional)
│   ├── wsgi.py                 # WSGI server config
│   └── celery.py               # Celery app initialization
│
├── web/                        # Frontend Assets (Templates & Static)
│   ├── templates/              # HTML files (Django Templates)
│   │   ├── body.html           # Main UI Wrapper
│   │   └── parts/              # Reusable components (Header, Dropdown)
│   └── static/                 # CSS, JS, Images
│       ├── css/
│       └── js/
│
├── apps/                       # Application Logic
│   ├── core/                   # Shared Utilities
│   │   ├── __init__.py
│   │   ├── models.py           # Abstract base models
│   │   └── utils.py            # Generic helpers
│   │
│   ├── web/                    # The Web App View Logic
│   │   ├── __init__.py
│   │   ├── views.py            # HTTP Handlers (Index, API)
│   │   ├── urls.py             # Web-specific routes
│   │   ├── models.py           # Application specific models
│   │   ├── forms.py            # Input validation
│   │
│   └── agents/                 # The Intelligence Layer (LangGraph)
│       ├── __init__.py
│       ├── models.py           # Agent specific DB models
│       ├── tasks.py            # Celery Tasks
│       ├── state.py            # Shared State Schema
│       │
│       ├── services/           # External Service Connectors
│       │   ├── __init__.py
│       │   └── llm_connector.py # Wrapper for Custom LLM Library
│       │
│       ├── tools/              # Actionable Capabilities
│       │   ├── __init__.py
│       │   ├── search_tools.py # Web Search Functions
│       │   └── email_tools.py  # Email API Functions
│       │
│       └── graphs/             # Agent Logic Definitions
│           ├── __init__.py
│           ├── controller.py   # Main Router Graph
│           ├── research.py     # Research Sub-Graph
│           └── email.py        # Email Sub-Graph
```

---

## 5. Implementation Roadmap

### Phase 1: Foundation & Infrastructure
1.  **Environment Setup:** Initialize Python venv, install Django, Celery, Redis.
2.  **Django Init:** Create the project and the three apps (core, web, agents).
4.  **LLM Verification:** Ensure Llama-CPP server is running and llm_connector.py can successfully retrieve a "Hello World" response from GPT-OSS 20B.

### Phase 2: The Agent "Brain" (Backend)
1.  **State Definition:** Define the AgentState dictionary in apps/agents/state.py (e.g., messages, next_step, tool_output).
2.  **Tool Creation:** Build the Python functions in apps/agents/tools/ for Searching and Emailing (mock these initially if API keys aren't ready).
3.  **Graph Logic:**
    * Build research.py: Node A (Search) -> Node B (Summarize).
    * Build controller.py: The routing logic that decides which graph to call.
4.  **Testing:** Write a simple script to invoke the graphs directly from the terminal to ensure logic flows correctly.

### Phase 3: The Integration Layer
1.  **Celery Setup:** Configure config/celery.py and ensure the worker can start.
2.  **Task Creation:** Create run_agent_task inside apps/agents/tasks.py. This task should accept a user string, invoke the Graph, and return the result.
3.  **Database Models:** Create a Message model in apps/web/models.py to store the conversation history.

### Phase 4: The Interface (Frontend)
1.  **Templates:** Create a clean chat interface using HTML/CSS.
2.  **Views:**
    * POST /chat/: Saves user message to DB, triggers Celery task, returns "Processing" status.
    * GET /chat/poll/: Checks DB to see if the Celery task has finished and created a bot response.
3.  **Javascript:** Basic fetch logic to handle the sending and polling.

---

## 6. Key Configuration Notes

* **Prompt Engineering:** Since you are using a local model, your System Prompts in controller.py must be highly structured. Use clear delimiters (like ###) to separate instructions from context.
* **Timeouts:** Local inference varies in speed. Ensure your Celery worker timeout (soft_time_limit) is set high enough (e.g., 300 seconds) to accommodate long generation times.
* **API Security:** Keep your credentials.json (Gmail) and Client Secrets (Outlook) strictly in .env and never commit them to version control.