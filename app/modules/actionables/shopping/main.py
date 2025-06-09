from app.modules.actionables.agents.agent_service import AgentService


async def process_shopping_actionables(email_id: int, email_thread: str):
    """
    Process shopping actionables from an email thread.
    """
    agent_service = AgentService(email_id, email_thread)
    response = await agent_service.run_shopping_agent()
    return response
