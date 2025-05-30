import json
import os
import asyncio
from typing import List, Set, Tuple

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
    LLMConfig,  # Import ajouté pour v0.6
)
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from models.exposant import exposant
from utils.data_utils import is_complete_exposant, is_duplicate_exposant
from config import CSS_SELECTORS, SCROLL_CONFIG


def get_browser_config() -> BrowserConfig:
    """
    Returns the browser configuration for the crawler.
    """
    return BrowserConfig(
        browser_type="chromium",
        headless=False,  # Garder False pour voir le scroll en action
        verbose=True,
        viewport_width=1920,
        viewport_height=1080,
    )


def get_css_extraction_strategy() -> JsonCssExtractionStrategy:
    """
    Configuration pour extraire les données via CSS au lieu de LLM.
    Plus rapide et plus précis pour des structures HTML fixes.
    """
    schema = {
        "name": "exposants",
        "baseSelector": "div[data-exposant]",  # Ajustez selon votre HTML
        "fields": [
            {
                "name": "nom_entreprise",
                "selector": "h2, h3, .company-name",  # Ajustez selon votre structure
                "type": "text"
            },
            {
                "name": "secteur_activite", 
                "selector": CSS_SELECTORS["secteur"],
                "type": "text"
            },
            {
                "name": "pays",
                "selector": CSS_SELECTORS["pays"],
                "type": "text"
            },
            {
                "name": "ville",
                "selector": CSS_SELECTORS["ville"], 
                "type": "text"
            },
            {
                "name": "emplacement",
                "selector": CSS_SELECTORS["emplacement"],
                "type": "text"
            },
            {
                "name": "jours_presences",
                "selector": CSS_SELECTORS["jours"],
                "type": "text"
            },
            {
                "name": "startup",
                "selector": CSS_SELECTORS["startup"],
                "type": "text"
            },
            {
                "name": "description",
                "selector": CSS_SELECTORS["description"],
                "type": "text"
            },
            {
                "name": "tags",
                "selector": CSS_SELECTORS["sous_secteur"],
                "type": "text"
            }
        ]
    }
    
    return JsonCssExtractionStrategy(schema)


def get_llm_strategy() -> LLMExtractionStrategy:
    """
    Configuration LLM comme fallback ou alternative.
    Syntaxe mise à jour pour Crawl4AI 0.6
    """
    # Configuration LLM pour v0.6
    llm_config = LLMConfig(
        provider="groq/deepseek-r1-distill-llama-70b",
        api_token=os.getenv("GROQ_API_KEY"),
    )
    
    return LLMExtractionStrategy(
        llm_config=llm_config,  # Utiliser llm_config au lieu de provider et api_token
        schema=exposant.model_json_schema(),
        extraction_type="schema",
        instruction=(
            "Extraire tous les exposants avec leurs informations : nom d'entreprise, "
            "secteur d'activité, pays, ville, emplacement, jours de présence, "
            "statut startup, tags/sous-secteurs, et description."
        ),
        input_format="html",
        verbose=True,
    )


async def scroll_and_load_content(
    crawler: AsyncWebCrawler,
    url: str,
    session_id: str
) -> str:
    """
    Scroll la page pour charger tout le contenu dynamique.
    Compatible avec Crawl4AI 0.6
    
    Returns:
        str: Le HTML complet après tous les scrolls
    """
    print("Démarrage du scroll pour charger le contenu...")
    
    # Première visite de la page pour initialiser
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id=session_id,
        ),
    )
    
    if not result.success:
        print(f"Erreur lors de l'accès initial: {result.error_message}")
        return ""
    
    # Simulation manuelle du scroll avec des requêtes multiples
    print("Simulation du scroll avec attentes...")
    
    max_attempts = SCROLL_CONFIG["max_scrolls"]
    pause_time = SCROLL_CONFIG["scroll_pause_time"]
    
    for attempt in range(max_attempts):
        print(f"Tentative {attempt + 1}/{max_attempts}")
        
        # Pause pour laisser le temps au contenu de se charger
        await asyncio.sleep(pause_time)
        
        # Nouvelle requête pour récupérer le contenu mis à jour
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                session_id=session_id,
            ),
        )
        
        if not result.success:
            print(f"Erreur tentative {attempt + 1}: {result.error_message}")
            continue
            
        # On garde le dernier résultat valide
        if result.cleaned_html:
            print(f"Contenu récupéré: {len(result.cleaned_html)} caractères")
    
    print("Simulation de scroll terminée.")
    return result.cleaned_html if result.success else ""


async def extract_all_exposants(
    crawler: AsyncWebCrawler,
    url: str,
    session_id: str,
    extraction_strategy,
    required_keys: List[str],
    seen_names: Set[str],
) -> List[dict]:
    """
    Extrait tous les exposants après avoir scrollé pour charger le contenu.
    """
    print("Extraction des exposants avec scroll infini...")
    
    # D'abord, scroll pour charger tout le contenu
    await scroll_and_load_content(crawler, url, session_id)
    
    # Ensuite, extraire les données
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
            session_id=session_id,
        ),
    )
    
    if not (result.success and result.extracted_content):
        print(f"Erreur lors de l'extraction: {result.error_message}")
        return []
    
    # Parser le contenu extrait
    try:
        extracted_data = json.loads(result.extracted_content)
        print(f"Données extraites brutes: {len(extracted_data)} éléments")
    except json.JSONDecodeError as e:
        print(f"Erreur de parsing JSON: {e}")
        return []
    
    # Traiter les exposants
    complete_exposants = []
    for exposant_data in extracted_data:
        print(f"Traitement exposant: {exposant_data}")
        
        # Nettoyer les données
        clean_exposant = {}
        for key, value in exposant_data.items():
            if value and str(value).strip():
                clean_exposant[key] = str(value).strip()
        
        # Vérifier si l'exposant est complet
        if not is_complete_exposant(clean_exposant, required_keys):
            print(f"Exposant incomplet ignoré: {clean_exposant}")
            continue
        
        # Vérifier les doublons
        exposant_name = clean_exposant.get("nom_entreprise", "")
        if is_duplicate_exposant(exposant_name, seen_names):
            print(f"Doublon ignoré: {exposant_name}")
            continue
        
        # Ajouter à la liste
        seen_names.add(exposant_name)
        complete_exposants.append(clean_exposant)
        print(f"Exposant ajouté: {exposant_name}")
    
    print(f"Total exposants valides extraits: {len(complete_exposants)}")
    return complete_exposants


async def get_total_exposants_count(
    crawler: AsyncWebCrawler,
    url: str,
    session_id: str
) -> int:
    """
    Tente de récupérer le nombre total d'exposants affichés sur la page.
    Version pour Crawl4AI 0.6
    """
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id=session_id,
        ),
    )
    
    if result.success and result.cleaned_html:
        # Estimation basique du nombre d'éléments potentiels
        import re
        html = result.cleaned_html
        
        # Patterns pour détecter les cartes d'exposants
        patterns = [
            r'class="[^"]*company[^"]*"',
            r'class="[^"]*card[^"]*"',
            r'class="[^"]*exposant[^"]*"',
            r'class="[^"]*enterprise[^"]*"',
            r'data-[^=]*="[^"]*company[^"]*"'
        ]
        
        max_count = 0
        for pattern in patterns:
            matches = len(re.findall(pattern, html, re.IGNORECASE))
            if matches > max_count:
                max_count = matches
        
        print(f"Estimation basée sur l'HTML: ~{max_count} éléments détectés")
        return max_count
    
    return 0