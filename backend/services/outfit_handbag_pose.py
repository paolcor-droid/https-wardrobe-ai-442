"""Placement guidance for the selected handbag in a full-body fashion preview.

Used as part of the image-generation prompt; this is not a guarantee that
an image model will obey every visual constraint.
"""

HANDBAG_POSE_VERSION = "handbag-natural-carry-v2"


def handbag_pose_guidance() -> str:
    return (
        " COMPOSITION AND PHYSICAL PLACEMENT ARE CRITICAL. "
        "Show the complete adult model from the top of the head and hair to the soles "
        "of both shoes, with comfortable space above the head and below both feet. "
        "Keep the person and handbag completely inside the vertical studio frame. "
        "The model must carry the handbag NATURALLY, not display it near the floor: "
        "bend one arm comfortably and hold the handbag's short top handle near the "
        "side of the waist or hip, with the handbag body resting beside the upper "
        "thigh and its bottom clearly ABOVE THE KNEE. "
        "If the photographed handbag is a clutch, hold it tucked gently against "
        "the hip or in the hand at waist/upper-thigh height. "
        "If a long detachable shoulder strap or chain exists, keep it neatly "
        "coiled, looped or draped along the handbag at hip height, never hanging "
        "down toward the knees, ankles or floor. "
        "Do not lengthen the handles or straps. Do not suspend the bag from "
        "the fingertips of a straight arm at knee level. "
        "No handbag on the ground, touching the floor, or floating. "
        "Realistic anatomical arm and hand proportions, bag scaled to the "
        "verified catalogue dimensions relative to the person's body. "
        "The hand grasps a real handle or strap securely, no missing hands or "
        "detached straps. Keep the full look balanced, easy to inspect, and "
        "photographed straight-on at a natural standing distance."
    )
