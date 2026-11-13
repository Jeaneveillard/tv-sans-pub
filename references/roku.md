# Roku

Lecteurs Roku et téléviseurs « Roku TV » (TCL, Hisense, Sharp, Westinghouse, Philips Roku).

## Inventaire des chaînes à distance

`python scripts/decouvrir_tv.py --roku <IP>` lit le modèle et la liste des chaînes
(protocole ECP, lecture seule). Si le Roku ne répond pas :
Paramètres > Système > **Paramètres système avancés** > **Contrôle par applications
mobiles** > Accès réseau : « Par défaut » ou « Permissif ».
Adresse IP : Paramètres > Réseau > **À propos**.

Roku ne donne pas l'historique d'utilisation et ne permet pas de supprimer à distance :
montrer la liste, demander lesquelles la personne n'ouvre jamais, puis guider.

## Retirer une chaîne

Sur l'accueil, placer le curseur sur la chaîne > touche **✱** de la télécommande >
**Supprimer la chaîne** > confirmer. Les chaînes préinstallées par le fabricant se
suppriment aussi, sauf quelques-unes (Live TV, The Roku Channel).

## Réglages

| Où | Quoi | Effet |
|---|---|---|
| Paramètres > **Confidentialité** > **Expérience Smart TV** (Roku TV seulement) | « Utiliser les informations des entrées TV » : décoché | Coupe l'ACR, y compris sur HDMI et antenne |
| Paramètres > Confidentialité > **Publicité** | « Limiter le suivi publicitaire » (ancien) ou couper la personnalisation des annonces ; réinitialiser l'identifiant | Pubs non ciblées |
| Paramètres > **Écran d'accueil** (Roku OS 12 et plus) | Masquer « Que regarder », « Gratuit », « Sports », « TV en direct » si non utilisés | Accueil moins chargé |
| Paramètres > Thème > **Écrans de veille** | Choisir un écran de veille sans contenu promu | — |
| Paramètres > Confidentialité > **Accès au microphone** | Au choix | — |

## Limites à dire

Le grand encart publicitaire à droite de l'accueil Roku ne se retire pas par les
réglages. Le blocage DNS (`blocage-dns.md`) peut le vider partiellement, mais peut aussi
casser des chaînes : tester une liste à la fois.
