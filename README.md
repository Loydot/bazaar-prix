# Bazaar — collecteur de prix

Ce dépôt relève les prix du marché de Warframe toutes les six heures et publie
le résultat dans un seul fichier JSON.

**Le fichier :** https://loydot.github.io/bazaar-prix/prix.json

## Pourquoi

[Bazaar](https://www.overwolf.com/) classe les objets de Warframe par ce qu'ils
rapportent réellement — le prix multiplié par le nombre de ventes par jour.
Pour ça, il lui faut le marché en entier.

Sans ce dépôt, chaque installation de l'application interrogerait
warframe.market de son côté. À dix utilisateurs c'est sans importance ; à dix
mille, c'est exactement ce que leurs limites de débit cherchent à éviter.

Une seule machine fait donc le relevé, et tout le monde télécharge le même
fichier en une requête.

## Le format

```json
{
  "stamp": "2026-08-26T09:00:00Z",
  "source": "warframe.market",
  "note": "prix median et ventes par jour, ventes conclues sur 48 h",
  "prix": {
    "ash_prime_set": [95.0, 41.2]
  }
}
```

Chaque entrée est `[prix médian, ventes par jour]`, calculée sur les ventes
conclues des 48 dernières heures. Environ 3 800 objets, une centaine de
kilo-octets.

Servez-vous : si vous écrivez un outil pour Warframe, ce fichier vous évite de
refaire le relevé.

## Les règles de warframe.market, respectées

- cadence tenue sous 3 requêtes par seconde (l'écart est fixé à 350 ms) ;
- `User-Agent` dédié, qui dit qui appelle et donne une adresse de contact ;
- reprise progressive en cas d'erreur 429 ;
- aucune donnée de compte, aucune annonce individuelle — uniquement des
  agrégats déjà publics.

## Faire tourner le relevé chez soi

```bash
python collecteur.py                    # catalogue complet, ~20 minutes
python collecteur.py --sortie /tmp/p.json
```

Aucune dépendance : la bibliothèque standard suffit.

## Ce qu'il y a dans le dépôt

| | |
|---|---|
| `collecteur.py` | le relevé |
| `.github/workflows/prix.yml` | la tâche planifiée, toutes les 6 h |
| `docs/prix.json` | le fichier produit, servi par GitHub Pages |

> GitHub met en sommeil les tâches planifiées d'un dépôt resté 60 jours sans
> activité. Ici les commits du collecteur suffisent à le tenir éveillé.

## Licence

Le code est sous licence MIT. Les données viennent de warframe.market et
appartiennent à leur communauté ; Warframe est une marque de Digital Extremes.
Ce projet n'est affilié ni à l'un ni à l'autre.
