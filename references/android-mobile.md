# Téléphones, tablettes et boîtiers Android branchés sur la télé

Tout appareil Android qui n'a **pas** l'interface TV : téléphone ou tablette relié à la
télé (câble USB-C vers HDMI, Samsung DeX, Motorola Smart Connect, envoi d'écran),
tablette Fire d'Amazon, mini-PC ou boîtier HDMI qui tourne sous l'Android des tablettes.
L'inventaire les reconnaît : famille `android-mobile`.

Ce que la télé affiche alors, c'est l'écran de l'appareil : c'est lui qu'on nettoie.
Un boîtier **sans marque** passe d'abord par `autres-appareils.md` (certification Play
Protect). Un boîtier ou une clé avec l'interface TV (Android TV, Google TV) suit
`android-tv.md`.

Ici, on est plus prudent que sur une TV : un téléphone sert aux appels, aux SMS, à la
banque et aux alertes d'urgence.

## D'abord, les réglages (sans ADB)

Les noms varient selon la marque et la version d'Android : si un menu ne correspond pas,
demander une photo de l'écran. Un réglage à la fois.

| Réglage | Chemin (Android 9 et plus) | Effet |
|---|---|---|
| **DNS privé** | Paramètres > Réseau et Internet > DNS privé > Nom d'hôte : `dns.adguard-dns.com`. Samsung : Connexions > Plus de paramètres de connexion. Xiaomi : Connexion et partage. | Filtre les pubs et le pistage dans presque toutes les applis et les navigateurs, en Wi-Fi comme en données mobiles. Voir `blocage-dns.md`. |
| **Identifiant publicitaire** | Paramètres > Confidentialité (ou Google) > Annonces > Supprimer l'identifiant publicitaire | Pubs non ciblées |
| **Confidentialité dans les annonces** (Android 13 et plus) | Même menu : désactiver les thèmes des annonces, les annonces suggérées par les applis et la mesure des annonces | Moins de profilage |
| **Utilisation et diagnostics** | Paramètres > Google > Tous les services (ou ⋮) > Utilisation et diagnostics : désactivé | Moins de données envoyées |
| **Notifications** | Paramètres > Notifications > par appli : couper celles qui font de la promotion | Fin des pubs en notification |

### Par marque

- **Samsung** : Paramètres > Sécurité et confidentialité > Plus de paramètres de
  confidentialité : « Service de personnalisation » désactivé, « Envoyer des données de
  diagnostic » désactivé. Galaxy Store > Menu > Paramètres : couper les notifications
  promotionnelles.
- **Xiaomi, Redmi, POCO** (MIUI, HyperOS) : Paramètres > Mots de passe et sécurité >
  Autorisation et révocation : retirer **msa**. Paramètres > Mots de passe et sécurité >
  Confidentialité > Services publicitaires : « Recommandations d'annonces
  personnalisées » désactivé. Dans chaque appli système (Sécurité, Thèmes, Gestionnaire
  de fichiers, Téléchargements) : Paramètres > « Recevoir des recommandations » désactivé.
- **Tablettes Fire (Amazon)** : Paramètres > Applis et notifications > Paramètres des
  applis Amazon > Écrans d'accueil : désactiver les recommandations. Les pubs de l'écran
  de verrouillage (« Offres spéciales ») ne s'enlèvent qu'en payant Amazon, dans le
  compte : Gérer votre contenu et vos appareils > l'appareil > Offres spéciales. Le dire
  franchement.
- **Pixel, Motorola, Nokia** : peu de pubs ; les réglages du tableau suffisent.

## Ensuite, si la personne le veut : l'inventaire par ADB

1. Activer les options pour les développeurs : Paramètres > À propos du téléphone >
   toucher **7 fois** « Numéro de build » (Samsung : À propos du téléphone > Informations
   sur le logiciel > Numéro de version).
2. Paramètres > Système > Options pour les développeurs > **Débogage USB**, puis brancher
   l'appareil à l'ordinateur par câble : `adb devices` le liste, et l'appareil demande
   d'autoriser l'ordinateur. Sans câble (Android 11 et plus) : **Débogage sans fil** et
   `appairer`, comme dans `android-tv.md`.
3. `python scripts/tv_android.py inventaire --appareil <série ou IP:port>`

Sur cette famille, le script est volontairement limité :

- Il propose seulement les **paquets de pub et de pistage connus** du catalogue (MSA et
  statistiques Xiaomi, services préinstallés de Meta…) et les **applis installées par la
  personne**.
- Une **appli préinstallée** n'est jamais proposée d'office. Si la personne veut en
  couper une (jeu ou réseau social préinstallé par l'opérateur) : chercher son rôle,
  obtenir un oui pour ce paquet précis, puis `--autoriser <paquet>`.
- Il **refuse toujours**, même avec `--autoriser` : téléphone, appels, SMS, contacts,
  alertes d'urgence, carte SIM, NFC, l'accueil, le clavier, les réglages, le Play Store et
  les services de sécurité de la marque. Cette protection ne dépend pas d'une liste
  complète : tout paquet dont le nom évoque la téléphonie (`dialer`, `telephony`, `ims`,
  `messaging`, `cellbroadcast`, `emergency`…) est refusé.
- Si l'inventaire affiche la famille `android` (appareil non reconnu, ou réponse
  incomplète de l'appareil), les mêmes garde-fous s'appliquent : relancer l'inventaire
  avant de conclure.

Tout reste réversible : désactivation seulement, fichier de restauration écrit avant.

## À la fin

Couper le débogage USB et le débogage sans fil. Sur un téléphone, c'est encore plus
important que sur une TV : il sort de la maison.

## Limites

- Les pubs **dans** les applis (YouTube, jeux gratuits) : le DNS en retire une partie,
  jamais celles servies par le même serveur que le contenu.
- Pas de root, pas d'applis modifiées, pas de contournement d'achats.
- Un profil professionnel ou un téléphone géré par un employeur : ne pas y toucher.
