from __future__ import annotations

from app.models import ChatRequest, ChatResponse

from app.services.do_agent import DOAgentClient


async def gradient_chat(case_id: str, req: ChatRequest) -> ChatResponse:
    client = DOAgentClient()

    system = (
        "You are a detective-case assistant. You must ground your answers in the attached knowledge base. "
        "If information is missing or uncertain, say so clearly. Keep replies concise and investigative."
    )

    persona = (
        "Role: Co-detective."
        if req.role == "co_detective"
        else "Role: Witness. Only state what this witness personally observed; do not invent facts."
    )

    resp = await client.chat_completions(
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"case_id={case_id}\n"
                    f"stage={req.stage}\n"
                    f"{persona}\n\n"
                    f"User message:\n{req.message}"
                ),
            },
        ],
        include_retrieval_info=True,
        include_guardrails_info=True,
    )

    content = client.extract_content(resp).strip()
    return ChatResponse(role=req.role, reply=content)

