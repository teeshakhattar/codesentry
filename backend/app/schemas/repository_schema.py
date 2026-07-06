from pydantic import BaseModel, HttpUrl


class RepositoryRequest(BaseModel):
    repo_url: HttpUrl