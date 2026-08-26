# bazaar-prix

Relève les prix du marché de Warframe toutes les 6 heures et les publie dans
un seul fichier :

https://loydot.github.io/bazaar-prix/prix.json

## Pourquoi

L'application Bazaar classe les objets par ce qu'ils rapportent vraiment,
c'est-à-dire le prix multiplié par le nombre de ventes par jour. Pour ça il
lui faut tout le marché, pas juste l'objet qu'on regarde.

Si chaque installation allait chercher ces prix de son côté, ça ferait des
milliers de requêtes en double sur warframe.market. Une seule machine fait
donc le relevé et tout le monde télécharge le même fichier.

## Le format

```json
{
  "stamp": "2026-08-26T08:34:56Z",
  "source": "warframe.market",
  "note": "prix median et ventes par jour, ventes conclues sur 48 h",
  "prix": {
    "ash_prime_set": [95.0, 41.2]
  }
}
```

Chaque entrée vaut `[prix médian, ventes par jour]`, calculé sur les ventes
conclues des 48 dernières heures. Environ 3 800 objets, une centaine de Ko.

Le fichier est produit pour l'application Bazaar et son format peut changer
sans préavis.

## Les règles de warframe.market

Le collecteur reste sous 3 requêtes par seconde (350 ms entre chaque), envoie
un User-Agent qui dit qui appelle et où le joindre, et ralentit tout seul en
cas d'erreur 429.

Il ne récupère aucune donnée de compte ni aucune annonce individuelle,
seulement des agrégats déjà publics.

## Faire tourner le relevé chez soi

```bash
python collecteur.py                    # tout le catalogue, ~35 minutes
python collecteur.py --sortie /tmp/p.json
```

Pas de dépendance, la bibliothèque standard suffit.

## Contenu du dépôt

`collecteur.py` fait le relevé. `.github/workflows/prix.yml` le lance toutes
les 6 heures. `docs/prix.json` est le fichier produit, servi par GitHub Pages.

Attention : GitHub met en sommeil les tâches planifiées d'un dépôt resté
60 jours sans activité. Ici les commits du collecteur suffisent à le tenir
réveillé.

## Licence

Code sous licence MIT. Les données viennent de warframe.market et
appartiennent à leur communauté. Warframe est une marque de Digital Extremes,
ce projet n'est affilié ni à l'un ni à l'autre.
