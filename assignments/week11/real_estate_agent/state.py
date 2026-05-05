from pydantic import BaseModel, Field
from typing import Literal


class BuyerProfile(BaseModel):
    budget_min_lakhs: int
    budget_max_lakhs: int
    locations: list[str]
    property_type: Literal["apartment", "villa", "plot"]
    bhk: int                        # buyer's stated preference
    bhk_min: int | None = None      # set only during relaxation step 3
    bhk_max: int | None = None      # set only during relaxation step 3
    possession_months: int
    must_haves: list[str]           = Field(default_factory=list)
    lifestyle_tags: list[str]       = Field(default_factory=list)
    constraint_tensions: list[str]  = Field(default_factory=list)
    incomplete: bool                = False


class Property(BaseModel):
    property_id: str
    title: str
    location: str
    price_lakhs: float
    bhk: int
    possession_months: int
    tags: list[str]     = Field(default_factory=list)
    amenities: list[str] = Field(default_factory=list)


class ScoredProperty(Property):
    budget_fit: float       = 0.0
    location_match: float   = 0.0
    lifestyle_tags: float   = 0.0
    possession_fit: float   = 0.0
    amenities_match: float  = 0.0
    total_score: float      = 0.0
    rationale: str          = ""


class GraphState(BaseModel):
    # populated by Intake Agent
    buyer_profile: BuyerProfile | None          = None

    # populated by Search Agent
    candidates: list[Property]                  = Field(default_factory=list)
    relaxations_applied: list[str]              = Field(default_factory=list)
    search_exhausted: bool                      = False
    recovery_triggered: bool                    = False

    # populated by Analysis Agent
    shortlist: list[ScoredProperty]             = Field(default_factory=list)

    # populated by Communication Agent
    recommendation_report: str                  = ""

    # conversation history for Intake Agent
    messages: list[dict]                        = Field(default_factory=list)
