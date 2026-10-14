from pydantic import BaseModel, Field

class PaginationParams(BaseModel):
limit int = Field(default=20, ge=1, le=100)
offset int = Field(default=0, ge=0)

class PaginationMetadata(BaseModel):
count: int
limit: int
offset: int
has_more: bool