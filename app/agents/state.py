import operator
from typing import Annotated, List, Optional, Literal
from pydantic import BaseModel, Field


class ChangedFile(BaseModel):
    filename: str
    status: Literal["added", "modified", "deleted", "renamed"]
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    patch: str
    full_content: Optional[str] = None



class ReviewComment(BaseModel):
    file_path: str
    line_number: Optional[int] = None
    comment: str
    severity: Optional[Literal["info", "warning", "error"]] = None

class PRMetadata(BaseModel):
    title: str
    description: str
    author: str
    base_branch: str
    labels: List[str] = Field(default_factory=list)

class PRData(BaseModel):
    pr_metadata: PRMetadata
    files_changed: List[ChangedFile] = Field(default_factory=list)
    linked_issues: List[str] = Field(default_factory=list)
    review_comments: List[ReviewComment] = Field(default_factory=list)

class PRState(BaseModel):
    pr_data: Optional[PRData] = Field(default=None, description="PR data")
    files_to_review: Optional[List[ChangedFile]] = Field(default=None,description="Files to review with their metadata")
    skipped_files: Optional[List[str]] = Field(default=None, description="Lockfiles, generated code, etc.")
    current_file_index: Optional[int] = Field(default=0, description="Current file index being reviewed", ge=0)
    file_reviews: Optional[Annotated[List, operator.add]] = Field(default=None, description="Accumulated reviews across nodes")
    summary: Optional[str] = Field(default=None, description="PR summary")
    approval_recommendation: Optional[str] = Field(default=None, description="Recommendation: approve, comment, or request_changes")
    all_issues: Optional[Annotated[List, operator.add]] = Field(default=None, description="Accumulated issues across nodes")
    error: Optional[str] = Field(default=None, description="Error field to capture exceptions during processing. If populated, process stopped.")
