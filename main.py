import asyncio
import time
import re
import json
import sys

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig
from dotenv import load_dotenv

from config import BASE_URL, REQUIRED_KEYS, SCROLL_CONFIG
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
    Version adaptée pour Crawl4AI 0.6
    """
    print("=== Démarrage du crawler d'exposants avec scroll infini ===")
    print(f"URL cible: {BASE_URL}")
    
    # Configuration
    browser_config = get_browser_config()
    
    # Stratégie d'extraction (CSS par défaut, LLM en fallback)
    try:
        css_strategy = get_css_extraction_strategy()
        llm_strategy = get_llm_strategy()
    except Exception as e:
        print(f"Erreur lors de la configuration des stratégies: {e}")
        return
    
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
            if len(exposants_css) < max(total_estimate * 0.3, 5):  # Si moins de 30% récupérés ou moins de 5
                print(f"\nÉtape 3: Extraction avec stratégie LLM (fallback)...")
                print(f"CSS a récupéré {len(exposants_css)} exposants sur {total_estimate} estimés")
                try:
                    exposants_llm = await extract_all_exposants(
                        crawler, BASE_URL, session_id, llm_strategy, 
                        REQUIRED_KEYS, seen_names.copy()
                    )
                except Exception as e:
                    print(f"Erreur avec stratégie LLM: {e}")
                    exposants_llm = []
            else:
                print(f"\nÉtape 3: Extraction CSS suffisante ({len(exposants_css)} exposants), LLM non nécessaire")
            
            # Étape 4: Combiner les résultats
            print("\nÉtape 4: Combinaison des résultats...")
            all_exposants = combine_results(exposants_css, exposants_llm, seen_names)
            
        except Exception as e:
            print(f"Erreur lors du crawling: {e}")
            print(f"Type d'erreur: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return
    
    # Étape 5: Sauvegarde et statistiques
    end_time = time.time()
    duration = end_time - start_time
    
    if all_exposants:
        filename = f"exposants_scroll_{int(time.time())}.csv"
        save_exposants_to_csv(all_exposants, filename)
        
        print(f"\n=== RÉSULTATS ===")
        print(f"✅ {len(all_exposants)} exposants extraits et sauvegardés")
        print(f"📁 Fichier: {filename}")
        print(f"⏱️  Durée: {duration:.1f} secondes")
        print(f"📊 Taux de réussite: {len(all_exposants)}/{max(total_estimate, 1)} ({len(all_exposants)/max(total_estimate,1)*100:.1f}%)")
        
        # Statistiques détaillées
        print_statistics(all_exposants)
        
    else:
        print("❌ Aucun exposant n'a été trouvé")
        print("\n🔧 Suggestions de diagnostic:")
        print("1. Vérifiez l'URL dans config.py")
        print("2. Vérifiez les sélecteurs CSS dans config.py")
        print("3. Lancez 'python main.py test' pour analyser la structure HTML")
        print("4. Vérifiez que le site est accessible et ne nécessite pas d'authentification")
    
    # Afficher les statistiques LLM si utilisé
    if exposants_llm:
        try:
            if hasattr(llm_strategy, 'show_usage'):
                llm_strategy.show_usage()
        except Exception as e:
            print(f"Impossible d'afficher les stats LLM: {e}")


def combine_results(css_results: list, llm_results: list, seen_names: set) -> list:
    """
    Combine les résultats des deux stratégies d'extraction.
    """
    print(f"Combinaison: {len(css_results)} (CSS) + {len(llm_results)} (LLM)")
    
    # Commencer avec les résultats CSS
    combined = css_results.copy()
    seen_names.update(exp.get('nom_entreprise', '') for exp in css_results if exp.get('nom_entreprise'))
    
    # Ajouter les résultats LLM uniques
    added_from_llm = 0
    for exp in llm_results:
        name = exp.get('nom_entreprise', '').strip()
        if name and name not in seen_names:
            combined.append(exp)
            seen_names.add(name)
            added_from_llm += 1
    
    print(f"Résultat final: {len(combined)} exposants ({added_from_llm} ajoutés par LLM)")
    return combined


def print_statistics(exposants: list):
    """
    Affiche des statistiques détaillées sur les exposants extraits.
    """
    print(f"\n=== STATISTIQUES DÉTAILLÉES ===")
    
    # Statistiques par secteur
    secteurs = {}
    pays = {}
    villes = {}
    startups = {"oui": 0, "non": 0, "N/A": 0}
    
    for exp in exposants:
        # Secteurs
        secteur = exp.get('secteur_activite', 'N/A').strip()
        if secteur:
            secteurs[secteur] = secteurs.get(secteur, 0) + 1
        
        # Pays
        pays_exp = exp.get('pays', 'N/A').strip()
        if pays_exp:
            pays[pays_exp] = pays.get(pays_exp, 0) + 1
        
        # Villes
        ville = exp.get('ville', 'N/A').strip()
        if ville:
            villes[ville] = villes.get(ville, 0) + 1
        
        # Startups
        startup_status = exp.get('startup', 'N/A').lower().strip()
        if startup_status in ['oui', 'yes', 'true', '1']:
            startups["oui"] += 1
        elif startup_status in ['non', 'no', 'false', '0']:
            startups["non"] += 1
        else:
            startups["N/A"] += 1
    
    # Affichage des top 5
    print(f"🏢 Top 5 secteurs:")
    for secteur, count in sorted(secteurs.items(), key=lambda x: x[1], reverse=True)[:5]:
        if secteur != 'N/A':
            print(f"  - {secteur}: {count}")
    
    print(f"\n🌍 Top 5 pays:")
    for pays_name, count in sorted(pays.items(), key=lambda x: x[1], reverse=True)[:5]:
        if pays_name != 'N/A':
            print(f"  - {pays_name}: {count}")
    
    print(f"\n🏙️ Top 5 villes:")
    for ville_name, count in sorted(villes.items(), key=lambda x: x[1], reverse=True)[:5]:
        if ville_name != 'N/A':
            print(f"  - {ville_name}: {count}")
    
    print(f"\n🚀 Statut startup:")
    for status, count in startups.items():
        if count > 0:
            print(f"  - {status.capitalize()}: {count}")


async def test_scroll_only():
    """
    Fonction de test pour vérifier l'accès au site et analyser la structure.
    Version complète pour Crawl4AI 0.6
    """
    print("=== TEST: Accès au site et analyse du contenu ===")
    print(f"URL testée: {BASE_URL}")
    
    browser_config = get_browser_config()
    session_id = "test_session"
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
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
                debug_filename = "debug_page.html"
                with open(debug_filename, "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"🔍 Page sauvegardée dans '{debug_filename}' pour inspection")
                
                # Analyser la structure
                analyze_html_structure(html_content)
                
                # Tester les sélecteurs CSS configurés
                print(f"\n=== TEST DES SÉLECTEURS CSS ===")
                test_css_selectors(html_content)
                
            else:
                print(f"❌ Échec de l'accès à la page")
                if result.error_message:
                    print(f"Erreur: {result.error_message}")
                else:
                    print("Aucun contenu HTML récupéré")
                
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            import traceback
            traceback.print_exc()


def analyze_html_structure(html_content: str):
    """
    Analyse la structure HTML pour identifier les patterns d'éléments.
    """
    print(f"\n=== ANALYSE DE LA STRUCTURE HTML ===")
    
    # Patterns pour détecter les éléments
    analysis_patterns = {
        "Divs avec class": r'<div[^>]+class="[^"]*"',
        "Spans avec class": r'<span[^>]+class="[^"]*"',
        "Éléments avec 'company'": r'class="[^"]*company[^"]*"',
        "Éléments avec 'card'": r'class="[^"]*card[^"]*"',
        "Éléments avec 'exposant'": r'class="[^"]*exposant[^"]*"',
        "Éléments avec 'partner'": r'class="[^"]*partner[^"]*"',
        "Attributs data-*": r'data-[^=]+="[^"]*"',
        "Titres H1-H6": r'<h[1-6][^>]*>([^<]+)</h[1-6]>',
        "Liens": r'<a[^>]+href="[^"]*"',
        "Images": r'<img[^>]+src="[^"]*"'
    }
    
    results = {}
    for name, pattern in analysis_patterns.items():
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        results[name] = len(matches)
        
        if name == "Titres H1-H6" and matches:
            # Afficher quelques exemples de titres
            print(f"\n📋 Exemples de titres trouvés:")
            for i, title in enumerate(matches[:5]):
                clean_title = title.strip()
                if clean_title:
                    print(f"  {i+1}. {clean_title}")
    
    print(f"\n📊 Éléments détectés dans la page:")
    for name, count in results.items():
        if count > 0 and name != "Titres H1-H6":
            print(f"  - {name}: {count}")
    
    # Recherche de structures répétitives
    print(f"\n🔍 Recherche de structures répétitives...")
    repetitive_classes = find_repetitive_classes(html_content)
    if repetitive_classes:
        print("Classes qui apparaissent fréquemment (potentielles cartes d'exposants):")
        for class_name, count in repetitive_classes[:10]:
            print(f"  - '{class_name}': {count} occurrences")


def find_repetitive_classes(html_content: str) -> list:
    """
    Trouve les classes CSS qui apparaissent fréquemment dans le HTML.
    """
    # Extraire toutes les classes
    class_pattern = r'class="([^"]*)"'
    all_classes = re.findall(class_pattern, html_content)
    
    # Compter les occurrences de chaque classe individuelle
    class_counts = {}
    for class_attr in all_classes:
        individual_classes = class_attr.split()
        for cls in individual_classes:
            if cls and len(cls) > 2:  # Ignorer les classes très courtes
                class_counts[cls] = class_counts.get(cls, 0) + 1
    
    # Retourner les classes les plus fréquentes (potentielles cartes)
    return sorted(class_counts.items(), key=lambda x: x[1], reverse=True)


def test_css_selectors(html_content: str):
    """
    Teste les sélecteurs CSS configurés sur le HTML récupéré.
    """
    from config import CSS_SELECTORS
    
    # Simulation simple des sélecteurs CSS avec regex
    # Note: Ce n'est pas parfait mais donne une idée
    
    selector_tests = {
        "secteur": CSS_SELECTORS.get("secteur", ""),
        "pays": CSS_SELECTORS.get("pays", ""),
        "ville": CSS_SELECTORS.get("ville", ""),
        "container": CSS_SELECTORS.get("container", "")
    }
    
    for name, selector in selector_tests.items():
        if selector:
            # Test basique avec regex (approximation)
            if "span" in selector and "p-0" in selector:
                pattern = r'<span[^>]*class="[^"]*p-0[^"]*"[^>]*>([^<]*)</span>'
            elif "div" in selector:
                pattern = r'<div[^>]*>([^<]*)</div>'
            elif "span" in selector:
                pattern = r'<span[^>]*>([^<]*)</span>'
            else:
                pattern = selector
            
            try:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                print(f"  - {name} ('{selector}'): {len(matches)} éléments potentiels")
                
                # Afficher quelques exemples
                if matches:
                    for i, match in enumerate(matches[:3]):
                        clean_match = match.strip()
                        if clean_match:
                            print(f"    Ex{i+1}: {clean_match}")
            except re.error:
                print(f"  - {name}: Sélecteur invalide pour test regex")


async def main():
    """
    Point d'entrée principal avec gestion des arguments.
    """
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            await test_scroll_only()
        elif command == "analyze":
            await test_scroll_only()  # Même fonction pour l'analyse
        elif command == "help":
            print_help()
        else:
            print(f"❌ Commande inconnue: {command}")
            print_help()
    else:
        # Lancement normal du crawler
        await crawl_exposants_infinite_scroll()


def print_help():
    """
    Affiche l'aide sur les commandes disponibles.
    """
    print("=== AIDE - Crawler d'exposants ===")
    print("Commandes disponibles:")
    print("  python main.py          - Lance le crawl complet")
    print("  python main.py test     - Teste l'accès et analyse la structure")
    print("  python main.py analyze  - Alias pour 'test'")
    print("  python main.py help     - Affiche cette aide")
    print("\nConfiguration:")
    print(f"  - URL cible: {BASE_URL}")
    print(f"  - Champs requis: {', '.join(REQUIRED_KEYS)}")
    print("\nFichiers de configuration:")
    print("  - config.py: URL et sélecteurs CSS")
    print("  - .env: Clés API (GROQ_API_KEY)")


if __name__ == "__main__":
    asyncio.run(main())