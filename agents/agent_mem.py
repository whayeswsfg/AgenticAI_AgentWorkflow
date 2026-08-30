import logging
from datetime import datetime

from dotenv import load_dotenv

from agentspan.agents import Agent, AgentRuntime, ConversationMemory, run, tool

load_dotenv()

logging.basicConfig(level=logging.WARNING)
logging.getLogger("agentspan").setLevel(logging.WARNING)
logging.getLogger("conductor").setLevel(logging.WARNING)


@tool
def get_current_time() ->str:
    """returns the current local time"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:S")

#add memory for the model
conversation_memory = ConversationMemory(max_messages=5)

assistant = Agent(
    name="wanda_personal_assistant",
    model="openai/gpt-5.4",
    instructions=(
        "You are a concise personal assistant.  Use tools when they help"
        " and remember useful user details across turns"
    ),
    tools=[get_current_time],
    memory=conversation_memory,

)

if __name__ == "__main__":
    print("Starting agent...")

    with AgentRuntime() as runtime:
        while True:
            prompt = input("You: ").strip()
            if prompt.lower() == "q":
                break
            if not prompt:
                continue

            result = run(assistant, prompt, runtime=runtime)
            readable_result =   result.output.get('result')
            conversation_memory.add_user_message(prompt)
            conversation_memory.add_assistant_message(readable_result)


            print(f"WH Assistant Response: {result.output.get('result')}")

