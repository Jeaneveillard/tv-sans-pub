#!/usr/bin/env python3
"""Trouve les téléviseurs et boîtiers TV du réseau local et dit ce qu'on peut en faire.

Lecture seule : annonces SSDP (UPnP) et mDNS (Apple TV, Google Cast), lecture des fiches
des appareils qui répondent, test de quelques ports connus sur ces seuls appareils.
Rien n'est modifié.

  python decouvrir_tv.py                 découverte (environ 4 secondes)
  python decouvrir_tv.py --tout          inclut aussi ce qui ne ressemble pas à une TV
  python decouvrir_tv.py --json          sortie JSON
  python decouvrir_tv.py --roku IP       modèle et chaînes installées d'un Roku
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import struct
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from analyse_android import texte_affichable

GROUPE_SSDP = ("239.255.255.250", 1900)
CIBLES_SSDP = [
    "ssdp:all",
    "roku:ecp",
    "urn:dial-multiscreen-org:service:dial:1",
    "urn:samsung.com:device:RemoteControlReceiver:1",
    "urn:lge-com:service:webos-second-screen:1",
]
DUREE_ECOUTE = 4.0
REPONSES_MAX_PAR_IP = 40
DELAI_HTTP = 3.0
DELAI_PORT = 0.6
TAILLE_MAX_HTTP = 512 * 1024
PORTS = {
    5555: "adb",          # débogage ADB réseau (Android TV, Fire TV)
    8060: "roku",         # Roku External Control Protocol
    8001: "samsung",      # API Samsung Tizen
    8002: "samsung",
    3000: "lg",           # webOS second screen
    3001: "lg",
    8008: "cast",         # Google Cast intégré
    8009: "cast",
    7345: "vizio",
    1925: "philips",      # JointSpace
    1926: "philips",
    36669: "hisense",     # VIDAA
    9295: "playstation",  # Remote Play (PS4, PS5)
}

GROUPE_MDNS = ("224.0.0.251", 5353)
SERVICES_MDNS = [
    "_airplay._tcp.local",          # Apple TV, et TV compatibles AirPlay
    "_companion-link._tcp.local",   # Apple TV
    "_googlecast._tcp.local",       # Chromecast, Google TV, TV avec Cast intégré
]
DUREE_MDNS = 2.0
TYPE_PTR, TYPE_TXT = 12, 16
CLES_TXT = {"model", "rpmd", "md", "fn", "manufacturer"}  # rpMd : modèle Apple (companion-link)
SAUTS_MAX = 16
ENREGISTREMENTS_MAX = 64
# Décodeurs de fournisseurs (câble, IPTV). Pas les noms de fabricants de modems
# (Technicolor, Sagemcom…), qui désigneraient aussi le routeur.
MARQUEURS_DECODEUR = ("xcal", "rdk", "mediaroom", "set-top", "settop")


def adresse_locale(ip: str) -> bool:
    try:
        adresse = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return adresse.is_private or adresse.is_link_local


def parser_reponse_ssdp(donnees: bytes) -> dict[str, str]:
    """Réponse HTTPU d'une annonce SSDP → en-têtes en minuscules."""
    entetes = {}
    for ligne in donnees.decode("utf-8", errors="replace").split("\r\n")[1:]:
        cle, sep, valeur = ligne.partition(":")
        if sep:
            entetes[cle.strip().lower()] = valeur.strip()
    return entetes


def ecouter_ssdp(duree: float = DUREE_ECOUTE) -> dict[str, list[dict[str, str]]]:
    prise = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    prise.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    prise.settimeout(0.5)
    try:
        for cible in CIBLES_SSDP:
            message = ("M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n"
                       f'MAN: "ssdp:discover"\r\nMX: 2\r\nST: {cible}\r\n\r\n')
            prise.sendto(message.encode("ascii"), GROUPE_SSDP)
    except OSError as exc:
        prise.close()
        print(f"Découverte impossible ({exc}). Pas de réseau, ou un VPN capte le trafic : "
              "le couper, ou demander la marque de la TV.", file=sys.stderr)
        return {}
    reponses: dict[str, list[dict[str, str]]] = {}
    fin = time.monotonic() + duree
    while time.monotonic() < fin:
        try:
            donnees, (ip, _port) = prise.recvfrom(8192)
        except socket.timeout:
            continue
        except OSError:
            break
        liste = reponses.setdefault(ip, []) if adresse_locale(ip) else None
        if liste is not None and len(liste) < REPONSES_MAX_PAR_IP:
            liste.append(parser_reponse_ssdp(donnees))
    prise.close()
    return reponses


def construire_requete_mdns(services: list[str]) -> bytes:
    """Requête DNS-SD (PTR) pour ces services, réponse demandée en direct (bit QU)."""
    entete = struct.pack("!HHHHHH", 0, 0, len(services), 0, 0, 0)
    questions = b""
    for service in services:
        for etiquette in service.strip(".").split("."):
            brut = etiquette.encode("utf-8")
            questions += bytes([len(brut)]) + brut
        questions += b"\x00" + struct.pack("!HH", TYPE_PTR, 0x8001)
    return entete + questions


def _lire_nom(paquet: bytes, position: int) -> tuple[list[str], int]:
    """Nom DNS (avec compression) → étiquettes, et position après le nom."""
    etiquettes: list[str] = []
    suite = None
    sauts = 0
    while True:
        longueur = paquet[position]
        if longueur & 0xC0 == 0xC0:
            sauts += 1
            if sauts > SAUTS_MAX:
                raise ValueError("pointeurs en boucle")
            if suite is None:
                suite = position + 2
            position = ((longueur & 0x3F) << 8) | paquet[position + 1]
            continue
        if longueur == 0:
            return etiquettes, suite if suite is not None else position + 1
        fin = position + 1 + longueur
        if fin > len(paquet):
            raise ValueError("nom tronqué")
        etiquettes.append(paquet[position + 1:fin].decode("utf-8", errors="replace"))
        position = fin


def _lire_txt(donnees: bytes) -> dict[str, str]:
    paires = {}
    position = 0
    while position < len(donnees):
        longueur = donnees[position]
        cle, _sep, valeur = donnees[position + 1:position + 1 + longueur] \
            .decode("utf-8", errors="replace").partition("=")
        if cle.lower() in CLES_TXT:
            paires[cle.lower()] = valeur
        position += 1 + longueur
    return paires


def parser_reponse_mdns(paquet: bytes) -> dict:
    """Réponse mDNS → services annoncés, nom d'instance, quelques clés TXT. {} si abîmée."""
    services: list[str] = []
    nom = ""
    txt: dict[str, str] = {}
    try:
        _id, _drapeaux, questions, *comptes = struct.unpack_from("!HHHHHH", paquet, 0)
        position = 12
        for _ in range(questions):
            _etiquettes, position = _lire_nom(paquet, position)
            position += 4
        for _ in range(min(sum(comptes), ENREGISTREMENTS_MAX)):
            proprietaire, position = _lire_nom(paquet, position)
            type_, _classe, _ttl, longueur = struct.unpack_from("!HHIH", paquet, position)
            debut = position + 10
            position = debut + longueur
            if position > len(paquet):
                raise ValueError("enregistrement tronqué")
            service = ".".join(proprietaire).lower()
            if type_ == TYPE_PTR and service in SERVICES_MDNS:
                instance, _fin = _lire_nom(paquet, debut)
                if service not in services:
                    services.append(service)
                nom = nom or (instance[0] if instance else "")
            elif type_ == TYPE_TXT:
                txt.update(_lire_txt(paquet[debut:position]))
    except (struct.error, ValueError, IndexError):
        return {}
    return {"services": services, "nom": nom, "txt": txt} if services else {}


def ecouter_mdns(duree: float = DUREE_MDNS) -> dict[str, dict]:
    """Interroge les services mDNS des boîtiers TV ; une fiche par IP locale qui répond."""
    prise = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    prise.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    prise.settimeout(0.5)
    try:
        prise.sendto(construire_requete_mdns(SERVICES_MDNS), GROUPE_MDNS)
    except OSError:
        prise.close()
        return {}
    trouves: dict[str, dict] = {}
    fin = time.monotonic() + duree
    while time.monotonic() < fin:
        try:
            donnees, (ip, _port) = prise.recvfrom(9000)
        except socket.timeout:
            continue
        except OSError:
            break
        info = parser_reponse_mdns(donnees) if adresse_locale(ip) else {}
        if not info:
            continue
        fiche = trouves.setdefault(ip, {"services": [], "nom": "", "txt": {}})
        fiche["services"] += [s for s in info["services"] if s not in fiche["services"]]
        fiche["nom"] = fiche["nom"] or info["nom"]
        fiche["txt"] = {**info["txt"], **fiche["txt"]}
    prise.close()
    return trouves


def fiche_depuis_mdns(info: dict) -> dict[str, str]:
    """Annonce mDNS → mêmes clés qu'une fiche UPnP."""
    txt = info.get("txt", {})
    fiche = {}
    nom = txt.get("fn") or info.get("nom", "")
    modele = txt.get("model") or txt.get("rpmd") or txt.get("md", "")
    if nom:
        fiche["friendlyName"] = nom
    if modele:
        fiche["modelName"] = modele
    if txt.get("manufacturer"):
        fiche["manufacturer"] = txt["manufacturer"]
    elif modele.lower().startswith("appletv"):
        fiche["manufacturer"] = "Apple"
    return fiche


class _SansRedirection(urllib.request.HTTPRedirectHandler):
    """Une redirection pourrait mener hors du réseau local : on ne la suit pas."""

    def redirect_request(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


_OUVREUR = urllib.request.build_opener(_SansRedirection)


def lire_http(url: str) -> bytes | None:
    """GET limité aux adresses du réseau local, sans redirection, taille et délai bornés."""
    hote = urlparse(url).hostname or ""
    if urlparse(url).scheme != "http" or not adresse_locale(hote):
        return None
    try:
        with _OUVREUR.open(url, timeout=DELAI_HTTP) as reponse:
            if reponse.status != 200:
                return None
            return reponse.read(TAILLE_MAX_HTTP)
    except (OSError, ValueError):
        return None


def lire_xml(donnees: bytes) -> ET.Element | None:
    """XML venu d'un appareil du réseau : refuse les DTD et entités (expansion)."""
    entete = donnees[:4096].lower()
    if b"<!doctype" in entete or b"<!entity" in donnees.lower():
        return None
    try:
        return ET.fromstring(donnees)
    except ET.ParseError:
        return None


def parser_fiche_upnp(xml: bytes) -> dict[str, str]:
    """Fiche de description UPnP → fabricant, modèle, nom."""
    racine = lire_xml(xml)
    if racine is None:
        return {}
    fiche = {}
    for element in racine.iter():
        balise = element.tag.rsplit("}", 1)[-1]
        if balise in ("friendlyName", "manufacturer", "modelName", "modelNumber") \
                and balise not in fiche and element.text:
            fiche[balise] = element.text.strip()
    return fiche


def ports_ouverts(ip: str) -> list[int]:
    ouverts = []
    for port in PORTS:
        try:
            with socket.create_connection((ip, port), timeout=DELAI_PORT):
                ouverts.append(port)
        except OSError:
            continue
    return ouverts


def deviner_famille(serveurs: str, fiche: dict[str, str], ports: list[int]) -> tuple[str, str]:
    """Famille de système et ce que la compétence peut faire avec."""
    texte = " ".join([serveurs, *fiche.values()]).lower()
    services = {PORTS[p] for p in ports}
    if "appletv" in texte or "apple tv" in texte:
        return "apple-tv", "réglages guidés (tvOS) + blocage DNS"
    if "xbox" in texte:
        return "xbox", "réglages guidés (console) + compte Microsoft"
    if "playstation" in services or "playstation" in texte or "sony interactive" in texte:
        return "playstation", "réglages guidés (console) + compte PlayStation"
    if "roku" in texte or "roku" in services:
        return "roku", "inventaire des chaînes (ECP) + réglages guidés"
    if "amazon" in texte or "fire tv" in texte or \
            fiche.get("modelName", "").lower().startswith("aft"):
        return "fire-tv", _action_android(services)
    if "webos" in texte or "lg electronics" in texte or "lg" in services:
        return "lg-webos", "réglages guidés + blocage DNS"
    if "samsung" in texte and ("samsung" in services or "tizen" in texte or "tv" in texte):
        return "samsung-tizen", "réglages guidés + blocage DNS"
    if "vizio" in texte or "vizio" in services:
        return "vizio", "réglages guidés + blocage DNS"
    if "adb" in services:
        return "android", _action_android(services)
    if any(marqueur in texte for marqueur in MARQUEURS_DECODEUR):
        return "decodeur", "décodeur du fournisseur : réglages guidés + espace client"
    if "eureka" in texte or "chromecast" in texte:
        return "chromecast", ("Chromecast avec Google TV (avec télécommande) : activer ADB ; "
                              "Chromecast classique : pas d'accueil, rien à nettoyer")
    if "cast" in services and any(marque in texte for marque in (
            "android", "google", "sony", "tcl", "philips", "hisense", "nvidia", "xiaomi")):
        return "android-tv?", _action_android(services)
    if "hisense" in texte or "hisense" in services:
        return "hisense", "Google TV, Roku, Fire TV ou VIDAA : demander le système"
    if "philips" in services:
        return "philips", "Android TV ou Saphi : demander le système"
    return "inconnu", ""


def _action_android(services: set[str]) -> str:
    if "adb" in services:
        return "ADB ouvert : inventaire et nettoyage directs"
    return "activer le débogage ADB pour le nettoyage direct"


def decouvrir(tout: bool) -> list[dict]:
    appareils = []
    trouves = ecouter_ssdp()
    annonces_mdns = ecouter_mdns()
    adresses = {ip for ip in [*trouves, *annonces_mdns] if adresse_locale(ip)}
    for ip in sorted(adresses, key=ipaddress.ip_address):
        reponses = trouves.get(ip, [])
        mdns = annonces_mdns.get(ip, {})
        serveurs = " ".join(sorted(({r.get("server", "") for r in reponses} |
                                    {r.get("st", "") for r in reponses} |
                                    set(mdns.get("services", []))) - {""}))
        fiche: dict[str, str] = {}
        for emplacement in sorted({r.get("location", "") for r in reponses if r.get("location")}):
            if urlparse(emplacement).hostname == ip:
                fiche = {**parser_fiche_upnp(lire_http(emplacement) or b""), **fiche}
        fiche = {**fiche_depuis_mdns(mdns), **fiche}
        ports = ports_ouverts(ip)
        famille, action = deviner_famille(serveurs, fiche, ports)
        if famille == "inconnu" and not tout:
            continue
        appareils.append({"ip": ip, "famille": famille, "action": action,
                          "nom": texte_affichable(fiche.get("friendlyName", ""), 60),
                          "fabricant": texte_affichable(fiche.get("manufacturer", ""), 40),
                          "modele": texte_affichable(fiche.get("modelName", ""), 40),
                          "ports": ports, "serveur": texte_affichable(serveurs, 120)})
    return appareils


def parser_apps_roku(xml: bytes) -> list[dict[str, str]]:
    racine = lire_xml(xml)
    if racine is None:
        return []
    return [{"id": texte_affichable(app.get("id", ""), 20),
             "nom": texte_affichable(app.text or "", 60),
             "type": texte_affichable(app.get("type", ""), 20),
             "version": texte_affichable(app.get("version", ""), 20)}
            for app in racine.iter("app")]


def inventaire_roku(ip: str) -> int:
    if not adresse_locale(ip):
        print("Adresse invalide : il faut l'IP locale du Roku (ex. 192.168.1.60).")
        return 1
    infos = lire_http(f"http://{ip}:8060/query/device-info")
    apps = lire_http(f"http://{ip}:8060/query/apps")
    if infos is None or apps is None:
        print("Le Roku ne répond pas. Activer : Paramètres > Système > Paramètres système "
              "avancés > Contrôle par applications mobiles > Accès réseau.")
        return 1
    racine = lire_xml(infos)
    fiche = {e.tag: texte_affichable(e.text or "", 60) for e in racine} if racine is not None \
        else {}
    print(f"# {fiche.get('friendly-device-name', 'Roku')} — {fiche.get('model-name', '?')} "
          f"(Roku OS {fiche.get('software-version', '?')})")
    liste = parser_apps_roku(apps)
    print(f"\n## Chaînes installées ({len(liste)})\n| Nom | Id | Type |\n|---|---|---|")
    for app in liste:
        print(f"| {app['nom']} | {app['id']} | {app['type']} |")
    print("\nRoku ne fournit pas l'historique d'utilisation : demander lesquelles sont ouvertes.")
    return 0


def afficher(appareils: list[dict]) -> None:
    if not appareils:
        print("Aucune TV trouvée. La TV est-elle allumée et sur le même réseau ? "
              "Certaines TV ne répondent pas : demander la marque.")
        return
    print("| IP | Famille | Nom / modèle | Ports | Possible |\n|---|---|---|---|---|")
    for a in appareils:
        nom = " ".join(x for x in (a["nom"], a["fabricant"], a["modele"]) if x) or "?"
        ports = ", ".join(f"{p} ({PORTS[p]})" for p in a["ports"]) or "-"
        print(f"| {a['ip']} | {a['famille']} | {nom} | {ports} | {a['action']} |")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parseur = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawTextHelpFormatter)
    parseur.add_argument("--tout", action="store_true")
    parseur.add_argument("--json", action="store_true")
    parseur.add_argument("--roku", metavar="IP")
    args = parseur.parse_args(argv)
    if args.roku:
        return inventaire_roku(args.roku)
    appareils = decouvrir(args.tout)
    if args.json:
        print(json.dumps(appareils, ensure_ascii=False, indent=2))
    else:
        afficher(appareils)
    return 0


if __name__ == "__main__":
    sys.exit(main())
