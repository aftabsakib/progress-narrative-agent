import asyncio
import contextvars
from contextlib import asynccontextmanager
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn

current_user: contextvars.ContextVar[str] = contextvars.ContextVar("current_user", default="unknown")

from app.tools.log_activity import log_activity
from app.tools.get_daily_brief import get_daily_brief_tool
from app.tools.get_velocity_report import get_velocity_report
from app.tools.get_pipeline_snapshot import get_pipeline_snapshot
from app.tools.check_commitments import check_commitments
from app.tools.score_activity import score_activity
from app.tools.add_commitment import add_commitment
from app.tools.correct_entry import correct_entry
from app.tools.get_alerts import get_alerts
from app.tools.get_artifact_status import get_artifact_status
from app.tools.get_recent_activity import get_recent_activity
from app.tools.send_brief_now import send_brief_now
from app.models.schemas import (
    LogActivityInput, AddCommitmentInput, CorrectEntryInput
)

server = Server("progress-narrative-agent")
scheduler = AsyncIOScheduler(job_defaults={"misfire_grace_time": 600})


@scheduler.scheduled_job("cron", hour=4, minute=0)
async def send_daily_brief():
    from app.services.narrator import generate_daily_brief
    from app.services.emailer import send_daily_brief_email
    from app.tools.get_recent_activity import get_recent_activity
    brief = generate_daily_brief()
    activity_log = get_recent_activity(hours=24)
    full_email = f"{brief}\n\n---\n\nACTIVITY LOG (LAST 24H)\n\n{activity_log}"
    send_daily_brief_email(full_email)


@scheduler.scheduled_job("cron", hour=10, minute=0)
async def send_afternoon_brief():
    from app.services.narrator import generate_acceleration_brief
    from app.services.emailer import send_acceleration_email
    brief = generate_acceleration_brief()
    send_acceleration_email(brief)


@scheduler.scheduled_job("cron", hour="*/2")
async def check_and_send_alerts():
    from app.services.alerts import run_all_alert_checks
    from app.database import db
    run_all_alert_checks()
    # Alert emails disabled — alerts surface in session and morning brief only


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="log_activity",
            description="Paste any text — transcript, summary, update. Extracts activities, commitments, and contacts automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "created_by": {"type": "string", "enum": ["faisal", "aftab"]},
                    "source": {"type": "string", "default": "manual"}
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="get_daily_brief",
            description="Generate today's narrative: velocity check, what moved, what is at risk, today's priority.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_velocity_report",
            description="Speed program report: outreach rate vs target, Tier 1 stalls, InMail utilization, AAEP countdown.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_pipeline_snapshot",
            description="Where each principal sits in the 6-stage role journey. Stalls flagged.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="check_commitments",
            description="All open commitments by person and deadline. Overdue flagged.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="score_activity",
            description="Score any activity against Tangier's three strategic tests.",
            inputSchema={
                "type": "object",
                "properties": {"description": {"type": "string"}},
                "required": ["description"]
            }
        ),
        Tool(
            name="add_commitment",
            description="Log a commitment manually without pasting a full transcript.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "due_date": {"type": "string"},
                    "promised_by": {"type": "string"},
                    "contact_name": {"type": "string"}
                },
                "required": ["description", "promised_by"]
            }
        ),
        Tool(
            name="correct_entry",
            description="Fix a misclassified activity, wrong commitment, or incorrect contact stage.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_type": {"type": "string"},
                    "entry_id": {"type": "string"},
                    "field": {"type": "string"},
                    "new_value": {"type": "string"}
                },
                "required": ["entry_type", "entry_id", "field", "new_value"]
            }
        ),
        Tool(
            name="get_alerts",
            description="Pull all pending alerts. Runs automatically at session start.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_artifact_status",
            description="Status of all produced artifacts — sent, responded, conversion rate.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_recent_activity",
            description="Show all activities logged in the last N hours. Default 24 hours. Use this to see what Faisal or Aftab logged recently.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {"type": "integer", "default": 24},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ),
        Tool(
            name="send_brief_now",
            description="Manually trigger an email brief right now. brief_type: 'morning' (default) sends the narrative brief + activity log. 'afternoon' sends the acceleration brief.",
            inputSchema={
                "type": "object",
                "properties": {
                    "brief_type": {"type": "string", "enum": ["morning", "afternoon"]}
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    result = ""
    if name == "log_activity":
        if "created_by" not in arguments:
            arguments["created_by"] = current_user.get()
        result = await log_activity(LogActivityInput(**arguments))
    elif name == "get_daily_brief":
        result = get_daily_brief_tool()
    elif name == "get_velocity_report":
        result = get_velocity_report()
    elif name == "get_pipeline_snapshot":
        result = get_pipeline_snapshot()
    elif name == "check_commitments":
        result = check_commitments()
    elif name == "score_activity":
        result = score_activity(arguments["description"])
    elif name == "add_commitment":
        result = add_commitment(AddCommitmentInput(**arguments))
    elif name == "correct_entry":
        result = correct_entry(CorrectEntryInput(**arguments))
    elif name == "get_alerts":
        result = get_alerts()
    elif name == "get_artifact_status":
        result = get_artifact_status()
    elif name == "get_recent_activity":
        result = get_recent_activity(
            hours=arguments.get("hours", 24),
            limit=arguments.get("limit", 20)
        )
    elif name == "send_brief_now":
        result = send_brief_now(arguments.get("brief_type", "morning"))
    else:
        result = f"Unknown tool: {name}"
    return [TextContent(type="text", text=result)]


sse = SseServerTransport("/messages")


async def handle_sse(request: Request):
    user = request.query_params.get("user", "unknown")
    current_user.set(user)
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


async def health(request: Request):
    return JSONResponse({"status": "ok"})


@asynccontextmanager
async def lifespan(_app):
    scheduler.start()
    yield
    scheduler.shutdown()


_starlette = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/health", endpoint=health),
    ]
)


async def app(scope, receive, send):
    if scope["type"] == "http" and scope.get("path", "").startswith("/messages"):
        await sse.handle_post_message(scope, receive, send)
    else:
        await _starlette(scope, receive, send)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
