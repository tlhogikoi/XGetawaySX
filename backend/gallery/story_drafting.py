"""Provider-agnostic, fail-closed AI story drafting.

A configured provider may rewrite only the owner's supplied facts. The service
validates the response shape and length; it never approves or publishes stories.
"""
from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.exceptions import APIException, ValidationError


class StoryDraftingUnavailable(APIException):
    status_code = 503
    default_detail = "AI story drafting is not configured. You can still write the summary manually."
    default_code = "story_drafting_unavailable"


def build_source_facts(story):
    """Return only facts explicitly supplied for this story, never inferred data."""
    facts = story.ai_source_facts or []
    if not isinstance(facts, list) or not all(isinstance(item, str) and item.strip() for item in facts):
        raise ValidationError({"ai_source_facts": "Source facts must be a list of non-empty factual statements."})
    if not facts:
        raise ValidationError({"ai_source_facts": "Add owner-supplied facts before requesting AI assistance."})
    return facts


def draft_story_summary(story):
    provider_path = getattr(settings, "GALLERY_STORY_DRAFTER", "")
    if not provider_path:
        raise StoryDraftingUnavailable()
    try:
        provider = import_string(provider_path)
    except (ImportError, AttributeError) as exc:
        raise StoryDraftingUnavailable() from exc

    facts = build_source_facts(story)
    result = provider(source_facts=facts, target_words=(30, 60), instruction=(
        "Write a concise 30–60-word story using only the supplied facts. "
        "Do not add dates, founders, origins, awards, events, cultural claims, "
        "or other details not explicitly stated. If the facts are insufficient, "
        "ask for clarification instead of guessing. Return summary and unsupported_claims."
    ))
    if not isinstance(result, dict):
        raise ValidationError("The configured story drafting provider returned an invalid response.")
    summary = result.get("summary")
    unsupported = result.get("unsupported_claims", [])
    if not isinstance(summary, str) or not 30 <= len(summary.split()) <= 60:
        raise ValidationError({"summary": "The AI draft must contain 30–60 words."})
    if not isinstance(unsupported, list):
        raise ValidationError("The provider's unsupported-claims report is invalid.")
    if unsupported:
        raise ValidationError({
            "unsupported_claims": unsupported,
            "detail": "The draft contains claims requiring owner evidence. No draft was saved.",
        })
    return summary
