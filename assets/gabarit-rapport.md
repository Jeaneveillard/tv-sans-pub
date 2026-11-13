# Nettoyage de la TV — {appareil} ({date})

## Fait

| Nom | Paquet | Action | Résultat |
|---|---|---|---|
| {nom} | `{paquet}` | désactivé / retiré / désinstallé | ok / refusé par le système |

Réglages coupés à la main : {liste}.

## Toujours visible, et pourquoi

- {limite 1}

## Revenir en arrière

- Tout restaurer :
  `python scripts/tv_android.py restaurer --appareil {serie} --fichier "{chemin restauration}" --confirmer`
- Un seul paquet : `adb -s {serie} shell pm enable {paquet}`
- Fichier de restauration : `{chemin restauration}`

## Débogage ADB

{Coupé à la fin / laissé actif à ta demande}. Pour restaurer ou réappliquer, le réactiver :
{chemin du menu Options pour les développeurs}.

## Après une mise à jour de la TV

Les mises à jour réactivent souvent des paquets. Relancer l'inventaire, puis réappliquer
le plan : `{chemin du plan}`.
