# Samsung (Tizen)

Aucun accès système possible sans pirater la TV : on ne le fait pas. On guide les réglages,
on retire les applis supprimables, et on propose le blocage DNS.

Demander l'année du modèle (étiquette au dos, ou Paramètres > Assistance > À propos de ce
téléviseur). Les menus ont changé en 2022, puis encore en 2025. La lettre qui suit le
numéro de la série donne l'année : B = 2022, C = 2023, D = 2024, F = 2025 (ex.
QN55QN90**F**, UN50U8000**F**).
En lecture seule, `http://<IP>:8001/api/v2/` donne le modèle, la langue des menus
(`Language`) et l'état (`PowerState`), sans appairage.

## Modèles 2025 (vérifié sur deux TV, menus anglais et français)

| Étape | Anglais | Français |
|---|---|---|
| Confidentialité | General & Privacy > Terms & Privacy > **Terms & Conditions** | Général et confidentialité > Conditions et confidentialité > écran « Conditions et avis de confidentialité » |
| Démarrage | **Advanced Features** > Start Screen Option | **Fonctions avancées** > Option d'écran d'accueil |
| Applis | Support > **Device Care** > **Manage Storage** | Assistance > Device Care (le nom varie) > Gérer le stockage |
| DNS | **Connection** > Network > Network Status > IP Settings | **Connexion** > Réseau > État du réseau > Paramètres IP |

- **Privacy Center** n'a rien à couper : il explique seulement. Les cases sont dans
  Terms & Conditions : décocher « Viewing Information Services » / « Services basés sur
  les informations de visionnage », « Interest-Based Advertising » / « … marketing fondé
  sur les intérêts », et l'Art Store si la personne ne s'en sert pas. Laisser acceptées
  les Conditions de Samsung et l'Avis de confidentialité de Smart Hub (sinon plus
  d'applis). La case « J'accepte toutes les conditions » se décoche seule ; valider par OK.
- Démarrage : « Start with Smart Hub Home » et « Autorun Samsung TV Plus » sur Off.
- L'écran Applis n'a plus d'icône ⚙ : passer par Manage Storage (cocher, Delete, OK).
  Pour réinstaller une appli supprimée par erreur : la **loupe** de la barre de gauche
  de l'accueil. Une activation IPTV payée est liée à la TV (adresse MAC), pas à l'appli.
- DNS : laisser l'IP en automatique, DNS « Enter manually », un seul champ (94.140.14.14).

## Réglages de confidentialité et de pub

| Modèles | Chemin |
|---|---|
| 2022 et plus | Paramètres > Tous les paramètres > **Général et confidentialité** > **Conditions et confidentialité** > **Choix de confidentialité** |
| 2018 à 2021 | Paramètres > **Assistance** > **Conditions et confidentialité** > **Choix de confidentialité** (ou « Paramètres de confidentialité ») |

Dans ce menu :
- **Services d'informations de visionnage** : désactivé. C'est l'ACR (la TV reconnaît ce
  qui passe à l'écran, même sur HDMI).
- **Publicité basée sur les centres d'intérêt** : désactivé.
- **Services de reconnaissance vocale** : au choix de la personne (désactiver coupe la
  commande vocale).
- Si présent, « Réinitialiser l'identifiant publicitaire ».

Samsung propose aussi ces choix pour tous ses appareils dans le compte Samsung en ligne
(tableau de bord de confidentialité).

## Démarrage et accueil

- 2022 et plus : Général et confidentialité > **Options de l'écran de démarrage** :
  ne pas démarrer sur Smart Hub / Accueil si la personne préfère la dernière source.
- 2018 à 2021 : Général > **Fonctions intelligentes** > « Exécution auto de Smart Hub » :
  désactivé ; « Exécution auto de la dernière appli » : au choix.
- Si **Samsung TV Plus** se lance tout seul, chercher l'option d'exécution automatique dans
  le même menu. Samsung TV Plus ne se désinstalle pas.

## Retirer les applis

Accueil > **Applis** > icône ⚙ (Paramètres, en haut à droite) > choisir l'appli >
**Supprimer**. Les applis préinstallées par Samsung n'offrent souvent que « Retirer de
l'accueil » ou rien : le dire franchement. Demander lesquelles la personne n'ouvre pas ;
Tizen n'expose pas l'historique d'utilisation.

## DNS

Paramètres > Général (et confidentialité) > **Réseau** > État du réseau > **Paramètres IP**
> Paramètres DNS : **Saisir manuellement**. Voir `blocage-dns.md`. Certaines applis
Samsung tombent en panne si on bloque trop de domaines Samsung : y aller par étapes.
