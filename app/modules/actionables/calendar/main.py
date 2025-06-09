from app.modules.actionables.agents.agent_service import AgentService


async def process_calendar_actionables(email_id: int, email_thread: str):
    """
    Process calendar actionables from an email thread.
    """
    agent_service = AgentService(email_id, email_thread)
    response = await agent_service.run_calendar_agent()
    return response
