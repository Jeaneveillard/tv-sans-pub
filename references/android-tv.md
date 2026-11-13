# Android TV et Google TV

Boîtiers et clés HDMI : Chromecast avec Google TV, Google TV Streamer, Nvidia Shield,
Xiaomi TV Box et TV Stick, onn, Mecool, Homatics, Formuler, Realme. Téléviseurs : Sony
Bravia, TCL, Hisense (modèles Google TV), Philips (Android), Sharp, Xiaomi, Toshiba
(Android). Projecteurs sous Android TV. Tout le travail ADB de `scripts/tv_android.py`
s'applique.

Un boîtier **sans marque**, ou qui affiche un accueil de tablette plutôt que l'accueil
TV : voir d'abord `autres-appareils.md` (certification Play Protect), puis
`android-mobile.md`. Un téléphone ou une tablette branché en HDMI : `android-mobile.md`.

Google TV = la nouvelle interface (onglets « Pour vous », « Films », « Séries »).
Android TV = l'ancienne (rangées de « chaînes » sous les applis). L'inventaire le détecte.

## Activer le débogage ADB

1. **Google TV** : Paramètres > Système > À propos > cliquer **7 fois** sur
   « Build du système d'exploitation Android TV ».
   **Android TV** : Paramètres > Préférences de l'appareil > À propos > **Build**, 7 fois.
2. Revenir : Paramètres > Système (ou Préférences de l'appareil) > **Options pour les
   développeurs** > **Débogage USB** : activé. Sur la plupart des TV, cela ouvre aussi
   l'ADB réseau sur le port 5555.
3. Si `connecter` échoue sur Android 11 ou plus récent (Google TV Streamer, TV récentes) :
   activer **Débogage sans fil**, choisir « Associer l'appareil avec un code », puis
   `python scripts/tv_android.py appairer <IP>:<port affiché> <code>` et enfin
   `connecter <IP>:<port de connexion>` (les deux ports sont différents).
4. Adresse IP : Paramètres > Réseau et Internet > (le réseau) .

## Réglages à couper

| Où | Quoi | Effet |
|---|---|---|
| Google TV : Paramètres > **Comptes et connexion** > (profil) | **Mode Applications uniquement** : activé | Retire les recommandations personnalisées de l'accueil. Coupe aussi la recherche et l'Assistant Google ; des contenus sponsorisés peuvent rester. Le dire avant. |
| Paramètres > **Confidentialité** > **Annonces** | Désactiver la personnalisation des annonces ; réinitialiser ou supprimer l'identifiant publicitaire | Pubs non ciblées |
| Paramètres > Confidentialité > **Utilisation et diagnostics** | Désactivé | Moins de données envoyées |
| Android TV : Paramètres > Préférences de l'appareil > **Écran d'accueil** | « Aperçus vidéo » et « Aperçus audio » : désactivés ; décocher les **chaînes** des applis inutiles | Plus de vidéos qui démarrent seules |
| Sony : Paramètres > Préférences de l'appareil > … **Samba Interactive TV** (ou « Samba TV ») | Désactivé / retirer le consentement | Coupe l'ACR de Samba |
| TCL, Hisense, Philips : Paramètres > **Confidentialité** ou **Conditions** | Tout ce qui parle d'« informations de visionnage », « ACR », « Smart TV Experience » : désactivé | Coupe la reconnaissance de contenu |

## Paquets

- **Ne jamais désactiver le lanceur** (`com.google.android.apps.tv.launcherx`,
  `com.google.android.tvlauncher`) : sur certaines TV, l'appareil se réinitialise ou n'a
  plus d'accueil. Les recommandations se coupent par le mode Applications uniquement.
- `com.google.android.katniss` (recherche vocale) et `com.google.android.apps.mediashell`
  (Chromecast intégré) sont protégés : la personne s'en sert souvent sans le savoir.
- Applis préinstallées fréquentes, proposées si jamais ouvertes : YouTube Music, YouTube
  Kids, Google Play Films (« Google TV »), Play Jeux, applis du fabricant (Sony Select,
  TCL Channel, Philips TV Collection, Mi Channel / PatchWall).
- Les paquets des puces (`com.mediatek.`, `com.realtek.`, `com.droidlogic`, `com.mstar.`,
  `com.amlogic.`) font marcher l'image, le son et la télécommande : protégés.

## DNS privé (option ADB, Android 9 et plus)

Android TV accepte un DNS filtrant chiffré sans toucher au routeur. À proposer comme
étape du plan, avec l'accord de la personne :

```bash
adb -s <appareil> shell settings put global private_dns_mode hostname
adb -s <appareil> shell settings put global private_dns_specifier dns.adguard-dns.com
```

Annuler : `settings put global private_dns_mode opportunistic`. Noter la valeur d'avant
(`settings get global private_dns_mode`) dans le rapport. Voir `blocage-dns.md` pour les
fournisseurs et les effets secondaires.
