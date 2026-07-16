"""Tracer: JSON local grava jsonl; build_tracer cai p/ JSON sem keys Langfuse."""

import json
from types import SimpleNamespace

from rag_assistant.observability.tracer import JsonTracer, NullTracer, build_tracer


def test_json_tracer_appends_lines(tmp_path):
    tr = JsonTracer(tmp_path / "traces")
    tr.trace({"query": "q1", "answer": "a1"})
    tr.trace({"query": "q2", "answer": "a2"})
    lines = tr.path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["query"] == "q1"


def test_null_tracer_is_noop():
    assert NullTracer().trace({"x": 1}) is None


def test_build_tracer_defaults_to_json_without_keys(tmp_path):
    settings = SimpleNamespace(
        langfuse_public_key=None,
        langfuse_secret_key=None,
        traces_path=str(tmp_path / "t"),
    )
    tr = build_tracer(settings)
    assert isinstance(tr, JsonTracer)
