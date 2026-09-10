from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActorProfile:
    allowed_actions: frozenset[tuple[str, str]]
    allowed_environments: frozenset[str]


@dataclass(frozen=True)
class ActorAuthorization:
    authorized: bool
    reason_codes: tuple[str, ...]


ACTOR_PROFILES: dict[str, ActorProfile] = {
    "support-agent-7": ActorProfile(
        allowed_actions=frozenset(
            {
                ("ticket_triage", "route_ticket"),
                ("ticket_triage", "close_ticket"),
            }
        ),
        allowed_environments=frozenset({"production", "staging"}),
    ),
    "finance-agent-2": ActorProfile(
        allowed_actions=frozenset({("refund_approval", "refund")}),
        allowed_environments=frozenset({"production", "staging"}),
    ),
    "release-agent-1": ActorProfile(
        allowed_actions=frozenset({("code_deploy", "deploy")}),
        allowed_environments=frozenset({"production", "staging"}),
    ),
}


def authorize_actor(actor: str, domain: str, action_type: str, environment: str) -> ActorAuthorization:
    profile = ACTOR_PROFILES.get(actor)
    if profile is None:
        return ActorAuthorization(False, ("UNKNOWN_ACTOR",))

    reasons: list[str] = []
    if (domain, action_type) not in profile.allowed_actions:
        reasons.append("ACTOR_NOT_AUTHORIZED_FOR_ACTION")
    if environment.strip().lower() not in profile.allowed_environments:
        reasons.append("ACTOR_NOT_AUTHORIZED_FOR_ENVIRONMENT")

    return ActorAuthorization(not reasons, tuple(reasons))
