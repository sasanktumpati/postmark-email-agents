from pydantic_ai import Agent

from app.core.config import settings
from app.modules.actionables.shopping.models.response import ShoppingAgentResponse
from app.modules.actionables.shopping.tools import (
    ShoppingDependencies,
    save_bill,
    save_coupon,
)

shopping_system_prompt = """
You are an intelligent assistant that extracts shopping-related information from emails.
Your task is to identify and save bills and coupons from transactional or promotional emails.

- For bills, extract the vendor, amount, currency, due date, and a payment URL.
- For coupons, extract the vendor, coupon code, a description of the discount, and the expiry date.

An email might contain multiple bills or coupons. You must identify all of them and use the provided tools to save each one.
If any required information is missing, make a reasonable inference based on the context, but do not hallucinate.

You must return a list of all identified actions.
"""

shopping_agent = Agent(
    model=settings.gemini_model,
    deps_type=ShoppingDependencies,
    output_type=ShoppingAgentResponse,
    system_prompt=shopping_system_prompt,
    tools=[
        save_bill,
        save_coupon,
    ],
    retries=3,
    output_retries=3,
)
