class Parcel: 
    def __init__(self, parcel_id, weight, dimension, fragile):
        self.id = parcel_id
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
#Responsibilities of parcel

