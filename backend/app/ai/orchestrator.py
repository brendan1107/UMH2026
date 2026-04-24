"""
AI Orchestrator

Main orchestration module that coordinates the AI reasoning pipeline.
Builds context, calls GLM, parses structured output, and triggers
follow-up actions (task generation, fact extraction, recommendation updates).

Corresponds to SAD Section 4.2: AI Orchestration Module.
"""

from app.ai.review_layer import ReviewLayer


class AIOrchestrator:
    """Orchestrates the multi-step agentic AI reasoning pipeline."""

    def __init__(
        self,
        glm_client,
        context_builder,
        response_parser,
        memory_manager,
        review_layer=None,
    ):
        self.glm_client = glm_client
        self.context_builder = context_builder
        self.response_parser = response_parser
        self.memory_manager = memory_manager
        self.review_layer = review_layer or ReviewLayer()

    async def process_user_input(self, case_id: str, session_id: str, user_message: str):
        """
        Full AI processing pipeline for a user message.

        Flow (SAD Section 5 & 8):
        1. Build context from structured memory, facts, place data, uploads
        2. Send prompt to GLM
        3. Parse structured output (questions, facts, tasks, recommendation)
        4. Run review layer for sanity check
        5. Return structured AI response
        """
        context = self.context_builder.build_context(case_id)
        context["latest_user_message"] = user_message

        memory = await self.memory_manager.get_structured_memory(case_id)
        context["memory"] = memory

        if self.glm_client is None:
            return self._fallback_response(user_message)

        raw_response = await self.glm_client.chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are F&B Genie. Return concise JSON with keys: "
                        "message, follow_up_questions, extracted_facts, "
                        "generated_tasks, recommendation_update."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Context: {context}\n\n"
                        f"User message: {user_message}"
                    ),
                },
            ],
            temperature=0.2,
        )
        parsed = self.response_parser.parse_ai_response(raw_response)
        facts = self.response_parser.extract_facts(parsed)
        facts = await self.review_layer.validate_facts(facts)
        tasks = self.response_parser.extract_tasks(parsed)
        recommendation = self.response_parser.extract_recommendation(parsed)
        if recommendation:
            review = await self.review_layer.review_recommendation(
                recommendation,
                context,
            )
            if review.get("recommendation"):
                recommendation = review["recommendation"]
        await self.memory_manager.update_memory(case_id, facts)

        return {
            "message": parsed.get("message") or str(raw_response),
            "follow_up_questions": parsed.get("follow_up_questions"),
            "extracted_facts": facts,
            "generated_tasks": tasks,
            "recommendation_update": recommendation,
            "conversation_summary": parsed.get("conversation_summary"),
        }

    async def reanalyze_after_evidence(self, case_id: str, new_evidence: dict):
        """
        Re-analyze business case after new evidence is submitted.
        Updates recommendation based on completed tasks or uploaded evidence.
        (PRD Section 4.2: Re-analysis After New Evidence)
        """
        evidence_summary = (
            new_evidence.get("summary")
            if isinstance(new_evidence, dict)
            else str(new_evidence)
        )
        return await self.process_user_input(
            case_id=case_id,
            session_id=str(case_id),
            user_message=f"New evidence submitted: {evidence_summary}",
        )

    async def generate_business_report(self, case_id: str):
        """
        Generate a comprehensive business report based on all available data.
        (PRD Section 4.2: Business Plan Generation)
        """
        context = self.context_builder.build_context(case_id)
        if self.glm_client is None:
            return {
                "case_id": case_id,
                "report": "AI report generation is not configured.",
                "context": context,
            }
        report = await self.glm_client.chat_completion(
            [
                {
                    "role": "system",
                    "content": "Generate a concise F&B business report.",
                },
                {"role": "user", "content": str(context)},
            ],
            temperature=0.2,
        )
        return {
            "case_id": case_id,
            "report": report,
            "context": context,
        }

    @staticmethod
    def _fallback_response(user_message: str) -> dict:
        return {
            "message": (
                "I recorded your input. The AI model is not configured yet, "
                "so I could not generate model-backed analysis."
            ),
            "follow_up_questions": [
                "What budget, location, and target customers should I use for the analysis?"
            ],
            "extracted_facts": [],
            "generated_tasks": [],
            "recommendation_update": None,
            "conversation_summary": user_message[:240],
        }
