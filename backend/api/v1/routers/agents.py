from typing import List
from fastapi import APIRouter, Depends, HTTPException
from backend.models.agent import AgentModel
from backend.services.agent_service import agent_service
from backend.models.user import UserModel
from backend.api.deps import get_current_user


router = APIRouter()

@router.get("/", response_model=List[AgentModel])
async def list_agents(
    current_user: UserModel = Depends(get_current_user)
):
    """List all agents."""
    return await agent_service.list_all()

@router.post("/", response_model=AgentModel)
async def create_agent(
    agent: AgentModel,
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new agent."""
    return await agent_service.create(agent)

@router.get("/{agent_id}", response_model=AgentModel)
async def get_agent(
    agent_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get a specific agent."""
    agent = await agent_service.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.put("/{agent_id}", response_model=AgentModel)
async def update_agent(
    agent_id: str,
    agent_data: AgentModel,
    current_user: UserModel = Depends(get_current_user)
):
    """Update a specific agent."""
    updated = await agent_service.update(agent_id, agent_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Agent not found")
    return updated

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete an agent."""
    # Optional: Prevent deleting the last/default agent?
    # For now, let's allow it as per requirements.
    success = await agent_service.delete(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "success"}
