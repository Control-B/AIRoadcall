from app.api.routes.shop_ai import _emergency_flags, _split_key_points, _symptom_category


def test_symptom_category_detects_common_breakdowns() -> None:
    assert _symptom_category("Truck has DPF derate and DEF warning") == "dpf_derate"
    assert _symptom_category("Air leak, cannot build PSI") == "brakes_air"
    assert _symptom_category("Steer tire blowout on the shoulder") == "tire"


def test_emergency_flags_detects_handoff_risk() -> None:
    assert _emergency_flags("Stop engine light and unsafe shoulder") == [
        "stop_engine_light",
        "unsafe_location",
        "roadside_exposure",
    ]


def test_split_key_points_limits_to_four_sentences() -> None:
    assert _split_key_points("One. Two. Three. Four. Five.") == ["One", "Two", "Three", "Four"]
