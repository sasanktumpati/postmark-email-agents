import asyncio
from typing import Any, Dict

from app.core.config import get_config
from app.core.logger import get_logger
from app.modules.actionables.agents.calendar_agent import (
    CalendarDependencies,
    calendar_agent,
)
from app.modules.actionables.agents.notes_agent import (
    NotesDependencies,
    notes_agent,
)
from app.modules.actionables.agents.shopping_agent import (
    ShoppingDependencies,
    shopping_agent,
)

logger = get_logger(__name__)
config = get_config()


class AgentService:
    """
    Service class to manage all PydanticAI agents for actionables processing.
    This provides a unified interface to interact with all agents.
    """

    def __init__(self, email_id: int, email_thread: str):
        self.email_id = email_id
        self.email_thread = email_thread
        logger.info(f"AgentService initialized for email_id: {email_id}")
        logger.debug(f"Email thread content length: {len(email_thread)} characters")

    async def run_calendar_agent(self) -> Dict[str, Any]:
        """Process calendar-related actionables from email thread."""
        try:
            logger.info(
                f"Processing calendar actionables for email_id: {self.email_id}"
            )
            logger.debug(
                f"Starting calendar agent iteration with model: {config.gemini_model}"
            )

            step_count = 0
            async with calendar_agent.iter(
                self.email_thread,
                deps=CalendarDependencies(email_id=self.email_id),
                model=config.gemini_model,
                retries=3,
            ) as agent_run:
                async for step in agent_run:
                    step_count += 1
                    logger.info(
                        f"Calendar agent step {step_count}: {type(step).__name__}"
                    )
                    if hasattr(step, "tool_name"):
                        logger.info(f"Tool call detected: {step.tool_name}")
                    if hasattr(step, "content"):
                        logger.debug(f"Step content: {step.content}")

                logger.info(f"Calendar agent completed {step_count} steps")
                result = agent_run.result

            logger.info(
                f"Calendar actionables processed successfully for email_id: {self.email_id} response={result.output}"
            )
            logger.debug(f"Calendar agent usage: {result.usage()}")
            return {"success": True, "data": result.output, "usage": result.usage()}
        except Exception as e:
            logger.error(
                f"Error processing calendar actionables for email_id {self.email_id}: {str(e)}",
                exc_info=e,
            )
            return {"success": False, "error": str(e)}

    async def run_notes_agent(self) -> Dict[str, Any]:
        """Process notes-related actionables from email thread."""
        try:
            logger.info(f"Processing notes actionables for email_id: {self.email_id}")
            logger.debug(
                f"Starting notes agent iteration with model: {config.gemini_model}"
            )

            step_count = 0
            async with notes_agent.iter(
                self.email_thread,
                deps=NotesDependencies(email_id=self.email_id),
                model=config.gemini_model,
                retries=3,
            ) as agent_run:
                async for step in agent_run:
                    step_count += 1
                    logger.info(f"Notes agent step {step_count}: {type(step).__name__}")
                    if hasattr(step, "tool_name"):
                        logger.info(f"Tool call detected: {step.tool_name}")
                    if hasattr(step, "content"):
                        logger.debug(f"Step content: {step.content}")

                logger.info(f"Notes agent completed {step_count} steps")
                result = agent_run.result

            logger.info(
                f"Notes actionables processed successfully for email_id: {self.email_id} response={result.output}"
            )
            logger.debug(f"Notes agent usage: {result.usage()}")
            return {"success": True, "data": result.output, "usage": result.usage()}
        except Exception as e:
            logger.error(
                f"Error processing notes actionables for email_id {self.email_id}: {str(e)}",
                exc_info=e,
            )
            return {"success": False, "error": str(e)}

    async def run_shopping_agent(self) -> Dict[str, Any]:
        """Process shopping-related actionables from email thread."""
        try:
            logger.info(
                f"Processing shopping actionables for email_id: {self.email_id}"
            )
            logger.debug(
                f"Starting shopping agent iteration with model: {config.gemini_model}"
            )

            step_count = 0
            async with shopping_agent.iter(
                self.email_thread,
                deps=ShoppingDependencies(email_id=self.email_id),
                model=config.gemini_model,
                retries=3,
            ) as agent_run:
                async for step in agent_run:
                    step_count += 1
                    logger.info(
                        f"Shopping agent step {step_count}: {type(step).__name__}"
                    )
                    if hasattr(step, "tool_name"):
                        logger.info(f"Tool call detected: {step.tool_name}")
                    if hasattr(step, "content"):
                        logger.debug(f"Step content: {step.content}")

                logger.info(f"Shopping agent completed {step_count} steps")
                result = agent_run.result

            logger.info(
                f"Shopping actionables processed successfully for email_id: {self.email_id} response={result.output}"
            )
            logger.debug(f"Shopping agent usage: {result.usage()}")
            return {"success": True, "data": result.output, "usage": result.usage()}
        except Exception as e:
            logger.error(
                f"Error processing shopping actionables for email_id {self.email_id}: {str(e)}",
                exc_info=e,
            )
            return {"success": False, "error": str(e)}

    async def run_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Process all types of actionables concurrently.
        Returns a dictionary with results from all agents.
        """
        logger.info(
            f"Processing all actionables concurrently for email_id: {self.email_id}"
        )

        results = await asyncio.gather(
            self.run_calendar_agent(),
            self.run_notes_agent(),
            self.run_shopping_agent(),
            return_exceptions=True,
        )

        calendar_result, notes_result, shopping_result = results

        if isinstance(calendar_result, Exception):
            calendar_result = {"success": False, "error": str(calendar_result)}
        if isinstance(notes_result, Exception):
            notes_result = {"success": False, "error": str(notes_result)}
        if isinstance(shopping_result, Exception):
            shopping_result = {"success": False, "error": str(shopping_result)}

        logger.info(
            f"All actionables processing completed for email_id: {self.email_id}"
        )

        return {
            "calendar": calendar_result,
            "notes": notes_result,
            "shopping": shopping_result,
        }
