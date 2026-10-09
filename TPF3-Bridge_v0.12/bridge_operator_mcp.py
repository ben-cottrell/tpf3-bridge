"""Local stdio MCP boundary; no HTTP listener or additional model calls."""
import asyncio
import json
from pathlib import Path
from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from bridge_operator import Operator

op=Operator()
server=MCPServer('tpf3-operator',instructions=(
    'Keep a spatial design plan before construction. plan_layout records data; build_layout '
    'executes it sequentially without redesigning. Inspect needs_attention; never blindly '
    'replay a mutation. Use compact outcomes and open full local evidence only when needed. '
    'Native paths, actual trains and visual design acceptance are separate conclusions.'),log_level='WARNING')
read=ToolAnnotations(readOnlyHint=True)
write=ToolAnnotations(readOnlyHint=False,destructiveHint=True,idempotentHint=False)
gate=asyncio.Lock()

async def invoke(fn,*args,**kwargs):
    # One operation owns the adapter at a time, including complete multi-step builds.
    async with gate:
        try:
            return await asyncio.to_thread(fn,*args,**kwargs)
        except Exception as exc:
            return {'status':'error','error_type':type(exc).__name__,'error':str(exc)[:500]}

@server.tool(annotations=read)
async def session_status() -> dict:
    """Read adapter responsiveness and current view; no game mutation."""
    return await invoke(op.status)

@server.tool(annotations=read)
async def survey_site(region: dict, terrain_points: list[list[float]] | None = None) -> dict:
    """Read a bounded site and optional terrain samples; return compact evidence."""
    return await invoke(op.survey,region,terrain_points)

@server.tool(annotations=ToolAnnotations(readOnlyHint=False,destructiveHint=False))
async def plan_layout(plan: dict) -> dict:
    """Record a version1 named construction plan and draw its geometry; no game writes."""
    return await invoke(op.plan,plan)

@server.tool(annotations=write)
async def build_layout(run: str) -> dict:
    """Execute an unattempted plan, retaining native receipts; stop on a concrete failure."""
    return await invoke(op.execute,run)

@server.tool(annotations=read)
async def run_status(run: str) -> dict:
    """Read compact progress from a local run; no native queries."""
    return await invoke(op.summary,run)

@server.tool(annotations=read)
async def review_layout(run: str) -> dict:
    """Check planned directed routes and draw current geometry against its original plan."""
    return await invoke(op.review,run)

@server.tool(annotations=write)
async def frame_view(center: list[float], distance: float) -> dict:
    """Point native camera at a world position; changes view, not railway geometry."""
    return await invoke(op.gui,'camera',center=center,distance=distance)

@server.tool(annotations=ToolAnnotations(readOnlyHint=False,destructiveHint=False))
async def capture_view() -> dict:
    """Request a native screenshot in the game userdata screenshots folder."""
    return await invoke(op.gui,'capture')

@server.tool(annotations=write)
async def save_checkpoint(name: str) -> dict:
    """Save the running map under the supplied name; waits for native completion callback."""
    return await invoke(op.gui,'save',name=name)

if __name__=='__main__':server.run()
