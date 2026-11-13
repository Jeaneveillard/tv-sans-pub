# Autres systèmes

D'abord, vérifier le vrai système : beaucoup de marques vendent plusieurs plateformes, et
les combinaisons changent selon le pays et l'année. L'écran d'accueil et le menu
« À propos » le disent. Si c'est Android TV, Google TV, Fire TV ou Roku : utiliser le
guide correspondant.

| Marque | Systèmes possibles |
|---|---|
| Sony | Google TV / Android TV (couper aussi « Samba TV », voir `android-tv.md`) |
| TCL | Google TV, Roku, Fire TV |
| Hisense | Google TV, Roku, Fire TV, VIDAA |
| Philips | Google TV / Android TV, Roku, Saphi, Titan OS |
| Panasonic | Fire TV (2024 et plus), Android TV, My Home Screen |
| Sharp | Google TV / Android TV, Roku |
| Toshiba | Fire TV, VIDAA, Android TV |
| Insignia | Fire TV, Roku |
| Xiaomi, Skyworth, Coocaa | Google TV / Android TV |
| Westinghouse, Element, JVC, onn | Roku (certaines onn : Google TV) |
| Vizio | SmartCast / Vizio OS (voir plus bas) |
| Grundig, Telefunken, Metz, Loewe | selon le modèle : Android TV, VIDAA, Titan OS, système maison |

## Méthode générale (tout système sans accès ADB)

Parcourir les réglages avec la personne, un menu à la fois, en cherchant ces mots :

| Mot clé dans les menus | Action |
|---|---|
| ACR, Informations de visionnage, Viewing Information, Viewing Data, Smart TV Experience, Live Plus, Samba TV | Désactiver |
| Publicité ciblée, basée sur les centres d'intérêt, personnalisation des annonces | Désactiver |
| Identifiant publicitaire | Réinitialiser, ou limiter le suivi |
| Lecture automatique, aperçus vidéo, démarrage automatique de l'accueil | Désactiver |
| Recommandations, contenu promu, promotion de l'accueil | Désactiver |
| Accords, consentements, conditions | Retirer ceux sur le visionnage et la pub ; garder les conditions générales |

## Vizio (SmartCast)

Menu > **Admin et confidentialité** (« Admin & Privacy ») > **Données de visionnage** :
désactivé. Dans le même menu, la section **Publicité** : limiter le suivi publicitaire.
Les applis intégrées de SmartCast ne se suppriment pas.

## Hisense VIDAA

Paramètres > Système (ou Assistance) > chercher **Confidentialité**, **Avis de
confidentialité**, **Informations de visionnage** et **Publicité** ; désactiver ce qui
concerne le visionnage et la pub. Retirer les applis : Accueil > Applis > appui long >
supprimer, quand c'est permis.

## Panasonic My Home Screen

Menu > Réseau > **Paramètres de confidentialité** (ou Configuration > Réglages de
confidentialité) : refuser la collecte de données de visionnage et la publicité ciblée.

## Philips Saphi et Titan OS

Réglages > Paramètres généraux > **Confidentialité** ou **Conditions d'utilisation** :
retirer les consentements de publicité et de suivi. Peu d'applis sont supprimables.

## Quand rien ne suffit

Le blocage DNS (`blocage-dns.md`) marche sur toutes les marques. Et, honnêtement : un
boîtier séparé (Apple TV, Nvidia Shield, ou une clé Android TV nettoyée avec cette
compétence) branché sur une TV laissée hors ligne est la façon la plus radicale d'en
finir avec les pubs du téléviseur. Le mentionner une fois, sans insister.
