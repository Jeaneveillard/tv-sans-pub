# TV sans pub

Une compétence (*skill*) pour [Claude Code](https://claude.com/claude-code) qui nettoie
les téléviseurs intelligents et tout ce qui se branche dessus (boîtiers de streaming,
Apple TV, consoles, décodeurs, boîtiers IPTV…) : publicités de l'écran d'accueil,
contenus sponsorisés, pistage (reconnaissance de contenu, identifiant publicitaire,
statistiques) et applications préinstallées qu'on n'ouvre jamais.

Elle parle français, explique chaque terme technique et ne change rien sans un « oui »
explicite.

## Ce qu'elle fait

| Famille | Exemples | Moyen |
|---|---|---|
| Fire TV | Fire TV Stick, Fire TV Cube, TV Fire TV | Action directe par ADB + réglages |
| Android TV / Google TV | Chromecast avec Google TV, Shield, boîtiers et clés HDMI, Sony, TCL, Hisense, Philips | Action directe par ADB + réglages |
| Android sans interface TV | Téléphone ou tablette branché en HDMI, tablette Fire, mini-PC et boîtier HDMI | Réglages guidés + DNS privé ; ADB avec garde-fous (jamais la téléphonie) |
| Roku | Roku, TCL Roku TV | Inventaire des chaînes à distance + réglages guidés |
| Samsung (Tizen) | Toutes depuis 2015, menus 2025 compris | Réglages guidés |
| LG (webOS) | Toutes depuis 2014 | Réglages guidés |
| Autres smart TV | Sony, TCL, Hisense, Philips, Panasonic, Sharp, Toshiba, Insignia, Vizio, Xiaomi… | Selon le système (table des marques) |
| Apple TV | Apple TV HD, Apple TV 4K | Réglages guidés |
| Consoles | PlayStation 4 et 5, Xbox One et Series, Nintendo Switch | Réglages guidés + compte en ligne |
| Autres appareils | Décodeurs des fournisseurs, boîtiers IPTV, boîtiers Android sans marque, Blu-ray, barres de son, projecteurs, ordinateurs | Selon l'appareil |

Sur tous les appareils, elle peut aussi proposer un **blocage par DNS** (AdGuard DNS,
NextDNS, Pi-hole), réglé sur l'appareil ou sur le routeur, et elle repère un VPN sur le
routeur qui court-circuiterait ce filtre.

La découverte réseau (`scripts/decouvrir_tv.py`, lecture seule) trouve les appareils
qui s'annoncent par SSDP/UPnP ou mDNS (AirPlay, Google Cast). Pour un boîtier Android
**sans marque**, la compétence fait d'abord vérifier la certification Play Protect
(alerte du FBI de juin 2025 sur les boîtiers infectés dès l'usine).

## Principes

- **Rien ne change sans accord.** Inventaire en lecture seule, plan proposé, la personne
  choisit, puis application.
- **Réversible par défaut.** Sur Android, les paquets sont désactivés (pas supprimés) et un
  fichier de restauration est écrit avant chaque modification.
- **Jamais toucher** au lanceur d'accueil, au clavier, aux mises à jour de sécurité, à la
  voix ni à la connexion du compte. Le script refuse ces paquets.
- **Pas de piratage.** Sur Samsung, LG et Roku, on guide les réglages officiels.
- **Honnête sur les limites.** Les pubs *dans* YouTube, Prime Video ou Netflix ne
  relèvent pas de cette compétence ; elle ne propose ni appli modifiée ni contournement
  d'abonnement.

## Installation

Il faut [Claude Code](https://claude.com/claude-code), **Python 3.8+** (bibliothèque
standard seulement) et, pour Fire TV et Android TV,
[adb](https://developer.android.com/tools/releases/platform-tools) dans le `PATH`.

```bash
git clone https://github.com/<compte>/tv-sans-pub.git ~/.claude/skills/tv-sans-pub
```

Sous Windows, le dossier est `%USERPROFILE%\.claude\skills\tv-sans-pub`.

## Utilisation

Dans Claude Code, il suffit de demander, par exemple :

- « Enlève les pubs de mon Fire TV Stick »
- « Nettoie ma télé Samsung »
- « Quelles télés y a-t-il sur mon réseau ? »

Les fichiers de travail (inventaires, plans, fichiers de restauration, rapports) sont
écrits dans `~/Documents/TV sans pub/`.

## Contenu

```
SKILL.md                    instructions de la compétence
references/                 un guide par famille d'appareil + blocage DNS
scripts/decouvrir_tv.py     découverte réseau (SSDP, mDNS, ports connus), inventaire Roku
scripts/tv_android.py       connexion, inventaire, application, restauration par ADB
scripts/analyse_android.py  classement des paquets
scripts/catalogue_paquets.json  paquets connus : pubs, pistage, superflus, protégés
assets/                     gabarits du plan et du rapport
tests/                      tests unitaires
```

## Tests

```bash
python -m unittest discover -s tests
```

## Licence

MIT, voir [LICENSE](LICENSE).
