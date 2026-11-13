# Autres appareils branchés sur la télé

Décodeurs des fournisseurs, boîtiers IPTV, boîtiers Android sans marque, lecteurs
Blu-ray, barres de son, projecteurs et ordinateurs. Pour chacun, d'abord trouver le vrai
système : beaucoup tournent sous Android TV, Fire TV ou Roku, et ont alors leur guide.

## Décodeurs des fournisseurs (câble, fibre, IPTV)

Exemples : Vidéotron Helix, Rogers Ignite, Xfinity (plateforme X1), Bell Fibe, Telus
Optik, Cogeco, DirecTV. Le fournisseur gère l'appareil.

- **Ne pas les modifier par ADB**, même quand ils tournent sous Android : le fournisseur
  les verrouille, et une désactivation peut couper le service de télé.
- Dans les réglages du décodeur, chercher : confidentialité, consentements, données de
  visionnage, recommandations, publicité. Désactiver ce qui touche au visionnage et à la
  pub.
- Dans l'**espace client en ligne** du fournisseur : section confidentialité ou
  consentements. C'est souvent là que se refuse l'usage des données de visionnage.
- Les pubs des chaînes de télé en direct ne se retirent pas.
- Ces services exigent souvent d'être **sur le réseau du fournisseur, dans le pays** : un
  VPN sur le routeur les bloque (voir `blocage-dns.md`).

## Boîtiers IPTV

- **MAG** (Infomir, système Linux) : peu de pubs ; rien à nettoyer côté système.
- **Formuler, Buzz TV et autres boîtiers Android** : guide `android-tv.md`.
- Ne jamais aider à contourner un abonnement ni installer une appli modifiée.

## Boîtiers Android sans marque (T95, X96, H96, MXQ…)

Prudence : le 5 juin 2025, le FBI a averti (alerte I-060525-PSA, ic3.gov) que des
boîtiers TV, projecteurs et cadres photo Android **non certifiés Play Protect**, souvent
sans marque, sont infectés par le réseau BADBOX 2.0, parfois dès l'usine. Le nettoyage
ADB ne suffit pas quand le logiciel malveillant est dans le système lui-même.

- Vérifier la certification : Play Store > Paramètres > À propos > **Certification Play
  Protect**. « Non certifié », ou pas de Play Store : le dire franchement.
- Conseiller de **remplacer** l'appareil par un boîtier certifié ou de marque, plutôt que
  de le nettoyer. En attendant, le débrancher du réseau quand il ne sert pas.

## Lecteurs Blu-ray et barres de son

- **Lecteur Blu-ray connecté** (Samsung, LG, Sony…) : peu de pubs. Même logique que la TV
  de la marque pour la confidentialité. S'il ne sert jamais aux applis, le laisser hors
  réseau, ou couper la « veille réseau ».
- **Barre de son avec assistant vocal** (Alexa, Google) : bouton qui coupe le micro ; les
  réglages de confidentialité se font dans l'appli de l'assistant sur le téléphone.
- Garder les mises à jour du micrologiciel.

## Projecteurs intelligents

Selon le système : Android TV (XGIMI, Nebula…), Tizen (Samsung Freestyle), webOS (LG
CineBeam), Fire TV ou Roku intégrés. Utiliser le guide correspondant.

## Ordinateur branché sur la télé

Hors du cœur de cette compétence, mais rapide à faire.

- **Windows 11** : Paramètres > Confidentialité et sécurité > **Général** : tout
  désactiver (identifiant de publicité, contenu suggéré…). Paramètres > Personnalisation
  > **Accueil** (Start) : désactiver les recommandations de conseils et de nouvelles
  applis. Personnalisation > **Écran de verrouillage** : désactiver les « anecdotes,
  astuces et conseils ».
- **Mac** : Réglages Système > Confidentialité et sécurité > **Publicité Apple** :
  désactiver les publicités personnalisées ; **Analyse et améliorations** : désactiver.

## Téléphone ou tablette qui « envoie » vers la télé

Cast ou AirPlay : rien à nettoyer sur la télé pour ça. Le nettoyage se fait sur l'appareil
qui reçoit (TV, Chromecast, Apple TV).
