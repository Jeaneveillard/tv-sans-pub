"""Tests de tv_android.py avec un faux ADB : aucune TV n'est touchée."""
import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import analyse_android as an  # noqa: E402
import tv_android as tv  # noqa: E402

CATALOGUE = an.charger_catalogue(tv.CATALOGUE)


class FausseTv:
    """Simule les réponses ADB d'un Fire TV et note les commandes reçues."""

    def __init__(self, refuser=()):
        self.desactives = {"com.amazon.tv.acr"}
        self.refuser = set(refuser)
        self.commandes = []
        self.ajouts = []
        self.lanceur = "com.amazon.tv.launcher/.ui.Home"

    def __call__(self, serie, *args, verifier=True):
        self.commandes.append(args)
        if args == ("get-state",):
            return "device\n"
        if args[:1] == ("shell",):
            return self.shell(list(args[1:]))
        if args[:1] == ("pull",):
            Path(args[2]).write_bytes(b"apk")
            return "1 file pulled\n"
        return ""

    def shell(self, cmd):
        systeme = ["com.amazon.tv.launcher", "com.amazon.tv.ime", "com.amazon.sneakpeek",
                   "com.amazon.tv.acr", "com.amazon.bueller.photos", "com.amazon.tcomm",
                   *self.ajouts]
        tiers = ["org.xbmc.kodi"]
        if cmd[:3] == ["pm", "list", "packages"]:
            option = cmd[3] if len(cmd) > 3 else ""
            choix = {"-s": systeme, "-3": tiers, "-d": sorted(self.desactives)}
            return "".join(f"package:{p}\n" for p in choix.get(option, systeme + tiers))
        if cmd[:2] == ["cmd", "package"] and cmd[2] == "resolve-activity":
            return f"priority=950\n{self.lanceur}\n"
        if cmd[:2] == ["cmd", "package"] and cmd[2] == "query-activities":
            return "com.amazon.bueller.photos/.Main\norg.xbmc.kodi/.Splash\n"
        if cmd[:3] == ["settings", "get", "secure"]:
            return "com.amazon.tv.ime/.FireTVIME\n"
        if cmd[:2] == ["pm", "disable-user"]:
            paquet = cmd[-1]
            if paquet in self.refuser:
                return "Error: java.lang.SecurityException: Shell cannot change component state\n"
            self.desactives.add(paquet)
            return f"Package {paquet} new state: disabled-user\n"
        if cmd[:2] == ["pm", "uninstall"]:
            return "Success\n"
        if cmd[:2] == ["pm", "path"]:
            return f"package:/data/app/{cmd[2]}-1/base.apk\n"
        if cmd[:1] == ["getprop"]:
            return {"ro.product.manufacturer": "Amazon", "ro.product.model": "AFTR"}.get(
                cmd[1], "") + "\n"
        if cmd[:3] == ["pm", "list", "features"]:
            return "feature:amazon.hardware.fire_tv\n"
        if cmd[:2] == ["dumpsys", "activity"]:
            return ("* Recent #0: T\n realActivity=org.xbmc.kodi/.Main\n"
                    " lastActiveTime=200000000 (inactive for 90000s)\n")
        return ""


class FauxTelephone(FausseTv):
    """Téléphone Android : applis préinstallées visibles, téléphonie, une appli ajoutée."""

    PREINSTALLEES = ["com.sec.android.app.launcher", "com.exemple.clavier",
                     "com.samsung.android.dialer", "com.operateur.portail",
                     "com.facebook.appmanager"]
    AJOUTEES = ["com.exemple.jeu"]

    def __init__(self):
        super().__init__()
        self.desactives = set()
        self.lanceur = "com.sec.android.app.launcher/.Home"

    def shell(self, cmd):
        if cmd[:3] == ["pm", "list", "packages"]:
            option = cmd[3] if len(cmd) > 3 else ""
            choix = {"-s": self.PREINSTALLEES, "-3": self.AJOUTEES,
                     "-d": sorted(self.desactives)}
            return "".join(f"package:{p}\n"
                           for p in choix.get(option, self.PREINSTALLEES + self.AJOUTEES))
        if cmd[:2] == ["cmd", "package"] and cmd[2] == "query-activities":
            return ("com.samsung.android.dialer/.Main\ncom.operateur.portail/.Main\n"
                    "com.exemple.jeu/.Main\n")
        if cmd[:3] == ["settings", "get", "secure"]:
            return "com.exemple.clavier/.Clavier\n"
        if cmd[:1] == ["getprop"]:
            return {"ro.product.manufacturer": "samsung", "ro.product.model": "SM-A546W"}.get(
                cmd[1], "") + "\n"
        if cmd[:3] == ["pm", "list", "features"]:
            return "feature:android.hardware.telephony\nfeature:android.hardware.touchscreen\n"
        if cmd[:2] == ["dumpsys", "activity"]:
            return ""
        return super().shell(cmd)


class BaseTv(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        self.tv = FausseTv()
        correctif = mock.patch.object(tv, "adb", self.tv)
        correctif.start()
        self.addCleanup(correctif.stop)

    def plan(self, contenu):
        chemin = Path(self.dossier.name) / "plan.json"
        chemin.write_text(json.dumps(contenu), encoding="utf-8")
        return chemin

    def args(self, **valeurs):
        defauts = {"appareil": "192.168.1.50:5555", "dossier": self.dossier.name,
                   "confirmer": False, "repli_desinstaller": False, "autoriser": None,
                   "forcer": False}
        return argparse.Namespace(**{**defauts, **valeurs})

    def executer(self, fonction, *params):
        sortie = io.StringIO()
        with redirect_stdout(sortie):
            code = fonction(*params)
        return code, sortie.getvalue()

    def commandes_modifiantes(self):
        verbes = {"disable-user", "uninstall", "enable", "install-existing"}
        return [c for c in self.tv.commandes if verbes & set(c)]


class TestPlan(BaseTv):
    def test_plan_valide_dedoublonne(self):
        plan = tv.lire_plan(self.plan({"desactiver": ["com.a.b", "com.a.b"]}))
        self.assertEqual(plan, {"desactiver": ["com.a.b"], "desinstaller": []})

    def test_plan_refuse_injection(self):
        with self.assertRaises(tv.ErreurTv):
            tv.lire_plan(self.plan({"desactiver": ["com.a.b; reboot"]}))

    def test_plan_refuse_formes_invalides(self):
        for contenu in ([], {"desactiver": "com.a.b"}, {"desactiver": [1]}, {}):
            with self.assertRaises(tv.ErreurTv, msg=str(contenu)):
                tv.lire_plan(self.plan(contenu))

    def test_plan_illisible(self):
        chemin = Path(self.dossier.name) / "casse.json"
        chemin.write_text("{pas du json", encoding="utf-8")
        with self.assertRaises(tv.ErreurTv):
            tv.lire_plan(chemin)


class TestAppliquer(BaseTv):
    def test_simulation_ne_modifie_rien(self):
        plan = self.plan({"desactiver": ["com.amazon.sneakpeek"]})
        code, sortie = self.executer(tv.appliquer, self.args(plan=str(plan)), CATALOGUE)
        self.assertEqual(code, 0)
        self.assertIn("Simulation", sortie)
        self.assertEqual(self.commandes_modifiantes(), [])
        self.assertEqual(list(Path(self.dossier.name).glob("restauration-*.json")), [])

    def test_refus_protege_absent_deja_fait_systeme(self):
        plan = self.plan({"desactiver": ["com.amazon.tv.launcher", "com.amazon.tv.ime",
                                         "com.absent.app", "com.amazon.tv.acr"],
                          "desinstaller": ["com.amazon.bueller.photos"]})
        code, sortie = self.executer(tv.appliquer,
                                     self.args(plan=str(plan), confirmer=True), CATALOGUE)
        self.assertEqual(code, 0)
        self.assertIn("Rien à appliquer", sortie)
        for motif in ("protégé", "absent", "déjà fait", "appli système"):
            self.assertIn(motif, sortie)
        self.assertEqual(self.commandes_modifiantes(), [])

    def test_application_ecrit_restauration_avant(self):
        plan = self.plan({"desactiver": ["com.amazon.sneakpeek"],
                          "desinstaller": ["org.xbmc.kodi"]})
        code, _ = self.executer(tv.appliquer, self.args(plan=str(plan), confirmer=True),
                                CATALOGUE)
        self.assertEqual(code, 0)
        [fichier] = Path(self.dossier.name).glob("restauration-*.json")
        journal = json.loads(fichier.read_text(encoding="utf-8"))
        self.assertEqual(journal["statut"], "termine")
        resultats = {a["paquet"]: (a["action"], a["resultat"]) for a in journal["actions"]}
        self.assertEqual(resultats["com.amazon.sneakpeek"], ("desactiver", "ok"))
        self.assertEqual(resultats["org.xbmc.kodi"], ("desinstaller", "ok"))
        apk = journal["actions"][1]["apks"][0]
        self.assertTrue(Path(apk).exists(), "l'APK est sauvegardé avant la désinstallation")

    def test_refus_systeme_puis_repli(self):
        self.tv.refuser = {"com.amazon.sneakpeek"}
        plan = self.plan({"desactiver": ["com.amazon.sneakpeek"]})
        code, sortie = self.executer(tv.appliquer, self.args(plan=str(plan), confirmer=True),
                                     CATALOGUE)
        self.assertEqual(code, 2)
        self.assertIn("refusé par le système", sortie)
        code, sortie = self.executer(
            tv.appliquer, self.args(plan=str(plan), confirmer=True, repli_desinstaller=True),
            CATALOGUE)
        self.assertEqual(code, 0)
        self.assertIn("retire_utilisateur", sortie)
        self.assertEqual(len(list(Path(self.dossier.name).glob("restauration-*.json"))), 2,
                         "une restauration existante n'est jamais écrasée")

    def test_pas_de_repli_sans_refus_explicite(self):
        self.tv.shell = lambda cmd: "" if cmd[:2] == ["pm", "disable-user"] else \
            FausseTv.shell(self.tv, cmd)
        plan = self.plan({"desactiver": ["com.amazon.sneakpeek"]})
        code, sortie = self.executer(
            tv.appliquer, self.args(plan=str(plan), confirmer=True, repli_desinstaller=True),
            CATALOGUE)
        self.assertEqual(code, 2)
        self.assertIn("aucune réponse de la TV", sortie)
        self.assertFalse([c for c in self.tv.commandes if "uninstall" in c],
                         "pas de retrait si la TV n'a pas explicitement refusé")

    def test_liste_blanche_systeme_et_a_verifier(self):
        plan = self.plan({"desactiver": ["com.amazon.tcomm", "com.amazon.kso.blackbird"]})
        self.tv.ajouts = ["com.amazon.kso.blackbird"]
        code, sortie = self.executer(tv.appliquer, self.args(plan=str(plan), confirmer=True),
                                     CATALOGUE)
        self.assertIn("classé « systeme »", sortie)
        self.assertIn("classé « a_verifier »", sortie)
        self.assertEqual(self.commandes_modifiantes(), [])
        code, sortie = self.executer(
            tv.appliquer,
            self.args(plan=str(plan), confirmer=True, autoriser=["com.amazon.kso.blackbird"]),
            CATALOGUE)
        self.assertEqual(code, 0)
        self.assertEqual([c[-1] for c in self.commandes_modifiantes()],
                         ["com.amazon.kso.blackbird"])

    def test_lanceur_inconnu_bloque_tout(self):
        self.tv.lanceur = "android/com.android.internal.app.ResolverActivity"
        plan = self.plan({"desactiver": ["com.amazon.sneakpeek"]})
        with self.assertRaises(tv.ErreurTv):
            self.executer(tv.appliquer, self.args(plan=str(plan), confirmer=True), CATALOGUE)
        self.assertEqual(self.commandes_modifiantes(), [])

    def test_apk_inscrit_au_journal_avant_desinstallation(self):
        instantanes = []
        original = tv._ecrire_json

        def espion(chemin, donnees):
            instantanes.append(json.loads(json.dumps(donnees)))
            original(chemin, donnees)

        plan = self.plan({"desinstaller": ["org.xbmc.kodi"]})
        with mock.patch.object(tv, "_ecrire_json", espion):
            self.executer(tv.appliquer, self.args(plan=str(plan), confirmer=True), CATALOGUE)
        avant_retrait = [i for i in instantanes if i["actions"][0].get("apks")
                         and "resultat" not in i["actions"][0]]
        self.assertTrue(avant_retrait, "le journal contient l'APK avant « pm uninstall »")


class TestRestaurer(BaseTv):
    def fichier(self, actions, appareil="192.168.1.50:5555"):
        chemin = Path(self.dossier.name) / "restauration-test.json"
        chemin.write_text(json.dumps({"appareil": appareil, "actions": actions}),
                          encoding="utf-8")
        return str(chemin)

    def test_commandes_de_restauration(self):
        dossier = Path(self.dossier.name).resolve()
        (dossier / "a").mkdir()
        base, split = dossier / "a" / "base.apk", dossier / "a" / "split.apk"
        for apk in (base, split, dossier / "a" / "x.sh"):
            apk.write_bytes(b"apk")
        commande = tv._commande_restauration
        self.assertEqual(commande({"action": "desactiver"}, "com.a", dossier),
                         ["shell", "pm", "enable", "com.a"])
        self.assertEqual(commande({"action": "retire_utilisateur"}, "com.a", dossier),
                         ["shell", "cmd", "package", "install-existing", "com.a"])
        self.assertEqual(commande({"action": "desinstaller",
                                   "apks": [str(base), str(split), "a/x.sh"]}, "com.a", dossier),
                         ["install-multiple", "-r", str(base), str(split)])
        self.assertEqual(commande({"action": "desinstaller", "apks": [str(base)]}, "com.a",
                                  dossier), ["install", "-r", str(base)])
        self.assertEqual(commande({"action": "desinstaller"}, "com.a", dossier), [])
        self.assertEqual(commande({"action": "desinstaller", "apks": "pas une liste"}, "com.a",
                                  dossier), [])

    def test_apk_hors_du_dossier_ignore(self):
        with tempfile.TemporaryDirectory() as ailleurs:
            etranger = Path(ailleurs) / "piege.apk"
            etranger.write_bytes(b"apk")
            self.assertEqual(tv._apks_sauvegardes([str(etranger)],
                                                  Path(self.dossier.name).resolve()), [])

    def test_simulation_puis_confirmation(self):
        fichier = self.fichier([{"paquet": "com.amazon.sneakpeek", "action": "desactiver"}])
        code, sortie = self.executer(tv.restaurer, self.args(fichier=fichier))
        self.assertEqual((code, self.commandes_modifiantes()), (0, []))
        self.assertIn("pm enable com.amazon.sneakpeek", sortie)
        code, _ = self.executer(tv.restaurer, self.args(fichier=fichier, confirmer=True))
        self.assertEqual(len(self.commandes_modifiantes()), 1)
        self.assertEqual(code, 2, "le faux ADB ne répond pas « enabled » : échec signalé")

    def test_autre_appareil_refuse_sauf_forcer(self):
        fichier = self.fichier([{"paquet": "com.amazon.sneakpeek", "action": "desactiver"}],
                               appareil="autre:5555")
        with self.assertRaises(tv.ErreurTv):
            tv.restaurer(self.args(fichier=fichier))
        code, _ = self.executer(tv.restaurer, self.args(fichier=fichier, forcer=True))
        self.assertEqual(code, 0)

    def test_succes_selon_la_commande(self):
        reponses = {("shell", "pm", "enable", "com.a"): "Package com.a new state: enabled",
                    ("install", "-r", "x.apk"): "Performing Streamed Install\nSuccess"}
        with mock.patch.object(tv, "adb", lambda s, *c, verifier=True: reponses.get(c, "")):
            with redirect_stdout(io.StringIO()):
                self.assertTrue(tv._executer_restauration("s", ["shell", "pm", "enable", "com.a"]))
                self.assertTrue(tv._executer_restauration("s", ["install", "-r", "x.apk"]))
                self.assertFalse(tv._executer_restauration(
                    "s", ["shell", "cmd", "package", "install-existing", "com.a"]))

    def test_entrees_invalides_refusees(self):
        fichier = self.fichier(["pas un objet"])
        with self.assertRaises(tv.ErreurTv):
            tv.restaurer(self.args(fichier=fichier))

    def test_paquet_invalide_refuse(self):
        fichier = self.fichier([{"paquet": "x; reboot", "action": "desactiver"}])
        with self.assertRaises(tv.ErreurTv):
            self.executer(tv.restaurer, self.args(fichier=fichier, confirmer=True))

    def test_fichier_illisible(self):
        chemin = Path(self.dossier.name) / "vide.json"
        chemin.write_text("[]", encoding="utf-8")
        with self.assertRaises(tv.ErreurTv):
            tv.restaurer(self.args(fichier=str(chemin)))


class TestInventaire(BaseTv):
    def test_inventaire_classe_et_ecrit(self):
        code, sortie = self.executer(tv.main, ["inventaire", "--appareil", "192.168.1.50:5555",
                                               "--dossier", self.dossier.name])
        self.assertEqual(code, 0)
        self.assertIn("fire-tv", sortie)
        self.assertIn("Applications visibles (2)", sortie)
        [fichier] = Path(self.dossier.name).glob("inventaire-AFTR-*.json")
        inventaire = json.loads(fichier.read_text(encoding="utf-8"))
        par_paquet = {p["paquet"]: p for p in inventaire["paquets"]}
        self.assertEqual(par_paquet["com.amazon.sneakpeek"]["proposition"], "desactiver")
        self.assertEqual(par_paquet["com.amazon.tv.acr"]["proposition"], "deja_fait")
        self.assertEqual(par_paquet["com.amazon.tv.launcher"]["categorie"], "protege")
        self.assertIn("il y a 1 jour", par_paquet["org.xbmc.kodi"]["utilisation"]["texte"])
        self.assertEqual(self.commandes_modifiantes(), [], "l'inventaire est en lecture seule")


class TestConnexionEtErreurs(BaseTv):
    def test_appareil_non_pret(self):
        with mock.patch.object(tv, "adb", return_value="unauthorized\n"):
            with self.assertRaises(tv.ErreurTv):
                tv.verifier_appareil("192.168.1.50:5555")
        with self.assertRaises(tv.ErreurTv):
            tv.verifier_appareil("x;reboot")

    def test_connecter_ajoute_le_port(self):
        appels = []

        def faux(serie, *args, verifier=True):
            appels.append(args)
            return "device\n" if args == ("get-state",) else "connected\n"

        with mock.patch.object(tv, "adb", faux):
            code, _ = self.executer(tv.connecter, argparse.Namespace(hote="192.168.1.50"))
        self.assertEqual(code, 0)
        self.assertEqual(appels[0], ("connect", "192.168.1.50:5555"))

    def test_connecter_adresse_invalide(self):
        with self.assertRaises(tv.ErreurTv):
            tv.connecter(argparse.Namespace(hote="1.2.3.4;rm"))

    def test_appairer_valide_le_code(self):
        with self.assertRaises(tv.ErreurTv):
            tv.appairer(argparse.Namespace(hote="192.168.1.50:37000", code="12ab"))

    def test_main_affiche_les_erreurs(self):
        with mock.patch.object(tv, "adb", side_effect=tv.ErreurTv("adb est introuvable")):
            erreurs = io.StringIO()
            with mock.patch.object(sys, "stderr", erreurs):
                code = tv.main(["appareils"])
        self.assertEqual(code, 1)
        self.assertIn("introuvable", erreurs.getvalue())


class TestTelephone(BaseTv):
    """Sur un téléphone ou une tablette, on ne touche pas aux applis préinstallées."""

    def setUp(self):
        super().setUp()
        self.tv = FauxTelephone()
        correctif = mock.patch.object(tv, "adb", self.tv)
        correctif.start()
        self.addCleanup(correctif.stop)

    def appliquer(self, paquets, **options):
        plan = self.plan({"desactiver": paquets})
        return self.executer(tv.appliquer,
                             self.args(plan=str(plan), confirmer=True, **options), CATALOGUE)

    def test_inventaire_signale_le_mobile(self):
        inventaire = tv.inventorier("ABC123", CATALOGUE)
        self.assertEqual(inventaire["appareil"]["famille"], "android-mobile")
        propositions = {l["paquet"]: l["proposition"] for l in inventaire["paquets"]}
        self.assertEqual(propositions["com.operateur.portail"], "verifier")
        self.assertEqual(propositions["com.exemple.jeu"], "choix_personne")
        self.assertEqual(propositions["com.facebook.appmanager"], "desactiver")
        self.assertEqual(propositions["com.samsung.android.dialer"], "ne_pas_toucher")
        sortie = io.StringIO()
        with redirect_stdout(sortie):
            tv.afficher_inventaire(inventaire)
        self.assertIn("téléphone", sortie.getvalue().lower())
        self.assertIn("--autoriser", sortie.getvalue())

    def test_preinstallee_refusee_sans_autorisation(self):
        code, sortie = self.appliquer(["com.operateur.portail"])
        self.assertEqual(code, 0)
        self.assertIn("--autoriser com.operateur.portail", sortie)
        self.assertEqual(self.commandes_modifiantes(), [])

    def test_preinstallee_acceptee_avec_autorisation(self):
        code, _sortie = self.appliquer(["com.operateur.portail"],
                                       autoriser=["com.operateur.portail"])
        self.assertEqual(code, 0)
        self.assertIn("com.operateur.portail", self.tv.desactives)

    def test_telephonie_refusee_meme_avec_autorisation(self):
        _code, sortie = self.appliquer(["com.samsung.android.dialer"],
                                       autoriser=["com.samsung.android.dialer"])
        self.assertIn("protégé", sortie)
        self.assertEqual(self.commandes_modifiantes(), [])

    def test_fonctions_illisibles_ne_levent_pas_la_garde(self):
        # « pm list features » vide (délai dépassé, réponse abîmée) : la famille devient
        # « android ». La garde des applis préinstallées doit tenir quand même.
        original = self.tv.shell

        def shell_sans_fonctions(cmd):
            return "" if cmd[:3] == ["pm", "list", "features"] else original(cmd)

        self.tv.shell = shell_sans_fonctions
        code, sortie = self.appliquer(["com.operateur.portail"])
        self.assertEqual(code, 0)
        self.assertIn("--autoriser com.operateur.portail", sortie)
        self.assertEqual(self.commandes_modifiantes(), [])
        inventaire = tv.inventorier("ABC123", CATALOGUE)
        self.assertEqual(inventaire["appareil"]["famille"], "android")
        ecran = io.StringIO()
        with redirect_stdout(ecran):
            tv.afficher_inventaire(inventaire)
        self.assertIn("--autoriser", ecran.getvalue())

    def test_appli_ajoutee_et_pub_connue_appliquees(self):
        code, _sortie = self.appliquer(["com.exemple.jeu", "com.facebook.appmanager"])
        self.assertEqual(code, 0)
        self.assertEqual(self.tv.desactives, {"com.exemple.jeu", "com.facebook.appmanager"})


if __name__ == "__main__":
    unittest.main()
