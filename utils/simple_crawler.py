# simple_crawler.py - Version compatible avec Crawl4AI 0.6

import asyncio
import json
import time
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai import LLMConfig  # Import ajouté pour v0.6
from dotenv import load_dotenv
import os
import csv

load_dotenv()

# Configuration
BASE_URL = "https://vivatechnology.com/partners"  # Remplacez par votre URL
OUTPUT_FILE = f"exposants_simple_{int(time.time())}.csv"

# Modèle simple des données
EXPOSANT_FIELDS = [
    "nom_entreprise",
    "secteur_activite", 
    "pays",
    "ville",
    "emplacement",
    "jours_presences",
    "startup",
    "tags",
    "description"
]


async def simple_crawl_with_llm():
    """
    Version simplifiée qui utilise uniquement LLM pour l'extraction.
    Compatible avec Crawl4AI 0.6
    """
    print("=== Crawler simplifié avec LLM ===")
    
    # Configuration du navigateur
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=False,  # Mettre True pour plus rapide
        verbose=True,
        viewport_width=1920,
        viewport_height=1080,
    )
    
    # Configuration LLM pour v0.6
    llm_config = LLMConfig(
        provider="groq/deepseek-r1-distill-llama-70b",
        api_token=os.getenv("GROQ_API_KEY"),
    )
    
    # Configuration LLM
    llm_strategy = LLMExtractionStrategy(
        llm_config=llm_config,  # Utiliser llm_config au lieu de provider et api_token
        schema={
            "type": "object",
            "properties": {
                "exposants": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nom_entreprise": {"type": "string"},
                            "secteur_activite": {"type": "string"},
                            "pays": {"type": "string"},
                            "ville": {"type": "string"},
                            "emplacement": {"type": "string"},
                            "jours_presences": {"type": "string"},
                            "startup": {"type": "string"},
                            "tags": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                }
            }
        },
        extraction_type="schema",
        instruction="""
        Extraire TOUS les exposants/entreprises visibles sur cette page.
        Pour chaque entreprise, récupérer :
        - nom_entreprise : le nom de l'entreprise
        - secteur_activite : le secteur principal d'activité
        - pays : le pays d'origine
        - ville : la ville
        - emplacement : numéro de stand ou emplacement
        - jours_presences : jours de présence au salon
        - startup : "oui" si c'est une startup, "non" sinon
        - tags : mots-clés ou sous-secteurs
        - description : description courte de l'entreprise
        
        Si une information n'est pas disponible, mettre "N/A".
        Extraire le maximum d'entreprises possible de la page.
        """,
        input_format="html",
        verbose=True,
    )
    
    session_id = "simple_crawl_session"
    all_exposants = []
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"Accès à {BASE_URL}...")
        
        # Première extraction
        result = await crawler.arun(
            url=BASE_URL,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=llm_strategy,
                session_id=session_id,
            ),
        )
        
        if result.success and result.extracted_content:
            try:
                extracted_data = json.loads(result.extracted_content)
                exposants_data = extracted_data.get("exposants", [])
                
                print(f"✅ Première extraction: {len(exposants_data)} exposants trouvés")
                
                # Nettoyer et valider les données
                for exp in exposants_data:
                    clean_exp = {}
                    for field in EXPOSANT_FIELDS:
                        value = exp.get(field, "N/A")
                        clean_exp[field] = str(value).strip() if value else "N/A"
                    
                    # Vérifier que l'exposant a au moins un nom
                    if clean_exp["nom_entreprise"] and clean_exp["nom_entreprise"] != "N/A":
                        all_exposants.append(clean_exp)
                
                print(f"✅ Exposants valides: {len(all_exposants)}")
                
            except json.JSONDecodeError as e:
                print(f"❌ Erreur parsing JSON: {e}")
                print(f"Contenu brut: {result.extracted_content[:500]}...")
        
        else:
            print(f"❌ Échec extraction: {result.error_message if result else 'Pas de réponse'}")
    
    # Sauvegarde
    if all_exposants:
        save_to_csv(all_exposants, OUTPUT_FILE)
        print(f"\n🎉 {len(all_exposants)} exposants sauvegardés dans {OUTPUT_FILE}")
        
        # Statistiques
        secteurs = {}
        for exp in all_exposants:
            secteur = exp.get("secteur_activite", "N/A")
            secteurs[secteur] = secteurs.get(secteur, 0) + 1
        
        print("\n📊 Top 5 secteurs:")
        for secteur, count in sorted(secteurs.items(), key=lambda x: x[1], reverse=True)[:5]:
            if secteur != "N/A":
                print(f"  - {secteur}: {count}")
    else:
        print("❌ Aucun exposant trouvé")
    
    # Afficher les stats LLM
    try:
        llm_strategy.show_usage()
    except:
        pass


async def analyze_page_structure():
    """
    Analyse la structure HTML de la page pour comprendre l'organisation.
    """
    print("=== Analyse de la structure de la page ===")
    
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=False,
        verbose=True,
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url=BASE_URL,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                session_id="analysis_session",
            ),
        )
        
        if result.success and result.cleaned_html:
            html = result.cleaned_html
            
            # Sauvegarder pour inspection manuelle
            with open("page_structure.html", "w", encoding="utf-8") as f:
                f.write(html)
            
            print(f"✅ Page analysée ({len(html)} caractères)")
            print("📄 Structure sauvegardée dans 'page_structure.html'")
            
            # Analyse automatique
            patterns = {
                "Divs": r'<div[^>]*>',
                "Spans": r'<span[^>]*>',
                "Classes avec 'company'": r'class="[^"]*company[^"]*"',
                "Classes avec 'card'": r'class="[^"]*card[^"]*"',
                "Classes avec 'item'": r'class="[^"]*item[^"]*"',
                "Attributs data-*": r'data-[^=]+="[^"]*"',
                "IDs": r'id="[^"]*"',
            }
            
            print("\n📊 Éléments détectés:")
            for name, pattern in patterns.items():
                matches = len(re.findall(pattern, html, re.IGNORECASE))
                if matches > 0:
                    print(f"  - {name}: {matches}")
            
            # Chercher des patterns de noms d'entreprises
            potential_companies = re.findall(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', html)
            if potential_companies:
                print(f"\n🏢 Titres potentiels d'entreprises trouvés: {len(potential_companies)}")
                for i, company in enumerate(potential_companies[:5]):
                    print(f"  {i+1}. {company.strip()}")
                if len(potential_companies) > 5:
                    print(f"  ... et {len(potential_companies) - 5} autres")
        
        else:
            print(f"❌ Impossible d'accéder à la page: {result.error_message if result else 'Erreur inconnue'}")


def save_to_csv(exposants, filename):
    """Sauvegarde les exposants dans un fichier CSV."""
    if not exposants:
        return
    
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=EXPOSANT_FIELDS)
        writer.writeheader()
        writer.writerows(exposants)


async def main():
    """Point d'entrée principal."""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "analyze":
            await analyze_page_structure()
        elif sys.argv[1] == "test":
            await analyze_page_structure()
        else:
            print("Commandes disponibles:")
            print("  python simple_crawler.py analyze  - Analyser la structure")
            print("  python simple_crawler.py         - Lancer le crawl")
    else:
        await simple_crawl_with_llm()


if __name__ == "__main__":
    asyncio.run(main())