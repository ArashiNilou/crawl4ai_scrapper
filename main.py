import asyncio
import time

from crawl4ai import AsyncWebCrawler
from dotenv import load_dotenv

from config import BASE_URL, REQUIRED_KEYS
from utils.data_utils import save_exposants_to_csv
from utils.scraper_utils import (
    get_browser_config,
    get_css_extraction_strategy,
    get_llm_strategy,
    extract_all_exposants,
    get_total_exposants_count
)

load_dotenv()


async def crawl_exposants_infinite_scroll():
    """
    Fonction principale pour crawler les exposants avec scroll infini.
    """
    print("=== Démarrage du crawler d'exposants avec scroll infini ===")
    
    # Configuration
    browser_config = get_browser_config()
    
    # Stratégie d'extraction (CSS par défaut, LLM en fallback)
    css_strategy = get_css_extraction_strategy()
    llm_strategy = get_llm_strategy()
    
    session_id = "exposant_infinite_scroll_session"
    seen_names = set()
    
    start_time = time.time()
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            # Étape 1: Obtenir une estimation du nombre total
            print("Étape 1: Estimation du nombre total d'exposants...")
            total_estimate = await get_total_exposants_count(crawler, BASE_URL, session_id)
            print(f"Estimation: ~{total_estimate} exposants détectés")
            
            # Étape 2: Extraction avec CSS
            print("\nÉtape 2: Extraction avec stratégie CSS...")
            exposants_css = await extract_all_exposants(
                crawler, BASE_URL, session_id, css_strategy, 
                REQUIRED_KEYS, seen_names.copy()
            )
            
            # Étape 3: Extraction avec LLM si CSS n'a pas bien fonctionné
            exposants_llm = []
            if len(exposants_css) < total_estimate * 0.5:  # Si moins de 50% récupérés
                print("\nÉtape 3: Extraction avec stratégie LLM (fallback)...")
                exposants_llm = await extract_all_exposants(
                    crawler, BASE_URL, session_id, llm_strategy, 
                    REQUIRED_KEYS, seen_names.copy()
                )
            
            # Étape 4: Combiner les résultats
            print("\nÉtape 4: Combinaison des résultats...")
            all_exposants = combine_results(exposants_css, exposants_llm, seen_names)
            
        except Exception as e:
            print(f"Erreur lors du crawling: {e}")
            return
    
    # Étape 5: Sauvegarde
    end_time = time.time()
    duration = end_time - start_time
    
    if all_exposants:
        filename = f"exposants_scroll_{int(time.time())}.csv"
        save_exposants_to_csv(all_exposants, filename)
        
        print(f"\n=== RÉSULTATS ===")
        print(f"✅ {len(all_exposants)} exposants extraits et sauvegardés")
        print(f"📁 Fichier: {filename}")
        print(f"⏱️  Durée: {duration:.1f} secondes")
        print(f"📊 Taux de réussite: {len(all_exposants)}/{total_estimate} ({len(all_exposants)/max(total_estimate,1)*100:.1f}%)")
        
        # Statistiques détaillées
        print(f"\n=== STATISTIQUES ===")
        secteurs = {}
        pays = {}
        for exp in all_exposants:
            secteur = exp.get('secteur_activite', 'N/A')
            secteurs[secteur] = secteurs.get(secteur, 0) + 1
            
            pays_exp = exp.get('pays', 'N/A') 
            pays[pays_exp] = pays.get(pays_exp, 0) + 1
        
        print(f"Top 5 secteurs:")
        for secteur, count in sorted(secteurs.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {secteur}: {count}")
            
        print(f"Top 5 pays:")
        for pays_name, count in sorted(pays.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {pays_name}: {count}")
            
    else:
        print("❌ Aucun exposant n'a été trouvé")
        print("Vérifiez:")
        print("1. L'URL dans config.py")
        print("2. Les sélecteurs CSS dans config.py")
        print("3. La structure HTML du site")
    
    # Afficher les statistiques LLM si utilisé
    if 'llm_strategy' in locals():
        try:
            llm_strategy.show_usage()
        except:
            pass


def combine_results(css_results: list, llm_results: list, seen_names: set) -> list:
    """
    Combine les résultats des deux stratégies d'extraction.
    """
    print(f"Combinaison: {len(css_results)} (CSS) + {len(llm_results)} (LLM)")
    
    # Commencer avec les résultats CSS
    combined = css_results.copy()
    seen_names.update(exp.get('nom_entreprise', '') for exp in css_results)
    
    # Ajouter les résultats LLM uniques
    added_from_llm = 0
    for exp in llm_results:
        name = exp.get('nom_entreprise', '')
        if name and name not in seen_names:
            combined.append(exp)
            seen_names.add(name)
            added_from_llm += 1
    
    print(f"Résultat final: {len(combined)} exposants ({added_from_llm} ajoutés par LLM)")
    return combined


async def test_scroll_only():
    """
    Fonction de test pour vérifier l'accès au site.
    Version simplifiée pour Crawl4AI 0.4.247
    """
    print("=== TEST: Accès au site et analyse du contenu ===")
    
    browser_config = get_browser_config()
    session_id = "test_session"
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url=BASE_URL,
            config=CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                session_id=session_id,
            ),
        )
        
        if result.success and result.cleaned_html:
            html_content = result.cleaned_html
            print(f"✅ Accès réussi, HTML récupéré ({len(html_content)} caractères)")
            
            # Sauvegarder pour inspection
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("🔍 Page sauvegardée dans 'debug_page.html' pour inspection")
            
            # Analyser la structure
            import re
            
            # Chercher différents patterns d'éléments
            analysis = {
                "Divs avec class": len(re.findall(r'<div[^>]+class="[^"]*"', html_content)),
                "Spans avec class": len(re.findall(r'<span[^>]+class="[^"]*"', html_content)),
                "Éléments avec 'company'": len(re.findall(r'class="[^"]*company[^"]*"', html_content, re.IGNORECASE)),
                "Éléments avec 'card'": len(re.findall(r'class="[^"]*card[^"]*"', html_content, re.IGNORECASE)),
                "Éléments avec 'exposant'": len(re.findall(r'class="[^"]*exposant[^"]*"', html_content, re.IGNORECASE)),
                "Attributs data-*": len(re.findall(r'data-[^=]+="[^"]*"', html_content)),
            }
            
            print("\n📊 Analyse de la structure HTML:")
            for element, count in analysis.items():
                if count > 0:
                    print(f"  - {element}: {count}")
            
            # Suggestions de sélecteurs
            print("\n💡 Suggestions pour améliorer les sélecteurs CSS:")
            print("1. Inspectez 'debug_page.html' dans un navigateur")
            print("2. Recherchez les patterns récurrents autour des noms d'entreprises")
            print("3. Mettez à jour CSS_SELECTORS dans config.py")
            
        else:
            print(f"❌ Échec de l'accès au site: {result.error_message if result else 'Pas de réponse'}")
            print("Vérifiez l'URL dans config.py")


async def main():
    """
    Point d'entrée principal.
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        await test_scroll_only()
    else:
        await crawl_exposants_infinite_scroll()


if __name__ == "__main__":
    asyncio.run(main())