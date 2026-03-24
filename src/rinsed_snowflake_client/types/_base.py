"""Base Pydantic model for all Rinsed response types."""

from pydantic import BaseModel, ConfigDict


class RinsedModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
