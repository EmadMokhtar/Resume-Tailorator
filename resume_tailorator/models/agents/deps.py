from pydantic import BaseModel, Field


class JobContentDeps(BaseModel):
    content: str
    file_path: str = Field(
        description="Path to the file containing the job posting content."
    )
