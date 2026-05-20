"""Change event input contract for release review runs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ChangeType = Literal[
    "document_update",
    "prompt_change",
    "model_change",
    "retriever_change",
    "chunking_change",
    "embedding_change",
    "config_change",
    "unknown",
]
ReviewStage = Literal["pre_delivery", "post_delivery_change", "monthly_review", ""]


class ChangedAsset(BaseModel):
    """Asset changed before a gate run."""

    type: str = ""
    name: str = ""
    version: str = ""
    path: str = ""
    content_hash: str = ""

    model_config = ConfigDict(extra="forbid")


class ChangeEvent(BaseModel):
    """Input model for change-event.yml."""

    change_id: str = Field(min_length=1)
    change_type: ChangeType = "unknown"
    change_summary: str = ""
    target_release: str = ""
    changed_assets: list[ChangedAsset] = Field(default_factory=list)
    affected_documents: list[str] = Field(default_factory=list)
    affected_business_categories: list[str] = Field(default_factory=list)
    retest_reason: str = ""
    review_stage: ReviewStage = ""

    model_config = ConfigDict(extra="forbid")
