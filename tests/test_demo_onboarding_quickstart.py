from __future__ import annotations

import shutil

from rqg.demo.onboarding_quickstart import PROFILE_CONFIGS, build_parser, run_demo


def test_onboarding_quickstart_parser_defaults_to_demo_cycle():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.profile == "demo_cycle"


def test_onboarding_quickstart_parser_accepts_wiki_profile():
    parser = build_parser()
    args = parser.parse_args(["--profile", "wiki"])
    assert args.profile == "wiki"


def test_onboarding_quickstart_profile_templates_exist():
    assert "demo_cycle" in PROFILE_CONFIGS
    assert "hr" in PROFILE_CONFIGS
    assert "wiki" in PROFILE_CONFIGS

    for config in PROFILE_CONFIGS.values():
        assert config.template_pack_dir.exists()


def test_onboarding_quickstart_demo_cycle_passes_with_fallback_embeddings(monkeypatch):
    class BrokenSentenceTransformer:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("offline")

    monkeypatch.setattr("rqg.serving.rag.SentenceTransformer", BrokenSentenceTransformer)

    summary_path = None
    try:
        summary, summary_path = run_demo(profile="demo_cycle")
        assert summary.gate_status == "pass"
        assert summary.changed_evidence_count >= 1
        assert summary.impacted_case_count >= 1
    finally:
        if summary_path is not None:
            shutil.rmtree(summary_path.parent, ignore_errors=True)
