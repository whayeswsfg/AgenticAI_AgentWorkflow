import logging

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from agentspan.agents import(
    Agent,
    AgentRuntime,
    ConversationMemory,
    EventType,
    Guardrail,
    GuardrailResult,
    OnFail,
    Position,
    guardrail,
    start,
    tool,
)

load_dotenv(override=True)
logging.basicConfig(level=logging.WARNING, force=True)
logging.disable(logging.INFO)

MOCK_DB = {
    "orders": {"A100": {"status":"delivered", "total": 49.99}},
    "accounts": {"whayeswsfg@gmail.com": {"status": "active", "tier": "pro"}},
}

DOCS = {
    "refund policy": "Refunds are processed within 5 busienss days.",
    "shipping": "Standard shipping takes 3 to 7 business days.",
    "account": "Pro accounts include priority support.",
}

#how we want the agent to give the output.  instead of random text put it in a format that is readable
class SupportResponse(BaseModel):
    stage: str = Field(description="Stage like answered, refunded or rejected")
    successful: bool
    message: str

@tool
def search_knowledge_base(query: str) ->str:
    """search support docs"""
    for title, body in DOCS.items():
        if title in query.lower():
            return body
    return "No matching support articles found."
965
@tool
def lookup_order(order_id: str) -> dict:
    """lookup order in database by ID"""
    return MOCK_DB["orders"].get(order_id, {"error": "order not found"})

@tool(approval_required=True)
def process_refund(order_id: str, amount: float) -> str:
    """request a refund, pause for human approval think before you run this tool"""
    return(f"Refund of ${amount} for order {order_id} has been processed. ")

support_agent = Agent(
    name="wh_support_agent",
    model="openai/gpt-5.4",
    instructions=(
        "You are a customer support agent. Use the knowledge base first."
        "If the customer wants a refund: when you know the order ID, call "
        "lookup_order to get the amount.  Before calling process_refund, "
        "write a short plain-English sentence describing exactly what refund "
        "you are about to issue, for example: 'I am going to refund $49.99 "
        "for order A100.' Then call process_refund.  The tool will pause for "
        "human approval automatically.  If the order ID is missing, ask the "
        "customer for it.  Always populate the message field with a clear reply. "
    ),
    output_type=SupportResponse, #force the model to give the output in a structured format
    tools=[search_knowledge_base, lookup_order, process_refund],
    memory=ConversationMemory(max_messages=50), #automatically add the content including the tool calls to memory
    max_turns=10, # number of turns before the agent stops the conversation
)

def run_interactive(prompt: str) ->None:
    with AgentRuntime() as runtime:
        handle = start(support_agent, prompt, runtime=runtime)
        stream = handle.stream()

        order_id, amount = None, None
        for event in stream:
            if event.type==EventType.TOOL_CALL and event.args:
                order_id=event.args.get("order_id") or order_id
            elif event.type == EventType.TOOL_RESULT and isinstance(event.result,dict):
                amount = event.result.get("total") or amount
            elif event.type==EventType.WAITING:
                print(f"\nApproval required: refund ${amount} for order {order_id}")
                decision = input("Approve? (y/n): ").lower().strip()
                if decision=="y":
                    handle.approve()
                else:
                    handle.reject("user rejected refund")


        result = stream.get_result()
        output = result.output.get("result")
        print(f" \n{output}\n")

if __name__=="__main__":
    print("Support bot starting....")
    while True:
        prompt = input("You: ").strip()
        if prompt.lower()=="q":
            break
        if not prompt:
            continue
        run_interactive(prompt)
        
        

