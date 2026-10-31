import uuid


class Parcel: 
    def __init__(self, weight, dimension, fragile):
        self.id = str(uuid.uuid4())  # Generate a unique parcel ID
        self.weight = weight
        self.dimension = dimension
        self.fragile = fragile 

    def to_dict(self):
        return {
            "parcel_id": self.id,
            "weight": self.weight,
            "dimension": self.dimension,
            "fragile": self.fragile
        }


    def verify_handover(self):
        # Logic to verify the handover of the parcel
        pass

