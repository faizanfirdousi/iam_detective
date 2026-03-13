from __future__ import annotations

from app.models import ChatRequest, ChatResponse
from app.services.do_agent import DOAgentClient


# Persona system prompts — override the agent's base instructions for non-default roles.
# Co-detective uses the DO console instructions as-is (no override needed).
_PERSONA_PROMPTS: dict[str, str] = {
    "witness": (
        "ROLE OVERRIDE: You are now speaking as a witness in this case. "
        "Answer ONLY from what this witness personally observed or stated on record. "
        "Do not speculate, theorise, or share information you could not have witnessed directly. "
        "If asked about something you did not see, say 'I don't know' or 'I wasn't there.'"
    ),
    "suspect": (
        "ROLE OVERRIDE: You are now speaking as a suspect in this case. "
        "Answer defensively and in character. Admit only what the knowledge base confirms was publicly stated. "
        "Do not confess to anything unless it is a matter of public record. "
        "You may deflect, express frustration, or deny accusations — stay in character."
    ),
}


async def gradient_chat(case_id: str, req: ChatRequest) -> ChatResponse:
    client = DOAgentClient(case_id=case_id)

    base_system = (
        "You are a detective-case assistant. Ground your answers strictly in the attached knowledge base. "
        "If information is missing or uncertain, say so clearly. Keep replies concise and investigative. "
        f"The active case is: {case_id}. Only use facts that belong to this case."
    )

    # Build persona override (empty string = co_detective, uses DO console instructions)
    persona_override = ""
    if req.role in _PERSONA_PROMPTS:
        persona_override = _PERSONA_PROMPTS[req.role]
    if req.persona_id:
        persona_override += f"\nYou are specifically: {req.persona_id}."

    system_content = base_system
    if persona_override:
        system_content += "\n\n" + persona_override

    resp = await client.chat_completions(
        messages=[
            {"role": "system", "content": system_content},
            {
                "role": "user",
                "content": (
                    f"case_id={case_id}\n"
                    f"stage={req.stage}\n\n"
                    f"User message:\n{req.message}"
                ),
            },
        ],
        include_retrieval_info=True,
        include_guardrails_info=True,
    )

    content = client.extract_content(resp).strip()

    # Check if the agent suggests advancing the investigation stage
    stage_suggestion: int | None = None
    if "stage_suggestion:" in content.lower():
        for line in content.splitlines():
            if line.lower().startswith("stage_suggestion:"):
                try:
                    stage_suggestion = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass

    return ChatResponse(role=req.role, reply=content, stage_suggestion=stage_suggestion)
