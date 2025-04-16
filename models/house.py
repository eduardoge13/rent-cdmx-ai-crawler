from pydantic import BaseModel


class House(BaseModel):
    """
    Represents the data structure of a House.
    """

    Address: str
    Price: int
    Rooms: int
    Neighborhood: str
    City_Province: str
    Square_foot_units_square_meters: int
    Commodities: str
