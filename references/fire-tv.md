# Fire TV (Fire OS)

Firestick, Fire TV Cube, Fire TV Stick 4K, et téléviseurs « Fire TV Edition » (Toshiba,
Insignia, Panasonic depuis 2024, certains Hisense et Grundig). Fire OS est un Android
modifié : tout le travail ADB de `scripts/tv_android.py` s'applique.

## Activer le débogage ADB

1. Paramètres > **Ma Fire TV** > **Options pour les développeurs**.
   Si ce menu n'existe pas : Ma Fire TV > **À propos**, puis cliquer **7 fois** sur le nom
   de l'appareil (« Fire TV Stick 4K », etc.). Un message confirme le mode développeur.
2. **Débogage ADB** : Activé.
3. Adresse IP : Ma Fire TV > À propos > **Réseau**.
4. Sur l'ordinateur : `python scripts/tv_android.py connecter <IP>` ; accepter la fenêtre
   sur la TV (« Toujours autoriser depuis cet ordinateur »).

## Réglages à couper (à faire même avec ADB)

Les libellés varient un peu selon la version de Fire OS ; chercher le mot clé.

| Où | Quoi | Effet |
|---|---|---|
| Paramètres > Préférences > **Contenu en vedette** | « Autoriser la lecture vidéo automatique » et « audio automatique » : **Désactivé** | Les pubs vidéo de l'accueil deviennent des images fixes |
| Paramètres > Préférences > **Paramètres de confidentialité** | « Données d'utilisation de l'appareil » : Désactivé | Moins de données envoyées |
| idem | « Collecter les données d'utilisation des applications » : Désactivé | idem |
| idem | « **Publicités basées sur les centres d'intérêt** » : Désactivé | Pubs non ciblées |
| Paramètres > Préférences > **Paramètres de notification** | Couper les notifications des applis inutiles | Moins d'alertes promotionnelles |
| Paramètres > Affichage et sons > **Écran de veille** | Choisir une collection de photos, ou couper « Expérience ambiante » si présente | Moins de contenus mis en avant au repos |
| Accueil > rangée des applis > appui long (bouton ☰) | **Retirer** ou déplacer les icônes inutiles | Accueil plus propre, sans rien désactiver |

## Paquets

Le catalogue contient les paquets Fire TV connus (pubs, pistage, tutoriels). Points
particuliers à dire à la personne :

- **La grande bannière en haut de l'accueil reste.** Elle fait partie du lanceur Amazon
  (`com.amazon.tv.launcher`), qu'on ne désactive jamais : sans lui, plus d'accueil.
  Couper la lecture automatique et `com.amazon.sneakpeek` la rend fixe et silencieuse.
- **Lanceur alternatif** : on peut installer un autre lanceur et l'ouvrir à la main, mais
  depuis 2023 Amazon empêche de remplacer le bouton Accueil. Ne pas promettre plus.
- **Alexa** : sur un Fire TV Cube, ne rien toucher qui commence par `com.amazon.alexa`,
  `com.amazon.vizzini` ou `amazon.speech` (le catalogue les protège déjà).
- **Promotions Amazon** (`com.amazon.device.sale.service`) : ne pas le désactiver. Il garde
  la liste des notifications bloquées ; sans lui, Paramètres > Préférences > Paramètres de
  notification > Notifications des applications plante à chaque clic et ramène à
  Préférences (journal : « Unknown URL content://com.amazon.device.sale.provider/… »).
  S'il est déjà désactivé : `adb -s <appareil> shell pm enable com.amazon.device.sale.service`.
- **Mises à jour** : ne jamais désactiver `com.amazon.device.software.ota*` ni
  `com.amazon.tv.forcedotaupdater.v2`. Bloquer les mises à jour laisse des failles ouvertes.
- **Refus** : sur Fire OS 7.6 et plus, Amazon empêche de désactiver certains paquets
  (message « Shell cannot change component state »). Le script le signale. Le repli
  `--repli-desinstaller` retire le paquet pour l'utilisateur seulement ; il se restaure
  avec `cmd package install-existing`. Le proposer, ne pas l'imposer.
- **Après une mise à jour** de Fire OS, des paquets reviennent souvent. Relancer
  l'inventaire et réappliquer le même plan.
- **Applis Amazon préinstallées** (Amazon Music, Amazon Photos, Jeux, Freevee, miniTV) :
  ce sont les « sponsors » maison. Elles apparaissent dans « Applications visibles » :
  les proposer à la désactivation si la personne ne les ouvre pas.

## Blocage DNS

Fire TV n'offre pas de réglage DNS en Wi-Fi standard dans ses menus (seulement en IP
statique, dans Réseau > Wi-Fi > « Rejoindre » avec configuration avancée). Deux moyens
simples :

- **DNS privé par ADB** (vérifié sur Fire OS 7 et Fire OS 8) : les mêmes commandes que pour
  Android TV (voir `android-tv.md`, section « DNS privé »). Il marche aussi quand le
  routeur passe par un VPN. Le noter dans le plan et faire valider avant.
- **DNS sur le routeur** : couvre toute la maison, voir `blocage-dns.md`.

Une liste dédiée existe
(Perflyst « AmazonFireTV »). Bloquer trop de domaines Amazon peut vider l'accueil ou
casser l'Appstore : y aller progressivement.
