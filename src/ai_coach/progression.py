"""Translate feedback evidence into a bounded HQ proposal."""

from .workout_library import step_template

ACTION_VERSION = "1.0"


def adaptation_proposal(feedback, current_template_id):
    state = feedback["state"] if feedback else "INSUFFICIENT_EVIDENCE"
    if state == "PROGRESS":
        candidate = step_template(current_template_id, "UP")
        action = "PROGRESS_ONE_STEP" if candidate != current_template_id else "KEEP_AT_FAMILY_CEILING"
    elif state == "REDUCE":
        candidate = step_template(current_template_id, "DOWN")
        action = "REDUCE_ONE_STEP"
    elif state in ("MOVE", "AVOID_COMBINATION"):
        candidate = current_template_id
        action = "REVIEW_SPACING"
    elif state == "CONSOLIDATE":
        candidate = current_template_id
        action = "CONSOLIDATE"
    elif state == "KEEP":
        candidate = current_template_id
        action = "KEEP"
    else:
        candidate = current_template_id
        action = "COLLECT_MORE_EVIDENCE"

    return {
        "authority": "ADVISORY_ONLY",
        "requires_hq_approval": True,
        "action": action,
        "current_template_id": current_template_id,
        "candidate_template_id": candidate,
        "feedback_state": state,
        "constraints": ["HQ_MUST_APPROVE", "ONE_DOSE_CHANGE_AT_A_TIME", "RECHECK_RECENT_TOLERANCE"],
    }
