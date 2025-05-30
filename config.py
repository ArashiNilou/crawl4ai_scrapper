# config.py

# URL de base de votre site
BASE_URL = "https://vivatechnology.com/partners"  # Remplacez par votre URL

# Sélecteurs CSS basés sur votre image
CSS_SELECTORS = {
    "container": "div",  # Conteneur principal des exposants
    "secteur": "span.p-0.flex-1",
    "pays": ".text-sm.span:nth-of-type(2)",
    "ville": "div:nth-of-type(3) p.text-xl",
    "emplacement": "span.ml-1",
    "jours": "span.ml-1",
    "sous_secteur": "div.max-w-fit:nth-of-type(2) span, div.max-w-fit:nth-of-type(3) span, div.max-w-fit:nth-of-type(4) span",
    "startup": "span.capitalize",
    "description": "div.my-4"
}

# Champs requis pour considérer un exposant comme complet
REQUIRED_KEYS = [
    "nom_entreprise",
    "secteur_activite", 
    "pays",
    "ville"
]

# Configuration pour le scroll
SCROLL_CONFIG = {
    "scroll_pause_time": 10,  # Temps d'attente après chaque scroll (secondes)
    "max_scrolls": 100,       # Nombre maximum de scrolls
    "scroll_height": 1000,   # Hauteur de scroll en pixels
    "no_new_content_limit": 3  # Nombre de scrolls sans nouveau contenu avant d'arrêter
}