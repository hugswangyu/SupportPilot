import asyncio
import inspect
import json
import threading
import queue as queue_module
from contextlib import asynccontextmanager
from queue import Queue

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config.settings import settings

agent_instance = None
_agent_lock: asyncio.Lock = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_instance, _agent_lock
    _agent_lock = asyncio.Lock()

    if settings.multi_agent_enabled:
        from app.multi_agent.orchestrator import MultiAgentOrchestrator
        agent_instance = MultiAgentOrchestrator()
    else:
        from app.agent.chat import EcomAgent
        agent_instance = EcomAgent()

    yield

    if agent_instance:
        agent_instance.save()
        agent_instance.close()


app = FastAPI(title="SupportPilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
async def chat_endpoint(body: ChatRequest):
    if not agent_instance:
        raise HTTPException(503, "Agent not initialized")

    q: Queue = Queue()
    loop = asyncio.get_event_loop()
    supports_trace = "trace_callback" in inspect.signature(agent_instance.chat).parameters

    async def generate():
        async with _agent_lock:
            def run():
                def trace_cb(event):
                    q.put(event)

                try:
                    if supports_trace:
                        result = agent_instance.chat(body.message, trace_callback=trace_cb)
                    else:
                        result = agent_instance.chat(body.message)
                    q.put({"type": "done", "data": result.model_dump()})
                except Exception as exc:
                    import traceback
                    traceback.print_exc()
                    q.put({"type": "error", "message": str(exc)})
                finally:
                    q.put(None)

            t = threading.Thread(target=run, daemon=True)
            t.start()

            while True:
                try:
                    event = await loop.run_in_executor(None, lambda: q.get(timeout=120))
                except queue_module.Empty:
                    if not t.is_alive():
                        yield "data: [DONE]\n\n"
                        break
                    continue

                if event is None:
                    yield "data: [DONE]\n\n"
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/reset")
async def reset_session():
    if agent_instance:
        async with _agent_lock:
            agent_instance.reset()
    return {"success": True}


@app.get("/api/session")
async def get_session():
    if not agent_instance:
        return {"history_size": 0, "mode": "unknown", "model": settings.model_name}
    mode = "Multi-Agent" if settings.multi_agent_enabled else "ReAct + MCP + RAG"
    return {
        "history_size": agent_instance.history_size,
        "mode": mode,
        "model": settings.model_name,
    }


@app.get("/api/memory")
async def get_memory():
    if not agent_instance or not hasattr(agent_instance, "memory_manager"):
        return {"enabled": False}
    mm = agent_instance.memory_manager
    if not mm.memory_enabled:
        return {"enabled": False}
    stm = mm.stm
    ltm = mm.ltm
    return {
        "enabled": True,
        "short_term": list(stm.facts) if stm.facts else [],
        "long_term": [
            {"category": f.category, "content": f.content} for f in ltm.facts
        ],
        "summaries": ltm.interaction_summaries[-3:] if ltm.interaction_summaries else [],
    }


@app.get("/api/skills")
async def get_skills():
    if not agent_instance or not hasattr(agent_instance, "skill_manager"):
        return {"enabled": False, "skills": []}
    sm = agent_instance.skill_manager
    if not sm.enabled:
        return {"enabled": False, "skills": []}
    return {"enabled": True, "skills": sm.get_catalog()}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
