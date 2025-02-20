from pydantic import BaseModel, Field
from typing_extensions import List, Annotated, TypedDict, Dict, Any, Optional
import asyncio


def generic_reducer(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        result = a.copy()
        for key in b:
            if key in a:
                result[key] = generic_reducer(a[key], b[key])
            else:
                result[key] = b[key]
        return result
    elif isinstance(a, list) and isinstance(b, list):
        return a + b
    else:
        return b


class CharacterStats(TypedDict):
    name: str
    gender: str
    slogan: str
    description: str
    role: str
    inventory: Dict[str, Any]
    health: int
    energy: int
    education: str


class Decision(TypedDict):
    need_replan: bool
    action_description: List[str]
    action_result: List[str]
    new_plan: List[str]
    daily_objective: List[List[str]]
    meta_seq: List[str]
    reflection: List[str]
    expanded_meta_seq: List[str]


class Meta(TypedDict):
    tool_functions: str
    day: str
    available_locations: List[str]


class Prompts(TypedDict):
    daily_goal: str
    refer_to_previous: str
    life_style: str
    daily_objective_ar: str
    task_priority: List[str]
    max_actions: int
    meta_seq_ar: str
    replan_time_limit: int
    meta_seq_adjuster_ar: str
    focus_topic: List[str]
    depth_of_reflection: str
    reflection_ar: str
    level_of_detail: str
    tone_and_style: str


class PublicData(TypedDict):
    market_data: Dict[str, Any]


class RunningState(TypedDict):
    userid: int
    character_stats: Annotated[CharacterStats, generic_reducer]
    decision: Annotated[Decision, generic_reducer]
    meta: Annotated[Meta, generic_reducer]
    prompts: Annotated[Prompts, generic_reducer]
    message_queue: asyncio.Queue
    event_queue: asyncio.Queue
    false_action_queue: asyncio.Queue
    public_data: PublicData
    past_stats: Annotated[CharacterStats, generic_reducer]
    websocket: Any
    current_pointer: str
    instance: Any


class DailyObjective(BaseModel):
    """Daily objective to follow in future"""

    progress: str = Field(description="progress")
    objectives: List[str] = Field(description="daily objectives list")


class TradeObjective(BaseModel):
    """Trade objective to follow in future"""

    decision: str = Field(description="do some trade or not")
    objectives: List[str] = Field(description="trade objectives list")


class DetailedPlan(BaseModel):
    """Detailed plan to follow in future"""

    detailed_plan: str = Field(description="detailed plan")


class MetaActionSequence(BaseModel):
    """Meta action sequence to follow in future"""

    meta_action_sequence: List[str] = Field(description="meta action sequence")
    action_emoji_sequence: List[str] = Field(
        description="emoji sequence that describes actions"
    )
    state_emoji_sequence: List[str] = Field(
        description="emoji sequence that describes states"
    )
    description_sequence: List[str] = Field(description="description sequence")


class DetailedMetaAction(BaseModel):
    action: str = Field(
        ...,
        description="The action to take, e.g., 'goto workshop', 'craft feed 5', etc.",
    )
    cost: Optional[str] = Field(
        None,
        description="Energy/Money or other materials cost. Not all actions need this field",
    )
    status_before: Optional[str] = Field(
        None, description="User Status Info before this action is taken."
    )
    status_after: Optional[str] = Field(
        None,
        description="User Status Info after this action is taken. All after status should not be negative, or the action is invalid.",
    )
    inventory_before: Optional[str] = Field(
        None, description="User Inventory Info before this action is taken"
    )
    inventory_after: Optional[str] = Field(
        None,
        description="User Inventory Info after this action is taken. All after inventory should not be negative, or the action is invalid.",
    )
    reason: str = Field(None, description="Why this action is needed")


class DetailedMetaActionSequence(BaseModel):
    """Crafting and trading action sequence to follow in future"""

    action_sequence: List[DetailedMetaAction] = Field(
        ..., description="Detailed meta-action sequence"
    )


class CV(BaseModel):
    """CV to follow in future"""

    job_id: int = Field(description="job id")
    job_name: str = Field(description="job name")
    cv: str = Field(description="cv")


class NewCV(BaseModel):
    """New CV to follow in future"""

    job_id: int = Field(description="job id")
    cv: str = Field(description="The content of CV")


class MayorDecision(BaseModel):
    """Mayor decision to follow in future"""

    decision: str = Field(description="yes or no")
    comments: str = Field(description="comments")


class Reflection(BaseModel):
    resource_management:  str = Field(description="The content of resource_management")
    energy_and_health:  str = Field(description="The content of energy_and_health")
    time_efficiency:   str = Field(description="The content of time_efficiency")
    financial_strategy:   str = Field(description="The content of financial_strategy")
    task_prioritization:   str = Field(description="The content of task_prioritization")


class Response(BaseModel):
    """Response to user."""

    response: str


class CharacterArc(BaseModel):
    """Character arc to follow in future"""

    belief: str = Field(description="belief")
    mood: str = Field(description="mood")
    values: str = Field(description="values")
    habits: str = Field(description="habits")
    personality: str = Field(description="personality")


class AccommodationDecision(BaseModel):
    """Accommodation decision including accommodation_id and lease_weeks."""

    accommodation_id: int = Field(description="ID of the chosen accommodation")
    lease_weeks: int = Field(description="Number of weeks to lease (1-4)")
    comments: str = Field(description="comments")


class EmojiSeq(BaseModel):
    content: str = Field(description="The appropriate monologues for each time point")
    emoji: str = Field(description="2 corresponding emojis")


class EmojiSequence(BaseModel):

    response: List[EmojiSeq] = Field(description="emoji sequence")


class MetaAction(BaseModel):
    """Meta action to follow in future"""

    action: str = Field(
        description="The action to take, e.g., 'goto workshop' or 'craft feed 5'"
    )
    cost: str = Field(description="Energy or resource cost")
    expected_effect: str = Field(
        description="Expected effect of the action, get from the model"
    )


class RefinedMetaActionSequence(BaseModel):
    """Refined meta action sequence to follow in future"""

    meta_action_sequence: List[MetaAction] = Field(description="meta action sequence")


class StateInfo(BaseModel):
    money: int = Field(description="money")
    energy: int = Field(description="energy")
    inventory: Dict[str, int] = Field(description="inventory")
    location: str = Field(description="location")


class RefinedActionsAndState(BaseModel):
    """Refined action and state to follow in future"""

    actions: str = Field(description="refined action")
    current_state: StateInfo = Field(description="current state")
    reason: str = Field(description="reason", default="None")


class MayorDecisionBatchly(BaseModel):
    """Batchly decision"""

    decision: List[str] = Field(description="decision list of mayor")
    comments: str = Field(description="comments for the decision")


if __name__ == "__main__":
    import pprint

    run = RunningState()

    pprint(run)
