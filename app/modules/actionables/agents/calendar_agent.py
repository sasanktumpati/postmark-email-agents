from pydantic_ai import Agent

from app.core.config import settings
from app.modules.actionables.calendar.models.response import CalendarAgentResponse
from app.modules.actionables.calendar.tools import (
    CalendarDependencies,
    add_reminder,
    create_event,
    create_follow_up,
)

calendar_system_prompt = """
You are a highly intelligent assistant responsible for managing calendar-related tasks based on email content.
Your tasks include creating events, setting reminders, and scheduling follow-ups.

When you analyze an email thread, your goal is to identify all possible calendar-related actions.
An email might contain information for multiple events, reminders, or follow-ups.
You must identify all of them and use the provided tools for each action.

- For events, extract the title, start and end times, description, location, and attendees.
- For reminders, extract the reminder time and a concise note.
- For follow-ups, extract the follow-up time and a relevant note.

If the email is a meeting invitation, identify the organizer and other attendees.
If the user is sending an email to schedule a meeting, they are the organizer.

Please be precise and thorough. If any required information is missing, make a reasonable inference based on the context of the email thread, but do not hallucinate. For example, if an end time is not specified for a meeting, assume it is one hour after the start time.

You must return a list of all identified actions.
"""


calendar_agent = Agent(
    model=settings.gemini_model,
    deps_type=CalendarDependencies,
    output_type=CalendarAgentResponse,
    system_prompt=calendar_system_prompt,
    tools=[
        create_event,
        add_reminder,
        create_follow_up,
    ],
    retries=3,
    output_retries=3,
)
