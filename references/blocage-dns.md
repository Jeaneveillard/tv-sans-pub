# Blocage au niveau du réseau (DNS)

## L'idée, en une phrase

Avant d'afficher une pub, la TV demande « quelle est l'adresse de serveur-de-pub.com ? ».
Un DNS filtrant répond « inconnu » pour les serveurs de pub et de pistage : la pub ne
s'affiche pas. Ça marche pour toutes les marques, mais ça ne fait rien pour les pubs
servies depuis le même domaine que la vidéo (YouTube, Prime Video, Netflix avec pub).

## Trois niveaux, du plus simple au plus complet

1. **DNS public filtrant, réglé sur la TV.** Aucune installation.
   - AdGuard DNS : `94.140.14.14` et `94.140.15.15` (DNS privé Android :
     `dns.adguard-dns.com`).
   - NextDNS : compte gratuit (quota mensuel limité), configurable ; il offre des
     protections contre le pistage « natif » par marque (Samsung, Roku, Amazon, Xiaomi…).
2. **DNS filtrant réglé sur le routeur.** Couvre toute la maison d'un coup. Chercher
   « DNS » dans l'interface du routeur (souvent 192.168.1.1) ; certains routeurs de
   fournisseurs ne le permettent pas.
3. **Pi-hole ou AdGuard Home** à la maison (Raspberry Pi, vieux PC, NAS). Contrôle total,
   journal des requêtes pour voir ce que la TV contacte. Listes utiles :
   - Perflyst SmartTV : `https://raw.githubusercontent.com/Perflyst/PiHoleBlocklist/master/SmartTV.txt`
   - Perflyst Fire TV : `https://raw.githubusercontent.com/Perflyst/PiHoleBlocklist/master/AmazonFireTV.txt`
   - HaGeZi « Native Tracker » (listes par marque)

## Effets secondaires à annoncer

- Une liste trop agressive peut **vider l'accueil**, casser la **connexion au compte**,
  l'**Appstore**, ou une appli précise. Ajouter une liste à la fois, tester, et garder
  une liste blanche pour ce qui casse.
- Certains appareils ignorent le DNS réglé et utilisent un DNS codé en dur (souvent
  8.8.8.8). Sur Pi-hole ou AdGuard Home, une règle du routeur qui redirige le port 53 règle
  ça ; c'est une étape avancée, la proposer seulement si la personne est à l'aise.
- Revenir en arrière : remettre le DNS en « automatique » sur la TV ou le routeur.
- **Un VPN sur le routeur court-circuite son DNS.** Quand un client VPN tourne sur le
  routeur (Asus, par exemple), le routeur résout souvent les noms par le DNS du VPN, même
  si AdGuard est choisi dans ses réglages WAN. Pour vérifier depuis un ordinateur du
  réseau : `nslookup doubleclick.net <IP du routeur>` doit répondre `0.0.0.0` ;
  `nslookup whoami.akamai.net <IP du routeur>` montre quel résolveur sort réellement.
  Dans ce cas, régler le DNS sur chaque appareil (DNS privé sur Android et Fire TV,
  réglage manuel sur Samsung et LG). Un VPN dans un autre pays bloque aussi les services
  liés au fournisseur Internet (télé du câblodistributeur, par exemple).

## Où se règle le DNS sur la TV

| Système | Chemin |
|---|---|
| Android TV / Google TV | DNS privé par ADB (voir `android-tv.md`), ou IP statique dans les réglages Wi-Fi |
| Fire TV | DNS privé par ADB (Fire OS 7 et 8, voir `fire-tv.md`), ou IP statique, ou routeur |
| Samsung | Réseau > État du réseau > Paramètres IP > DNS : saisir manuellement (2025 : Connexion > Réseau) |
| LG | Réseau > (connexion) > Paramètres avancés |
| Roku | Pas de réglage DNS : passer par le routeur |
| Apple TV | Réseau > (le réseau) > Configurer le DNS > Manuel |
| Consoles (PlayStation, Xbox, Switch) | Réglages réseau > paramètres avancés > DNS manuel (prudence : boutique et jeu en ligne) |
| Décodeur du fournisseur | Ne pas toucher : le fournisseur le gère |
| Vizio, Hisense VIDAA | Réseau > configuration manuelle (selon modèle) ; sinon routeur |
