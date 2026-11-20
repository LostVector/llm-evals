"""Harbor adapter for the repository's HARD-51 matched-work profile.

Load with the pinned upstream v2/tooling directory on PYTHONPATH.
"""

import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import time

from host_mini_swe import HarborSandboxEnvironment, HostMiniSweAgent
from minisweagent.agents.default import DefaultAgent
from minisweagent.exceptions import LimitsExceeded, TimeExceeded
from minisweagent.models.litellm_model import LitellmModel
import yaml


PROTOCOL = json.loads((Path(__file__).resolve().parents[1] / "protocols/hard51-matched-work.json").read_text())


def stop(reason, exception=LimitsExceeded):
    return exception({"role": "exit", "content": reason,
                      "extra": {"exit_status": reason, "submission": ""}})


class MatchedModel(LitellmModel):
    # A failed request may have consumed unreported work. Leave it as an infrastructure failure.
    abort_exceptions = [Exception, KeyboardInterrupt]

    def __init__(self, deadline, **kwargs):
        super().__init__(**kwargs)
        self.deadline = deadline
        self.requests = []
        self.completion_tokens = 0

    def _query(self, messages, **kwargs):
        remaining = PROTOCOL["max_completion_tokens_per_task"] - self.completion_tokens
        if remaining == 0:
            raise stop("CompletionTokenLimit")
        if len(self.requests) == PROTOCOL["max_model_calls_per_task"]:
            raise stop("ModelCallLimit")
        time_left = self.deadline - time.monotonic()
        if time_left <= 1:
            raise stop("WallGuard", TimeExceeded)
        cap = min(remaining, PROTOCOL["max_completion_tokens_per_call"])
        try:
            response = super()._query(messages, **(kwargs | {
                "max_tokens": cap, "timeout": time_left, "num_retries": 0,
            }))
        except Exception:
            if time.monotonic() >= self.deadline - 1:
                raise stop("WallGuard", TimeExceeded) from None
            raise

        usage = response.usage
        spent = getattr(usage, "completion_tokens", None)
        if type(spent) is not int or not 0 <= spent <= cap:
            raise ValueError("Endpoint completion usage missing or outside the requested budget")
        self.completion_tokens += spent
        details = getattr(usage, "completion_tokens_details", None)
        self.requests.append({
            "requested_completion_tokens": cap,
            "completion_tokens": spent,
            "reasoning_tokens": getattr(details, "reasoning_tokens", None),
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "finish_reason": response.choices[0].finish_reason,
        })
        if time.monotonic() >= self.deadline:
            raise stop("WallGuard", TimeExceeded)
        return response


class GuardedSandbox(HarborSandboxEnvironment):
    def __init__(self, *args, deadline, system, **kwargs):
        super().__init__(*args, **kwargs)
        self.deadline = deadline
        self.system = system

    def get_template_vars(self, **kwargs):
        return super().get_template_vars(**(self.system | kwargs))

    def execute(self, action, cwd="", *, timeout=None):
        remaining = math.floor(self.deadline - time.monotonic())
        if remaining <= 0:
            raise stop("WallGuard", TimeExceeded)
        seconds = min(timeout or self.timeout, remaining)
        command = shlex.quote(action["command"])
        return super().execute({**action, "command": f"timeout -k 3 {seconds} bash -c {command}"},
                               cwd, timeout=seconds + 5)


class Hard51MatchedAgent(HostMiniSweAgent):
    @staticmethod
    def name():
        return "hard51-matched-work"

    async def run(self, instruction, environment, context):
        config = Path(self._config_file).read_bytes()
        if hashlib.sha256(config).hexdigest() != PROTOCOL["agent_config_sha256"]:
            raise ValueError("Upstream agent config differs from the pinned profile")
        profile = yaml.safe_load(config)
        probe = await environment.exec(command=(
            'cd /app 2>/dev/null || cd /testbed 2>/dev/null || exit 1; '
            'printf "HARD51_CWD=%s\\n" "$PWD"; printf "HARD51_UNAME="; uname -srm'
        ))
        if probe.return_code:
            raise RuntimeError("Could not identify the task sandbox and repository")
        facts = dict(line.removeprefix("HARD51_").split("=", 1)
                     for line in probe.stdout.splitlines() if line.startswith("HARD51_"))
        cwd = facts["CWD"]
        os_name, release, machine = facts["UNAME"].split()
        started = time.monotonic()
        deadline = started + PROTOCOL["agent_wall_guard_seconds"]
        sandbox = GuardedSandbox(
            environment, asyncio.get_running_loop(), cwd=cwd,
            env=profile["environment"]["env"], timeout=60, deadline=deadline,
            system={"system": os_name, "release": release, "machine": machine},
        )
        profile["model"].pop("model_class")
        profile["model"].update(cost_tracking="ignore_errors")
        profile["model"]["model_kwargs"].update(
            api_base=os.environ["HARD51_BASE_URL"],
            allowed_openai_params=["reasoning_effort"],
            reasoning_effort=PROTOCOL["reasoning_effort"],
        )
        model = MatchedModel(deadline, model_name=self.model_name, **profile["model"])
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        agent = DefaultAgent(model, sandbox, output_path=self.logs_dir / "mini-swe-agent.trajectory.json",
                             **(profile["agent"] | {"step_limit": 0, "cost_limit": 0}))
        outcome = "InfrastructureError"
        try:
            result = await asyncio.to_thread(agent.run, instruction)
            outcome = result["exit_status"]
        finally:
            (self.logs_dir / "budget.json").write_text(json.dumps({
                "protocol": PROTOCOL["id"], "exit_status": outcome,
                "agent_wall_seconds": time.monotonic() - started,
                "n_calls": len(model.requests), "completion_tokens": model.completion_tokens,
                "requests": model.requests,
            }, indent=2) + "\n")
        patch = await environment.exec(command=f"git -C {shlex.quote(cwd)} add -A && "
                                       f"git -C {shlex.quote(cwd)} diff --cached --binary", timeout_sec=40)
        if patch.return_code:
            raise RuntimeError("Could not capture the model patch")
        (self.logs_dir / "model.patch").write_text(patch.stdout or "")
