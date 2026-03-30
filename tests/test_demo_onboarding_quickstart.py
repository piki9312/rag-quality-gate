from __future__ import annotations

from rqg.demo.onboarding_quickstart import PROFILE_CONFIGS, build_parser


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
