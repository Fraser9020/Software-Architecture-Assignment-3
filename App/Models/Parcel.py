import uuid
from pydantic import BaseModel, Field


class Parcel(BaseModel):

    # Same limits as the create order form
    weight: float = Field(ge=0.1, le=200)
    # L x W x H in cm, e.g. "12.5 x 10 x 5"
    dimension: str = Field(pattern=r"^\d+(\.\d+)?\s*x\s*\d+(\.\d+)?\s*x\s*\d+(\.\d+)?$")
    fragile: bool = False

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())  # Generate a unique parcel ID
    )

    def to_dict(self):
        return {
            "parcel_id": self.id,
            "weight": self.weight,
            "dimension": self.dimension,
            "fragile": self.fragile
        }
