"""Tests des fonctions pures d'analyse (aucune TV nécessaire).

Lancer depuis le dossier de la compétence : python -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import analyse_android as an  # noqa: E402

CATALOGUE = an.charger_catalogue(
    Path(__file__).resolve().parents[1] / "scripts" / "catalogue_paquets.json")

USAGESTATS_ANDROID9 = """\
user=0
  In-memory yearly stats
    packages
      package=com.exemple.video totalTime="12:30" lastTime="2026-11-10 22:15:42" appLaunchCount=0
      package=com.exemple.jamais totalTime="00:00" lastTime="1969-12-31 19:00:00" appLaunchCount=0
      package=com.exemple.notif totalTime="00:00" lastTime="2026-11-11 08:00:00" appLaunchCount=0
  App Standby States:
    package=com.exemple.video u=0 bucket=10 reason=u-su used=+10d0h idle=n
    package=com.exemple.jamais u=0 bucket=50 reason=d used=+1d idle=y
    package=com.exemple.ancienne u=0 bucket=30 reason=u-mf used=+5d0h0m0s idle=n
    package=com.exemple.rare u=0 bucket=40 reason=t used=+2d idle=y
    totalElapsedTime=+45d0h0m0s0ms
    totalScreenOnTime=+5d
"""

USAGESTATS_ANDROID12 = """\
      package=com.exemple.neuf totalTimeUsed="01:02:03" lastTimeUsed="2026-11-09 10:00:00" totalTimeVisible="01:02:03"
"""

RECENTS = """\
  * Recent #0: TaskRecord{420814a #2 A=10159:com.amazon.tv.launcher.home U=0 StackId=0 sz=1}
    realActivity=com.amazon.tv.launcher/.ui.HomeActivity_vNext
    hasBeenVisible=true lastActiveTime=604861775 (inactive for 0s)
  * Recent #1: TaskRecord{277c8bb #857 A=10212:com.exemple.youtube U=0 StackId=3 sz=1}
    realActivity=com.exemple.youtube/dev.cobalt.app.MainActivity
    hasBeenVisible=true lastActiveTime=326378812 (inactive for 278483s)
  * Recent #2: Task{a1 #3 type=standard A=10001:com.exemple.neuf}
    realActivity=ComponentInfo{com.exemple.neuf/com.exemple.neuf.Main}
    lastActiveTime=900000 (inactive for 30s)
  * Recent #3: TaskRecord{b503597 #853 A=10227:com.exemple.vieille U=0 StackId=-1 sz=0}
    realActivity=com.exemple.vieille/.Splash
    hasBeenVisible=false lastActiveTime=18646 (inactive for 604843s)
"""


class TestParsing(unittest.TestCase):
    def test_liste_paquets_ignore_lignes_invalides(self):
        texte = "package:com.a.b\r\npackage:/data/app/x.apk=com.c.d\nbruit\npackage:pas valide;rm\n"
        self.assertEqual(an.parser_liste_paquets(texte), {"com.a.b", "com.c.d"})

    def test_activites_extrait_paquets(self):
        texte = "2 activities found:\n  Activity #0:\n    priority=0 match=0x1\n" \
                "    com.amazon.bueller.music/com.amazon.music.MainActivity\n" \
                "    com.exemple/.Principale\n"
        self.assertEqual(an.parser_activites(texte), {"com.amazon.bueller.music", "com.exemple"})

    def test_resolution_lanceur(self):
        texte = "priority=950 preferredOrder=0 match=0x108000\ncom.amazon.tv.launcher/.ui.Home\n"
        self.assertEqual(an.parser_resolution(texte), "com.amazon.tv.launcher")
        self.assertIsNone(an.parser_resolution("No activity found\n"))

    def test_composant_clavier(self):
        self.assertEqual(an.parser_composant("com.amazon.tv.ime/.FireTVIME\n"), "com.amazon.tv.ime")
        self.assertIsNone(an.parser_composant("null"))
        self.assertIsNone(an.parser_composant(""))

    def test_duree_en_secondes(self):
        self.assertEqual(an.duree_en_secondes("+1d2h3m4s500ms"), 93784.5)
        self.assertEqual(an.duree_en_secondes("-2h"), -7200)
        self.assertIsNone(an.duree_en_secondes("abc"))
        self.assertIsNone(an.duree_en_secondes("+"))

    def test_usagestats_android9(self):
        stats = an.parser_usagestats(USAGESTATS_ANDROID9)
        video = stats.par_paquet["com.exemple.video"]
        self.assertEqual(video.derniere_date, "2026-11-10 22:15:42")
        self.assertIsNone(video.jours_depuis_usage, "u-su = mise à jour, pas un vrai usage")
        self.assertIsNone(stats.par_paquet["com.exemple.notif"].derniere_date)
        self.assertEqual(stats.par_paquet["com.exemple.jamais"].bucket, 50)
        self.assertAlmostEqual(stats.par_paquet["com.exemple.ancienne"].jours_depuis_usage, 40.0)

    def test_usagestats_android12(self):
        stats = an.parser_usagestats(USAGESTATS_ANDROID12)
        self.assertEqual(stats.par_paquet["com.exemple.neuf"].derniere_date, "2026-11-09 10:00:00")

    def test_recents(self):
        recents = an.parser_recents(RECENTS)
        self.assertEqual(recents["com.exemple.youtube"].inactif, 278483)
        self.assertFalse(recents["com.exemple.youtube"].avant_redemarrage)
        self.assertEqual(recents["com.exemple.neuf"].inactif, 30)
        self.assertEqual(recents["com.amazon.tv.launcher"].inactif, 0)

    def test_recents_recharges_au_demarrage(self):
        vieille = an.parser_recents(RECENTS)["com.exemple.vieille"]
        self.assertTrue(vieille.avant_redemarrage)
        self.assertAlmostEqual(vieille.depuis_demarrage, 604861.646)

    def test_recents_garde_la_plus_recente(self):
        texte = ("* Recent #0: T\n realActivity=com.a/.X\n lastActiveTime=500000 (inactive for 900s)\n"
                 "* Recent #1: T\n realActivity=com.a/.Y\n lastActiveTime=900000 (inactive for 500s)\n")
        self.assertEqual(an.parser_recents(texte)["com.a"].inactif, 500)


class TestIndice(unittest.TestCase):
    def setUp(self):
        self.stats = an.parser_usagestats(USAGESTATS_ANDROID9)
        self.recents = an.parser_recents(RECENTS)

    def test_recents_prioritaires(self):
        indice = an.indice_utilisation("com.exemple.youtube", self.stats, self.recents)
        self.assertEqual(indice["code"], "recente")
        self.assertIn("il y a 3 jours", indice["texte"])

    def test_aujourdhui(self):
        indice = an.indice_utilisation("com.exemple.neuf", self.stats, self.recents)
        self.assertEqual(indice["texte"], "dernière ouverture aujourd'hui")

    def test_avant_redemarrage(self):
        indice = an.indice_utilisation("com.exemple.vieille", self.stats, self.recents)
        self.assertEqual(indice["code"], "avant_redemarrage")
        self.assertIn("redémarrage de la TV (il y a 7 jours)", indice["texte"])
        recent = an.Recent(inactif=60, avant_redemarrage=True, depuis_demarrage=60)
        self.assertIn("(aujourd'hui)", an._indice_avant_redemarrage(recent)["texte"])

    def test_statistique_precise_prime_sur_redemarrage(self):
        recents = {"com.exemple.ancienne": an.Recent(10, True, 10)}
        indice = an.indice_utilisation("com.exemple.ancienne", self.stats, recents)
        self.assertIn("40 jours", indice["texte"])

    def test_ancienne_par_veille(self):
        indice = an.indice_utilisation("com.exemple.ancienne", self.stats, {})
        self.assertEqual(indice["code"], "ancienne")
        self.assertIn("40 jours", indice["texte"])

    def test_date_stats(self):
        self.assertEqual(an.indice_utilisation("com.exemple.video", self.stats, {})["code"],
                         "recente")

    def test_jamais_rare_inconnu(self):
        self.assertEqual(an.indice_utilisation("com.exemple.jamais", self.stats, {})["code"],
                         "jamais")
        self.assertEqual(an.indice_utilisation("com.exemple.rare", self.stats, {})["code"], "rare")
        self.assertEqual(an.indice_utilisation("com.inconnu", self.stats, {})["code"], "inconnu")

    def test_un_jour_au_singulier(self):
        self.assertIn("il y a 1 jour", an._indice_jours(1.5, "x")["texte"])
        self.assertNotIn("jours", an._indice_jours(1.5, "x")["texte"])


class TestClassement(unittest.TestCase):
    CONTEXTE = {"lanceur": "com.amazon.tv.launcher", "clavier": "com.amazon.tv.ime",
                "famille": "fire-tv"}

    def classer(self, paquet, etat="actif", visible=False, systeme=True):
        infos = {"systeme": systeme, "visible": visible, "etat": etat}
        return an.classifier(paquet, infos, CATALOGUE, self.CONTEXTE)

    def test_pub_connue_proposee(self):
        decision = self.classer("com.amazon.sneakpeek")
        self.assertEqual((decision["categorie"], decision["proposition"]),
                         ("publicite", "desactiver"))

    def test_pub_deja_desactivee(self):
        self.assertEqual(self.classer("com.amazon.tv.acr", etat="desactive")["proposition"],
                         "deja_fait")

    def test_incertain_jamais_propose(self):
        decision = self.classer("com.amazon.kso.blackbird")
        self.assertEqual((decision["categorie"], decision["proposition"]),
                         ("a_verifier", "verifier"))

    def test_promotions_amazon_jamais_propose(self):
        # Ce paquet garde la liste des notifications bloquées : désactivé, le menu
        # « Notifications des applications » de Fire TV plante.
        decision = self.classer("com.amazon.device.sale.service")
        self.assertEqual((decision["categorie"], decision["proposition"]),
                         ("a_verifier", "verifier"))
        self.assertIn("notifications", decision["raison"])

    def test_protections(self):
        self.assertEqual(self.classer("com.amazon.tv.launcher")["categorie"], "protege")
        self.assertEqual(self.classer("com.amazon.tv.ime")["categorie"], "protege")
        self.assertEqual(self.classer("com.amazon.device.software.ota")["categorie"], "protege")
        self.assertEqual(self.classer("com.android.providers.tv", visible=True)["categorie"],
                         "protege")
        self.assertEqual(self.classer("com.amazon.alexa.datastore.app")["categorie"], "protege")

    def test_lanceur_et_clavier_du_contexte(self):
        contexte = {"lanceur": "com.autre.lanceur", "clavier": "com.autre.clavier"}
        infos = {"systeme": False, "visible": True, "etat": "actif"}
        self.assertEqual(an.raison_protection("com.autre.lanceur", CATALOGUE, contexte),
                         "Lanceur d'accueil actif")
        self.assertEqual(an.classifier("com.autre.clavier", infos, CATALOGUE, contexte)
                         ["categorie"], "protege")

    def test_application_visible(self):
        decision = self.classer("com.amazon.bueller.photos", visible=True)
        self.assertEqual((decision["categorie"], decision["proposition"]),
                         ("application", "choix_personne"))
        self.assertIn("préinstallée", decision["raison"])
        self.assertIn("installée par vous", self.classer("org.xbmc.kodi", visible=True,
                                                         systeme=False)["raison"])
        self.assertEqual(self.classer("org.xbmc.kodi", visible=True, etat="desactive")
                         ["proposition"], "deja_fait")

    def test_nom_suspect(self):
        self.assertTrue(an.nom_suspect("com.tcl.ad.service"))
        self.assertTrue(an.nom_suspect("com.vendor.tv.metrics"))
        self.assertFalse(an.nom_suspect("com.road.trip"), "« road » ne doit pas matcher « ad »")
        self.assertFalse(an.nom_suspect("ad.exemple.app"), "le premier segment est ignoré")
        self.assertEqual(self.classer("com.vendor.promo.center")["categorie"], "a_verifier")

    def test_systeme_par_defaut(self):
        decision = self.classer("com.amazon.tcomm")
        self.assertEqual((decision["categorie"], decision["proposition"]),
                         ("systeme", "ne_pas_toucher"))

    def test_nom_humain(self):
        self.assertEqual(an.nom_humain("com.amazon.avod", CATALOGUE), "Prime Video")
        self.assertEqual(an.nom_humain("com.amazon.tv.acr", CATALOGUE),
                         "Reconnaissance de contenu (ACR)")
        self.assertEqual(an.nom_humain("com.inconnu", CATALOGUE), "")


class TestTexteAffichable(unittest.TestCase):
    def test_nettoyage(self):
        self.assertEqual(an.texte_affichable("a\x00b\n| c"), "a b / c")
        self.assertEqual(an.texte_affichable("x" * 10, 5), "xxxx…")
        self.assertEqual(an.texte_affichable(None), "None")

    def test_nom_paquet_avec_retour_ligne_refuse(self):
        self.assertFalse(an.est_nom_paquet("com.a.b\n"))


class TestFamille(unittest.TestCase):
    def test_familles(self):
        self.assertEqual(an.famille_appareil({"ro.product.manufacturer": "Amazon"}, set(), set()),
                         "fire-tv")
        self.assertEqual(an.famille_appareil({}, {"android.software.leanback"},
                                             {"com.google.android.apps.tv.launcherx"}),
                         "google-tv")
        self.assertEqual(an.famille_appareil({}, {"android.software.leanback"}, set()),
                         "android-tv")
        self.assertEqual(an.famille_appareil({}, set(), set()), "android")

    def test_familles_mobiles(self):
        tactile = {"android.hardware.touchscreen"}
        self.assertEqual(an.famille_appareil({"ro.product.manufacturer": "samsung"},
                                             tactile | {"android.hardware.telephony"}, set()),
                         "android-mobile")
        self.assertEqual(an.famille_appareil({"ro.product.manufacturer": "Amazon",
                                              "ro.product.model": "KFTRWI"}, tactile, set()),
                         "android-mobile", "tablette Fire")
        self.assertEqual(an.famille_appareil({}, tactile, set()), "android-mobile",
                         "boîtier HDMI sans interface TV")

    def test_la_tv_prime_sur_le_tactile(self):
        tactile = {"android.hardware.touchscreen"}
        self.assertEqual(an.famille_appareil({}, tactile | {"android.software.leanback"}, set()),
                         "android-tv")
        self.assertEqual(an.famille_appareil({"ro.product.manufacturer": "Amazon",
                                              "ro.product.model": "AFTMM"}, tactile, set()),
                         "fire-tv")
        self.assertEqual(an.famille_appareil({}, tactile,
                                             {"com.google.android.apps.tv.launcherx"}),
                         "google-tv")


class TestMobile(unittest.TestCase):
    CONTEXTE = {"lanceur": "com.sec.android.app.launcher", "clavier": "com.exemple.clavier",
                "famille": "android-mobile"}
    PREINSTALLEE = {"systeme": True, "visible": True, "etat": "actif"}
    AJOUTEE = {"systeme": False, "visible": True, "etat": "actif"}

    def test_appli_preinstallee_jamais_proposee(self):
        decision = an.classifier("com.operateur.portail", self.PREINSTALLEE, CATALOGUE,
                                 self.CONTEXTE)
        self.assertEqual((decision["categorie"], decision["proposition"]),
                         ("application", "verifier"))
        self.assertIn("préinstallée", decision["raison"])

    def test_appli_ajoutee_au_choix(self):
        decision = an.classifier("com.exemple.jeu", self.AJOUTEE, CATALOGUE, self.CONTEXTE)
        self.assertEqual(decision["proposition"], "choix_personne")

    def test_sur_une_tv_la_preinstallee_reste_au_choix(self):
        contexte = {**self.CONTEXTE, "famille": "fire-tv"}
        decision = an.classifier("com.operateur.portail", self.PREINSTALLEE, CATALOGUE, contexte)
        self.assertEqual(decision["proposition"], "choix_personne")

    def test_famille_inconnue_ou_absente_ferme_la_porte(self):
        # Si la lecture des fonctions de l'appareil échoue, la famille n'est pas reconnue :
        # on ne doit pas retomber sur la règle permissive des TV.
        for contexte in ({**self.CONTEXTE, "famille": "android"},
                         {"lanceur": "x", "clavier": "y"}):
            decision = an.classifier("com.operateur.portail", self.PREINSTALLEE, CATALOGUE,
                                     contexte)
            self.assertEqual(decision["proposition"], "verifier", contexte)
            ajoutee = an.classifier("com.exemple.jeu", self.AJOUTEE, CATALOGUE, contexte)
            self.assertEqual(ajoutee["proposition"], "choix_personne", contexte)

    def test_noms_vitaux_proteges_sans_liste(self):
        for paquet in ("com.google.android.cellbroadcastservice", "com.sec.imsservice",
                       "com.samsung.android.app.telephonyui", "com.google.android.apps.safetyhub",
                       "com.sec.epdg", "com.operateur.dialer", "com.marque.android.incallui",
                       "com.sec.phone"):
            self.assertIsNotNone(an.raison_protection(paquet, CATALOGUE, {}), paquet)
        for paquet in ("com.amazon.bueller.photos", "com.exemple.headphones",
                       "org.telegram.messenger", "com.exemple.jeu"):
            self.assertIsNone(an.raison_protection(paquet, CATALOGUE, {}), paquet)

    def test_pub_connue_proposee_sur_mobile(self):
        infos = {"systeme": True, "visible": False, "etat": "actif"}
        decision = an.classifier("com.miui.msa.global", infos, CATALOGUE, self.CONTEXTE)
        self.assertEqual((decision["categorie"], decision["proposition"]),
                         ("publicite", "desactiver"))

    def test_telephonie_et_paquets_vitaux_proteges(self):
        for paquet in ("com.android.phone", "com.android.server.telecom",
                       "com.google.android.dialer", "com.samsung.android.dialer",
                       "com.samsung.android.messaging", "com.google.android.apps.messaging",
                       "com.android.emergency", "com.android.cellbroadcastreceiver",
                       "com.miui.securitycenter", "com.xiaomi.finddevice",
                       "com.samsung.android.providers.contacts"):
            self.assertIsNotNone(an.raison_protection(paquet, CATALOGUE, {}), paquet)


class TestCatalogue(unittest.TestCase):
    def test_noms_valides_et_categories_connues(self):
        for paquet, fiche in CATALOGUE["paquets"].items():
            self.assertTrue(an.est_nom_paquet(paquet), paquet)
            self.assertIn(fiche["categorie"], an.CATEGORIES_A_DESACTIVER, paquet)
            self.assertIn(fiche["confiance"], {"verifie", "communaute", "incertain"}, paquet)
            for cle in ("plateforme", "nom", "role"):
                self.assertTrue(fiche.get(cle), f"{paquet} : {cle} manquant")

    def test_aucun_paquet_a_la_fois_cible_et_protege(self):
        for paquet in CATALOGUE["paquets"]:
            self.assertIsNone(an.raison_protection(paquet, CATALOGUE, {}), paquet)

    def test_catalogue_incomplet_refuse(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "c.json"
            chemin.write_text(json.dumps({"paquets": {}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                an.charger_catalogue(chemin)


if __name__ == "__main__":
    unittest.main()
