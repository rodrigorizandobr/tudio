import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.repositories.agent_repository import agent_repository

def check_agent():
    print("Checking agent 'Capô Imaculado'...")
    agent = agent_repository.find_by_name("Capô Imaculado")
    
    if agent:
        print(f"Found Agent ID: {agent.id}")
        print("-" * 20)
        print(f"Prompt Init (first 100 chars): {agent.prompt_init[:100]}")
        print("-" * 20)
        print(f"Full Length: {len(agent.prompt_init)}")
    else:
        print("Agent not found.")

if __name__ == "__main__":
    check_agent()
