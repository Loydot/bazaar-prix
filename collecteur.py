#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collecteur de prix — a faire tourner AILLEURS que sur le PC des joueurs.

Pourquoi : sans lui, chaque utilisateur de l'application interroge
warframe.market de son cote. A dix utilisateurs c'est sans importance, a dix
mille c'est exactement ce que leurs limites de debit cherchent a eviter. Une
seule machine fait le releve, tout le monde telecharge le resultat.

Ce script produit UN fichier `prix.json` :

    {"stamp": "2026-08-25T20:00:00Z",
     "source": "warframe.market",
     "prix": {"ash_prime_set": [95.0, 41.2], ...}}   # [prix median, ventes/j]

Duree : une trentaine de minutes pour le catalogue complet, la cadence etant
volontairement tenue sous la limite de 3 requetes/seconde. Sur un runner
GitHub, dont l'adresse est partagee, compter un peu plus.

Usage :
    python collecteur.py            # catalogue complet
    python collecteur.py --rapide   # uniquement la route groupee (742 Primes)
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

V1 = "https://api.warframe.market/v1"
V2 = "https://api.warframe.market/v2"
UA = {
    # Identification demandee par leurs regles : qui appelle, et pourquoi.
    "User-Agent": "Bazaar-collector/1.0 (collecteur de prix communautaire; "
                  "+https://github.com/Loydot/bazaar-prix)",
    "Platform": "pc",
    "Language": "en",
}
ECART = 0.35            # ~2,85 requetes/seconde, sous la limite de 3
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prix.json")

_dernier = [0.0]


def _cadence():
    """Tient l'ecart minimum entre deux requetes. Jamais de rafale."""
    attente = ECART - (time.time() - _dernier[0])
    if attente > 0:
        time.sleep(attente)
    _dernier[0] = time.time()


def _get(url, essais=4):
    for essai in range(essais):
        _cadence()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 and essai < essais - 1:
                # trop rapide a leur gout : on laisse retomber avant de reessayer
                time.sleep(2.0 * (essai + 1))
                continue
            raise
        except Exception:
            if essai == essais - 1:
                raise
            time.sleep(1.5 * (essai + 1))
    return None


def catalogue():
    """La liste des objets echangeables : slug, identifiant, chemin interne.

    On passe par la v2 : la route v1 equivalente est depreciee et repond 403.
    L'identifiant sert a relier la route groupee, qui n'expose pas les slugs.
    Le champ gameRef est le chemin que le jeu utilise en interne, du genre
    /Lotus/Upgrades/Mods/Pistol/DualStat/CorruptedCritChanceFireRatePistol.
    C'est lui qui permettra de reconnaitre l'objet qu'un joueur regarde.
    """
    d = _get(V2 + "/items") or {}
    return [(it["slug"], it.get("id"), it.get("gameRef"))
            for it in (d.get("data") or []) if it.get("slug")]


def normaliser_chemin(chemin):
    """Ramene un chemin du jeu a la forme utilisee par warframe.market.

    Overwolf annonce l'objet regarde avec un segment /StoreItems/ en plus,
    que le marche n'a pas. On l'enleve et on passe en minuscules, la casse
    n'etant pas fiable d'une source a l'autre.
    """
    return chemin.replace("/StoreItems/", "/").lower()


def ecrire_correspondances(objets, chemin_sortie):
    """Ecrit la table chemin -> slug, a cote du fichier de prix.

    Elle ne bouge que quand Digital Extremes ajoute des objets, mais la
    reecrire a chaque passage ne coute rien : le catalogue est deja telecharge.
    """
    table = {}
    for slug, _ident, ref in objets:
        if ref:
            table[normaliser_chemin(ref)] = slug
    sortie = {
        "stamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "chemin interne du jeu (segment /StoreItems/ retire, minuscules) "
                "-> objet du marche",
        "objets": table,
    }
    tmp = chemin_sortie + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sortie, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, chemin_sortie)
    print("ecrit : %s  (%d correspondances, %.0f Ko)"
          % (chemin_sortie, len(table), os.path.getsize(chemin_sortie) / 1024))


def prix_groupes():
    """742 Primes en une requete : prix median et identifiant d'objet."""
    d = _get(V1 + "/tools/ducats") or {}
    p = d.get("payload") or {}
    lst = p.get("previous_hour") or p.get("previous_day") or []
    return {x["item"]: x["median"] for x in lst
            if x.get("item") and (x.get("median") or 0) > 0}


def stats(slug):
    """Prix median et ventes par jour.

    IMPORTANT : le calcul doit etre RIGOUREUSEMENT identique a celui du
    moteur de l'application (engine.py, fetch_stats), sinon les prix livres
    et ceux mesures a l'ecran ne veulent pas dire la meme chose et le
    classement devient incoherent d'un objet a l'autre.

    Methode : releves quotidiens des ventes CONCLUES sur 90 jours, on garde
    les 7 derniers, de preference au rang 0 pour les mods (un mod maxe se
    vend beaucoup plus cher et fausserait la mediane).
    """
    # Certains slugs contiennent une apostrophe typographique
    # ("albrecht’s_archive_scene") : sans encodage, urllib refuse l'URL et
    # l'objet est perdu du releve.
    d = _get(V1 + "/items/%s/statistics" % urllib.parse.quote(slug, safe=""))
    if not d:
        return None
    jours = ((d.get("payload") or {}).get("statistics_closed") or {}).get("90days") or []
    if not jours:
        return None
    lignes = [r for r in jours if (r.get("mod_rank") or 0) == 0][-7:] or jours[-7:]
    if not lignes:
        return None
    medians = sorted(r["median"] for r in lignes)
    n = len(medians)
    med = medians[n // 2] if n % 2 else (medians[n // 2 - 1] + medians[n // 2]) / 2
    vol = sum(r["volume"] for r in lignes) / len(lignes)
    return round(med, 1), round(vol, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapide", action="store_true",
                    help="uniquement la route groupee (742 Primes, ~1 s)")
    ap.add_argument("--sortie", default=SORTIE)
    args = ap.parse_args()

    debut = time.time()
    prix = {}

    if args.rapide:
        # La route groupee est indexee par identifiant d'objet, pas par slug :
        # sans le catalogue on ne peut pas la relier. On la garde donc pour un
        # usage cote application, pas ici.
        print("mode rapide : releve le catalogue quand meme pour relier les identifiants")

    objets = catalogue()
    print("catalogue : %d objets" % len(objets))

    # Tout de suite, avant la demi-heure de releve : si celui-ci echoue en
    # route, la table est deja a jour et publiee.
    ecrire_correspondances(
        objets, os.path.join(os.path.dirname(os.path.abspath(args.sortie)),
                             "gameref.json"))

    # La route groupee donne le prix de ~740 Primes en UNE requete. Autant
    # commencer par la : c'est 4 minutes de moins a interroger un par un.
    # Elle ne fournit pas le volume, donc ces objets passent quand meme par
    # le releve detaille ; mais s'il echoue, on a deja leur prix.
    groupes = {}
    try:
        par_id = prix_groupes()
        for slug, ident in objets:
            m = ident and par_id.get(ident)
            if m:
                groupes[slug] = m
        print("route groupee : %d prix obtenus en 1 requete" % len(groupes))
    except Exception as e:
        print("route groupee indisponible :", e, file=sys.stderr)

    for i, (slug, _ident, _ref) in enumerate(objets, 1):
        try:
            s = stats(slug)
            if s:
                prix[slug] = list(s)
            elif slug in groupes:
                # aucune vente conclue sur 48 h : on garde au moins le prix
                prix[slug] = [groupes[slug], 0]
        except Exception as e:
            if slug in groupes:
                prix[slug] = [groupes[slug], 0]
            print("  %-40s echec : %s" % (slug, e), file=sys.stderr)
        if i % 250 == 0:
            print("  %d / %d  (%.0f s ecoulees)" % (i, len(objets), time.time() - debut))

    sortie = {
        "stamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "warframe.market",
        "note": "prix median et ventes par jour, ventes conclues sur 48 h",
        "prix": prix,
    }
    tmp = args.sortie + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sortie, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, args.sortie)      # ecriture atomique

    taille = os.path.getsize(args.sortie) / 1024
    print("ecrit : %s  (%d objets, %.0f Ko, %.0f min)"
          % (args.sortie, len(prix), taille, (time.time() - debut) / 60))


if __name__ == "__main__":
    main()
