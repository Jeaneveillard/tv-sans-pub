#!/usr/bin/env python3
"""Nettoyage réversible d'une TV Android, Google TV ou Fire TV par ADB.

Sous-commandes :
  appareils                       liste les appareils ADB connus
  connecter HOTE[:PORT]           se connecte en ADB réseau (port 5555 par défaut)
  appairer HOTE:PORT CODE         appairage « débogage sans fil » (Android 11 et plus)
  inventaire --appareil SERIE     lecture seule : classe chaque paquet, écrit un JSON
  appliquer --appareil SERIE --plan plan.json [--confirmer] [--repli-desinstaller]
  restaurer --appareil SERIE --fichier restauration.json [--confirmer]

Sans --confirmer, `appliquer` et `restaurer` ne font qu'afficher ce qu'ils feraient.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

import analyse_android as an

ICI = Path(__file__).resolve().parent
CATALOGUE = ICI / "catalogue_paquets.json"
DOSSIER_DEFAUT = Path.home() / "Documents" / "TV sans pub"
DELAI_ADB = 90
PORT_ADB = 5555
HOTE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-]*(:\d{1,5})?|\[[0-9A-Fa-f:]+\](:\d{1,5})?")
CODE_RE = re.compile(r"\d{6}")
SERIE_RE = re.compile(r"[A-Za-z0-9\[][A-Za-z0-9.:\-_\[\]]*")
# Propositions de l'inventaire qu'on peut appliquer sans autorisation explicite.
PROPOSITIONS_APPLICABLES = {"desactiver", "choix_personne"}
# Seuls ces messages de refus déclenchent le repli « retirer pour l'utilisateur ».
MOTS_REFUS = ("securityexception", "cannot change", "not allowed", "permission denial")


class ErreurTv(RuntimeError):
    """Erreur à montrer telle quelle à la personne."""


# --- Accès ADB ---------------------------------------------------------------------------

def chemin_adb() -> str:
    chemin = shutil.which("adb")
    if not chemin:
        raise ErreurTv(
            "adb est introuvable. Installer les Android Platform Tools :\n"
            "  Windows : winget install Google.PlatformTools\n"
            "  macOS   : brew install android-platform-tools\n"
            "  Linux   : paquet « android-tools-adb » ou « android-tools »"
        )
    return chemin


def adb(serie: str | None, *args: str, verifier: bool = True) -> str:
    commande = [chemin_adb()] + (["-s", serie] if serie else []) + list(args)
    try:
        res = subprocess.run(commande, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=DELAI_ADB)
    except subprocess.TimeoutExpired as exc:
        raise ErreurTv(f"ADB ne répond pas ({' '.join(args[:3])}). La TV est-elle allumée ?") from exc
    sortie = (res.stdout or "").replace("\r", "")
    erreurs = (res.stderr or "").replace("\r", "")
    if verifier and res.returncode != 0:
        detail = (erreurs or sortie).strip()
        raise ErreurTv(f"Échec de « adb {' '.join(args[:4])} » : {detail}")
    return sortie if verifier else sortie + erreurs


def shell(serie: str, *args: str, verifier: bool = True) -> str:
    return adb(serie, "shell", *args, verifier=verifier)


def verifier_paquet(nom: str) -> str:
    """Seuls des noms de paquets valides atteignent `adb shell` (pas d'injection)."""
    if not an.est_nom_paquet(nom):
        raise ErreurTv(f"Nom de paquet invalide : {nom!r}")
    return nom


def verifier_appareil(serie: str) -> str:
    if not SERIE_RE.fullmatch(serie):
        raise ErreurTv(f"Identifiant d'appareil invalide : {serie!r}")
    etat = adb(serie, "get-state", verifier=False).strip()
    if etat != "device":
        raise ErreurTv(
            f"L'appareil {serie} n'est pas prêt (état : {etat or 'absent'}). "
            "Si l'état est « unauthorized », accepter la demande affichée sur la TV."
        )
    return serie


# --- Lecture de l'état de l'appareil -----------------------------------------------------

def lire_proprietes(serie: str) -> dict:
    cles = ["ro.product.manufacturer", "ro.product.brand", "ro.product.model",
            "ro.build.version.release", "ro.build.version.sdk", "ro.build.version.name"]
    return {cle: shell(serie, "getprop", cle, verifier=False).strip() for cle in cles}


def lire_fonctions(serie: str) -> set[str]:
    texte = shell(serie, "pm", "list", "features", verifier=False)
    return {ligne.split(":", 1)[1].split("=")[0].strip()
            for ligne in texte.splitlines() if ligne.startswith("feature:")}


def lire_paquets(serie: str) -> dict[str, set[str]]:
    def lister(*options: str) -> set[str]:
        return an.parser_liste_paquets(shell(serie, "pm", "list", "packages", *options))

    tous = lister("-u")
    installes = lister()
    return {"tous": tous, "installes": installes, "systeme": lister("-s"),
            "tiers": lister("-3"), "desactives": lister("-d"),
            "retires": tous - installes}


def lire_visibles(serie: str) -> set[str]:
    visibles = set()
    for categorie in ("android.intent.category.LEANBACK_LAUNCHER",
                      "android.intent.category.LAUNCHER"):
        texte = shell(serie, "cmd", "package", "query-activities", "--brief",
                      "-a", "android.intent.action.MAIN", "-c", categorie, verifier=False)
        visibles |= an.parser_activites(texte)
    return visibles


def lire_contexte(serie: str) -> dict:
    accueil = shell(serie, "cmd", "package", "resolve-activity", "--brief",
                    "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME",
                    verifier=False)
    clavier = shell(serie, "settings", "get", "secure", "default_input_method", verifier=False)
    return {"lanceur": an.parser_resolution(accueil), "clavier": an.parser_composant(clavier)}


def lire_famille(serie: str, paquets_presents: set[str]) -> str:
    return an.famille_appareil(lire_proprietes(serie), lire_fonctions(serie), paquets_presents)


def exiger_contexte(contexte: dict) -> None:
    """Sans lanceur identifié, la protection de l'accueil saute : on n'applique rien."""
    if contexte.get("lanceur") in (None, "android"):
        raise ErreurTv(
            "Impossible d'identifier le lanceur d'accueil (version d'Android trop ancienne, ou "
            "plusieurs lanceurs sans choix par défaut). Par sécurité, rien n'est appliqué. "
            "Choisir un accueil par défaut sur la TV, puis relancer."
        )
    if not contexte.get("clavier"):
        print("Attention : clavier actif inconnu ; vérifier qu'aucun clavier n'est dans le plan.")


def etat_paquet(paquet: str, paquets: dict[str, set[str]]) -> str:
    if paquet in paquets["retires"]:
        return "retire"
    if paquet in paquets["desactives"]:
        return "desactive"
    return "actif"


# --- inventaire --------------------------------------------------------------------------

def inventorier(serie: str, catalogue: dict) -> dict:
    proprietes = lire_proprietes(serie)
    paquets = lire_paquets(serie)
    famille = an.famille_appareil(proprietes, lire_fonctions(serie), paquets["tous"])
    contexte = {**lire_contexte(serie), "famille": famille}
    visibles = lire_visibles(serie)
    stats = an.parser_usagestats(shell(serie, "dumpsys", "usagestats", verifier=False))
    recents = an.parser_recents(shell(serie, "dumpsys", "activity", "recents", verifier=False))
    lignes = []
    for paquet in sorted(paquets["tous"]):
        infos = {"systeme": paquet in paquets["systeme"], "visible": paquet in visibles,
                 "etat": etat_paquet(paquet, paquets)}
        decision = an.classifier(paquet, infos, catalogue, contexte)
        ligne = {"paquet": paquet, "nom": an.nom_humain(paquet, catalogue), **infos, **decision}
        if infos["visible"]:
            ligne["utilisation"] = an.indice_utilisation(paquet, stats, recents)
        lignes.append(ligne)
    resume: dict[str, int] = {}
    for ligne in lignes:
        resume[ligne["categorie"]] = resume.get(ligne["categorie"], 0) + 1
    return {"appareil": {"serie": serie, **contexte,
                         "fabricant": proprietes["ro.product.manufacturer"],
                         "modele": proprietes["ro.product.model"],
                         "android": proprietes["ro.build.version.release"],
                         "version": proprietes["ro.build.version.name"],
                         "date": dt.datetime.now().isoformat(timespec="seconds")},
            "resume": resume, "paquets": lignes}


def afficher_inventaire(inventaire: dict) -> None:
    app = {cle: an.texte_affichable(valeur or "") for cle, valeur in
           inventaire["appareil"].items()}
    print(f"# {app['fabricant']} {app['modele']} — {app['famille']} (Android {app['android']}"
          f"{', ' + app['version'] if app['version'] else ''})")
    print(f"Lanceur : {app['lanceur']} · Clavier : {app['clavier']}")
    if app["famille"] == an.FAMILLE_MOBILE:
        print("Téléphone, tablette ou boîtier Android sans interface TV : les applis "
              "préinstallées ne sont jamais proposées d'office. Une par une, après "
              "vérification et accord de la personne : --autoriser <paquet>.")
    elif app["famille"] not in an.FAMILLES_TV:
        print("ATTENTION : famille d'appareil non reconnue. Par prudence, les applis "
              "préinstallées ne sont pas proposées d'office. Une par une, après "
              "vérification et accord de la personne : --autoriser <paquet>.")
    print("\nRésumé :", ", ".join(f"{k} {v}" for k, v in sorted(inventaire["resume"].items())))
    lignes = inventaire["paquets"]
    _tableau("Pubs, pistage et superflu",
             [l for l in lignes if l["categorie"] in an.CATEGORIES_A_DESACTIVER],
             lambda l: [l["paquet"], l["nom"], l["categorie"], l["etat"], l["proposition"]],
             ["Paquet", "Nom", "Catégorie", "État", "Proposition"])
    _tableau("Applications visibles",
             [l for l in lignes if l["categorie"] == "application"],
             lambda l: [l["nom"] or "?", l["paquet"],
                        "préinstallée" if l["systeme"] else "ajoutée", l["etat"],
                        l["utilisation"]["texte"]],
             ["Nom", "Paquet", "Origine", "État", "Utilisation"])
    _tableau("À vérifier avant toute action",
             [l for l in lignes if l["categorie"] == "a_verifier"],
             lambda l: [l["paquet"], l["nom"], l["etat"], l["raison"]],
             ["Paquet", "Nom", "État", "Pourquoi"])


def _tableau(titre: str, lignes: list[dict], colonnes: Callable[[dict], list],
             entetes: list[str]) -> None:
    print(f"\n## {titre} ({len(lignes)})")
    if not lignes:
        print("(aucun)")
        return
    print("| " + " | ".join(entetes) + " |")
    print("|" + "---|" * len(entetes))
    for ligne in lignes:
        print("| " + " | ".join(an.texte_affichable(c, 120) for c in colonnes(ligne)) + " |")


# --- appliquer ---------------------------------------------------------------------------

def lire_plan(chemin: Path) -> dict[str, list[str]]:
    try:
        plan = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ErreurTv(f"Plan illisible ({chemin}) : {exc}") from exc
    if not isinstance(plan, dict):
        raise ErreurTv("Le plan doit être un objet JSON avec « desactiver » et « desinstaller ».")
    resultat = {}
    for cle in ("desactiver", "desinstaller"):
        valeur = plan.get(cle, [])
        if not isinstance(valeur, list) or not all(isinstance(v, str) for v in valeur):
            raise ErreurTv(f"« {cle} » doit être une liste de noms de paquets.")
        resultat[cle] = list(dict.fromkeys(verifier_paquet(v.strip()) for v in valeur))
    if not resultat["desactiver"] and not resultat["desinstaller"]:
        raise ErreurTv("Le plan est vide : rien à faire.")
    return resultat


def preparer_actions(plan: dict[str, list[str]], paquets: dict[str, set[str]],
                     catalogue: dict, contexte: dict, visibles: set[str],
                     autorises: frozenset[str] = frozenset()) -> tuple[list[dict], list[dict]]:
    """Sépare le plan en actions permises et en refus motivés.

    Liste blanche : on n'applique que ce que l'inventaire propose (pub, pistage, superflu
    connus, ou appli visible). Un paquet « à vérifier » ou « système » exige --autoriser.
    Un paquet protégé est refusé dans tous les cas.
    """
    actions, refus = [], []
    demandes = [(p, "desactiver") for p in plan["desactiver"]] + \
               [(p, "desinstaller") for p in plan["desinstaller"]]
    for paquet, action in demandes:
        motif = _motif_refus(paquet, action, paquets, catalogue, contexte, visibles, autorises)
        if motif:
            refus.append({"paquet": paquet, "raison": motif})
        else:
            actions.append({"paquet": paquet, "action": action, "etat_avant": "actif"})
    return actions, refus


def _motif_refus(paquet: str, action: str, paquets: dict[str, set[str]], catalogue: dict,
                 contexte: dict, visibles: set[str], autorises: frozenset[str]) -> str | None:
    protection = an.raison_protection(paquet, catalogue, contexte)
    if protection:
        return f"protégé : {protection}"
    if paquet not in paquets["tous"]:
        return "absent de l'appareil"
    etat = etat_paquet(paquet, paquets)
    if etat != "actif":
        return f"déjà fait (état : {etat})"
    if action == "desinstaller" and paquet not in paquets["tiers"]:
        return "appli système : utiliser « desactiver »"
    infos = {"systeme": paquet in paquets["systeme"], "visible": paquet in visibles,
             "etat": etat}
    decision = an.classifier(paquet, infos, catalogue, contexte)
    if decision["proposition"] not in PROPOSITIONS_APPLICABLES and paquet not in autorises:
        return (f"classé « {decision['categorie']} » par l'inventaire : "
                f"ajouter --autoriser {paquet} si la personne l'a validé après vérification")
    return None


def desactiver(serie: str, paquet: str, repli: bool) -> tuple[str, str]:
    sortie = shell(serie, "pm", "disable-user", "--user", "0", paquet, verifier=False).strip()
    if "disabled-user" in sortie:
        return "desactiver", "ok"
    refus_systeme = any(mot in sortie.lower() for mot in MOTS_REFUS)
    if repli and refus_systeme:
        retrait = shell(serie, "pm", "uninstall", "-k", "--user", "0", paquet,
                        verifier=False).strip()
        if retrait.startswith("Success"):
            return "retire_utilisateur", "ok"
        sortie = f"{sortie} / repli : {retrait}"
    cause = "refusé par le système" if refus_systeme else "échec"
    return "desactiver", f"{cause} : {sortie[:200] or 'aucune réponse de la TV'}"


def sauvegarder_apk(serie: str, paquet: str, dossier: Path) -> list[str]:
    chemins = [ligne.split(":", 1)[1].strip()
               for ligne in shell(serie, "pm", "path", paquet).splitlines()
               if ligne.startswith("package:")]
    if not chemins:
        raise ErreurTv(f"Impossible de trouver l'APK de {paquet}")
    cible = dossier / paquet
    cible.mkdir(parents=True, exist_ok=True)
    fichiers = []
    for distant in chemins:
        local = cible / Path(distant).name
        adb(serie, "pull", distant, str(local))
        fichiers.append(str(local))
    return fichiers


def desinstaller(serie: str, action: dict, dossier: Path, enregistrer: Callable[[], None]) -> None:
    """Sauvegarde l'APK, l'inscrit dans le journal, puis seulement désinstalle."""
    paquet = action["paquet"]
    try:
        action["apks"] = sauvegarder_apk(serie, paquet, dossier)
    except ErreurTv as exc:
        action["resultat"] = f"annulé, sauvegarde impossible : {exc}"
        return
    enregistrer()                                # l'APK figure au journal avant le retrait
    sortie = shell(serie, "pm", "uninstall", paquet, verifier=False).strip()
    action["resultat"] = "ok" if sortie.startswith("Success") else f"échec : {sortie[:200]}"


def appliquer(args: argparse.Namespace, catalogue: dict) -> int:
    serie = verifier_appareil(args.appareil)
    plan = lire_plan(Path(args.plan))
    paquets = lire_paquets(serie)
    contexte = {**lire_contexte(serie), "famille": lire_famille(serie, paquets["tous"])}
    exiger_contexte(contexte)
    autorises = frozenset(verifier_paquet(p) for p in (args.autoriser or []))
    actions, refus = preparer_actions(plan, paquets, catalogue, contexte,
                                      lire_visibles(serie), autorises)
    for r in refus:
        print(f"  ignoré  {r['paquet']} — {r['raison']}")
    for a in actions:
        print(f"  {a['action']:<12} {a['paquet']}")
    if not actions:
        print("Rien à appliquer.")
        return 0
    if not args.confirmer:
        print("\nSimulation : rien n'a été modifié. Relancer avec --confirmer pour appliquer.")
        return 0
    dossier = Path(args.dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    horodatage = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    restauration = dossier / f"restauration-{horodatage}.json"
    numero = 1
    while restauration.exists():                 # ne jamais écraser une restauration
        numero += 1
        restauration = dossier / f"restauration-{horodatage}-{numero}.json"
    journal = {"appareil": serie, "date": horodatage, "statut": "en_cours", "actions": actions}
    _ecrire_json(restauration, journal)          # écrit AVANT de toucher à la TV
    print(f"\nFichier de restauration : {restauration}")
    for a in actions:
        if a["action"] == "desinstaller":
            desinstaller(serie, a, dossier / f"apk-{horodatage}",
                         lambda: _ecrire_json(restauration, journal))
        else:
            a["action"], a["resultat"] = desactiver(serie, a["paquet"], args.repli_desinstaller)
        print(f"  {a['action']:<18} {a['paquet']} → {a['resultat']}")
        _ecrire_json(restauration, journal)
    journal["statut"] = "termine"
    _ecrire_json(restauration, journal)
    reussis = sum(1 for a in actions if a["resultat"] == "ok")
    print(f"\n{reussis}/{len(actions)} action(s) réussie(s).")
    return 0 if reussis == len(actions) else 2


def _ecrire_json(chemin: Path, donnees: dict) -> None:
    temporaire = chemin.with_suffix(".tmp")
    temporaire.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    temporaire.replace(chemin)


# --- restaurer ---------------------------------------------------------------------------

def lire_restauration(chemin: Path) -> tuple[dict, list[dict]]:
    try:
        journal = json.loads(chemin.read_text(encoding="utf-8"))
        actions = journal["actions"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ErreurTv(f"Fichier de restauration illisible : {exc}") from exc
    if not isinstance(actions, list) or not all(isinstance(a, dict) for a in actions):
        raise ErreurTv("Fichier de restauration invalide : « actions » doit être une liste.")
    return journal, actions


def restaurer(args: argparse.Namespace) -> int:
    serie = verifier_appareil(args.appareil)
    fichier = Path(args.fichier).resolve()
    journal, actions = lire_restauration(fichier)
    if journal.get("appareil") != serie and not args.forcer:
        raise ErreurTv(f"Ce fichier concerne {journal.get('appareil')}, pas {serie}. "
                       "Ajouter --forcer seulement s'il s'agit bien de la même TV.")
    echecs = 0
    for a in actions:
        paquet = verifier_paquet(str(a.get("paquet", "")))
        commande = _commande_restauration(a, paquet, fichier.parent)
        print(f"  {' '.join(commande) or f'{paquet} : aucune sauvegarde, rien à restaurer'}")
        if args.confirmer and commande:
            echecs += not _executer_restauration(serie, commande)
    if not args.confirmer:
        print("\nSimulation : rien n'a été modifié. Relancer avec --confirmer pour restaurer.")
        return 0
    print("Restauration terminée." if not echecs else f"{echecs} restauration(s) en échec.")
    return 0 if not echecs else 2


def _commande_restauration(action: dict, paquet: str, dossier: Path) -> list[str]:
    if action.get("action") == "retire_utilisateur":
        return ["shell", "cmd", "package", "install-existing", paquet]
    if action.get("action") == "desinstaller":
        apks = _apks_sauvegardes(action.get("apks", []), dossier)
        if not apks:
            return []
        return ["install-multiple", "-r", *apks] if len(apks) > 1 else ["install", "-r", apks[0]]
    return ["shell", "pm", "enable", paquet]


def _apks_sauvegardes(chemins: object, dossier: Path) -> list[str]:
    """Seuls les APK rangés à côté du fichier de restauration sont réinstallés."""
    if not isinstance(chemins, list):
        return []
    retenus = []
    for chemin in chemins:
        apk = Path(str(chemin)).resolve()
        if apk.suffix == ".apk" and apk.is_file() and dossier in apk.parents:
            retenus.append(str(apk))
    return retenus


def _executer_restauration(serie: str, commande: list[str]) -> bool:
    sortie = adb(serie, *commande, verifier=False)
    if commande[:3] == ["shell", "pm", "enable"]:
        reussi = "new state: enabled" in sortie
    elif "install-existing" in commande:
        reussi = "installed for user" in sortie
    else:
        reussi = "Success" in sortie
    print(f"    → {'ok' if reussi else sortie.strip()[:200]}")
    return reussi


# --- connexion ---------------------------------------------------------------------------

def connecter(args: argparse.Namespace) -> int:
    hote = args.hote if ":" in args.hote.lstrip("[").split("]")[-1] else f"{args.hote}:{PORT_ADB}"
    if not HOTE_RE.fullmatch(hote):
        raise ErreurTv(f"Adresse invalide : {args.hote!r}")
    print(adb(None, "connect", hote, verifier=False).strip())
    etat = adb(hote, "get-state", verifier=False).strip() or "absent"
    print(f"État : {etat}")
    if "unauthorized" in etat:
        print("La TV affiche une demande : cocher « Toujours autoriser », puis OK. Relancer ensuite.")
    elif etat != "device":
        print("Vérifier que le débogage ADB est activé et que la TV est sur le même réseau.")
    return 0 if etat == "device" else 1


def appairer(args: argparse.Namespace) -> int:
    if not HOTE_RE.fullmatch(args.hote) or not CODE_RE.fullmatch(args.code):
        raise ErreurTv("Usage : appairer IP:PORT CODE (code à 6 chiffres affiché sur la TV)")
    print(adb(None, "pair", args.hote, args.code, verifier=False).strip())
    print("Ensuite : connecter IP:PORT (le port de connexion, différent du port d'appairage).")
    return 0


# --- programme principal -----------------------------------------------------------------

def construire_parseur() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sous = p.add_subparsers(dest="commande", required=True)
    sous.add_parser("appareils", help="liste les appareils ADB")
    c = sous.add_parser("connecter", help="connexion ADB réseau")
    c.add_argument("hote")
    pa = sous.add_parser("appairer", help="appairage débogage sans fil (Android 11+)")
    pa.add_argument("hote")
    pa.add_argument("code")
    for nom in ("inventaire", "appliquer", "restaurer"):
        s = sous.add_parser(nom)
        s.add_argument("--appareil", required=True, help="série ADB, ex. 192.168.1.50:5555")
        s.add_argument("--dossier", default=str(DOSSIER_DEFAUT), help="dossier de travail")
        if nom == "appliquer":
            s.add_argument("--plan", required=True)
            s.add_argument("--repli-desinstaller", action="store_true",
                           help="si la désactivation est refusée, retirer pour l'utilisateur 0")
            s.add_argument("--autoriser", action="append", metavar="PAQUET",
                           help="autorise un paquet « à vérifier » ou « système » validé par "
                                "la personne (répétable)")
        if nom == "restaurer":
            s.add_argument("--fichier", required=True)
            s.add_argument("--forcer", action="store_true",
                           help="accepter un fichier d'un autre identifiant d'appareil")
        if nom != "inventaire":
            s.add_argument("--confirmer", action="store_true", help="appliquer pour de vrai")
        else:
            s.add_argument("--json", action="store_true", help="afficher le JSON complet")
    return p


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = construire_parseur().parse_args(argv)
    try:
        if args.commande == "appareils":
            print(adb(None, "devices", "-l").strip())
            return 0
        if args.commande == "connecter":
            return connecter(args)
        if args.commande == "appairer":
            return appairer(args)
        catalogue = an.charger_catalogue(CATALOGUE)
        if args.commande == "inventaire":
            return _commande_inventaire(args, catalogue)
        if args.commande == "appliquer":
            return appliquer(args, catalogue)
        return restaurer(args)
    except ErreurTv as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1


def _commande_inventaire(args: argparse.Namespace, catalogue: dict) -> int:
    serie = verifier_appareil(args.appareil)
    inventaire = inventorier(serie, catalogue)
    dossier = Path(args.dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    modele = re.sub(r"[^A-Za-z0-9_-]+", "-", inventaire["appareil"]["modele"] or "tv")
    chemin = dossier / f"inventaire-{modele}-{dt.date.today().isoformat()}.json"
    _ecrire_json(chemin, inventaire)
    if args.json:
        print(json.dumps(inventaire, ensure_ascii=False, indent=2))
    else:
        afficher_inventaire(inventaire)
    print(f"\nInventaire complet : {chemin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
