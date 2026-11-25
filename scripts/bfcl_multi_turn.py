"""Run or independently audit the pinned BFCL Multi-Turn Base cohort."""

import argparse
import ast
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from importlib.metadata import version
import hashlib
import inspect
import json
from pathlib import Path
import time
import urllib.request
from urllib.parse import urlsplit

import httpx
from scripts.audit_local import binary_summary
from scripts.gpqa_diamond import private_path, save
from bfcl_eval.eval_checker import eval_runner
from bfcl_eval.eval_checker.multi_turn_eval import multi_turn_utils
from bfcl_eval.model_handler.api_inference.openai_completion import OpenAICompletionsHandler
from bfcl_eval.utils import load_dataset_entry, load_ground_truth_entry

CATEGORY = "multi_turn_base"
BACKENDS = set(multi_turn_utils.CLASS_FILE_PATH_MAPPING.values())


def execute_backend_call(expression):
    # The upstream evaluator resolves calls against its simulated backend
    # instances. Invoke only their public methods with literal arguments.
    call = ast.parse(expression, mode="eval").body
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
        raise ValueError("Expected a simulated backend call")
    method = call.func
    if not isinstance(method.value, ast.Name) or method.attr.startswith("_"):
        raise ValueError("Expected a public simulated backend method")
    backend = vars(multi_turn_utils).get(method.value.id)
    if type(backend).__module__ not in BACKENDS:
        raise ValueError("Unknown simulated backend")
    function = getattr(backend, method.attr, None)
    if not inspect.ismethod(function) or function.__self__ is not backend:
        raise ValueError("Unknown simulated tool")
    args = [ast.literal_eval(arg) for arg in call.args]
    kwargs = {arg.arg: ast.literal_eval(arg.value) for arg in call.keywords}
    if None in kwargs or len(kwargs) != len(call.keywords):
        raise ValueError("Invalid tool arguments")
    return function(*args, **kwargs)


multi_turn_utils.eval = execute_backend_call


class LocalHandler(OpenAICompletionsHandler):
    def __init__(self, *args, endpoint, budget, **kwargs):
        self.endpoint = endpoint
        self.budget = budget
        super().__init__(*args, **kwargs)

    def _build_client_kwargs(self):
        return dict(base_url=self.endpoint, api_key="local-benchmark",
                    http_client=httpx.Client(trust_env=False, timeout=1500), max_retries=2)

    def generate_with_backoff(self, **kwargs):
        kwargs.pop("store", None)
        extra = {"reasoning_budget_tokens": self.budget} if self.budget is not None else {}
        start = time.monotonic()
        response = self.client.chat.completions.create(
            **kwargs, max_tokens=8192, reasoning_effort="medium", extra_body=extra
        )
        return response, time.monotonic() - start


PROFILE = {
    "harness": "2026.3.23", "category": CATEGORY, "temperature": 0.001,
    "max_tokens": 8192, "reasoning_effort": "medium", "tool_mode": "native FC",
    "step_limit": 20,
}
ENGINES = ("gufo", "llama.cpp", "halogen")
EXPECTED_CASES = 200
DATASET_SHA256 = "c79d26cb042a2a0d319b2927df5b757a4d0ee12f6e629c92940e40494ffa2288"
REFERENCE_SHA256 = "7cfd433df6b3e7bbeed6f915290c4c05b351ec6258f06d0b7ed198ffa2ebbccf"


def reasoning_budget(engine):
    return None if engine == "halogen" else 6963


def stable_digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def load_cases():
    if version("bfcl-eval") != PROFILE["harness"]:
        raise ValueError(f"Install bfcl-eval=={PROFILE['harness']}")
    entries = {row["id"]: row for row in load_dataset_entry(CATEGORY)}
    truth = {row["id"]: row["ground_truth"] for row in load_ground_truth_entry(CATEGORY)}
    if len(entries) != EXPECTED_CASES or set(entries) != set(truth):
        raise ValueError("Unexpected Multi-Turn Base dataset size or IDs")
    if stable_digest(entries) != DATASET_SHA256 or stable_digest(truth) != REFERENCE_SHA256:
        raise ValueError("BFCL question or reference data differs from the pinned cohort")
    return entries, truth


def audit(directory):
    config = read(directory / "manifest.json")
    expected = PROFILE
    if any(config.get(k) != v for k, v in expected.items()):
        raise ValueError("Stored BFCL profile differs from the run protocol")
    engine = config["engine"]
    if engine not in ENGINES:
        raise ValueError("Unexpected engine")
    if config.get("reasoning_budget_tokens") != reasoning_budget(engine):
        raise ValueError("Reasoning configuration differs")
    entries, truth = load_cases()
    files = {p.stem: p for p in directory.glob("multi_turn_base_*.json")}
    if set(files) != set(entries):
        raise ValueError("This audit requires exactly the pinned 200 cases")
    # Scoring only needs decode_execute and does not call a provider.
    handler = object.__new__(OpenAICompletionsHandler)
    handler.is_fc_model = True
    successes = []
    fingerprints = {}
    for name, entry in entries.items():
        path = files[name]
        recorded = read(path)
        if name != recorded["id"] or type(recorded["valid"]) is not bool:
            raise ValueError(f"Invalid checkpoint {name}")
        replay = eval_runner._evaluate_single_multi_turn_entry(
            handler, name, recorded["calls"], truth[name], copy.deepcopy(entry),
            "offline_replay", CATEGORY
        )
        if recorded["valid"] != replay["valid"]:
            raise ValueError(f"Replay disagrees for {name}")
        successes.append(int(replay["valid"]))
        fingerprints[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        **binary_summary(successes, EXPECTED_CASES),
        "profile": {**expected, "artifact": config["artifact"], "engine": engine,
                    "reasoning_budget_tokens": config["reasoning_budget_tokens"]},
        "dataset_sha256": DATASET_SHA256,
        "reference_sha256": REFERENCE_SHA256,
        "checkpoint_inventory_sha256": stable_digest(fingerprints),
    }


def deployment(args):
    endpoint = args.endpoint.rstrip("/")
    url = urlsplit(endpoint)
    if (url.scheme not in ("https", "http") or not url.hostname or url.username
            or url.path != "/v1" or url.query or url.fragment):
        raise ValueError("Expected an OpenAI-compatible /v1 endpoint")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(endpoint.removesuffix("/v1") + "/props", timeout=10) as response:
        props = json.load(response)
    if (
        props.get("model_alias") != args.model
        or props.get("build_info") != args.build
        or Path(props.get("model_path") or "").name != args.artifact
        or props.get("total_slots") != args.slots
        or props.get("default_generation_settings", {}).get("n_ctx") != args.context
    ):
        raise ValueError("Endpoint model, build, checkpoint, context, or slots differ")
    return {
        **PROFILE, "engine": args.engine, "model": args.model, "endpoint": endpoint,
        "artifact": args.artifact, "backend_revision": args.build, "slots": args.slots,
        "context_per_slot": args.context, "workers": args.workers, "limit": args.limit,
        "reasoning_budget_tokens": reasoning_budget(args.engine),
    }


def run(args):
    entries, truth = load_cases()
    manifest = deployment(args)
    path = args.output / "manifest.json"
    if path.exists() and read(path) != manifest:
        raise ValueError("Existing run profile differs")
    save(path, manifest)

    def evaluate(name):
        target = args.output / (name + ".json")
        if target.exists():
            stored = read(target)
            if stored["id"] != name or type(stored["valid"]) is not bool:
                raise ValueError("Existing BFCL score has the wrong identity or verdict")
            return stored["valid"]
        entry = entries[name]
        handler = LocalHandler(args.model, PROFILE["temperature"], "local-fc", True,
                               endpoint=manifest["endpoint"], budget=manifest["reasoning_budget_tokens"])
        try:
            handler.model_name_underline_replaced = "local_fc"
            calls, metrics = handler.inference_multi_turn_FC(copy.deepcopy(entry), False, True)
            verdict = eval_runner._evaluate_single_multi_turn_entry(
                handler, name, calls, truth[name], copy.deepcopy(entry), "local_fc", CATEGORY
            )
        finally:
            handler.client.close()
        payload = dict(id=name, valid=verdict["valid"], calls=calls, metrics=metrics,
                       verdict=verdict, endpoint_role="primary")
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, default=str) + "\n")
        temporary.replace(target)
        return payload["valid"]

    passed = failed = errors = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(evaluate, name): name for name in list(entries)[:args.limit]}
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                errors += 1
                print(name, "infrastructure_error", type(exc).__name__,
                      getattr(exc, "status_code", ""), flush=True)
                continue
            passed += result
            failed += not result
            print(name, "pass" if result else "fail", flush=True)
    print(json.dumps(dict(passed=passed, failed=failed, infrastructure_errors=errors)), flush=True)
    if errors:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    replay = commands.add_parser("audit")
    replay.add_argument("output", type=private_path)
    predict = commands.add_parser("run")
    predict.add_argument("output", type=private_path)
    predict.add_argument("--endpoint", required=True)
    predict.add_argument("--model", required=True)
    predict.add_argument("--artifact", required=True)
    predict.add_argument("--engine", choices=ENGINES, required=True)
    predict.add_argument("--build", required=True)
    predict.add_argument("--slots", type=int, default=4)
    predict.add_argument("--context", type=int, default=262144)
    predict.add_argument("--workers", type=int, default=3)
    predict.add_argument("--limit", type=int, default=EXPECTED_CASES)
    args = parser.parse_args()
    if args.command == "audit":
        print(json.dumps(audit(args.output), indent=2))
        return
    if not 1 <= args.workers <= min(args.slots, 3) or not 1 <= args.limit <= EXPECTED_CASES:
        parser.error("Use up to three workers and at most 200 tasks")
    run(args)


if __name__ == "__main__":
    main()
