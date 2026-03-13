"""Task management - agents create, claim, and complete work items."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.agent import Agent
from backend.models.role import Role
from backend.models.task import Task
from backend.models.city_event import CityEvent
from backend.core.auth import get_current_agent
from backend.schemas.task import TaskCreate, TaskComplete, TaskPublic

router = APIRouter()


async def _enrich(task: Task, db) -> TaskPublic:
    data = TaskPublic.model_validate(task)
    creator = (await db.execute(
        select(Agent.name).where(Agent.id == task.created_by)
    )).scalar()
    data.creator_name = creator or "Unknown"
    if task.assigned_to:
        assignee = (await db.execute(
            select(Agent.name).where(Agent.id == task.assigned_to)
        )).scalar()
        data.assignee_name = assignee or ""
    if task.role_id:
        role_name = (await db.execute(
            select(Role.name).where(Role.id == task.role_id)
        )).scalar()
        data.role_name = role_name or ""
    return data


@router.get("/", response_model=list[TaskPublic])
async def list_tasks(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Task).order_by(Task.priority.desc(), Task.created_at.desc())
    if status:
        query = query.where(Task.status == status)
    result = await db.execute(query)
    return [await _enrich(t, db) for t in result.scalars().all()]


@router.get("/open", response_model=list[TaskPublic])
async def open_tasks(
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Task)
        .where(Task.status == "open")
        .where(Task.assigned_to.is_(None))
        .order_by(Task.priority.desc(), Task.created_at.asc())
    )
    if role:
        role_result = await db.execute(select(Role).where(Role.name == role))
        role_obj = role_result.scalar_one_or_none()
        if role_obj:
            query = query.where(Task.role_id == role_obj.id)
    result = await db.execute(query)
    return [await _enrich(t, db) for t in result.scalars().all()]


@router.post("/", response_model=TaskPublic, status_code=201)
async def create_task(
    payload: TaskCreate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    role_id = None
    if payload.role_name:
        role_result = await db.execute(select(Role).where(Role.name == payload.role_name))
        role_obj = role_result.scalar_one_or_none()
        if role_obj:
            role_id = role_obj.id

    task = Task(
        title=payload.title,
        description=payload.description,
        role_id=role_id,
        priority=payload.priority,
        created_by=agent.id,
    )
    db.add(task)
    await db.flush()
    return await _enrich(task, db)


@router.post("/{task_id}/claim", response_model=TaskPublic)
async def claim_task(
    task_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    result = await db.execute(select(Task).where(Task.id == uuid.UUID(task_id)))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "open":
        raise HTTPException(status_code=400, detail="Task is not open")
    if task.assigned_to is not None:
        raise HTTPException(status_code=409, detail="Task already claimed")

    task.assigned_to = agent.id
    task.status = "in_progress"
    db.add(task)

    event = CityEvent(
        event_type="task_claimed",
        data={"task_id": str(task.id), "title": task.title, "by": str(agent.id)},
    )
    db.add(event)

    await db.flush()
    return await _enrich(task, db)


@router.post("/{task_id}/complete", response_model=TaskPublic)
async def complete_task(
    task_id: str,
    payload: TaskComplete,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    result = await db.execute(select(Task).where(Task.id == uuid.UUID(task_id)))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.assigned_to != agent.id:
        raise HTTPException(status_code=403, detail="Only the assigned agent can complete this task")
    if task.status != "in_progress":
        raise HTTPException(status_code=400, detail="Task is not in progress")

    task.status = "completed"
    task.completed_at = datetime.now(timezone.utc)
    if payload.result:
        task.description = (task.description or "") + f"\n\n--- Result ---\n{payload.result}"
    db.add(task)

    event = CityEvent(
        event_type="task_completed",
        data={"task_id": str(task.id), "title": task.title, "by": str(agent.id)},
    )
    db.add(event)

    await db.flush()
    return await _enrich(task, db)
