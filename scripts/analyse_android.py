"""Analyse des sorties ADB d'une TV Android ou Fire TV : fonctions pures, sans accès à l'appareil.

Tout ce qui lit l'appareil est dans tv_android.py ; ici on ne fait que parser et classer,
ce qui permet de tester sans TV.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Un nom de paquet Android : segments alphanumériques séparés par des points.
# Sert aussi de garde-fou : rien d'autre ne doit atteindre `adb shell`.
PAQUET_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*$")

SECONDES_PAR_JOUR = 86400
SECONDES_RECHARGEMENT = 180  # tâche « active » moins de 3 min après le démarrage = rechargée
JOURS_RECENTE = 7          # ouverte dans la semaine : « récente »
BUCKET_RARE = 40           # Android : 10 actif, 20 courant, 30 fréquent, 40 rare, 50 jamais
BUCKET_JAMAIS = 50
EPOQUES_VIDES = ("1969-", "1970-")
DUREES_NULLES = {"00:00", "0:00", "00:00:00"}
# Sous-raisons d'usage qui viennent vraiment de la personne (ouverture, premier plan).
USAGES_REELS = {"ui", "mf", "mb"}

MOTS_SUSPECTS = {
    "ad", "ads", "adid", "advert", "advertising", "advertisingid", "promo", "promos",
    "promotion", "sponsor", "sponsored", "acr", "metrics", "analytics", "telemetry",
    "tracking", "tracker", "logger", "feedback", "survey", "tutorial", "tutorials",
    "retaildemo", "storedemo", "demo", "demopage", "shop", "shopping",
}
CATEGORIES_A_DESACTIVER = {"publicite", "pistage", "superflu"}
FAMILLE_MOBILE = "android-mobile"
# Seules ces familles ont la règle souple « appli préinstallée visible = au choix de la
# personne ». Toute autre famille, ou une famille non reconnue, exige une vérification.
FAMILLES_TV = {"fire-tv", "google-tv", "android-tv"}
# Segments de nom qui désignent la téléphonie, les SMS, les contacts ou les alertes
# d'urgence : jamais touchés, même si le paquet n'est pas dans la liste du catalogue.
SEGMENTS_VITAUX = {
    "phone", "telephony", "telephonyui", "telecom", "dialer", "incallui", "ims", "imsservice",
    "epdg", "mms", "messaging", "contacts", "stk", "carrierconfig", "cellbroadcast",
    "cellbroadcastreceiver", "cellbroadcastservice", "emergency", "safetyhub",
}
FONCTIONS_TV = {"android.software.leanback", "android.hardware.type.television"}
FONCTIONS_MOBILE = {"android.hardware.telephony", "android.hardware.touchscreen"}
PREFIXE_TABLETTE_FIRE = "KF"


def est_nom_paquet(nom: str) -> bool:
    return bool(nom) and len(nom) <= 255 and bool(PAQUET_RE.fullmatch(nom))


def texte_affichable(valeur: object, longueur: int = 80) -> str:
    """Texte fourni par un appareil → une ligne courte, sans caractère de contrôle ni « | ».

    Ces textes (nom de la TV, modèle, nom d'appli) viennent du réseau : ce sont des
    données, jamais des instructions.
    """
    texte = re.sub(r"[\x00-\x1f\x7f]+", " ", str(valeur)).replace("|", "/").strip()
    return texte if len(texte) <= longueur else texte[: longueur - 1] + "…"


def charger_catalogue(chemin: Path) -> dict:
    with open(chemin, encoding="utf-8") as fichier:
        catalogue = json.load(fichier)
    for cle in ("paquets", "proteges", "prefixes_proteges", "noms_humains"):
        if cle not in catalogue:
            raise ValueError(f"Catalogue incomplet : clé « {cle} » manquante dans {chemin}")
    return catalogue


# --- Parsing des sorties ADB ------------------------------------------------------------

def parser_liste_paquets(texte: str) -> set[str]:
    """Sortie de `pm list packages [...]` → noms de paquets."""
    paquets = set()
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if ligne.startswith("package:"):
            nom = ligne[len("package:"):].split("=")[-1].strip()
            if est_nom_paquet(nom):
                paquets.add(nom)
    return paquets


def parser_activites(texte: str) -> set[str]:
    """Sortie de `cmd package query-activities --brief` → paquets qui ont une icône."""
    paquets = set()
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if "/" in ligne and " " not in ligne:
            nom = ligne.split("/", 1)[0]
            if est_nom_paquet(nom):
                paquets.add(nom)
    return paquets


def parser_resolution(texte: str) -> str | None:
    """Sortie de `cmd package resolve-activity --brief` → paquet qui répond (le lanceur)."""
    for ligne in reversed(texte.splitlines()):
        ligne = ligne.strip()
        if "/" in ligne and " " not in ligne:
            nom = ligne.split("/", 1)[0]
            return nom if est_nom_paquet(nom) else None
    return None


def parser_composant(texte: str) -> str | None:
    """`com.exemple.clavier/.Service` (réglage default_input_method) → paquet."""
    valeur = texte.strip()
    if not valeur or valeur == "null":
        return None
    nom = valeur.split("/", 1)[0]
    return nom if est_nom_paquet(nom) else None


def duree_en_secondes(texte: str) -> float | None:
    """Durée au format dumpsys (`+617d19h38m33s112ms`, `-3h`) → secondes."""
    texte = texte.strip()
    if not texte or texte[0] not in "+-":
        return None
    signe = -1 if texte[0] == "-" else 1
    morceaux = re.findall(r"(\d+)(ms|d|h|m|s)", texte[1:])
    if not morceaux:
        return None
    facteurs = {"d": 86400, "h": 3600, "m": 60, "s": 1, "ms": 0.001}
    return signe * sum(int(valeur) * facteurs[unite] for valeur, unite in morceaux)


@dataclass
class Utilisation:
    bucket: int | None = None
    raison: str | None = None
    jours_depuis_usage: float | None = None
    derniere_date: str | None = None


@dataclass
class StatsUtilisation:
    par_paquet: dict[str, Utilisation] = field(default_factory=dict)

    def de(self, paquet: str) -> Utilisation:
        return self.par_paquet.setdefault(paquet, Utilisation())


_RE_VEILLE = re.compile(r"package=(\S+) u=\d+ bucket=(\d+) reason=(\S+)(?: used=(\S+))?")
_RE_STATS = re.compile(
    r'package=(\S+) totalTime(?:Used)?="([^"]*)" lastTime(?:Used)?="([^"]*)"'
)
_RE_TOTAL = re.compile(r"totalElapsedTime=(\S+)")


def parser_usagestats(texte: str) -> StatsUtilisation:
    """Sortie de `dumpsys usagestats` (Android 9 à 14) → indices d'utilisation par paquet."""
    stats = StatsUtilisation()
    total = None
    veille: list[tuple[str, int, str, float | None]] = []
    for ligne in texte.splitlines():
        if (m := _RE_TOTAL.search(ligne)):
            total = duree_en_secondes(m.group(1))
        elif (m := _RE_VEILLE.search(ligne)):
            utilise = duree_en_secondes(m.group(4)) if m.group(4) else None
            veille.append((m.group(1), int(m.group(2)), m.group(3), utilise))
        elif (m := _RE_STATS.search(ligne)):
            _noter_derniere_date(stats.de(m.group(1)), m.group(2), m.group(3))
    for paquet, bucket, raison, utilise in veille:
        info = stats.de(paquet)
        info.bucket, info.raison = bucket, raison
        if total is not None and utilise is not None and utilise >= 0 and _usage_reel(raison):
            info.jours_depuis_usage = max(0.0, (total - utilise) / SECONDES_PAR_JOUR)
    return stats


def _noter_derniere_date(info: Utilisation, duree_totale: str, derniere: str) -> None:
    if duree_totale.strip() in DUREES_NULLES or derniere.startswith(EPOQUES_VIDES):
        return
    if info.derniere_date is None or derniere > info.derniere_date:
        info.derniere_date = derniere


def _usage_reel(raison: str) -> bool:
    principal, _, sous = raison.partition("-")
    return principal == "u" and sous in USAGES_REELS


@dataclass(frozen=True)
class Recent:
    inactif: float              # secondes depuis la dernière ouverture
    avant_redemarrage: bool     # tâche rechargée au démarrage : ouverte avant le redémarrage
    depuis_demarrage: float     # secondes depuis le démarrage de la TV


_RE_ACTIVE = re.compile(r"lastActiveTime=(\d+) \(inactive for (\d+)s\)")


def parser_recents(texte: str) -> dict[str, Recent]:
    """Sortie de `dumpsys activity recents` → dernière ouverture connue par paquet.

    `lastActiveTime` est compté depuis le démarrage : une tâche rechargée au démarrage
    a une valeur de quelques secondes, et son « inactive for » vaut alors la durée
    depuis le redémarrage, pas la vraie date d'ouverture.
    """
    resultat: dict[str, Recent] = {}
    paquet = None
    for ligne in texte.splitlines():
        if "* Recent #" in ligne:
            paquet = None
        if (m := re.search(r"realActivity=(?:ComponentInfo\{)?([\w.]+)/", ligne)):
            paquet = m.group(1)
        if paquet and (m := _RE_ACTIVE.search(ligne)):
            active, inactif = int(m.group(1)) / 1000, float(m.group(2))
            recent = Recent(inactif, active < SECONDES_RECHARGEMENT, active + inactif)
            if paquet not in resultat or recent.inactif < resultat[paquet].inactif:
                resultat[paquet] = recent
    return resultat


# --- Indice d'utilisation et classement --------------------------------------------------

def indice_utilisation(paquet: str, stats: StatsUtilisation, recents: dict[str, Recent]) -> dict:
    """Résume les indices d'utilisation en un code et une phrase pour la personne."""
    recent = recents.get(paquet)
    if recent and not recent.avant_redemarrage:
        return _indice_jours(recent.inactif / SECONDES_PAR_JOUR, "dernière ouverture")
    info = stats.par_paquet.get(paquet, Utilisation())
    if info.jours_depuis_usage is not None:
        return _indice_jours(info.jours_depuis_usage, "dernière utilisation")
    if info.derniere_date:
        return {"code": "recente", "jours": None,
                "texte": f"utilisée le {info.derniere_date[:10]}"}
    if recent:
        return _indice_avant_redemarrage(recent)
    if info.bucket == BUCKET_JAMAIS:
        return {"code": "jamais", "jours": None, "texte": "jamais ouverte selon Android"}
    if info.bucket == BUCKET_RARE:
        return {"code": "rare", "jours": None, "texte": "rarement utilisée selon Android"}
    return {"code": "inconnu", "jours": None,
            "texte": "pas d'ouverture récente connue (statistiques incomplètes)"}


def _indice_avant_redemarrage(recent: Recent) -> dict:
    jours = int(recent.depuis_demarrage / SECONDES_PAR_JOUR)
    quand = "aujourd'hui" if jours < 1 else f"il y a {jours} jour{'s' if jours > 1 else ''}"
    return {"code": "avant_redemarrage", "jours": None,
            "texte": f"pas ouverte depuis le redémarrage de la TV ({quand}), "
                     "mais ouverte au moins une fois avant"}


def _indice_jours(jours: float, libelle: str) -> dict:
    jours_arrondis = int(jours)
    if jours < 1:
        texte = f"{libelle} aujourd'hui"
    else:
        texte = f"{libelle} il y a {jours_arrondis} jour{'s' if jours_arrondis > 1 else ''}"
    code = "recente" if jours <= JOURS_RECENTE else "ancienne"
    return {"code": code, "jours": round(jours, 1), "texte": texte}


def raison_protection(paquet: str, catalogue: dict, contexte: dict) -> str | None:
    """Pourquoi un paquet ne doit jamais être touché, ou None s'il peut l'être."""
    if paquet == contexte.get("lanceur"):
        return "Lanceur d'accueil actif"
    if paquet == contexte.get("clavier"):
        return "Clavier actif"
    if paquet in catalogue["proteges"]:
        return catalogue["proteges"][paquet]
    for prefixe in catalogue["prefixes_proteges"]:
        if paquet.startswith(prefixe):
            return "Composant système essentiel"
    if SEGMENTS_VITAUX & set(re.split(r"[._]", paquet.lower())[1:]):
        return "Téléphonie, SMS, contacts ou alertes d'urgence"
    return None


def nom_suspect(paquet: str) -> bool:
    morceaux = re.split(r"[._]", paquet.lower())
    return any(morceau in MOTS_SUSPECTS for morceau in morceaux[1:])


def classifier(paquet: str, infos: dict, catalogue: dict, contexte: dict) -> dict:
    """Range un paquet dans une catégorie et dit ce qu'on propose d'en faire.

    `infos` : systeme (bool), etat (actif / desactive / retire), visible (bool).
    """
    protection = raison_protection(paquet, catalogue, contexte)
    if protection:
        return _decision("protege", "ne_pas_toucher", protection)
    fiche = catalogue["paquets"].get(paquet)
    if fiche and fiche.get("confiance") != "incertain":
        if infos["etat"] != "actif":
            return _decision(fiche["categorie"], "deja_fait", fiche["role"])
        return _decision(fiche["categorie"], "desactiver", fiche["role"])
    if fiche:
        return _decision("a_verifier", "verifier", fiche["role"])
    if infos.get("visible"):
        if infos.get("systeme") and infos["etat"] == "actif" \
                and contexte.get("famille") not in FAMILLES_TV:
            return _decision("application", "verifier",
                             "Appli préinstallée d'un appareil qui n'est pas une TV reconnue "
                             "(téléphone, tablette, boîtier) : vérifier son rôle avant d'y toucher")
        origine = "préinstallée" if infos.get("systeme") else "installée par vous"
        proposition = "choix_personne" if infos["etat"] == "actif" else "deja_fait"
        return _decision("application", proposition, f"Appli visible, {origine}")
    if nom_suspect(paquet):
        return _decision("a_verifier", "verifier", "Nom évoquant pub, pistage ou démo")
    return _decision("systeme", "ne_pas_toucher", "Service interne")


def _decision(categorie: str, proposition: str, raison: str) -> dict:
    return {"categorie": categorie, "proposition": proposition, "raison": raison}


def nom_humain(paquet: str, catalogue: dict) -> str:
    if paquet in catalogue["noms_humains"]:
        return catalogue["noms_humains"][paquet]
    fiche = catalogue["paquets"].get(paquet)
    return fiche["nom"] if fiche else ""


def famille_appareil(proprietes: dict, fonctions: set[str], paquets: set[str]) -> str:
    """fire-tv, google-tv, android-tv, android-mobile, ou android (famille inconnue).

    android-mobile : téléphone, tablette (dont les tablettes Fire, modèles « KF… »), ou
    boîtier HDMI qui tourne sous l'Android des tablettes, sans interface TV.
    """
    fabricant = proprietes.get("ro.product.manufacturer", "").lower()
    tablette_fire = fabricant == "amazon" and \
        proprietes.get("ro.product.model", "").upper().startswith(PREFIXE_TABLETTE_FIRE)
    if "amazon.hardware.fire_tv" in fonctions or (fabricant == "amazon" and not tablette_fire):
        return "fire-tv"
    if "com.google.android.apps.tv.launcherx" in paquets:
        return "google-tv"
    if FONCTIONS_TV & fonctions:
        return "android-tv"
    if tablette_fire or FONCTIONS_MOBILE & fonctions:
        return FAMILLE_MOBILE
    return "android"
