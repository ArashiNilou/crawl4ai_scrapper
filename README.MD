# Configuration et utilisation du crawler scroll infini

## 🔧 Étapes de configuration

### 1. Mise à jour de config.py
```python
# Remplacez par votre vraie URL
BASE_URL = "https://votre-site-exposants.com"
```

### 2. Ajustement des sélecteurs CSS
Basé sur votre image, vous devez identifier les sélecteurs exacts. Voici comment procéder :

**Méthode A: Inspection manuelle**
1. Ouvrez votre site dans Chrome/Firefox
2. Clic droit sur un nom d'entreprise → "Inspecter l'élément"
3. Notez le sélecteur CSS exact
4. Répétez pour chaque champ (secteur, pays, ville, etc.)

**Méthode B: Test automatique des sélecteurs**
```bash
python main.py test
```
Cela va faire le scroll et compter les éléments détectés.

### 3. Mise à jour des sélecteurs dans config.py
```python
CSS_SELECTORS = {
    "container": "div.exposant-card",  # Conteneur de chaque exposant
    "nom_entreprise": "h2.company-name, h3.title",  # Nom de l'entreprise
    "secteur": "span.p-0.flex-1",  # Comme dans votre image
    "pays": ".text-sm span:nth-of-type(2)",  # À ajuster
    "ville": "div:nth-of-type(3) p.text-xl",  # À ajuster
    # ... autres sélecteurs
}
```

## 🚀 Utilisation

### Lancement standard
```bash
python main.py
```

### Test du scroll uniquement
```bash
python main.py test
```

### Avec debug détaillé
Modifiez `headless=False` dans `get_browser_config()` pour voir le navigateur en action.

## 📋 Processus du crawler

1. **Initialisation** : Ouvre le navigateur et charge la page
2. **Scroll infini** : Scroll automatique jusqu'à charger tout le contenu
3. **Extraction CSS** : Utilise les sélecteurs CSS pour extraire rapidement
4. **Extraction LLM** : Fallback avec intelligence artificielle si nécessaire
5. **Déduplication** : Supprime les doublons
6. **Sauvegarde** : Export en CSV avec timestamp

## 🔍 Diagnostic des problèmes

### Si aucun exposant n'est trouvé :

1. **Vérifiez l'URL**
   ```python
   BASE_URL = "https://votre-vraie-url.com"
   ```

2. **Testez les sélecteurs CSS**
   - Ouvrez la console du navigateur sur votre site
   - Testez : `document.querySelectorAll("votre-selecteur")`
   - Doit retourner les éléments attendus

3. **Vérifiez la structure HTML**
   - Le contenu se charge-t-il vraiment par scroll ?
   - Y a-t-il des attributs `data-*` spécifiques ?

4. **Ajustez le timing du scroll**
   ```python
   SCROLL_CONFIG = {
       "scroll_pause_time": 5,  # Plus lent si le site est lent
       "max_scrolls": 100,      # Plus de scrolls si beaucoup de contenu
   }
   ```

### Si le scroll ne fonctionne pas :

1. **Vérifiez les triggers JavaScript**
   - Certains sites nécessitent des clics ou hover
   - Modifiez le script de scroll dans `scroll_and_load_content()`

2. **Testez avec headless=False**
   - Observez le comportement du scroll
   - Vérifiez si de nouveaux éléments apparaissent

## 📊 Optimisations possibles

### Pour de gros volumes (>1000 exposants) :
```python
# Dans config.py
SCROLL_CONFIG = {
    "scroll_pause_time": 1,  # Plus rapide
    "max_scrolls": 200,
    "scroll_height": 2000,   # Scrolls plus grands
}
```

### Pour des sites lents :
```python
SCROLL_CONFIG = {
    "scroll_pause_time": 5,  # Plus lent
    "no_new_content_limit": 5,  # Plus patient
}
```

## 🐛 Debug avancé

### Logs détaillés
Tous les `print()` montrent le progression. Cherchez :
- "Scroll terminé, contenu chargé"
- "Données extraites brutes: X éléments" 
- "Exposant ajouté: [nom]"

### Inspection du HTML
```python
# Ajoutez dans extract_all_exposants() après le scroll :
with open("debug_html.html", "w", encoding="utf-8") as f:
    f.write(result.cleaned_html)
```

### Test des sélecteurs un par un
```python
# Test individual des sélecteurs
test_selectors = {
    "nom": "h2, h3, .company-name",
    "secteur": "span.p-0.flex-1",
}

for name, selector in test_selectors.items():
    elements = await crawler.arun(
        url=BASE_URL,
        config=CrawlerRunConfig(
            css_selector=selector,
            cache_mode=CacheMode.BYPASS,
        )
    )
    print(f"{name}: {len(elements)} éléments trouvés")
```

## 📄 Format de sortie

Le CSV contiendra :
- `nom_entreprise` : Nom de l'entreprise
- `secteur_activite` : Secteur principal  
- `pays` : Pays d'origine
- `ville` : Ville
- `emplacement` : Stand/emplacement
- `jours_presences` : Jours de présence
- `startup` : Statut startup (oui/non)
- `tags` : Tags/sous-secteurs
- `description` : Description de l'entreprise

## 🔄 Prochaines étapes

1. **Configurez votre URL** dans `config.py`
2. **Identifiez vos sélecteurs CSS** précis
3. **Testez avec** `python main.py test`
4. **Ajustez les sélecteurs** si nécessaire
5. **Lancez le crawl complet** avec `python main.py`

N'hésitez pas si vous avez des questions sur l'adaptation à votre site spécifique !