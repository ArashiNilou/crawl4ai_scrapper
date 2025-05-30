from pydantic import BaseModel


class exposant(BaseModel):
    """
    Represents the data structure of a exposant.
    """

    nom_entreprise: str
    secteur_activite: str
    tags: str
    startup: str
    pays: str
    ville: str
    emplacement: str
    jours_presences: str
    description: str