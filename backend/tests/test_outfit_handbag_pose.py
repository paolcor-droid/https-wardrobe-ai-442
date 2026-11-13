"""Natural handbag placement constraints for optional full-outfit previews."""
from services.outfit_handbag_pose import HANDBAG_POSE_VERSION, handbag_pose_guidance


def test_handbag_stays_worn_or_carried_at_hip_height():
    prompt = handbag_pose_guidance()
    assert "waist or hip" in prompt
    assert "upper" in prompt and "thigh" in prompt
    assert "ABOVE THE KNEE" in prompt
    assert "No handbag on the ground" in prompt
    assert "never hanging" in prompt
    assert "to the soles" in prompt
    assert "space above the head" in prompt
    assert HANDBAG_POSE_VERSION.endswith("v2")


def test_handbag_prompt_constraints_are_bounded_and_without_user_data():
    text = handbag_pose_guidance()
    assert 100 < len(text) < 2500
    assert "customer" not in text.casefold()
    assert "http" not in text
