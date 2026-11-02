"""HTTP API and web page for the cost engine.

GET  /            the web page
GET  /scenarios   scenarios with their parameters, ranges and defaults
POST /solve       {"scenario": "...", "params": {...}} -> heuristic vs optimum
GET  /health      liveness check
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from typing import Annotated, Literal, Union

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .scenarios import PARAM_MODELS, SCENARIOS, describe

SOLVER_TIMEOUT = float(os.environ.get("SOLVER_TIMEOUT_SECONDS", "10"))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT_SOLVES", "4"))
STATIC = Path(__file__).parent / "static"
ROOT = Path(__file__).parent.parent

app = FastAPI(
    title="Cloud Cost Optimization Engine",
    description="Compare the thesis heuristic baselines with the LP optimum.",
    version="1.0",
)
_slots = asyncio.Semaphore(MAX_CONCURRENT)


def _request_model(sid: str) -> type[BaseModel]:
    params_model = PARAM_MODELS[sid]
    return type(
        f"Solve{params_model.__name__}",
        (BaseModel,),
        {
            "__annotations__": {"scenario": Literal[sid], "params": params_model},  # type: ignore[valid-type]
            "params": Field(default_factory=params_model),
            "model_config": ConfigDict(extra="forbid"),
        },
    )


SolveRequest = Annotated[
    Union[tuple(_request_model(sid) for sid in SCENARIOS)],  # type: ignore[misc]
    Field(discriminator="scenario"),
]


def _error(status: int, error: str, message: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": error, "message": message, **extra})


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/scenarios")
def scenarios() -> dict:
    return {
        "solver_timeout_seconds": SOLVER_TIMEOUT,
        "scenarios": [describe(s) for s in SCENARIOS.values()],
    }


async def _run_worker(payload: dict) -> dict:
    """Solve in a child process (own process group) and kill it on timeout."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "app.worker",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, cwd=ROOT, start_new_session=True,
    )
    try:
        out, err = await asyncio.wait_for(
            proc.communicate(json.dumps(payload).encode()), SOLVER_TIMEOUT)
    except asyncio.TimeoutError:
        try:
            os.killpg(proc.pid, signal.SIGKILL)  # the worker and the CBC solver it started
        except ProcessLookupError:
            pass
        await proc.wait()
        raise
    if proc.returncode != 0:
        raise RuntimeError(err.decode(errors="replace")[-500:])
    return json.loads(out)


@app.post("/solve", responses={
    422: {"description": "Invalid parameters, or no allocation meets the constraints (error: infeasible)"},
    503: {"description": "Too many solves running"},
    504: {"description": "Solver timed out"},
})
async def solve(req: SolveRequest):
    if _slots.locked():
        return _error(503, "busy", "Too many solves are running. Try again in a moment.")
    async with _slots:
        try:
            out = await _run_worker({"scenario": req.scenario, "params": req.params.model_dump()})
        except asyncio.TimeoutError:
            return _error(504, "timeout", f"The solver did not finish within {SOLVER_TIMEOUT:g} s.")
        except RuntimeError as e:
            raise HTTPException(500, "Solver failed") from e
    if out["ok"]:
        return out["result"]
    if out["error"] == "infeasible":
        return _error(422, "infeasible",
                      "No allocation meets every constraint with these inputs. "
                      "Loosen a limit, lower the demand or allow more instance types.",
                      solver_status=out.get("solver_status"))
    return _error(422, out["error"], out["message"])
