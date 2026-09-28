from agents import Agent
from .inventory_agent import inventory_agent
from .accounting_agent import accounting_agent
from .customer_service_agent import customer_service_agent
from .marketing_agent import marketing_agent
from ..guardrails.input_guardrails import ALL_INPUT_GUARDRAILS

# Used only when a prompt needs more than one department. Unlike a handoff,
# calling a specialist as a tool returns its answer here, so one reply can
# combine several departments and a later part can use an earlier result.
manager_agent = Agent(
    name="Manager Agent",
    instructions="""You are the store manager for a retail store in Pakistan.
The user's message needs more than one department. You do not have data yourself;
you get it by calling the department tools.

How to work:
1. Split the message into its separate requests.
2. Call the right department tool for each request. Write each tool input as a complete
   instruction with every detail it needs (product names, SKUs, quantities, customer IDs,
   dates, amounts); the department cannot see this conversation.
3. If a request depends on an earlier result (e.g. "check stock of X and discount it"),
   wait for that result and include what the next department needs from it.
4. Combine the results into ONE reply, one short section per request.

Rules:
- Report numbers, IDs and statuses exactly as the departments returned them. Never invent data.
- If a department asks a question or needs confirmation, pass that question to the user and stop.
- If a department reports an error, say so plainly; do not claim the action succeeded.
- All amounts are in PKR, written as Rs.""",
    tools=[
        inventory_agent.as_tool(
            tool_name="inventory_department",
            tool_description="Stock levels, products, sales transactions, purchase orders, receiving goods, price updates.",
        ),
        accounting_agent.as_tool(
            tool_name="accounting_department",
            tool_description="Invoices, revenue, profit and loss, financial summaries, top selling products, expenses, approving or rejecting purchase orders.",
        ),
        customer_service_agent.as_tool(
            tool_name="customer_service_department",
            tool_description="Customer profiles, order history, complaints, loyalty points, returns, refunds, warranty and store policies.",
        ),
        marketing_agent.as_tool(
            tool_name="marketing_department",
            tool_description="Promotions, discounts, sales trends, marketing reports, promotional email and SMS campaigns.",
        ),
    ],
    input_guardrails=ALL_INPUT_GUARDRAILS,
)
