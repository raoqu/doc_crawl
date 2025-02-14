from pydantic import BaseModel, Field

class CrawlResult(BaseModel):
    url: str = Field(default="")
    success: bool = Field(default=False)
    message: str = Field(default="")
    title: str = Field(default="")
    html: str = Field(default="")
    markdown: str = Field(default="")
    image_urls: list[str] = Field(default_factory=list)
    link_urls: list[str] = Field(default_factory=list)
    doc_id: int = Field(default=-1)