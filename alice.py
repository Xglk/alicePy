#! /usr/bin/python
# -*- coding: utf-8 -*-
# Python 3, PyQt5

"""
lancement d'une icone dans le tray.
    clic gauche sur l'icone => affiche la fenêtre programme
    clic droit sur l'icone => menu contextuel:
        -> quitte avec confirmation oui/non
"""

#from platform import system
import sys, sqlite3, re, gettext, os

from PyQt5 import (QtWidgets, QtGui, QtCore, QtWebEngineWidgets)
from datetime import datetime, timedelta, date
from threading import Timer


#############################################################################
#############################################################################
# adaptation au programme à lancer
# ================================


#instance globale pour recharger le menu de la classe SystemTrayIcon à partir de l'autre classe FAliceActivite
#global trayIcon
#============================================================================
# nom du programme
programme = "ChronoGestion des activités"
version = "V2.4"
email = "xglk673+alicepy@gmail.com"
#quantième de l'année
dj = datetime.now()
d1 = date(dj.year, dj.month, dj.day)
d0 = date(dj.year - 1, 12, 31)
quantieme = d1 - d0

# à partir de 5h on passe à un jour complet, en dessous de 1000 secondes on reste à zéro jour.
parametre_demi_jour = 1000
parametre_jour = 18000

change_de_jour = date(dj.year, dj.month, dj.day)

# bulle
#bulle = _("Aucune activité en cours")

# icone de la fenêtre qui sera aussi l'icone du tray
iconeStop = "AliceStop.ico"
iconeRun = "AliceRun.ico"
iconeRun1 = "Alice1.ico"
iconeRun2 = "Alice2.ico"
iconeRun3 = "Alice3.ico"
icone_run = 0


#============================================================================
# fonction qui lance la fenêtre sans l'afficher
def lancementfalice():
    """lance la fenêtre sans l'afficher
    """

    # retourne la variable d'instance de la fenêtre à lancer
    return FAlice()

# fonction qui lance la fenêtre sans l'afficher
def lancementfaliceactivite():
    """lance la fenêtre sans l'afficher
    """

    # retourne la variable d'instance de la fenêtre à lancer
    return FAliceActivite()

# fonction qui lance la fenêtre sans l'afficher
def lancementFenCorrection():
    return FAliceCorrection()

def lancementFenParametrages():
    return FAliceParametrages()

"""
Timer pour une action récurente sans bloquer le reste du code
"""
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

#############################################################################
#############################################################################
"""
Classe de l'icône en systray.
C'est le coeur de l'application, tout se contrôle à partir de là
"""
class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    #========================================================================
    def __init__(self, app, qicone, bul="", parent=None):
        super().__init__(qicone, parent)

        self.app = app
        self.parent = parent

        global parametre_jour
        global parametre_demi_jour
        #--------------------------------------------------------------------
        # un clic gauche affichera la fenêtre
        self.activated.connect(self.mousePressEvent)

        #--------------------------------------------------------------------
        # ajoute une bulle d'information quand la souris est sur l'icône tray
        if bul != "":
            self.setToolTip(bul)

        #accès à une base de données
        baseDB = "Alice.db"
        self.con = None
        self.con = sqlite3.connect(baseDB)
        self.cur = self.con.cursor()
        self.DB_connexion()  
        #vérification de la version et mises à jour nécessaires éventuelles
        self.lparam = self.DB_select_Param("version", "")
        #détection du passage à la V2 par présence ou non de ce paramètre
        #si c'est le cas on modifie un peu les données déjà saisies, modifications nécessaires sur le passage vers la V2.
        if len(self.lparam) == 0:
            self.mise_a_jour_BDD()
        elif not self.lparam[0][2] == version:
            #gérer les besoins de mises à jour ici sur un changement de version
            self.DB_update_Param("version", "", version, None, None, None)
        #accès à la langue
        #recherche paramétrage s'il existe, sinon on le crée avec une valeur par défaut
        self.lparam = self.DB_select_Param("langage", "")
        if len(self.lparam) == 0:
            system_language = 'fr_FR'
            self.DB_insert_Param("langage", "", system_language, None, None, None)
            self.lparam = self.DB_select_Param("langage", "") 
        self.langage = self.lparam[0][2]       
        try:
            gettext.find(self.langage)
            traduction = gettext.translation(self.langage, localedir='locale', languages=[self.langage])
            traduction.install(self.langage)
        except:
            gettext.install('fr_FR')

        #récupération des paramètres de calcul des jours
        self.lparam = self.DB_select_Param("calcul_jour", "un")
        if len(self.lparam) == 0:
            self.DB_insert_Param("calcul_jour", "un", None, None, parametre_jour, None)
            self.lparam = self.DB_select_Param("calcul_jour", "un") 
        parametre_jour = self.lparam[0][4]       
        self.lparam = self.DB_select_Param("calcul_jour", "demi")
        if len(self.lparam) == 0:
            self.DB_insert_Param("calcul_jour", "demi", None, None, parametre_demi_jour, None)
            self.lparam = self.DB_select_Param("calcul_jour", "demi") 
        parametre_demi_jour = self.lparam[0][4]       

        
        # lance la fenêtre sans affichage
        self.fenAlice = lancementfalice()
        # lance la fenêtre sans affichage
        self.fenAliceActivitees = lancementfaliceactivite()        
        #
        self.fenAliceParametrage = lancementFenParametrages()

        # initialise le menu
        self.initmenu()

        #
        global rt
        rt = RepeatedTimer(1, self.change_icone)
        if icone_run == 0:
            rt.stop()


    #accès base de donnée
    def DB_connexion(self):
            try:
                #Vérifie existence de la table
                TAppr = self.cur.execute("""SELECT tbl_name FROM sqlite_master WHERE type='table' AND tbl_name='activite';""").fetchall()
                if TAppr == []:
                    #print('table a creer')
                    self.DB_create()

            except sqlite3.Error as e:
                if self.con:
                    self.con.rollback()

                #print(f"Error {e.args[0]}")
                QtWidgets.QMessageBox.about(None, "ERREUR", f"Error {e.args[0]}")
                sys.exit(1)
    #création si inexistante
    def DB_create(self):
        self.cur.execute("""CREATE TABLE activite (libelle  TEXT NOT NULL, debut TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, fin TIMESTAMP,  id INTEGER, PRIMARY KEY( id  AUTOINCREMENT));""")
        self.cur.execute("""CREATE TABLE correction (libelle TEXT NOT NULL, jour DATE, correction INTEGER, duree INTEGER, tevt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);""")
        self.cur.execute("""CREATE TABLE parametres (type TEXT,stype TEXT,valeur_a TEXT,valeur_n REAL,valeur_int INTEGER,visible INTEGER);""")
        self.cur.execute("""CREATE TABLE taches ( libelle TEXT, parent TEXT, niveau INTEGER, ordre_calendrier INTEGER, ordre_menu INTEGER, affichage_menu INTEGER);""")
        self.DB_insert_Param("version", "", version, None, None, None)

    #mise à jour des données suite à montée de version
    def mise_a_jour_BDD(self):
        #mise à jour du chrono d'ordre d'affichage dans le calendrier trié par ce chrono (utile s'il est déjà alimenté) puis par libellé
        resultat = self.cur.execute("""select libelle, ordre_calendrier, row_number() over(order by ordre_calendrier, libelle) -1 from taches""").fetchall()
        if resultat:
            for i in range(len(resultat)):
                ligne = resultat[i]
                self.cur.execute("""update taches set ordre_calendrier = ? where libelle = ?""", (ligne[2], ligne[0]))
        #mise à jour de la valeur du parent en fonction du niveau des activités et de l'ordre
        self.cur.execute("""update taches  set parent = 
                            ifnull((select libelle 
                                    from taches p 
                                    where p.niveau < taches.niveau 
                                        and p.ordre_calendrier < taches.ordre_calendrier
                                        and not exists(select 1 from taches x
                                                        where x.niveau < taches.niveau 
                                                        and x.ordre_calendrier < taches.ordre_calendrier
                                                        and x.ordre_calendrier  > p.ordre_calendrier )
                                    ), '')
                         """)
        #insertion en base de la valeur de la version
        self.DB_insert_Param("version", "", version, None, None, None)
        
    
    #sélection des taches
    def DB_select_T(self):
        #select libelle from taches where affichage_menu = 1 order by ordre_menu
        #params = {"pjour": jour}
        self.cur.execute("""select libelle
                            from taches 
                            where affichage_menu = 1
                            order by ordre_menu""")
        return (self.cur.fetchall())

    #sélection de la tache active s'il y en a une
    def DB_select_TA(self):
        #select libelle from taches where affichage_menu = 1 order by ordre_menu
        #params = {"pjour": jour}
        self.cur.execute("""select libelle
                            from activite 
                            where fin is NULL and debut = (select max(debut) from activite) """)
        return (self.cur.fetchone())


    #Nouvelle activité
    def DB_insert_A(self, libActivite):
        #On commence par l'arrêt de toute activité déjà en cours
        self.cur.execute("""update activite set fin = datetime('now', 'localtime') where fin is NULL and substr(debut, 1, 10) = date()""")
        #et on démarre la suivante
        self.cur.execute("""insert into activite (libelle, debut, fin) values(? , datetime('now', 'localtime'), null)""", (libActivite, ))
        self.cur.execute("""commit""")

    #arrêt activité
    def DB_stop_A(self):
        #On arrête l'activité déjà en cours
        self.cur.execute("""update activite set fin = datetime('now', 'localtime') where fin is NULL and substr(debut, 1, 10) = date()""")

        self.cur.execute("""commit""")

    def DB_select_Param(self, type, stype):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select type, stype, valeur_a, valeur_n, valeur_int, visible
                            from parametres 
                            where type = ?
                              and stype = ?
                            order by type, stype""", (type, stype ))

        return (self.cur.fetchall())

    def DB_insert_Param(self, type, stype, valeur_a, valeur_n, valeur_int, visible):
        #
        #
        self.cur.execute("""insert into parametres (type, stype, valeur_a, valeur_n, valeur_int, visible)
                            values( ?, ?, ?, ?, ?, ?)""", (type, stype, valeur_a, valeur_n, valeur_int, visible ))

        self.cur.execute("""commit""")

    def DB_update_Param(self, type, stype, valeur_a, valeur_n, valeur_int, visible):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""update parametres 
                            set valeur_a = ?
                              , valeur_n = ?
                              , valeur_int = ?
                              , visible = ?
                            where type = ?
                              and stype = ?""", (valeur_a, valeur_n, valeur_int, visible, type, stype ))

        self.cur.execute("""commit""")

    def mousePressEvent(self, ev):
        """Détection des événements de la souris en systray.

        Args:
            ev: The QMouseEvent.
        """
        #recalcule des données à afficher dans tool tip
        dj = datetime.now()
        d1 = date(dj.year, dj.month, dj.day)
        d0 = date(dj.year - 1, 12, 31)
        quantieme = d1 - d0

        #QtWidgets.QSystemTrayIcon.Trigger = clic gauche
        #QtWidgets.QSystemTrayIcon.DoubleClick = ça se voit, non!
        #QtWidgets.QSystemTrayIcon.MiddleClick =  clic du milieu
        #QtWidgets.QSystemTrayIcon.Context = clic droit
        if ev ==  QtWidgets.QSystemTrayIcon.Trigger or ev == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.affichealice()


    #========================================================================
    def initmenu(self):
        """initialise le popupmenu qui apparaitra au clic droit sur l'icône 
        """
        global icone_run
        # crée le menu
        menu = QtWidgets.QMenu(self.parent)

        #Définition d'un groupe pour permettre la sélection visuelle avec une coche d'un élément
        #et d'un seul du groupe.
        self.activitesGroupe = QtWidgets.QActionGroup(self)
        #groupe pour les langues
        self.langueGroupe = QtWidgets.QActionGroup(self)

        fenIconA = QtGui.QIcon.fromTheme("application-exit", QtGui.QIcon(iconeStop))
        fenAlice = QtWidgets.QAction(fenIconA, _('Afficher Le &Calendrier'), self)
        fenAlice.triggered.connect(self.affichealice)
        menu.addAction(fenAlice)

        fenActivitees = QtWidgets.QAction(_("Gérer Les &Activités"), self)
        fenActivitees.triggered.connect(self.afficheactivitees)
        menu.addAction(fenActivitees)

        menuAutre = QtWidgets.QMenu(_("Infos"), menu)
        aproposde = QtWidgets.QAction(_("à propos de..."), self)
        aproposde.triggered.connect(self.aproposde)
        menuAutre.addAction(aproposde)
        menuAide = QtWidgets.QAction(_('Aide...'), self)
        menuAide.triggered.connect(self.afficheAide)
        menuAutre.addAction(menuAide)
        menuParametre = QtWidgets.QAction(_("Paramétrages..."), menu)
        menuParametre.triggered.connect(self.afficheParametrage)
        menuAutre.addAction(menuParametre)
        
        #ajout des langages
        menuLangue = QtWidgets.QMenu(_("Langue"), menuAutre)

        ##fr_FR
        #menuDetLangue = QtWidgets.QAction("Français", self)
        #menuDetLangue.setActionGroup(self.langueGroupe)
        #menuDetLangue.triggered.connect(self.langue)
        #menuLangue.addAction(menuDetLangue)
        #menuDetLangue.setCheckable(True)
        #if self.langage == "fr_FR":
        #    menuDetLangue.setChecked(True)
        ##en_GB
        #menuDetLangue = QtWidgets.QAction("English", self)
        #menuDetLangue.setActionGroup(self.langueGroupe)
        #menuDetLangue.triggered.connect(self.langue)
        #menuLangue.addAction(menuDetLangue)
        #menuDetLangue.setCheckable(True)
        #if self.langage == "en_GB":
        #    menuDetLangue.setChecked(True)
        #liste des langues
        l = [item for item in os.listdir("locale") if os.path.isdir(os.path.join("locale", item)) and not item.startswith(".")]
        for i in range (len(l)):
            menuDetLangue = QtWidgets.QAction(l[i], self)
            menuDetLangue.setActionGroup(self.langueGroupe)
            menuDetLangue.triggered.connect(self.langue)
            menuLangue.addAction(menuDetLangue)
            menuDetLangue.setCheckable(True)
            if self.langage == l[i]:
                menuDetLangue.setChecked(True)
        menuAutre.addMenu(menuLangue)
        menu.addMenu(menuAutre)
        

        menu.addSeparator()
        #recherche s'il y a une activité en cours pour la marquer
        activite_en_cours = self.DB_select_TA()
        #chargement des données de la base
        self.extraction = self.DB_select_T()
        #nb d'enreg extraits
        nb_lignes = len(self.extraction)
        #Boucle d'alimentation des activités de la semaine
        for i in range(nb_lignes):
            activite = str(self.extraction[i][0])
            if activite[0] == "/" and activite[1:3].isnumeric:
                menu.addSeparator()
            else:
                #QMessageBox.about(None, "Debug", str(activite))
                menuAction = QtWidgets.QAction(activite, self)
                menuAction.triggered.connect(self.actionMenu)
                #cochable
                menuAction.setCheckable(True)
                if not activite_en_cours == None:
                    if activite == activite_en_cours[0]:
                        menuAction.setChecked(True)
                        font = QtGui.QFont()
                        font.setBold(True)
                        menuAction.setFont(font)
                        # l'info bulle prend la valeur de l'action en cours
                        self.setToolTip(activite)
                        #permet de faire tourner les aiguilles de l'horloge
                        icone_run = 1
                #ajout dans le groupe
                menuAction.setActionGroup(self.activitesGroupe)
                menu.addAction(menuAction)
            
        menu.addSeparator()

        # ferme la fenêtre et quitte le programme:
        # l'icône de l'item "Quitter" du menu sera une simple croix rouge
        #stopperIcon = QtGui.QIcon.fromTheme("application-exit", QtGui.QIcon("icone_quitter.png"))
        #stopperAction = QtWidgets.QAction(stopperIcon, '&Stopper activité en cours', self)
        stopperAction = QtWidgets.QAction(_("&Stopper activité en cours"), self)
        stopperAction.triggered.connect(self.stopMenu)
        stopperAction.setCheckable(True)
        if activite_en_cours == None:
            stopperAction.setChecked(True)
            # l'info bulle prend la valeur de l'action en cours
            self.setToolTip(_("Aucune activité en cours"))        
        #on l'ajoute aussi dans le groupe pour que ça décoche une activité éventuellement sélectionnée
        stopperAction.setActionGroup(self.activitesGroupe)
        menu.addAction(stopperAction)

        # ferme la fenêtre et quitte le programme:
        # l'icône de l'item "Quitter" du menu sera une simple croix rouge
        #quitterIcon = QtGui.QIcon.fromTheme("application-exit", QtGui.QIcon("icone_quitter.png"))
        #quitterAction = QtWidgets.QAction(quitterIcon, '&Quitter', self)
        quitterAction = QtWidgets.QAction(_("&Quitter"), self)
        quitterAction.triggered.connect(self.quitter)
        menu.addAction(quitterAction)

        self.setContextMenu(menu)


    #========================================================================
    #L'heure tourne lorsqu'une activité est en cours
    def change_icone(self):
        global icone_run
        if icone_run == 1:
            icone_run = 2
            self.setIcon(QtGui.QIcon(iconeRun2))
        elif icone_run == 2:
            icone_run = 3
            self.setIcon(QtGui.QIcon(iconeRun3))
        else:
            icone_run = 1  
            self.setIcon(QtGui.QIcon(iconeRun1))

    #========================================================================
    def affichealice(self):
        """clic gauche sur l'icone => affiche la fenêtre au dessus des autres
        """
        self.fenAlice.showNormal()  # affiche en mode fenêtre
        self.fenAlice.activateWindow()  # affiche au dessus des autres fenêtres
        #Rechargement du calendier des activités
        if self.fenAlice.semaine.isChecked() == True:
            self.fenAlice.chargeTableauSemaine(0, None)
        if self.fenAlice.mois.isChecked() == True:
            self.fenAlice.chargeTableauMois(0, None)
        if self.fenAlice.annee.isChecked() == True:
            self.fenAlice.chargeTableauAnnee(0, None)
        # met le focus sur la ligne de saisie de la fenêtre en sélectionnant le texte déjà saisi s'il y en a
        #self.fenAlice.lineEdit.selectAll()
        #self.fenAlice.lineEdit.setFocus()

    def afficheParametrage(self):
        self.fenAliceParametrage.showNormal()
        self.fenAliceParametrage.activateWindow()

    def aproposde(self):
        """version
        """
        QtWidgets.QMessageBox.about(None, _("Version"), _("Version d'AlicePy: ") + version + "\r\nContact: " + email)


    def afficheAide(self):
        """aide utilisateur
           
        """
        #QtWidgets.QMessageBox.about(None, _("Aide"), _("Voir le document Word joint à l'applicatif"))
        self.aide = Aide()
        
        file_aide = "aide/aide_" + self.langage + ".html"
    
        fichierweb = "file:///" + os.path.abspath(file_aide).replace("\\", "/") + "#partiecommune"
        fichierweb = "file:///" + os.path.abspath(file_aide).replace("\\", "/")
        #fichierweb = "https://www.youtube.com/tv#/watch?v=bLhi6lppatw"
    
        self.aide.affiche(fichierweb)
        self.aide.show()



    #========================================================================
    def afficheactivitees(self):
        """clic gauche sur l'icone => affiche la fenêtre au dessus des autres
        """
        self.fenAliceActivitees.showNormal()  # affiche en mode fenêtre
        self.fenAliceActivitees.activateWindow()  # affiche au dessus des autres fenêtres

        # met le focus sur la ligne de saisie de la fenêtre en sélectionnant le texte déjà saisi s'il y en a
        self.fenAliceActivitees.saisie_activite.selectAll()
        self.fenAliceActivitees.saisie_activite.setFocus()

    def langue(self):
        """changement de langue
        """
        #Récupère le nom de la langue
        langage_menu = self.sender()
        entry = langage_menu.text()
        if entry == "Français":
            self.langage = "fr_FR"
        elif entry == "English":
            self.langage = "en_GB"
        else:
            self.langage = entry
        self.DB_update_Param("langage", "", self.langage, None, None, None)
        try:
            gettext.find(self.langage)
            traduction = gettext.translation(self.langage, localedir='locale', languages=[self.langage])
            traduction.install(self.langage)
        except:
            gettext.install('fr_FR')
        self.initmenu()
        self.fenAliceActivitees.libelles()
        self.fenAlice.libelles()
        self.fenAlice.fenCorrection.libelles()
        self.fenAliceParametrage.libelles()
        


    #========================================================================
    def actionMenu(self):
        """Démarrage d'une nouvelle activité
        """
        global change_de_jour
        global icone_run
        #Récupère le nom de cette activité
        action = self.sender()
        entry = action.text()
        #passage en gras de l'activité sélectionnée.
        #l'idée est de voir ce qu'on a fait dans la journée
        font = QtGui.QFont()
        font.setBold(True)
        action.setFont(font)
        #enregistre l'évènement en base
        self.DB_insert_A(entry)
        # l'info bulle prend la valeur de l'action en cours
        bulle = entry
        self.setToolTip(bulle)
        #Rechargement du calendier des activités
        if self.fenAlice.semaine.isChecked() == True:
            self.fenAlice.chargeTableauSemaine(0, None)
        if self.fenAlice.mois.isChecked() == True:
            self.fenAlice.chargeTableauMois(0, None)
        if self.fenAlice.annee.isChecked() == True:
            self.fenAlice.chargeTableauAnnee(0, None)
        #faire tourner l'icône d'horloge en systray
        self.setIcon(QtGui.QIcon(iconeRun))
        if icone_run == 0:
            rt.start()
            
        #recharge le menu si on change de journée, le but est de ne pas avoir tout en gras
        dj = datetime.now()
        cdj = date(dj.year, dj.month, dj.day)
        if not cdj == change_de_jour:
            self.initmenu()
            change_de_jour = cdj


    #========================================================================
    def stopMenu(self):
        """Arrêt de toute activité démarré le jour même
           une activité non terminée sur une journée antérieur pourra l'être via les corrections
        """
        global icone_run
        # l'info bulle prend la valeur d'absence d'activité
        bulle = _("Aucune activité en cours")
        self.setToolTip(bulle)
        #Arrêt de toute activité en cours (DB + icône tournante)
        self.DB_stop_A()
        self.setIcon(QtGui.QIcon(iconeStop))
        rt.stop()
        icone_run = 0
        #Rechargement du calendier des activités
        if self.fenAlice.semaine.isChecked() == True:
            self.fenAlice.chargeTableauSemaine(0, None)
        if self.fenAlice.mois.isChecked() == True:
            self.fenAlice.chargeTableauMois(0, None)
        if self.fenAlice.annee.isChecked() == True:
            self.fenAlice.chargeTableauAnnee(0, None)


    #========================================================================
    def quitter(self):
        """permet de quitter: ferme le programme ainsi que le systemtray
 
        """
        #on arrête toute éventuelle activité déjà démarrée
        self.stopMenu()
        #fin...
        self.app.quit()

class FAliceActivite(QtWidgets.QWidget):
    """gestion de la liste des activités
       créer de nouvelles activités
       les supprimer
       les ajouter au menu contextuel (classe précédente)
       les trier
       les renommer
    """
    def __init__(self):
        super().__init__()

        self.data_list = []

        self.init_ui()

    def init_ui(self):
        #accès unifiés dans la même classe
        self.DBAA = DB_Acces_Alice
        #accès à une base de données
        baseDB = "Alice.db"
        self.con = None
        # Ouvrir une connexion à la base de données SQLite (n'est pas exécuté si la connexion est déjà ouverte)
        self.con = sqlite3.connect(baseDB)
        self.cur = self.con.cursor()
        self.DB_connexion()  

        self.setWindowTitle(_("Liste des activités"))

        # Pour renommer des activités
        self.labela = QtWidgets.QLabel(_("Activité à renommer :"))
        renome_layout = QtWidgets.QHBoxLayout()
        self.select_activite = QtWidgets.QComboBox()
        self.select_activite.setToolTip(_("sélectionner l'activité à renommer"))
        self.renomme_activite = QtWidgets.QLineEdit()
        self.renomme_activite.setToolTip(_("saisir le nouveau nom de l'activité"))
        self.renomme_button = QtWidgets.QPushButton(_("Renommer"))
        self.renomme_button.clicked.connect(self.renommer)
        #le 2, je ne sais pas trop à quoi il sert mais il est bien :-)
        renome_layout.addWidget(self.select_activite, 2)
        renome_layout.addWidget(self.renomme_activite)
        renome_layout.addWidget(self.renomme_button)

        # pour ajouter des activités
        self.label = QtWidgets.QLabel(_("Ajouter des activités :"))
        self.saisie_activite = QtWidgets.QLineEdit()
        self.saisie_activite.setToolTip(_("saisir le libellé d'une nouvelle activité"))
        self.saisie_activite.returnPressed.connect(self.add_data)

        self.add_button = QtWidgets.QPushButton(_("Ajouter"))
        self.add_button.clicked.connect(self.add_data)
        self.del_button = QtWidgets.QPushButton(_("Supprimer"))
        self.del_button.clicked.connect(self.del_data)

        #self.data_list_activitees = QtWidgets.QListWidget()
        self.data_list_activitees = QtWidgets.QTreeWidget()
        
        self.data_list_activitees.setToolTip(_("liste des activités reconnues par l'application"))
        self.data_list_activitees.setSelectionMode(QtWidgets.QListWidget.ExtendedSelection)
        self.data_list_activitees.itemDoubleClicked.connect(self.move_right)

        self.liste_menu = QtWidgets.QListWidget()
        self.liste_menu.setToolTip(_("liste des activités affichées dans le menu"))
        self.liste_menu.setSelectionMode(QtWidgets.QListWidget.ExtendedSelection)
        self.liste_menu.itemDoubleClicked.connect(self.move_left)

        self.move_right_button = QtWidgets.QPushButton(">")
        self.move_right_button.setToolTip(_("Ajouter activités au menu"))
        self.move_left_button = QtWidgets.QPushButton("<")
        self.move_left_button.setToolTip(_("supprimer activités du menu"))
        self.move_up_button = QtWidgets.QPushButton("↑")
        self.move_up_button.setToolTip(_("remonter dans la liste du menu"))
        self.move_down_button = QtWidgets.QPushButton("↓")
        self.move_down_button.setToolTip(_("redescendre dans la liste du menu"))
        self.move_up_button2 = QtWidgets.QPushButton("↑")
        self.move_up_button2.setToolTip(_("remonter dans le calendrier"))
        self.move_down_button2 = QtWidgets.QPushButton("↓")
        self.move_down_button2.setToolTip(_("redescendre dans le calendrier"))
        self.parent_button = QtWidgets.QPushButton(_("Parent"))
        self.parent_button.setToolTip(_("remonter dans la hérarchie des activités"))
        self.enfant_button = QtWidgets.QPushButton(_("Enfant"))
        self.enfant_button.setToolTip(_("redescendre dans la hérarchie des activité"))
        

        self.move_right_button.clicked.connect(self.move_right)
        self.move_left_button.clicked.connect(self.move_left)
        self.move_up_button.clicked.connect(self.move_up)
        self.move_down_button.clicked.connect(self.move_down)
        self.move_up_button2.clicked.connect(self.move_up_cal)
        self.move_down_button2.clicked.connect(self.move_down_cal)
        self.parent_button.clicked.connect(self.parent_up)
        self.enfant_button.clicked.connect(self.enfant_down)
        

        # Créer le layout général
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.labela)
        #renome_layout: contient tout ce qui sert à renommer
        layout.addLayout(renome_layout)

        layout.addWidget(self.label)
        layout.addWidget(self.saisie_activite)
        layout.addWidget(self.add_button)
        layout.addWidget(self.del_button)

        button_layout = QtWidgets.QVBoxLayout()
        button_layout.addWidget(self.move_right_button)
        button_layout.addWidget(self.move_left_button)
        button_layout.addWidget(self.move_up_button2)
        button_layout.addWidget(self.move_down_button2)
        button_layout.addWidget(self.parent_button)
        button_layout.addWidget(self.enfant_button)

        button_layout2 = QtWidgets.QVBoxLayout()
        button_layout2.addWidget(self.move_up_button)
        button_layout2.addWidget(self.move_down_button)

        list_layout = QtWidgets.QHBoxLayout()
        list_layout.addWidget(self.data_list_activitees)
        list_layout.addLayout(button_layout)
        list_layout.addWidget(self.liste_menu)
        list_layout.addLayout(button_layout2)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(list_layout)

        self.setLayout(main_layout)
        
        #charger tableaux
        self.charge_activitees(None)
        self.charge_activitees_menu()
        
    def libelles(self):
        self.labela.setText(_("Activité à renommer :"))
        self.setWindowTitle(_("Liste des activités"))
        self.select_activite.setToolTip(_("sélectionner l'activité à renommer"))
        self.renomme_activite.setToolTip(_("saisir le nouveau nom de l'activité"))
        self.renomme_button.setText(_("Renommer"))
        self.label.setText(_("Ajouter des activités :"))
        self.saisie_activite.setToolTip(_("saisir le libellé d'une nouvelle activité"))
        self.add_button.setText(_("Ajouter"))
        self.del_button.setText(_("Supprimer"))
        self.data_list_activitees.setToolTip(_("liste des activités reconnues par l'application"))
        self.liste_menu.setToolTip(_("liste des activités affichées dans le menu"))
        self.move_right_button.setToolTip(_("Ajouter activités au menu"))
        self.move_left_button.setToolTip(_("supprimer activités du menu"))
        self.move_up_button.setToolTip(_("remonter dans la liste du menu"))
        self.move_down_button.setToolTip(_("redescendre dans la liste du menu"))
        self.move_up_button2.setToolTip(_("remonter dans le calendrier"))
        self.move_down_button2.setToolTip(_("redescendre dans le calendrier"))
        self.parent_button.setText(_("Parent"))
        self.parent_button.setToolTip(_("remonter dans la hérarchie des activités"))
        self.enfant_button.setText(_("Enfant"))
        self.enfant_button.setToolTip(_("redescendre dans la hérarchie des activité"))
        
    def renommer(self):
        """renommer une activité
        """
        #DB_update_renomme(self.select_activite, self.renomme_activite)
        a = self.select_activite.currentText()
        b = self.renomme_activite.text()
        #si aucune différence alors il n'y a rien à faire!
        if b == "" or a == None:
            QtWidgets.QMessageBox.information(self, _("Attention!!!"), _("Il faut saisir un nouveau nom"))
        elif a != b:
            #on cherche si ça existe déjà
            c = self.DB_select_AR(b)
            if c != None:
                buttonReply = QtWidgets.QMessageBox.question(self, _("Attention!!!"), _("Ce libellé existe déjà, voulez-vous continuer?"),QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            else:
                buttonReply = QtWidgets.QMessageBox.Yes
            if buttonReply == QtWidgets.QMessageBox.Yes:
                #si on fusionne 2 activités alors on va éviter de doubler l'activité dans la liste des taches
                if c == None:
                    self.DB_update_renomme(a, b)
                else:
                    self.DB_update_renomme2(a, b)
                #on recharge un peu tout pour un affichage qui corresponde aux nouvelles données partout
                self.charge_activitees(b)
                self.charge_activitees_menu()
                trayIcon.initmenu()
                self.renomme_activite.clear()
                #Rechargement du calendier des activités suite à l'application du correctif
                if trayIcon.fenAlice.semaine.isChecked() == True:
                    trayIcon.fenAlice.chargeTableauSemaine(0, None)
                if trayIcon.fenAlice.mois.isChecked() == True:
                    trayIcon.fenAlice.chargeTableauMois(0, None)
                if trayIcon.fenAlice.annee.isChecked() == True:
                    trayIcon.fenAlice.chargeTableauAnnee(0, None)
        else:
            self.renomme_activite.clear()


    def add_data(self):
        """créer une nouvelle activité
        """
        data = self.saisie_activite.text()
        if data:
            #On ne crée pas l'&activité si elle existe déjà
            a = self.DB_select_AR(data)
            if a != None:
                QtWidgets.QMessageBox.information(self, _("Attention!!!"), _("Ce libellé existe déjà"))
            else:
                #DB_insert_A(self, libActivite, parent, niveau, ordre_calendrier, ordre_menu, affichage_menu)
                self.DB_insert_A(data, "", 0, len(self.data_list), 0, 0)
                self.saisie_activite.clear()
                self.charge_activitees(data)

    def del_data(self):
        """supprimer une activité
           ne supprime pas l'historique du temps passé sur cette activité au calendrier
        """
        selected_items = self.data_list_activitees.selectedItems()
        for item in selected_items:
             if item.text(0) == '+':
                text = item.text(2)
                #DB_update_A(self, libActivite, parent, niveau, ordre_menu, affichage_menu)
                self.DB_update_A3(text)
                self.DB_delete_A(text)
        self.DB_update_parent()
        #charger tableaux
        self.charge_activitees(None)
        self.charge_activitees_menu()
        #rechargement du menu dans l'instance trayIcom
        trayIcon.initmenu()

    def move_right(self):
        """ajoute une activité au menu
        """
        selected_items = self.data_list_activitees.selectedItems()
        text = None
        for item in selected_items:
            if item.text(0) == '+':
                text = item.text(2)
                #self.selected_list.append(text)
                self.liste_menu.addItem(text)
                #DB_update_ASP(self, libActivite, niveau, ordre_menu, affichage_menu)
                self.DB_update_ASP(text, item.text(1), self.liste_menu.count() - 1, 1)
                #item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
        #rechargement du menu dans l'instance trayIcom
        trayIcon.initmenu()
        self.charge_activitees(text)

    def move_left(self):
        """supprime une activité du menu
        """
        selected_items = self.liste_menu.selectedItems()
        text = None
        for item in selected_items:
            text = item.text()
            index = self.liste_menu.row(item)
            #self.selected_list.remove(text)
            self.liste_menu.takeItem(self.liste_menu.row(item))
            iterator = QtWidgets.QTreeWidgetItemIterator(self.data_list_activitees)
            while iterator.value():
                it = iterator.value()
                if it.text(2) == text:
                    self.DB_update_ASP(text, it.text(1), 0, 0)
                    #it.setFlags(it.flags() | QtCore.Qt.ItemIsEnabled)
                    break
                iterator+=1
            #recalcul ordre des éléments du menu
            self.DB_update_A2(index)
        self.charge_activitees_menu()
        #rechargement du menu dans l'instance trayIcom
        trayIcon.initmenu()
        self.charge_activitees(text)

    def move_up(self):
        """remonte une activité dans la liste du menu
        """
        selected_items = self.liste_menu.selectedItems()
        selected_items.sort(key=lambda item: self.liste_menu.row(item))
        for item in selected_items:
            index = self.liste_menu.row(item)
            if index > 0:
                self.liste_menu.takeItem(index)
                self.liste_menu.insertItem(index - 1, item.text())
                #self.liste_menu.setItemSelected(item, True)
                self.liste_menu.setCurrentRow(index - 1)
                #mise à jour de l'ordre d'affichage. DB_update_ASP(self, libActivite, niveau, ordre_menu,  affichage_menu)
                self.DB_update_ASP(item.text(), 0, index - 1, 1)
                #mise à jour de l'ordre d'affichage
                item_permute = self.liste_menu.item(index)
                self.DB_update_ASP(item_permute.text(), 0, index, 1)
                #rechargement du menu dans l'instance trayIcom
                trayIcon.initmenu()

    def move_down(self):
        """redescend une activité dans la liste du menu
        """
        selected_items = self.liste_menu.selectedItems()
        selected_items.sort(key=lambda item: self.liste_menu.row(item))
        for item in reversed(selected_items):
            index = self.liste_menu.row(item)
            if index < self.liste_menu.count() - 1:
                self.liste_menu.takeItem(index)
                self.liste_menu.insertItem(index + 1, item.text())
                #self.liste_menu.setItemSelected(item, True)
                self.liste_menu.setCurrentRow(index + 1)
                #mise à jour de l'ordre d'affichage. DB_update_ASP(self, libActivite, niveau, ordre_menu,  affichage_menu)
                self.DB_update_ASP(item.text(), 0, index + 1, 1)
                #mise à jour de l'ordre d'affichage
                item_permute = self.liste_menu.item(index)
                self.DB_update_ASP(item_permute.text(), 0, index, 1)
                #rechargement du menu dans l'instance trayIcom
                trayIcon.initmenu()

    def move_up_cal(self):
        """remonte une activité dans la liste du calendrier
        """
        text = None
        selected_items = self.data_list_activitees.selectedItems()
        if selected_items:
            if len(selected_items) == 1:
                #cas simple géré simplement, une seule ligne sélectionnée
                for item in selected_items:
                    text = item.text(2)
                    self.DB_update_ACU(text)
                    self.DB_update_parent()
            else:
                #plusieurs lignes, l'ordre de traitement dépend de la hiérarchie , de l'ordre de sélection et impossible à trier correctement... donc on s'en affranchit! 
                for item in selected_items:
                    text = item.text(2)
                    self.DB_insert_Param("__temporaire__", "", text, None, None, None)
                self.DB_update_ACUM()
            self.charge_activitees(text)


    def move_down_cal(self):
        """redescend une activité dans la liste du calendrier
        """
        text = None
        selected_items = self.data_list_activitees.selectedItems()
        selected_items.sort(key=lambda item: self.data_list_activitees.indexOfTopLevelItem(item))
        if selected_items:
            if len(selected_items) == 1:
                for item in selected_items:
                    text = item.text(2)
                    self.DB_update_ACD(text)
                    self.DB_update_parent()
            else:
                #plusieurs lignes, l'ordre de traitement dépend de la hiérarchie et de l'ordre de sélection... donc on s'en affranchit! 
                for item in selected_items:
                    text = item.text(2)
                    self.DB_insert_Param("__temporaire__", "", text, None, None, None)
                self.DB_update_ACDM()
            self.charge_activitees(text)        

    def parent_up(self):
        """remonte dans la hiérarchie
        """
        text = None
        selected_items = self.data_list_activitees.selectedItems()
        for item in selected_items:
            text = item.text(2)
            self.DB_update_APU(text)
            self.DB_update_parent()
        self.charge_activitees(text)

    def enfant_down(self):
        """redescend dans la hiérarchie
        """
        text = None
        selected_items = self.data_list_activitees.selectedItems()
        for item in selected_items:
            text = item.text(2)
            self.DB_update_APD(text)
            self.DB_update_parent()
        self.charge_activitees(text)

    def charge_activitees(self, activite_selected):
        """chargement des listbox et combobox contenant l'ensemble des activités connues
        """
        self.data_list_activitees.clear()
        self.data_list_activitees.setColumnCount(3)
        self.data_list_activitees.setColumnWidth(0, 70)
        self.data_list_activitees.setColumnWidth(1, 4)
        self.data_list_activitees.setHeaderLabels([_("Menu"),_("Niv"), _("Libellé")])
        self.select_activite.clear()
        self.extraction = self.DB_select_AT()
        #nb d'enreg extraits
        nb_lignes = len(self.extraction)
        items = []
        item = None
        child = None
        child2 = None
        self.data_list = []
        #chargement des paramètres de police de caractère des 3 hiérarchies
        polices = self.DBAA.charge_polices(self)


        #Boucle d'alimentation des activités de la semaine
        #on ne gère que 3 niveaux hiérarchiques. sans doute principe à revoir si on veut en ajouter d'autres ensuite
        for i in range(nb_lignes):
            self.select_activite.addItem(self.extraction[i][0])
            self.data_list.append(self.extraction[i][0])
            #
            #niveau parent le plus bas
            if self.extraction[i][3] == 0:
                #à rupture on ajoute item
                if child:
                    item.addChild(child)
                    child = None
                if item:
                    items.append(item)
                    child = None
                item = QtWidgets.QTreeWidgetItem([str(self.extraction[i][1]), str(self.extraction[i][3]), self.extraction[i][0]])
                #police - freesansbold
                #taille
                #gras: 0 non - 25 léger - 50 normal - 63 demi-gras - 75 Gras - 87 Noir
                #italique
                #item.setFont(2, QtGui.QFont("Times New Roman", 10, 25, True ))
                #item.setFont(2, QtGui.QFont("freesansbold", 10, 25, False ))
                item.setFont(2, QtGui.QFont(polices[0][0], int(polices[0][1]), polices[0][2], polices[0][3] ))
            #
            #Niveau enfant intermédiaire
            elif self.extraction[i][3] == 1:
                #on a déja traité un enfant intermédiaire, on l'ajoute avant de traiter celui-ci
                if item and child:
                    item.addChild(child)
                if item:
                    child = QtWidgets.QTreeWidgetItem([str(self.extraction[i][1]), str(self.extraction[i][3]), self.extraction[i][0]])
                    child.setFont(2, QtGui.QFont(polices[1][0], int(polices[1][1]), polices[1][2], polices[1][3] ))
                #on commence sans un niveau zéro en début, on a de facto l'équivalent un niveau parent 0 même s'il est 1 ou 2
                else:
                    item = QtWidgets.QTreeWidgetItem([str(self.extraction[i][1]), str(self.extraction[i][3]), self.extraction[i][0]])
                    item.setFont(2, QtGui.QFont(polices[1][0], int(polices[1][1]), polices[1][2], polices[1][3] ))

            #
            #Niveau enfant 2
            elif self.extraction[i][3] == 2:
                #ajout au niveau 1 s'il y en a un en cours
                child2 = QtWidgets.QTreeWidgetItem([str(self.extraction[i][1]), str(self.extraction[i][3]), self.extraction[i][0]])
                child2.setFont(2, QtGui.QFont(polices[2][0], int(polices[2][1]), polices[2][2], polices[2][3] ))
                if child:
                    child.addChild(child2)
                #ajout au niveau racine si pas de niv1 en cours
                elif item:
                    item.addChild(child2)
                else:
                    #ou root si rien au dessus
                    item = QtWidgets.QTreeWidgetItem([str(self.extraction[i][1]), str(self.extraction[i][3]), self.extraction[i][0]])
                    item.setFont(2, QtGui.QFont(polices[2][0], int(polices[2][1]), polices[2][2], polices[2][3] ))
        if child:
            item.addChild(child)
        if item:
            items.append(item)
        self.data_list_activitees.insertTopLevelItems(0, items)
        self.data_list_activitees.expandAll()
        #sélection par défaut d'une ligne
        if activite_selected:
            iterator = QtWidgets.QTreeWidgetItemIterator(self.data_list_activitees)
            while iterator.value():
                it = iterator.value()
                if it.text(2) == activite_selected:
                    it.setSelected(True)
                    break
                iterator+=1



    def charge_activitees_menu(self):
        """chargement des activités définies sur le menu dans la listbox
           sert à savoir si les activités contenues dans la liste totale des activités sont 
             - grisées et non sélectionnables (et non supprimables) si elles sont dans le menu
             - saisissables et supprimables si elles ne sont plus dans le menu
           c'est une forme de contrôle qu'on ne supprime pas par erreur une activité toujours utilisée
        """
        self.liste_menu.clear()
        self.extraction = self.DB_select_AM()
        #nb d'enreg extraits
        nb_lignes = len(self.extraction)

        #Boucle d'alimentation des activités de la semaine
        for i in range(nb_lignes):
            item = QtWidgets.QListWidgetItem(self.extraction[i][0])
            if self.extraction[i][1] == 1:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
            else:
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEnabled)
            self.liste_menu.addItem(item)


    def keyPressEvent(self, event):
        """permettre le masquage de la fenêtre en appuyant sur la touche échap
        """
        #if event.key() == QtCore.Qt.Key_Enter:
        if event.key() in [QtCore.Qt.Key_Escape]:
            self.quitter_action()

    def quitter_action(self):
        """masquage de la fenêtre
        """
        self.hide()

    #accès base de donnée
    def DB_connexion(self):
            try:
                #Vérifie existence de la table
                TAppr = self.cur.execute("""SELECT tbl_name FROM sqlite_master WHERE type='table' AND tbl_name='activite';""").fetchall()
                if TAppr == []:
                    #print('table a creer')
                    self.DB_create()

            except sqlite3.Error as e:
                if self.con:
                    self.con.rollback()

                #print(f"Error {e.args[0]}")
                QtWidgets.QMessageBox.about(self, "ERREUR", f"Error {e.args[0]}")
                sys.exit(1)
    #création si inexistante
    def DB_create(self):
        self.cur.execute("""CREATE TABLE activite (libelle  TEXT NOT NULL, debut TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, fin TIMESTAMP,  id INTEGER, PRIMARY KEY( id  AUTOINCREMENT));""")
        self.cur.execute("""CREATE TABLE correction (libelle TEXT NOT NULL, jour DATE, correction INTEGER, duree INTEGER, tevt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);""")
        self.cur.execute("""CREATE TABLE parametres (type TEXT,stype TEXT,valeur_a TEXT,valeur_n REAL,valeur_int INTEGER,visible INTEGER);""")
        self.cur.execute("""CREATE TABLE taches ( libelle TEXT, parent TEXT, niveau INTEGER, ordre_calendrier INTEGER, ordre_menu INTEGER, affichage_menu INTEGER);""")
    #sélection de toutes les activités
    def DB_select_AT(self):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select libelle, case when affichage_menu = 1 then '-' else '+' end, parent, niveau
                            from taches
                            order by ordre_calendrier, libelle""")
        return (self.cur.fetchall())
    #sélection des activités pour le menu
    def DB_select_AM(self):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select libelle, parent, niveau
                            from taches
                            where affichage_menu = 1
                            order by ordre_menu""")
        return (self.cur.fetchall())

    #Nouvelle activité
    def DB_insert_A(self, libActivite, parent, niveau, ordre_calendrier, ordre_menu, affichage_menu):
        #On crée l'activité
        self.cur.execute("""insert into taches (libelle, parent, niveau, ordre_calendrier, ordre_menu, affichage_menu) values(? , ?, ?, ?, ?, ?)""", (libActivite, parent, niveau, ordre_calendrier, ordre_menu, affichage_menu))
        self.cur.execute("""commit""")

    #Mise à jour activité
    #def DB_update_A(self, libActivite, parent, niveau, ordre_menu, affichage_menu):
    #    #On commence par l'arrêt de toute activité déjà en cours
    #    self.cur.execute("""update taches set parent = ? , niveau = ? , ordre_menu = ? , affichage_menu = ? where libelle = ?""", (parent, niveau, ordre_menu, affichage_menu, libActivite))
    #    self.cur.execute("""commit""")

    #Mise à jour activité sans le parent
    def DB_update_ASP(self, libActivite, niveau, ordre_menu, affichage_menu):
        #On commence par l'arrêt de toute activité déjà en cours
        self.cur.execute("""update taches set niveau = ? , ordre_menu = ? , affichage_menu = ? where libelle = ?""", (niveau, ordre_menu, affichage_menu, libActivite))
        self.cur.execute("""commit""")

    #Mise à jour activité ordre affichage menu - 1 lorsqu'on retire un élément au milieu
    def DB_update_A2(self, ordre_menu):
        #On commence par l'arrêt de toute activité déjà en cours
        self.cur.execute("""update taches set ordre_menu = ordre_menu - 1 where ordre_menu > ?""", (ordre_menu, ))
        self.cur.execute("""commit""")

    #Mise à jour activité ordre affichage menu - 1 lorsqu'on retire un élément au milieu
    def DB_update_A3(self, libelle):
        #On commence par l'arrêt de toute activité déjà en cours
        self.cur.execute("""update taches set ordre_calendrier = ordre_calendrier - 1 where ordre_calendrier > 
                            (select ordre_calendrier from taches where libelle = ?)""", (libelle, ))
        self.cur.execute("""commit""")

    def DB_update_ACU(self, libelle):
        """mise à jour ordre calendrier vers le haut d'une seule ligne
        """
        self.cur.execute("""select ordre_calendrier - 1
                            from taches
                            where libelle = ?
                            and ordre_calendrier > 0""", (libelle, ))
        resultat = self.cur.fetchone()
        if resultat:
            #On permute celle sélectionnée avec celle du dessus
            self.cur.execute("""update taches set ordre_calendrier = ordre_calendrier + 1 
                                where ordre_calendrier = ?
                                """, (int(resultat[0]), ))
            self.cur.execute("""update taches set ordre_calendrier = ordre_calendrier - 1 where libelle = ?""", (libelle, ))
            self.cur.execute("""commit""")

    def DB_update_ACUM(self):
        """Mise à jour ordre calendrier vers le haut multi taches
        """
        self.cur.execute("""select libelle
                            from taches
                            where libelle in (select valeur_a from parametres
                                              where type = '__temporaire__')
                              and ordre_calendrier > 0
                            order by ordre_calendrier asc""")
        resultats = self.cur.fetchall()
        for resultat in resultats:
            self.DB_update_ACU(resultat[0])

            self.cur.execute("""delete from parametres where type = '__temporaire__'""")
            self.cur.execute("""commit""")

    def DB_select_Param(self, type, stype):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select type, stype, valeur_a, valeur_n, valeur_int, visible
                            from parametres 
                            where type = ?
                              and stype = ?
                            order by type, stype""", (type, stype ))

        return (self.cur.fetchall())

    def DB_insert_Param(self, type, stype, valeur_a, valeur_n, valeur_int, visible):
        #
        #
        self.cur.execute("""insert into parametres (type, stype, valeur_a, valeur_n, valeur_int, visible)
                            values( ?, ?, ?, ?, ?, ?)""", (type, stype, valeur_a, valeur_n, valeur_int, visible ))

        self.cur.execute("""commit""")

    def DB_update_Param(self, type, stype, valeur_a, valeur_n, valeur_int, visible):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""update parametres 
                            set valeur_a = ?
                              , valeur_n = ?
                              , valeur_int = ?
                              , visible = ?
                            where type = ?
                              and stype = ?""", (valeur_a, valeur_n, valeur_int, visible, type, stype ))

        self.cur.execute("""commit""")

    def DB_update_ACD(self, libelle):
        self.cur.execute("""select ordre_calendrier + 1
                            from taches
                            where libelle = ?
                            and ordre_calendrier < (select max(ordre_calendrier) from taches)""", (libelle, ))
        resultat = self.cur.fetchone()
        if resultat:
            #On permute celle sélectionnée avec celle du dessous
            self.cur.execute("""update taches set ordre_calendrier = ordre_calendrier - 1
                                where ordre_calendrier = ?
                            """, (int(resultat[0]), ))
            self.cur.execute("""update taches set ordre_calendrier = ordre_calendrier + 1 
                                where libelle = ?
                            """, (libelle, ))
            self.cur.execute("""commit""")

    def DB_update_ACDM(self):
        """Mise à jour ordre calendrier vers le bas multi taches
        """
        self.cur.execute("""select libelle
                            from taches
                            where libelle in (select valeur_a from parametres
                                              where type = '__temporaire__')
                              and ordre_calendrier < (select max(ordre_calendrier) from taches)
                            order by ordre_calendrier desc""")
        resultats = self.cur.fetchall()
        for resultat in resultats:
            self.DB_update_ACD(resultat[0])

            self.cur.execute("""delete from parametres where type = '__temporaire__'""")
            self.cur.execute("""commit""")


    def DB_update_APU(self, libelle):
        #On commence par l'arrêt de toute activité déjà en cours
        self.cur.execute("""update taches set niveau = niveau - 1 where niveau > 0 and libelle = ?""", (libelle, ))
        self.cur.execute("""commit""")

    def DB_update_APD(self, libelle):
        #On commence par l'arrêt de toute activité déjà en cours
        self.cur.execute("""update taches set niveau = niveau + 1 
                            where libelle = ?
                            and niveau < 2
                         """, (libelle, ))
        self.cur.execute("""commit""")

    def DB_update_parent(self):
        #mise à jour de la valeur du parent en fonction du niveau des activités et de l'ordre
        self.cur.execute("""update taches  set parent = 
                            ifnull((select libelle 
                                    from taches p 
                                    where p.niveau < taches.niveau 
                                        and p.ordre_calendrier < taches.ordre_calendrier
                                        and not exists(select 1 from taches x
                                                        where x.niveau < taches.niveau 
                                                        and x.ordre_calendrier < taches.ordre_calendrier
                                                        and x.ordre_calendrier  > p.ordre_calendrier )
                                    ), '')
                         """)
        self.cur.execute("""commit""")

    #recherche activité partout pour savoir si elle existe
    def DB_select_AR(self, lib):
        self.cur.execute("""select libelle from taches where libelle = ?
                         """,(lib, ))
        return (self.cur.fetchone())

    #Mise à jour du nom d'une activité
    def DB_update_renomme(self, libActivite, newlib):
        #On commence par l'arrêt de toute activité déjà en cours
        self.cur.execute("""update taches set libelle = ? where libelle = ?""", (newlib, libActivite))
        self.cur.execute("""update taches set parent = ? where parent = ?""", (newlib, libActivite))
        self.cur.execute("""update activite set libelle = ? where libelle = ?""", (newlib, libActivite))
        self.cur.execute("""update correction set libelle = ? where libelle = ?""", (newlib, libActivite))
        self.cur.execute("""commit""")

    #Mise à jour du nom d'une activité dans le cas d'une fusion(le nouveau nom existe déjà)
    def DB_update_renomme2(self, libActivite, newlib):
        #On commence par l'arrêt de toute activité déjà en cours
        self.cur.execute("""delete from taches where libelle = ?""", (libActivite,))
        self.cur.execute("""delete from taches where parent = ?""", (libActivite,))
        self.cur.execute("""update activite set libelle = ? where libelle = ?""", (newlib, libActivite))
        self.cur.execute("""update correction set libelle = ? where libelle = ?""", (newlib, libActivite))
        self.cur.execute("""commit""")

    #Suppression activité
    def DB_delete_A(self, libActivite):
        #On crée l'activité
        self.cur.execute("""delete from taches where libelle = ?""", (libActivite, ))
        self.cur.execute("""commit""")



class Aide(QtWidgets.QWidget):
 
    #========================================================================
    def __init__(self, parent=None):
        super().__init__(parent)
 
        self.setWindowTitle("Aide")
        self.resize(800, 600)
 
        self.view = QtWebEngineWidgets.QWebEngineView()
 
        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.view, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
 
        self.page = QtWebEngineWidgets.QWebEnginePage()
 
    #========================================================================
    def affiche(self, fichierweb):
        """affiche le fichier web donné
        """
        self.page.setUrl(QtCore.QUrl(fichierweb))
        self.view.setPage(self.page)
        self.view.show()

class FAlice(QtWidgets.QWidget):
    """fenêtre affichant le calendrier à la semaine ou au mois et contenant le temps passé 
       sur les différentes activités
       les cumuls sont possibles en jour ou en heures minutes secondes
    """
    #========================================================================
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.liste_entetes = []
        self.DBAA = DB_Acces_Alice

        #accès à une base de données
        baseDB = "Alice.db"
        self.con = None
        # Ouvrir une connexion à la base de données SQLite (n'est pas exécuté si la connexion est déjà ouverte)
        self.con = sqlite3.connect(baseDB)
        self.cur = self.con.cursor()
        self.DB_connexion()  

        self.setWindowTitle(_("Détail des activités"))
        self.setGeometry(50 , 50 , 1250 , 550)
        #self.setWindowIcon(QtGui.QIcon("icone_calendrier.png"))
        app_icon = QtGui.QIcon()
        app_icon.addFile("Alice1.ico", QtCore.QSize(16,16))

        self.setWindowIcon(app_icon)
        #date du jour
        self.dxj = date.today()
      
        
        # création d'un objet graphique QTableWidget qui va contenir les dates quantièmes et numéros de semaines
        self.table = QtWidgets.QTableWidget(self)
        #définition caractéristiques: position, dimensions, nombre de colonnes et lignes. fait pour que ça tienne dans un écran PC portable en hauteur sans ascenseur.
        self.table.setColumnCount(8)
        self.table.setGeometry(10 , 120 , 1200 , 400)
        #largeur de la première colonne
        self.table.setColumnWidth(0, 100)
        self.table.doubleClicked.connect(self.selection_tableau)
        self.table.clicked.connect(self.selection_tableau)
        ## adding header to the table

        #Date du jour
        self.ldatejour = QtWidgets.QPushButton(_("date du jour : ") + str(self.dxj), self)
        self.ldatejour.clicked.connect(self.semaineCourante)
        self.ldatejour.setGeometry(10 , 0 , 170 , 35)

        #Semaine
        self.lsemaine = QtWidgets.QLabel(self)
        #self.lsemaine.setText("Semaine " + str(s[1])) #inutile fait plus loin
        self.lsemaine.setGeometry(400, 0, 200, 50)

        #Toujours au dessus
        self.tadessus = QtWidgets.QCheckBox(self)
        self.tadessus.setText(_("Toujours au dessus"))
        self.tadessus.setChecked=False
        self.tadessus.toggled.connect(self.toujours_au_dessus)
        self.tadessus.setGeometry(10, 70, 200, 50)
        #self.tadessus.show()

        #Semaine ou année (ou mois?)
        #recherche paramétrage par défaut s'il existe, sinon on le crée avec une valeur par défaut
        self.lparam = self.DB_select_Param("periode", "")
        if len(self.lparam) == 0:
            self.DB_insert_Param("periode", "", "semaine", None, None, None)
            self.lparam = self.DB_select_Param("periode", "")
        self.groupbox1 = QtWidgets.QGroupBox(self)
        self.groupbox1.setGeometry(10, 35, 210, 40)
        self.semaine = QtWidgets.QRadioButton(self.groupbox1)
        self.semaine.setText(_("Semaine"))
        self.semaine.setGeometry(5, 10, 80, 20)
        if self.lparam[0][2] == "semaine":
            self.semaine.setChecked(True)
        else:
            self.semaine.setChecked(False)
        self.semaine.toggled.connect(self.selection_grille)
        self.mois = QtWidgets.QRadioButton(self.groupbox1)
        self.mois.setText(_("Mois"))
        self.mois.setGeometry(85, 10, 55, 20)
        if self.lparam[0][2] == "mois":
            self.mois.setChecked(True)
        else:
            self.mois.setChecked(False)
        self.mois.toggled.connect(self.selection_grille)
        self.annee = QtWidgets.QRadioButton(self.groupbox1)
        self.annee.setText(_("Année"))
        self.annee.setGeometry(140, 10, 65, 20)
        if self.lparam[0][2] == "annee":
            self.annee.setChecked(True)
        else:
            self.annee.setChecked(False)        
        #self.annee.setEnabled(False)
        self.annee.toggled.connect(self.selection_grille)
        

        #totaux affichés en Heure:minute:seconde ou quantième de jour de la semaine
        #recherche paramétrage par défaut s'il existe, sinon on le crée avec une valeur par défaut
        self.lparam = self.DB_select_Param("totaux", "")
        if len(self.lparam) == 0:
            self.DB_insert_Param("totaux", "", "heure", None, None, None)
            self.lparam = self.DB_select_Param("totaux", "")
        self.groupbox2 = QtWidgets.QGroupBox(self)
        self.groupbox2.setGeometry(230, 10, 100, 70)
        self.groupbox2.setTitle(_("Totaux"))
        self.semaine_heure = QtWidgets.QRadioButton(self.groupbox2)
        self.semaine_heure.setText("h:m:s")
        self.semaine_heure.setGeometry(10, 15, 100, 20)
        if self.lparam[0][2] == "heure":
            self.semaine_heure.setChecked(True)
        else:
            self.semaine_heure.setChecked(False)
        self.semaine_heure.toggled.connect(self.selection_semaine)

        self.semaine_jour = QtWidgets.QRadioButton(self.groupbox2)
        self.semaine_jour.setText(_("j"))
        self.semaine_jour.setGeometry(10, 45, 100, 20)
        if self.lparam[0][2] == "jour":
            self.semaine_jour.setChecked(True)
        else:
            self.semaine_jour.setChecked(False)
        self.semaine_jour.toggled.connect(self.selection_semaine)


        # créer bouton avant
        self.button_avant = QtWidgets.QPushButton(_("Période Précédente"), self)
        self.button_avant.clicked.connect(self.avant)
        self.button_avant.setGeometry(400, 50, 150, 50)

        # créer bouton après
        self.button_apres = QtWidgets.QPushButton(_("Période Suivante"), self)
        self.button_apres.clicked.connect(self.apres)
        self.button_apres.setGeometry(570, 50, 150, 50)

        ## créer le champ de saisie de texte lineEdit
        self.lineEdit = QtWidgets.QLineEdit(self)
        ##sur apui de la touche entrée lors de la saisie de texte, appel ok_action
        self.lineEdit.returnPressed.connect(self.ok_action)
        self.lineEdit.setGeometry(570, 10, 150, 30)
        self.lineEdit.setToolTip(_("saisir une date au format JJ.MM.SSAA ou SSAAMMJJ ou un quantième d'année aux formats QQQ ou AA.QQQ ou SSAA.QQQ puis entrée pour y accéder."))

        self.fenCorrection = lancementFenCorrection()

        #chargement initial du tableau avec dernière date du tableau = date du jour
        self.chargeTableauSemaine(0, None)
        #self.avant()


    def libelles(self):
        self.setWindowTitle(_("Détail des activités"))
        self.ldatejour.setText(_("date du jour : ") + str(self.dxj))
        self.semaine.setText(_("Semaine"))
        self.mois.setText(_("Mois"))
        self.annee.setText(_("Année"))
        self.tadessus.setText(_("Toujours au dessus"))
        self.groupbox2.setTitle(_("Totaux"))
        self.semaine_heure.setText("h:m:s")
        self.semaine_jour.setText(_("j"))
        self.button_avant.setText(_("Période Précédente"))
        self.button_apres.setText(_("Période Suivante"))
        self.lineEdit.setToolTip(_("saisir une date au format JJ.MM.SSAA ou SSAAMMJJ ou un quantième d'année aux formats QQQ ou AA.QQQ ou SSAA.QQQ puis entrée pour y accéder."))



    def date_du_jour(self):
        #date du jour
        self.dxj = date.today()

        #bouton
        self.ldatejour.setText(_("date du jour : ") + str(self.dxj))

    def resizeEvent(self, event):
        # Appeler la méthode resizeEvent de la classe parente
        super().resizeEvent(event)

        # Redimensionner le tableau pour occuper tout l'espace disponible
        self.table.setGeometry(10, 120, self.width() - 20, self.height() - 130)

    def selection_tableau(self):
        #corriger des saisies en cliquant sur le jour et on lance une boîte de dialogue de correction
        #on ne corrige pas en mode affichage à l'année
        if self.annee.isChecked() == False:
            for item in self.table.selectedItems():
                if item.row() == 1 and item.column() >= 1:
                    #message = message + str(item.row()) + ';' + str(item.column()) + ';' + item.text() + '-'
                    self.fenCorrection.showNormal()
                    self.fenCorrection.activateWindow()
                    #passage de la date à la fenêtre de correction
                    self.fenCorrection.setDate(self.table.horizontalHeaderItem(item.column()).text())
                
        #QtWidgets.QMessageBox.about(self, "Debug", message)

    def toujours_au_dessus(self):
        radio_button = self.sender()

        if radio_button.isChecked():
            #self.setWindowFlags(self.windowFlags() | 0x00000008)  # Définit le drapeau "Qt::WindowStaysOnTopHint"
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            #self.setWindowFlags(self.windowFlags() & ~0x00000008)  # Supprime le drapeau "Qt::WindowStaysOnTopHint"
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
        self.setVisible(True)

    def selection_grille(self):
        """sur changement de période sélectionnée, on sauvegarde le paramétrage et recharge tout
        """
        radio_button = self.sender()

        if radio_button.isChecked():
            if radio_button.text() == _("Semaine"):
                #sauvegarde paramétrage
                self.DB_update_Param("periode", "", "semaine", None, None, None)
                #rechargement
                self.chargeTableauSemaine(0, self.dd)
            if radio_button.text() == _("Mois"):
                #sauvegarde paramétrage
                self.DB_update_Param("periode", "", "mois", None, None, None)
                #rechargement
                self.chargeTableauMois(0, self.dd)
            if radio_button.text() == _("Année"):
                #sauvegarde paramétrage
                self.DB_update_Param("periode", "", "annee", None, None, None)
                #rechargement
                self.chargeTableauAnnee(0, self.dd)
                #QtWidgets.QMessageBox.about(self, "Debug", "selection1:" + radio_button.text())
                #self.chargeTableauAnnee(0, self.dd)

    def selection_semaine(self):
        """choix d'afficher les totaux en
           - heure minutes secondes passées
           - jour, la granularité de journée passée étant la 1/2 journée et le total une règle de 3
        """
        radio_button = self.sender()
        if radio_button.isChecked():
            if radio_button.text() == 'h:m:s':
                self.DB_update_Param("totaux", "", "heure", None, None, None)
            if radio_button.text() == _('j'):
                self.DB_update_Param("totaux", "", "jour", None, None, None)
        
        #sur changement de paramètre d'affichage, on recharge tout
        if self.semaine.isChecked() == True:
            self.chargeTableauSemaine(0, self.dd)
        elif self.mois.isChecked() == True:
            self.chargeTableauMois(0, self.dd)
        elif self.annee.isChecked() == True:
            self.chargeTableauAnnee(0, self.dd)            
            


    #def selection_total(self):
    #    radio_button = self.sender()
    #
    #    if radio_button.isChecked():
    #        QtWidgets.QMessageBox.about(self, "Debug", "selection3:" + radio_button.text())

    #chargement vers le passé
    def avant(self):
        if self.semaine.isChecked():
            self.chargeTableauSemaine(-1, None)
        elif self.mois.isChecked():
            self.chargeTableauMois(-1, None)
        elif self.annee.isChecked():
            self.chargeTableauAnnee(-1, None)

    #chargement vers le futur
    def apres(self):
        if self.semaine.isChecked():
            self.chargeTableauSemaine(1, None)
        elif self.mois.isChecked():
            self.chargeTableauMois(1, None)
        elif self.annee.isChecked():
            self.chargeTableauAnnee(1, None)

    #chargement semaine/mois en cours
    def semaineCourante(self):
        if self.semaine.isChecked():
            self.chargeTableauSemaine(0, None)
        elif self.mois.isChecked():
            self.chargeTableauMois(0, None)
        elif self.annee.isChecked():
            self.chargeTableauAnnee(0, None)

    #chargement avec sens de chargement en paramètre
    def chargeTableauSemaine(self, sens, date_origine):
        global parametre_jour
        global parametre_demi_jour

        #chargement des paramètres de police de caractère des 3 hiérarchies
        polices = self.DBAA.charge_polices(self)

        #refresh de la date et de la semaine sur le bouton et le label
        self.date_du_jour()
        #définition caractéristiques: position, dimensions, nombre de colonnes et lignes. fait pour que ça tienne dans un écran PC portable en hauteur sans ascenseur.
        self.table.setColumnCount(8)
        #QtWidgets.QMessageBox.about(self, "Debug", "dj:" + str(self.dj))
        #rechargement utile si le programme reste chargé plusieurs jours d'affilée
        self.dxj = date.today()
        #suivant le sens on part de la date min ou date max précédemment affichée
        if sens == -1:
            #permet d'ajouter ou supprimer des jours à une date
            deltaJour = timedelta(sens)            
            self.df = self.dd + deltaJour
            self.dd = self.df
        elif sens == 0:
            if date_origine == None:
                d1 = date(self.dxj.year, self.dxj.month, self.dxj.day)
            else:
                d1 = date(date_origine.year, date_origine.month, date_origine.day)
            deltajour = timedelta(d1.weekday())
            #1er jour de la semaine
            self.dd = d1 - deltajour
            #dernier jour de la semaine
            self.df = self.dd + timedelta(6)
            sens = 1
            deltaJour = timedelta(sens)         
        else:
            #permet d'ajouter ou supprimer des jours à une date
            deltaJour = timedelta(sens)
            self.dd = self.df + deltaJour
        jourSuivant = self.dd

        #Semaine
        s = self.dd.isocalendar()
        self.lsemaine.setText(_("Semaine ") + str(s[1]))        
        #préalimente à lignes du tableau, ça permet un init des données
        self.table.setRowCount(0)
        #préalimente 2 lignes du tableau
        self.table.setRowCount(2)

        headerV = [_('Quantième') , _('Correction')]
        # adding header to the table
        self.liste_entetes = []
        #boucle de chargement, à l'endroit ou à l'envers suivant le sens du chargement des données de date
        for i in range(0, 7):
            if sens == -1:
                r = 6 - i
            else:
                r = i
            #calcul quantième
            d1 = date(jourSuivant.year, jourSuivant.month, jourSuivant.day)
            d0 = date(jourSuivant.year - 1, 12, 31)
            quantieme = d1 - d0
            #ajout date en entête de colonne
            self.liste_entetes.append(str(d1))
            #calcul numéro de semaine
            s = d1.isocalendar()
            #affichage en gras des jours du week-end
            font = QtGui.QFont()
            if d1.weekday() >= 5:
                font.setBold(True)
            else:
                font.setBold(False)
            #affichage du jour "dx" (quantième ou date du jour) en gras italique
            font2 = QtGui.QFont()
            if d1 == self.dxj:
                font2.setBold(True)
                font2.setItalic(True)
            # tous les 10 quantièmes affiché en gras pour plus de lisibilité
            elif int(str(quantieme.days)) % 10 == 0:
                font2.setBold(True)
                font2.setItalic(False)
            else:
                font2.setBold(False)
                font2.setItalic(False)

            #pour affichage du jour de la semaine 
            if d1.weekday() == 0:
                jourS = _(' Lundi')
            elif d1.weekday() == 1:
                jourS = _(' Mardi')
            elif d1.weekday() == 2:
                jourS = _(' Mercredi')
            elif d1.weekday() == 3:
                jourS = _(' Jeudi')
            elif d1.weekday() == 4:
                jourS = _(' Vendredi')
            elif d1.weekday() == 5:
                jourS = _(' Samedi')
            elif d1.weekday() == 6:
                jourS = _(' Dimanche')
            else:
                jourS = ' '

            #alimentation d'une ligne du tableau cellule par cellule avec application des Font
            self.table.setItem(1 , r + 1 , QtWidgets.QTableWidgetItem(jourS))
            self.table.item(1, r + 1).setFont(font)
            self.table.item(1,r + 1).setToolTip("Cliquer pour corriger")
            #si traitement date "dx": fond de la cellule en rouge à moitié transparent
            if d1 == self.dxj:
                if d1 != self.dxj:
                    self.table.item(1, r + 1).setBackground(QtGui.QColor(0, 255, 0, 127))
                else:
                    self.table.item(1, r + 1).setBackground(QtGui.QColor(255, 255, 0, 127))
            self.table.setItem(0 , r + 1 , QtWidgets.QTableWidgetItem(str(quantieme.days)))
            self.table.item(0, r + 1).setFont(font2)
            #self.table.item(r, 1).setFont(font2)
            #calcul du jour suivant pour traitement ligne suivante
            jourSuivant = jourSuivant + deltaJour
        #à la fin on remet les DD ou DF à la bonne valeur pour que la pagination réagisse toujours de la même façon en pagination avant et arrière 
        # en réaffichant la date de début en date de fin ou inversement.
        if sens == -1:
            self.dd = jourSuivant + timedelta(sens * -1)
        else:
            self.df = jourSuivant + timedelta(sens * -1)
        #chargement des données de la base (libellé activité, chrono jour dans la semaine (0 à 6), nb d'heures, nb de minutes, nb de secondes, durée totale sur la journée en secondes )
        self.extraction = self.DB_select_S(str(self.dd), str(self.df))
        #nb d'enreg extraits
        nb_lignes = len(self.extraction)

        #on a préalimenté la ligne 0 et la 1 donc on va partir à 2 (1 + 1)
        lig = 1
        #variable temporaire pour calculer le total d'une activité sur la semaine
        totalDureeActivite_sans_cumul = 0
        totalDureeActivite_avec_cumul = 0
        hierarchie = 0
        #pour calculer le total quotidien indépendamment de la nature des activités
        totalDASem = [0, 0, 0, 0, 0, 0, 0, 0]
        activite_precedente = ""
        #pour ajouter des item vides dans les cases sans donnée pour permettre la colorisation du fond
        dernier_jour_traite = 0
        #Boucle d'alimentation des activités de la semaine
        for i in range(nb_lignes):
            activite = self.extraction[i]
            #si on n'est pas en date du jour et qu'une activité n'est pas arrêté, affichage jour en rouge
            if activite[6] >= 1:
                #affichage_rouge[int(activite[1])] += 1
                self.table.item(1, int(activite[1]) + 1).setBackground(QtGui.QColor(255, 0, 0, 127))
            if activite_precedente != activite[0]:
                if activite_precedente != "":
                    while dernier_jour_traite < 7:
                        item = QtWidgets.QTableWidgetItem("")
                        item.setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
                        item.setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
                        dernier_jour_traite += 1
                        self.table.setItem(lig, dernier_jour_traite, item)
                    dernier_jour_traite = 0
                    #termine par calculer et afficher le total sur la ligne en cours (on a des secondes transformées en "h m s")
                    #un temps négatif n'a pas trop de sens mais on l'affiche telquel. les calculs ne fonctionnent pas en négatif donc on calcule en positif et on rebascule le résultat final en négatif à la fin
                    if totalDureeActivite_sans_cumul < 0:
                        sens2 = -1
                    else:
                        sens2 = 1
                    totalDureeActivite_sans_cumul = totalDureeActivite_sans_cumul * sens2
                    if totalDureeActivite_avec_cumul < 0:
                        sens3 = -1
                    else:
                        sens3 = 1
                    totalDureeActivite_avec_cumul = totalDureeActivite_avec_cumul * sens3
                    if self.semaine_jour.isChecked() == True:
                        item = QtWidgets.QTableWidgetItem(str(totalDureeActivite_avec_cumul) )
                        item.setTextAlignment(QtCore.Qt.AlignRight)
                        item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
                        item.setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
                        item.setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
                        self.table.setItem(lig, 0, item)
                    else:
                        tDurActHeur = int(totalDureeActivite_avec_cumul // 3600)
                        tDurActHeur = tDurActHeur * sens3
                        tDurActMin = int((totalDureeActivite_avec_cumul - (totalDureeActivite_avec_cumul % 60) ) /60 % 60)
                        tDurActMin = tDurActMin * sens3
                        tDurActSec = int(totalDureeActivite_avec_cumul % 60)
                        tDurActSec = tDurActSec * sens3
                        #inscrit dans la cellule total
                        #self.table.setItem(lig, 0, QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s").setTextAlignment(QtCore.Qt.AlignRight))
                        item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
                        item.setTextAlignment(QtCore.Qt.AlignRight)
                        item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
                        self.table.setItem(lig, 0, item)
                        #pour le calcul des totaux
                        tDurActHeur = int(totalDureeActivite_sans_cumul // 3600)
                        tDurActHeur = tDurActHeur * sens2
                        tDurActMin = int((totalDureeActivite_sans_cumul - (totalDureeActivite_sans_cumul % 60) ) /60 % 60)
                        tDurActMin = tDurActMin * sens2
                        tDurActSec = int(totalDureeActivite_sans_cumul % 60)
                        tDurActSec = tDurActSec * sens2
                    self.table.item(lig, 0).setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
                    self.table.item(lig, 0).setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
                    totalDureeActivite_sans_cumul = 0
                    totalDureeActivite_avec_cumul = 0
                #ligne suivante
                lig += 1
                self.table.setRowCount(lig + 1)
                activite_precedente = activite[0]
                hierarchie = activite[8]
                headerV.append(activite[0])
            #
            #self.table.setItem(lig, int(activite[1]) + 1, QtWidgets.QTableWidgetItem(str(activite[2]) + "h" + str(activite[3]) + "m" + str(activite[4]) + "s"))
            if int(activite[1]) > dernier_jour_traite:
                while dernier_jour_traite < int(activite[1]):
                    item = QtWidgets.QTableWidgetItem("")
                    item.setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
                    item.setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
                    dernier_jour_traite += 1
                    self.table.setItem(lig, dernier_jour_traite, item)
            item = QtWidgets.QTableWidgetItem(str(activite[2]) + "h" + str(activite[3]) + "m" + str(activite[4]) + "s")
            item.setTextAlignment(QtCore.Qt.AlignRight)
            item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
            item.setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
            item.setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
            self.table.setItem(lig, int(activite[1]) + 1, item)
            dernier_jour_traite += 1
            #somme des secondes par journée
            totalDASem[int(activite[1])] += activite[5]
            #somme des secondes de la semaine
            totalDureeActivite_sans_cumul += activite[5]
            #totalDureeActivite_avec_cumul += activite[5]
            #totalDureeActivite_avec_cumul += activite[7]
            totalDureeActivite_avec_cumul += activite[10]
        #fin

        if activite_precedente != "":
            while dernier_jour_traite < 7:
                item = QtWidgets.QTableWidgetItem("")
                item.setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
                item.setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
                dernier_jour_traite += 1
                self.table.setItem(lig, dernier_jour_traite, item)
            dernier_jour_traite = 0            
            #termine sur première ligne par calculer et afficher le total sur la ligne en cours (on a des secondes transformées en "h m s")
            if totalDureeActivite_sans_cumul < 0:
                sens2 = -1
            else:
                sens2 = 1
            totalDureeActivite_sans_cumul = totalDureeActivite_sans_cumul * sens2
            if totalDureeActivite_avec_cumul < 0:
                sens3 = -1
            else:
                sens3 = 1
            totalDureeActivite_avec_cumul = totalDureeActivite_avec_cumul * sens3
            if self.semaine_jour.isChecked() == True:
                item = QtWidgets.QTableWidgetItem(str(totalDureeActivite_avec_cumul))
                item.setTextAlignment(QtCore.Qt.AlignRight)
                item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
                self.table.setItem(lig, 0, item)
            else:
                tDurActHeur = int(totalDureeActivite_avec_cumul // 3600)
                tDurActHeur = tDurActHeur * sens3
                tDurActMin = int((totalDureeActivite_avec_cumul - (totalDureeActivite_avec_cumul % 60) ) /60 % 60)
                tDurActMin = tDurActMin * sens3
                tDurActSec = int(totalDureeActivite_avec_cumul % 60)
                tDurActSec = tDurActSec * sens3
                #self.table.setItem(lig, 0, QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s"))
                item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
                self.table.setItem(lig, 0, item)
                #pour le calcul des totaux
                tDurActHeur = int(totalDureeActivite_sans_cumul // 3600)
                tDurActHeur = tDurActHeur * sens2
                tDurActMin = int((totalDureeActivite_sans_cumul - (totalDureeActivite_sans_cumul % 60) ) /60 % 60)
                tDurActMin = tDurActMin * sens2
                tDurActSec = int(totalDureeActivite_sans_cumul % 60)
                tDurActSec = tDurActSec * sens2
            self.table.item(lig, 0).setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
            self.table.item(lig, 0).setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
        #total par jour sur la dernière ligne
        lig += 1
        self.table.setRowCount(lig + 1)
        #libellé dernière ligne
        headerV.append(_("Total"))
        #variable pour le calcul du total général toutes activités incluses
        totalDureeActivitesTot = 0
        totalDureeActivitesSecondes = 0
        #calcul du total par jour affiché sur la dernière ligne
        for i in range(7):
            totalDureeActivite_sans_cumul = totalDASem[i]
            totalDureeActivitesSecondes += totalDASem[i]
            if totalDureeActivite_sans_cumul < 0:
                sens2 = -1
            else:
                sens2 = 1
            #affichage des totaux en jour (alternatives: 0, 0.5 ou 1)
            if self.semaine_jour.isChecked() == True:
                if totalDureeActivite_sans_cumul > parametre_jour: #3600*5 = 18000 (5h)
                    totalDureeActivitesTot += 1
                    totalDureeActivite_sans_cumul = 1
                elif totalDureeActivite_sans_cumul > parametre_demi_jour:
                    totalDureeActivitesTot += 0.5
                    totalDureeActivite_sans_cumul = 0.5
                else:
                    totalDureeActivite_sans_cumul = 0
                item = QtWidgets.QTableWidgetItem(str(totalDureeActivite_sans_cumul) + "J")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                self.table.setItem(lig, i + 1, item)
            else:
                #affichage du temps en hms standard
                totalDureeActivitesTot += totalDureeActivite_sans_cumul
                totalDureeActivite_sans_cumul = totalDureeActivite_sans_cumul * sens2
                tDurActHeur = int(totalDureeActivite_sans_cumul // 3600)
                tDurActHeur = tDurActHeur * sens2
                tDurActMin = int((totalDureeActivite_sans_cumul - (totalDureeActivite_sans_cumul % 60) ) /60 % 60)
                tDurActMin = tDurActMin * sens2
                tDurActSec = int(totalDureeActivite_sans_cumul % 60)
                tDurActSec = tDurActSec * sens2
                self.table.setItem(lig, i + 1, QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s"))
                item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
                self.table.setItem(lig, i + 1, item)

        #total général
        if self.semaine_jour.isChecked() == True:
            item = QtWidgets.QTableWidgetItem(str(totalDureeActivitesTot) + "J")
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.table.setItem(lig, 0, item)
        else:
            totalDureeActivite_sans_cumul = totalDureeActivitesTot
            if totalDureeActivite_sans_cumul < 0:
                sens2 = -1
            else:
                sens2 = 1
            totalDureeActivite_sans_cumul = totalDureeActivite_sans_cumul * sens2
            tDurActHeur = int(totalDureeActivite_sans_cumul // 3600)
            tDurActHeur = tDurActHeur * sens2
            tDurActMin = int((totalDureeActivite_sans_cumul - (totalDureeActivite_sans_cumul % 60) ) /60 % 60)
            tDurActMin = tDurActMin * sens2
            tDurActSec = int(totalDureeActivite_sans_cumul % 60)
            tDurActSec = tDurActSec * sens2
            item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.table.setItem(lig, 0, item)

        #ajout date en entête de colonne
        headerH = [_('Total Semaine') ,]
        if sens == -1:
            headerH = headerH + list(reversed(self.liste_entetes))
        else:
            headerH = headerH + self.liste_entetes
        #headerH.append("Total Semaine")
        
        self.table.setVerticalHeaderLabels(headerV)
        self.table.setHorizontalHeaderLabels(headerH)        
        #self.table.horizontalHeaderItem(1).setStyleSheet("::section{Background-color:rgb(190,1,1)}")

        #On repasse sur les totaux par activitÃ© pour les afficher en jour
        if self.semaine_jour.isChecked() == True:
            #variable temporaire pour calculer le total d'une activitÃ© sur le mois
            totalDureeActivite_sans_cumul = 0
            #Boucle d'alimentation des activitÃ©s du mois (triÃ© sur activitÃ© puis jour)
            for i in range(2, lig):
                self.table.horizontalHeaderItem(item.column()).text()
                totalDureeActivite_sans_cumul = float(self.table.item(i, 0).text())
                totalDAJ = round(totalDureeActivitesTot * totalDureeActivite_sans_cumul / totalDureeActivitesSecondes, 2)
                item = QtWidgets.QTableWidgetItem(str(totalDAJ) + "J")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                #récupération du backcolor pour le réappliquer car le self.table.setItem qui suit va le réinitialiser
                bc = self.table.item(i, 0).background()
                fg = self.table.item(i, 0).foreground()
                p = self.table.item(i, 0).font()
                item.setBackground(bc)
                item.setForeground(fg)
                item.setFont(p)
                self.table.setItem(i, 0, item)
            #fin

    #chargement avec sens de chargement en paramètre
    def chargeTableauMois(self, sens, date_origine):
        global parametre_jour
        global parametre_demi_jour

        #chargement des paramètres de police de caractère des 3 hiérarchies
        polices = self.DBAA.charge_polices(self)

        self.date_du_jour()
        #QtWidgets.QMessageBox.about(self, "Debug", "dj:" + str(self.dj))
        #rechargement utile si le programme reste chargé plusieurs jours d'affilée
        self.dxj = date.today()
        #suivant le sens on part de la date min ou date max précédemment affichée
        if sens == -1:
            #permet d'ajouter ou supprimer des jours à une date
            deltaJour = timedelta(sens)            
            self.df = self.dd + deltaJour
            self.dd = self.df.replace(day=1)
            sens = 1
            deltaJour = timedelta(sens)
        elif sens == 0:
            if date_origine == None:
                d1 = date(self.dxj.year, self.dxj.month, self.dxj.day)
            else:
                d1 = date(date_origine.year, date_origine.month, date_origine.day)
            #1er jour du mois
            self.dd = d1.replace(day=1)
            #dernier jour du mois
            self.df = (self.dd + timedelta(days=31)).replace(day=1) + timedelta(days=-1)
            sens = 1
            deltaJour = timedelta(sens)
        else:
            #permet d'ajouter ou supprimer des jours à une date
            deltaJour = timedelta(sens)
            self.dd = self.df + deltaJour
            self.df = (self.dd + timedelta(days=31)).replace(day=1) + timedelta(days=-1)
        jourSuivant = self.dd
        
        #Mois
        if self.dd.month == 1:
            m = _("Janvier")
        elif self.dd.month == 2:
            m = _("Février")
        elif self.dd.month == 3:
            m = _("Mars")
        elif self.dd.month == 4:
            m = _("Avril")
        elif self.dd.month == 5:
            m = _("Mai")
        elif self.dd.month == 6:
            m = _("Juin")
        elif self.dd.month == 7:
            m = _("Juillet")
        elif self.dd.month == 8:
            m = _("Août")
        elif self.dd.month == 9:
            m = _("Septembre")
        elif self.dd.month == 10:
            m = _("Octobre")
        elif self.dd.month == 11:
            m = _("Novembre")
        elif self.dd.month == 12:
            m = _("Décembre")
        else:
            m = _("Au delà vers l'infini!^^")
        self.lsemaine.setText(m + " " + str(self.dd.year))

        #max de la boucle = nb de jour dans le mois
        nbjdm = int(self.df.day)
        #définition caractéristiques: position, dimensions, nombre de colonnes et lignes. 
        self.table.setColumnCount(nbjdm + 1)
        #préalimente à lignes du tableau, ça permet un init des données
        self.table.setRowCount(0)
        #préalimente 2 lignes du tableau avec quantième et correction
        self.table.setRowCount(2)
        headerV = [_('Quantième') , _('Correction')]
        # adding header to the table
        self.liste_entetes = []

        #boucle de chargement, à l'endroit ou à l'envers suivant le sens du chargement des données de date
        #on charge les jours, quantièmes et date et on gère un affichage spécifique les week end et "aujourd'hui"
        for i in range(0, nbjdm):
            if sens == -1:
                r = nbjdm - 1 - i
            else:
                r = i
            #calcul quantième
            d1 = date(jourSuivant.year, jourSuivant.month, jourSuivant.day)
            d0 = date(jourSuivant.year - 1, 12, 31)
            quantieme = d1 - d0
            #ajout date en entête de colonne
            self.liste_entetes.append(str(d1))
            #calcul numéro de semaine
            s = d1.isocalendar()
            #affichage en gras des jours du week-end
            font = QtGui.QFont()
            if d1.weekday() >= 5:
                font.setBold(True)
            else:
                font.setBold(False)
            #affichage du jour "dx" (quantième ou date du jour) en gras italique
            font2 = QtGui.QFont()
            if d1 == self.dxj:
                font2.setBold(True)
                font2.setItalic(True)
            # tous les 10 quantièmes affiché en gras pour plus de lisibilité
            elif int(str(quantieme.days)) % 10 == 0:
                font2.setBold(True)
                font2.setItalic(False)
            else:
                font2.setBold(False)
                font2.setItalic(False)

            #pour affichage du jour de la semaine 
            if d1.weekday() == 0:
                jourS = _(' Lundi')
            elif d1.weekday() == 1:
                jourS = _(' Mardi')
            elif d1.weekday() == 2:
                jourS = _(' Mercredi')
            elif d1.weekday() == 3:
                jourS = _(' Jeudi')
            elif d1.weekday() == 4:
                jourS = _(' Vendredi')
            elif d1.weekday() == 5:
                jourS = _(' Samedi')
            elif d1.weekday() == 6:
                jourS = _(' Dimanche')
            else:
                jourS = ' '

            #alimentation d'une ligne du tableau cellule par cellule avec application des Font
            self.table.setItem(1 , r + 1 , QtWidgets.QTableWidgetItem(jourS))
            self.table.item(1, r + 1).setFont(font)
            #si traitement date "dx": fond de la cellule en rouge à moitié transparent
            if d1 == self.dxj:
                if d1 != self.dxj:
                    self.table.item(1, r + 1).setBackground(QtGui.QColor(0, 255, 0, 127))
                else:
                    self.table.item(1, r + 1).setBackground(QtGui.QColor(255, 255, 0, 127))
            self.table.setItem(0 , r + 1 , QtWidgets.QTableWidgetItem(str(quantieme.days)))
            self.table.item(0, r + 1).setFont(font2)
            #calcul du jour suivant pour traitement ligne suivante
            jourSuivant = jourSuivant + deltaJour
        #à la fin on remet les DD ou DF à la bonne valeur pour que la pagination réagisse toujours de la même façon en pagination avant et arrière 
        # en réaffichant la date de début en date de fin ou inversement.
        if sens == -1:
            self.dd = jourSuivant + timedelta(sens * -1)
        else:
            self.df = jourSuivant + timedelta(sens * -1)

        #chargement des données de la base 
        #(libellé activité, chrono jour dans le mois (0 à 30), nb d'heures, nb de minutes, nb de secondes, durée totale sur la journée en secondes )
        self.extraction = self.DB_select_S(str(self.dd), str(self.df))
        #nb d'enreg extraits
        nb_lignes = len(self.extraction)

        #on a préalimenté la ligne 0 et la 1 donc on va partir à 2 (1 + 1)
        lig = 1
        #variable temporaire pour calculer le total d'une activité sur le mois
        totalDureeActivite_sans_cumul = 0
        totalDureeActivite_avec_cumul = 0
        hierarchie = 0
        #pour calculer le total quotidien indépendamment de la nature des activités
        totalDAMois = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        activite_precedente = ""
        dernier_jour_traite = 0
        #Boucle d'alimentation des activités du mois (trié sur activité puis jour)
        for i in range(nb_lignes):
            activite = self.extraction[i]
            #si on n'est pas en date du jour et qu'une activité n'est pas arrêté, affichage jour en rouge
            if activite[6] >= 1:
                #affichage_rouge[int(activite[1])] += 1
                self.table.item(1, int(activite[1]) + 1).setBackground(QtGui.QColor(255, 0, 0, 127))
            #à rupture d'activité
            if activite_precedente != activite[0]:
                #on est sur le traitement de la 2ème ou plus activité
                if activite_precedente != "":
                    while dernier_jour_traite < nbjdm:
                        item = QtWidgets.QTableWidgetItem("")
                        item.setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
                        item.setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
                        dernier_jour_traite += 1
                        self.table.setItem(lig, dernier_jour_traite, item)
                    dernier_jour_traite = 0
                    #termine par calculer et afficher le total sur la ligne en cours (on a des secondes transformées en "h m s")
                    #un temps négatif n'a pas trop de sens mais on l'affiche telquel. les calculs ne fonctionnent pas en négatif donc on calcule en positif et on rebascule le résultat final en négatif à la fin
                    if totalDureeActivite_sans_cumul < 0:
                        sens2 = -1
                    else:
                        sens2 = 1
                    if totalDureeActivite_avec_cumul < 0:
                        sens3 = -1
                    else:
                        sens3 = 1
                    totalDureeActivite_sans_cumul = totalDureeActivite_sans_cumul * sens2
                    if self.semaine_jour.isChecked() == True:
                        item = QtWidgets.QTableWidgetItem(str(totalDureeActivite_avec_cumul) )
                        item.setTextAlignment(QtCore.Qt.AlignRight)
                        item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
                        self.table.setItem(lig, 0, item)
                    else:
                        tDurActHeur = int(totalDureeActivite_avec_cumul // 3600)
                        tDurActHeur = tDurActHeur * sens3
                        tDurActMin = int((totalDureeActivite_avec_cumul - (totalDureeActivite_avec_cumul % 60) ) /60 % 60)
                        tDurActMin = tDurActMin * sens3
                        tDurActSec = int(totalDureeActivite_avec_cumul % 60)
                        tDurActSec = tDurActSec * sens3
                        #inscrit dans la cellule total
                        #self.table.setItem(lig, 0, QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s"))
                        item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
                        item.setTextAlignment(QtCore.Qt.AlignRight)
                        item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
                        self.table.setItem(lig, 0, item)
                        #pour le calcul des totaux
                        tDurActHeur = int(totalDureeActivite_sans_cumul // 3600)
                        tDurActHeur = tDurActHeur * sens2
                        tDurActMin = int((totalDureeActivite_sans_cumul - (totalDureeActivite_sans_cumul % 60) ) /60 % 60)
                        tDurActMin = tDurActMin * sens2
                        tDurActSec = int(totalDureeActivite_sans_cumul % 60)
                        tDurActSec = tDurActSec * sens2
                    self.table.item(lig, 0).setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
                    self.table.item(lig, 0).setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
                    totalDureeActivite_sans_cumul = 0
                    totalDureeActivite_avec_cumul = 0
                #ligne suivante
                lig += 1
                self.table.setRowCount(lig + 1)
                activite_precedente = activite[0]
                hierarchie = activite[8]
                headerV.append(activite[0])
            #
            #self.table.setItem(lig, int(activite[1]) + 1, QtWidgets.QTableWidgetItem(str(activite[2]) + "h" + str(activite[3]) + "m" + str(activite[4]) + "s"))
            if int(activite[1]) > dernier_jour_traite:
                while dernier_jour_traite < int(activite[1]):
                    item = QtWidgets.QTableWidgetItem("")
                    item.setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
                    item.setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
                    dernier_jour_traite += 1
                    self.table.setItem(lig, dernier_jour_traite, item)
            item = QtWidgets.QTableWidgetItem(str(activite[2]) + "h" + str(activite[3]) + "m" + str(activite[4]) + "s")
            item.setTextAlignment(QtCore.Qt.AlignRight)
            item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
            item.setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
            item.setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
            self.table.setItem(lig, int(activite[1]) + 1, item)
            dernier_jour_traite += 1
            #somme des secondes par journée
            totalDAMois[int(activite[1])] += activite[5]
            #somme des secondes de la semaine
            totalDureeActivite_sans_cumul += activite[5]
            #totalDureeActivite_avec_cumul += activite[5]
            #totalDureeActivite_avec_cumul += activite[7]
            totalDureeActivite_avec_cumul += activite[10]
        #fin

        if activite_precedente != "":
            while dernier_jour_traite < nbjdm:
                item = QtWidgets.QTableWidgetItem("")
                item.setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
                item.setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
                dernier_jour_traite += 1
                self.table.setItem(lig, dernier_jour_traite, item)
            dernier_jour_traite = 0
            #termine sur première ligne par calculer et afficher le total sur la ligne en cours (on a des secondes transformées en "h m s")
            if totalDureeActivite_sans_cumul < 0:
                sens2 = -1
            else:
                sens2 = 1
            totalDureeActivite_sans_cumul = totalDureeActivite_sans_cumul * sens2
            if totalDureeActivite_avec_cumul < 0:
                sens3 = -1
            else:
                sens3 = 1
            totalDureeActivite_avec_cumul = totalDureeActivite_avec_cumul * sens3
            if self.semaine_jour.isChecked() == True:
                item = QtWidgets.QTableWidgetItem(str(totalDureeActivite_avec_cumul))
                item.setTextAlignment(QtCore.Qt.AlignRight)
                item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
                self.table.setItem(lig, 0, item)
            else:
                tDurActHeur = int(totalDureeActivite_avec_cumul // 3600)
                tDurActHeur = tDurActHeur * sens3
                tDurActMin = int((totalDureeActivite_avec_cumul - (totalDureeActivite_avec_cumul % 60) ) /60 % 60)
                tDurActMin = tDurActMin * sens3
                tDurActSec = int(totalDureeActivite_avec_cumul % 60)
                tDurActSec = tDurActSec * sens3
                #self.table.setItem(lig, 0, QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s"))
                item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
                self.table.setItem(lig, 0, item)
                #pour le calcul des totaux
                tDurActHeur = int(totalDureeActivite_sans_cumul // 3600)
                tDurActHeur = tDurActHeur * sens2
                tDurActMin = int((totalDureeActivite_sans_cumul - (totalDureeActivite_sans_cumul % 60) ) /60 % 60)
                tDurActMin = tDurActMin * sens2
                tDurActSec = int(totalDureeActivite_sans_cumul % 60)
                tDurActSec = tDurActSec * sens2
            #if hierarchie == 0:
            #    self.table.item(lig, 0).setBackground(QtGui.QColor(112, 114, 110, 127))
            #if hierarchie == 1:
            #    self.table.item(lig, 0).setBackground(QtGui.QColor(220, 220, 220, 127))
            self.table.item(lig, 0).setBackground(QtGui.QColor(int(polices[hierarchie][4][0]), int(polices[hierarchie][4][1]), int(polices[hierarchie][4][2]), int(polices[hierarchie][4][3])))
            self.table.item(lig, 0).setForeground(QtGui.QColor(int(polices[hierarchie][5][0]), int(polices[hierarchie][5][1]), int(polices[hierarchie][5][2]), int(polices[hierarchie][5][3])))
        #total par jour sur la dernière ligne
        lig += 1
        self.table.setRowCount(lig + 1)
        #libellé dernière ligne
        headerV.append(_("Total"))
        #variable pour le calcul du total général toutes activités incluses
        totalDureeActivitesTot = 0
        totalDureeActivitesSecondes = 0
        #calcul du total par jour affiché sur la dernière ligne
        for i in range(nbjdm):
            totalDureeActivite_sans_cumul = totalDAMois[i]
            totalDureeActivitesSecondes += totalDAMois[i]
            if totalDureeActivite_sans_cumul < 0:
                sens2 = -1
            else:
                sens2 = 1
            #affichage des totaux en jour (alternatives: 0, 0.5 ou 1)
            if self.semaine_jour.isChecked() == True:
                if totalDureeActivite_sans_cumul > parametre_jour: #3600*5 = 18000 (5h)
                    totalDureeActivitesTot += 1
                    totalDureeActivite_sans_cumul = 1
                elif totalDureeActivite_sans_cumul > parametre_demi_jour:
                    totalDureeActivitesTot += 0.5
                    totalDureeActivite_sans_cumul = 0.5
                else:
                    totalDureeActivite_sans_cumul = 0
                item = QtWidgets.QTableWidgetItem(str(totalDureeActivite_sans_cumul) + "J")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                self.table.setItem(lig, i + 1, item)
            else:
                #affichage du temps en hms standard
                totalDureeActivitesTot += totalDureeActivite_sans_cumul
                totalDureeActivite_sans_cumul = totalDureeActivite_sans_cumul * sens2
                tDurActHeur = int(totalDureeActivite_sans_cumul // 3600)
                tDurActHeur = tDurActHeur * sens2
                tDurActMin = int((totalDureeActivite_sans_cumul - (totalDureeActivite_sans_cumul % 60) ) /60 % 60)
                tDurActMin = tDurActMin * sens2
                tDurActSec = int(totalDureeActivite_sans_cumul % 60)
                tDurActSec = tDurActSec * sens2
                #self.table.setItem(lig, i + 1, QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s"))
                item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                item.setFont(QtGui.QFont(polices[hierarchie][0], int(polices[hierarchie][1]), polices[hierarchie][2], polices[hierarchie][3] ))
                self.table.setItem(lig, i + 1, item)
        #total général
        if self.semaine_jour.isChecked() == True:
            item = QtWidgets.QTableWidgetItem(str(totalDureeActivitesTot) + "J")
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.table.setItem(lig, 0, item)
        else:
            totalDureeActivite_sans_cumul = totalDureeActivitesTot
            if totalDureeActivite_sans_cumul < 0:
                sens2 = -1
            else:
                sens2 = 1
            totalDureeActivite_sans_cumul = totalDureeActivite_sans_cumul * sens2
            tDurActHeur = int(totalDureeActivite_sans_cumul // 3600)
            tDurActHeur = tDurActHeur * sens2
            tDurActMin = int((totalDureeActivite_sans_cumul - (totalDureeActivite_sans_cumul % 60) ) /60 % 60)
            tDurActMin = tDurActMin * sens2
            tDurActSec = int(totalDureeActivite_sans_cumul % 60)
            tDurActSec = tDurActSec * sens2
            item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.table.setItem(lig, 0, item)

        #ajout date en entête de colonne
        headerH = [_('Total Mois') ,]
        if sens == -1:
            headerH = headerH + list(reversed(self.liste_entetes))
        else:
            headerH = headerH + self.liste_entetes
        #headerH.append("Total Semaine")
        
        self.table.setVerticalHeaderLabels(headerV)
        self.table.setHorizontalHeaderLabels(headerH)        


        #On repasse sur les totaux par activité pour les afficher en jour
        if self.semaine_jour.isChecked() == True:
            #variable temporaire pour calculer le total d'une activité sur le mois
            totalDureeActivite_sans_cumul = 0
            #Boucle d'alimentation des activités du mois (trié sur activité puis jour)
            for i in range(2, lig):
                self.table.horizontalHeaderItem(item.column()).text()
                totalDureeActivite_sans_cumul = float(self.table.item(i, 0).text())
                totalDAJ = round(totalDureeActivitesTot * totalDureeActivite_sans_cumul / totalDureeActivitesSecondes, 2)
                item = QtWidgets.QTableWidgetItem(str(totalDAJ) + "J")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                #récupération du backcolor pour le réappliquer car le self.table.setItem qui suit va le réinitialiser
                bc = self.table.item(i, 0).background()
                fg = self.table.item(i, 0).foreground()
                p = self.table.item(i, 0).font()
                item.setBackground(bc)
                item.setForeground(fg)
                item.setFont(p)
                self.table.setItem(i, 0, item)
            #fin

    #chargement avec sens de chargement en paramètre
    def chargeTableauAnnee(self, sens, date_origine):
        self.date_du_jour()
        #QtWidgets.QMessageBox.about(self, "Debug", "dj:" + str(self.dj))
        #rechargement utile si le programme reste chargé plusieurs jours d'affilée
        self.dxj = date.today()
        #suivant le sens on part de la date min ou date max précédemment affichée
        if sens == -1:
            #permet d'ajouter ou supprimer des jours à une date
            self.df = date(self.dd.year - 1, 12, 31)
            self.dd = self.df.replace(day=1).replace(month=1)
            sens = 1
        elif sens == 0:
            if date_origine == None:
                d1 = date(self.dxj.year, self.dxj.month, self.dxj.day)
            else:
                d1 = date(date_origine.year, date_origine.month, date_origine.day)
            #1er jour de l'année
            self.dd = d1.replace(day=1).replace(month=1)
            #dernier jour de l'année
            self.df = self.dd.replace(month=12).replace(day=31)
            sens = 1
        else:
            #permet d'ajouter ou supprimer des jours à une date
            self.dd = date(self.dd.year + 1, 1, 1)
            self.df = date(self.dd.year + 1, 12, 31)
        #jourSuivant = self.dd
        
        self.lsemaine.setText(str(self.dd.year))

        #max de la boucle = nb de mois dans l'année
        #définition caractéristiques: position, dimensions, nombre de colonnes et lignes. 
        self.table.setColumnCount(13)
        #préalimente à lignes du tableau, ça permet un init des données
        self.table.setRowCount(0)
        #headerV = [_('Quantième') , _('Correction')]
        headerV = []
        # adding header to the table
        self.liste_entetes = []

        #boucle de chargement, à l'endroit ou à l'envers suivant le sens du chargement des données de date
        #on charge les jours, quantièmes et date et on gère un affichage spécifique les week end et "aujourd'hui"
        mois = [_(" Janvier"),_(" Février"),_(" Mars"),_(" Avril"),_(" Mai"),_(" Juin"),_(" Juillet"),_(" Août"),_(" Septembre"),_(" Octobre"),_(" Novembre"),_(" Décembre")]
        for i in range(0, 12):
            #ajout mois en entête de colonne
            self.liste_entetes.append(mois[i])

        #chargement des données de la base 
        #(libellé activité, chrono mois dans l'année (0 à 11), nb d'heures, nb de minutes, nb de secondes, durée totale sur la journée en secondes )
        self.extraction = self.DB_select_Annee(str(self.dd.year))
        #nb d'enreg extraits
        nb_lignes = len(self.extraction)
        if self.semaine_jour.isChecked() == True:
            self.extraction_jour = self.DB_select_j_m_Annee(str(self.dd.year))
            nb_lignes_jour = len(self.extraction_jour)

        #on démarre à la ligne 0  (-1 + 1 = 0)
        lig = -1
        #variable temporaire pour calculer le total d'une activité sur le mois
        totalDureeActivite = 0
        #pour calculer le total mensuel indépendamment de la nature des activités
        totalDAMois = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        activite_precedente = ""
        #Boucle d'alimentation des activités du mois (trié sur activité puis jour)
        for i in range(nb_lignes):
            activite = self.extraction[i]
            #si on n'est pas en date du jour et qu'une activité n'est pas arrêté, affichage jour en rouge
            #if activite[6] >= 1:
            #    #affichage_rouge[int(activite[1])] += 1
            #    self.table.item(1, int(activite[1]) + 1).setBackground(QtGui.QColor(255, 0, 0, 127))
            #à rupture d'activité
            if activite_precedente != activite[0]:
                #on est sur le traitement de la 2ème ou plus activité
                if activite_precedente != "":
                    #termine par calculer et afficher le total sur la ligne en cours (on a des secondes transformées en "h m s")
                    #un temps négatif n'a pas trop de sens mais on l'affiche telquel. les calculs ne fonctionnent pas en négatif donc on calcule en positif et on rebascule le résultat final en négatif à la fin
                    if totalDureeActivite < 0:
                        sens2 = -1
                    else:
                        sens2 = 1
                    totalDureeActivite = totalDureeActivite * sens2
                    if self.semaine_jour.isChecked() == True:
                        item = QtWidgets.QTableWidgetItem(str(totalDureeActivite) )
                        item.setTextAlignment(QtCore.Qt.AlignRight)
                        self.table.setItem(lig, 0, item)
                    else:
                        tDurActHeur = int(totalDureeActivite // 3600)
                        tDurActHeur = tDurActHeur * sens2
                        tDurActMin = int((totalDureeActivite - (totalDureeActivite % 60) ) /60 % 60)
                        tDurActMin = tDurActMin * sens2
                        tDurActSec = int(totalDureeActivite % 60)
                        tDurActSec = tDurActSec * sens2
                        item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
                        item.setTextAlignment(QtCore.Qt.AlignRight)
                        self.table.setItem(lig, 0, item)
                    totalDureeActivite = 0
                #ligne suivante
                lig += 1
                self.table.setRowCount(lig + 1)
                activite_precedente = activite[0]
                headerV.append(activite[0])
            #
            item = QtWidgets.QTableWidgetItem(str(activite[2]) + "h" + str(activite[3]) + "m" + str(activite[4]) + "s")
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.table.setItem(lig, int(activite[1]) + 1, item)
            #somme des secondes par mois
            totalDAMois[int(activite[1])] += activite[5]
            #somme des secondes de l'année
            totalDureeActivite += activite[5]
        #fin

        if activite_precedente != "":
            #termine sur première ligne par calculer et afficher le total sur la ligne en cours (on a des secondes transformées en "h m s")
            if totalDureeActivite < 0:
                sens2 = -1
            else:
                sens2 = 1
            totalDureeActivite = totalDureeActivite * sens2
            if self.semaine_jour.isChecked() == True:
                item = QtWidgets.QTableWidgetItem(str(totalDureeActivite))
                item.setTextAlignment(QtCore.Qt.AlignRight)
                self.table.setItem(lig, 0, item)
            else:
                tDurActHeur = int(totalDureeActivite // 3600)
                tDurActHeur = tDurActHeur * sens2
                tDurActMin = int((totalDureeActivite - (totalDureeActivite % 60) ) /60 % 60)
                tDurActMin = tDurActMin * sens2
                tDurActSec = int(totalDureeActivite % 60)
                tDurActSec = tDurActSec * sens2
                item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                self.table.setItem(lig, 0, item)

        #total par mois sur la dernière ligne
        lig += 1
        self.table.setRowCount(lig + 1)
        #libellé dernière ligne
        headerV.append(_("Total"))
        #variable pour le calcul du total général toutes activités incluses
        totalDureeActivitesTot = 0
        totalDureeActivitesSecondes = 0
        #calcul du total par jour affiché sur la dernière ligne
        if self.semaine_jour.isChecked() == True:
            for i in range (nb_lignes_jour):
                self.extraction_jour[i][1]
                item = QtWidgets.QTableWidgetItem(str(self.extraction_jour[i][1]) + "J")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                self.table.setItem(lig, self.extraction_jour[i][0] + 1, item)
                totalDureeActivitesTot += self.extraction_jour[i][1]
        for i in range(12):
            totalDureeActivite = totalDAMois[i]
            totalDureeActivitesSecondes += totalDAMois[i]
            if self.semaine_heure.isChecked() == True:
                if totalDureeActivite < 0:
                    sens2 = -1
                else:
                    sens2 = 1
                #affichage du temps en hms standard
                totalDureeActivitesTot += totalDureeActivite
                totalDureeActivite = totalDureeActivite * sens2
                tDurActHeur = int(totalDureeActivite // 3600)
                tDurActHeur = tDurActHeur * sens2
                tDurActMin = int((totalDureeActivite - (totalDureeActivite % 60) ) /60 % 60)
                tDurActMin = tDurActMin * sens2
                tDurActSec = int(totalDureeActivite % 60)
                tDurActSec = tDurActSec * sens2
                #self.table.setItem(lig, i + 1, QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s"))
                item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                self.table.setItem(lig, i + 1, item)
        #total général
        if self.semaine_jour.isChecked() == True:
            item = QtWidgets.QTableWidgetItem(str(totalDureeActivitesTot) + "J")
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.table.setItem(lig, 0, item)
        else:
            totalDureeActivite = totalDureeActivitesTot
            if totalDureeActivite < 0:
                sens2 = -1
            else:
                sens2 = 1
            totalDureeActivite = totalDureeActivite * sens2
            tDurActHeur = int(totalDureeActivite // 3600)
            tDurActHeur = tDurActHeur * sens2
            tDurActMin = int((totalDureeActivite - (totalDureeActivite % 60) ) /60 % 60)
            tDurActMin = tDurActMin * sens2
            tDurActSec = int(totalDureeActivite % 60)
            tDurActSec = tDurActSec * sens2
            item = QtWidgets.QTableWidgetItem(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.table.setItem(lig, 0, item)

        #ajout date en entête de colonne
        headerH = [_('Total Année') ,]
        if sens == -1:
            headerH = headerH + list(reversed(self.liste_entetes))
        else:
            headerH = headerH + self.liste_entetes
        #headerH.append("Total Semaine")
        
        self.table.setVerticalHeaderLabels(headerV)
        self.table.setHorizontalHeaderLabels(headerH)        


        #On repasse sur les totaux par activité pour les afficher en jour
        if self.semaine_jour.isChecked() == True:
            #variable temporaire pour calculer le total d'une activité sur le mois
            totalDureeActivite = 0
            #Boucle d'alimentation des activités du mois (trié sur activité puis jour)
            for i in range(0, lig):
                self.table.horizontalHeaderItem(item.column()).text()
                totalDureeActivite = float(self.table.item(i, 0).text())
                totalDAJ = round(totalDureeActivitesTot * totalDureeActivite / totalDureeActivitesSecondes, 2)
                item = QtWidgets.QTableWidgetItem(str(totalDAJ) + "J")
                item.setTextAlignment(QtCore.Qt.AlignRight)
                self.table.setItem(i, 0, item)
            #fin


    def transform_date_SSAAMMJJ(self, date_str):
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            transformed_date = date_obj.strftime("%d-%m-%Y")
            return datetime.strptime(transformed_date, "%d-%m-%Y")
        except ValueError:
            #return "Format de date incorrect. Utilisez le format YYYYMMDD."
            return None
            

    #validation de la saisie du quantième
    #il peut être saisi au format QQQ (année en cours implicitement sélectionnée) ou AAAA.QQQ pour spécifier une autre année
    # La date peut être saisie avec juste les derniers chiffres, on considère alors être en deux mille quelque chose
    # le quantième peut dépasser 365 ou 366, on passe sur une autre année et l'affichage n'aura pas trop de sens mais ça fonctionne.
    # on peut également saisir des dates au format SSAAMMJJ ou JJ.MM.SSAA avec comme séparateur 
    # l'un de ces caractères: espace .:;,-_/
    def ok_action(self):
        #sélection du contenu saisi pour permettre une nouvelle saisie plus rapidement
        self.lineEdit.selectAll()
        saisie = self.lineEdit.text()
        #si c'est vide on passe à la date du jour
        if saisie == "":
            if self.semaine.isChecked():
                self.chargeTableauSemaine(0, None)
            elif self.mois.isChecked():
                self.chargeTableauMois(0, None)
            elif self.annee.isChecked():
                self.chargeTableauAnnee(0, None)
        #vérification que c'est numérique (format de saisie QQQ)
        elif saisie.isdigit():
            if int(saisie) > 1000 and int(saisie) < 10000000 or int(saisie) > 30000000:
                QtWidgets.QMessageBox.about(self, _("Saisie incorrecte"), _("saisir le quantième avec ou sans l'année au format QQQ ou AAAA.QQQ ou une date au format SSAAMMJJ"))
            elif int(saisie) > 10000000:
                self.dd = self.transform_date_SSAAMMJJ(saisie)
                if self.dd is None:
                    QtWidgets.QMessageBox.about(self, _("Saisie incorrecte"), _("saisir une date existante au format SSAAMMJJ"))
                else:
                    if self.semaine.isChecked():
                        self.chargeTableauSemaine(0, self.dd)
                    elif self.mois.isChecked():
                        self.chargeTableauMois(0, self.dd)        
                    elif self.annee.isChecked():
                        self.chargeTableauAnnee(0, self.dd)        
            else:
                quantieme = timedelta(int(saisie))
                self.dd = date(date.today().year - 1, 12, 31)
                self.dd = self.dd + quantieme
                #self.dx = date(self.dd.year, self.dd.month, self.dd.day)
                if self.semaine.isChecked():
                    self.chargeTableauSemaine(0, self.dd)
                elif self.mois.isChecked():
                    self.chargeTableauMois(0, self.dd)        
                elif self.annee.isChecked():
                    self.chargeTableauAnnee(0, self.dd)        
        else:
        #vérification de saisie par le format A.Q
            #tabSaisie = self.lineEdit.text().split(".")
            tabSaisie = re.split("[. :;,\-/_]+", self.lineEdit.text())
            #on ne doit avoir que 2 arguments, la date puis le quantième, tous deux numériques. 
            if len(tabSaisie) == 2:
                if tabSaisie[0].isdigit():
                    if tabSaisie[1].isdigit():
                        if int(tabSaisie[0]) <= 0:
                            tabSaisie[0] = "2000"
                        elif int(tabSaisie[0]) < 10:
                            tabSaisie[0] = "200" + tabSaisie[0]
                        elif int(tabSaisie[0]) < 100:
                            tabSaisie[0] = "20" + tabSaisie[0]
                        elif int(tabSaisie[0]) < 1000:
                            tabSaisie[0] = "2" + tabSaisie[0]
                        quantieme = timedelta(int(tabSaisie[1]))
                        self.dd = date(int(tabSaisie[0]) - 1, 12, 31)
                        self.dd = self.dd + quantieme
                        #self.dx = date(self.dd.year, self.dd.month, self.dd.day)
                        if self.semaine.isChecked():
                            self.chargeTableauSemaine(0, self.dd)
                        elif self.mois.isChecked():
                            self.chargeTableauMois(0, self.dd)  
                        elif self.annee.isChecked():
                            self.chargeTableauAnnee(0, self.dd)  
                    else:                        
                        QtWidgets.QMessageBox.about(self, _("Saisie incorrecte"), _("saisir le quantième avec ou sans l'année au format QQQ ou AAAA.QQQ"))
                else:
                    QtWidgets.QMessageBox.about(self, _("Saisie incorrecte"), _("saisir le quantième avec ou sans l'année au format QQQ ou AAAA.QQQ"))
            elif len(tabSaisie) == 3:
                #vérification de saisie au format jj/mm/ssaa
                try:
                    self.dd = date(int(tabSaisie[2]), int(tabSaisie[1]), int(tabSaisie[0]))
                except:
                    QtWidgets.QMessageBox.about(self, _("Saisie incorrecte"), _("Ceci n'est pas une date existante. A saisir au format JJ-MM-SSAA"))
                if self.semaine.isChecked():
                    self.chargeTableauSemaine(0, self.dd)
                elif self.mois.isChecked():
                    self.chargeTableauMois(0, self.dd)  
                elif self.annee.isChecked():
                    self.chargeTableauAnnee(0, self.dd)  
            else:
                QtWidgets.QMessageBox.about(self, _("Saisie incorrecte"), _("saisir le quantième avec ou sans l'année au format QQQ ou AAAA.QQQ"))

    def keyPressEvent(self, event):
        #if event.key() == QtCore.Qt.Key_Enter:
        if event.key() in [QtCore.Qt.Key_Escape]:
            self.quitter_action()

    def quitter_action(self):
        self.hide()

    #accès base de donnée
    def DB_connexion(self):
            try:
                #Vérifie existence de la table
                TAppr = self.cur.execute("""SELECT tbl_name FROM sqlite_master WHERE type='table' AND tbl_name='activite';""").fetchall()
                if TAppr == []:
                    #print('table a creer')
                    self.DB_create()

            except sqlite3.Error as e:
                if self.con:
                    self.con.rollback()

                #print(f"Error {e.args[0]}")
                QtWidgets.QMessageBox.about(self, "ERREUR", f"Error {e.args[0]}")
                sys.exit(1)
    #création si inexistante
    def DB_create(self):
        self.cur.execute("""CREATE TABLE activite (libelle  TEXT NOT NULL, debut TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, fin TIMESTAMP,  id INTEGER, PRIMARY KEY( id  AUTOINCREMENT));""")
        self.cur.execute("""CREATE TABLE correction (libelle TEXT NOT NULL, jour DATE, correction INTEGER, duree INTEGER, tevt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);""")
        self.cur.execute("""CREATE TABLE parametres (type TEXT,stype TEXT,valeur_a TEXT,valeur_n REAL,valeur_int INTEGER,visible INTEGER);""")
        self.cur.execute("""CREATE TABLE taches ( libelle TEXT, parent TEXT, niveau INTEGER, ordre_calendrier INTEGER, ordre_menu INTEGER, affichage_menu INTEGER);""")

    #sélection d'une journée
    def DB_select_S(self, jour_debut, jour_fin):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        #curs out: libelle, jou, h, m, s, st, arrete, stcumul
        self.cur.execute("""with RECURSIVE act as (
                        select b.libelle
                            , cast(julianday(jour) - julianday( ? ) as int) as jou
                            , secondes as st
                            , arrete
                            , 0 as stcumul
                            , ifnull(parent, '') as parent
                            , ifnull(ordre_calendrier, 9999) as ordre_calendrier
                            , ifnull(niveau, 0) niveau
                        from (select libelle, jour, sum(secondes) as secondes , sum(arrete) as arrete
                            from (select libelle, substr(debut , 1, 10) as jour
                                        , sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes 
                                        , sum(case when fin is NULL and substr(debut , 1, 10) <> date() then 1 else 0 end) as arrete
                                    from activite
                                    group by libelle, substr(debut , 1, 10) 
                                    union all 
                                    select libelle, jour, sum(correction * duree) as secondes , 0 as arrete
                                    from correction 
                                    group by libelle , jour
                                ) as a  
                            group by libelle, jour
                            ) as b 
                        left join taches
                        on taches.libelle = b.libelle
                        where jour between ? and ?
                        )
                        , rec as(
                        select libelle, jou, st, arrete, stcumul, parent, ordre_calendrier, niveau
                        from ACT
                        union all
                        select taches.libelle, rec.jou, 0 as st, 0 as arrete, rec.st + rec.stcumul as stcumul, taches.parent, taches.ordre_calendrier, taches.niveau
                        from rec 
                        inner join taches
                        on taches.libelle = rec.parent
                        where rec.parent > ""
                        )
                        , cumul as (
                        select libelle, jou, sum(st) as st, sum(arrete) as arrete, sum(stcumul) as stcumul, parent, ordre_calendrier, niveau 
                        from rec
                        group by libelle, jou, parent, ordre_calendrier, niveau
                        )
                        select libelle
                            , jou
                            , cast((st + stcumul) / 3600 as int) as h
                            , cast((st + stcumul - ((st + stcumul) % 60) ) /60 % 60 as int) as m
                            , cast((st + stcumul) % 60 as int) as s 
                            , case when exists(select 1 from rec where rec.libelle = cumul.libelle and rec.stcumul <> 0) then 0 else st end as st
                            , arrete
                            , stcumul
                            , niveau
                            , ordre_calendrier
                            , stcumul + st as stt
                        from cumul
                        union ALL
                        select libelle || " " as libelle
                            , jou
                            , cast((st) / 3600 as int) as h
                            , cast((st - ((st) % 60) ) /60 % 60 as int) as m
                            , cast((st) % 60 as int) as s 
                            , st, arrete, 0 as stcumul
                            , niveau + 1 as niveau
                            , ordre_calendrier
                            , st as stt
                        from cumul
                        where st <> 0
                          and exists(select 1 from rec where rec.libelle = cumul.libelle and rec.stcumul <> 0)
                        order by ordre_calendrier, libelle, niveau, jou"""
                        , (jour_debut, jour_debut, jour_fin ))
        return (self.cur.fetchall())

    #sélection d'une année
    def DB_select_Annee(self, annee):
        #select libelle, mois (0 à 11), cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select libelle, cast(mois as int) - 1
                                 , cast(secondes / 3600 as int) as h
                                 , cast((secondes - (secondes % 60) ) /60 % 60 as int) as m
                                 , cast(secondes % 60 as int) as s 
                                 , secondes as st
                                 , arrete
                            from (select libelle, mois, sum(secondes) as secondes , sum(arrete) as arrete
                                  from (select libelle, substr(debut , 6, 2) as mois
                                             , sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes 
                                             , sum(case when fin is NULL and substr(debut , 1, 10) <> date() then 1 else 0 end) as arrete
                                        from activite 
                                        where substr(debut , 1, 4) = ?
                                        group by libelle, substr(debut , 1, 7)
                                        union all 
                                        select libelle, substr(jour, 6, 2) as mois, sum(correction * duree) as secondes , 0 as arrete
                                        from correction 
                                        where substr(jour, 1, 4) = ?
                                        group by libelle , substr(jour, 6, 2)
                                       ) as a  
                                  group by libelle, mois
                            ) as b 
                            order by libelle, mois""", (annee, annee))
        return (self.cur.fetchall())

    #sélection du nombre de jours par mois sur une année
    def DB_select_j_m_Annee(self, annee):
        #select mois (0 à 11), cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select cast(mois as int) - 1
                                 , j
                            from (select mois, sum(j) as j
                                  from (select mois, jour
                                        , case when sum(secondes) <= (select valeur_int from parametres where type = 'calcul_jour' and stype = 'demi') then 0
                                               when sum(secondes) > (select valeur_int from parametres where type = 'calcul_jour' and stype = 'un') then 1
                                               else 0.5 end as j
                                        from  (select substr(debut , 6, 2) as mois
                                                    , substr(debut , 1, 10) as jour
                                                    , sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes 
                                                from activite 
                                                where substr(debut , 1, 4) = ?
                                                group by substr(debut , 1, 10)
                                                union all 
                                                select substr(jour, 6, 2) as mois
                                                    , jour
                                                    , sum(correction * duree) as secondes
                                                from correction 
                                                where substr(jour, 1, 4) = ?
                                                group by substr(jour, 1, 10)
                                            ) as a  
                                        group by mois, jour
                                       ) as b
                                  group by mois
                            ) as b 
                            order by mois""", (annee, annee))
        return (self.cur.fetchall())

    def DB_select_Param(self, type, stype):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select type, stype, valeur_a, valeur_n, valeur_int, visible
                            from parametres 
                            where type = ?
                              and stype = ?
                            order by type, stype""", (type, stype ))

        return (self.cur.fetchall())

    def DB_insert_Param(self, type, stype, valeur_a, valeur_n, valeur_int, visible):
        #
        #
        self.cur.execute("""insert into parametres (type, stype, valeur_a, valeur_n, valeur_int, visible)
                            values( ?, ?, ?, ?, ?, ?)""", (type, stype, valeur_a, valeur_n, valeur_int, visible ))

        self.cur.execute("""commit""")

    def DB_update_Param(self, type, stype, valeur_a, valeur_n, valeur_int, visible):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""update parametres 
                            set valeur_a = ?
                              , valeur_n = ?
                              , valeur_int = ?
                              , visible = ?
                            where type = ?
                              and stype = ?""", (valeur_a, valeur_n, valeur_int, visible, type, stype ))

        self.cur.execute("""commit""")


class FAliceCorrection(QtWidgets.QWidget):
    """écran de correction de temps passé sur différentes activités
       - transfert 
       - ajout
       - stop
    """

    #========================================================================
    def __init__(self, parent=None):
        super().__init__(parent)

        #
        self.dateCorrection = None
        #accès à une base de données
        baseDB = "Alice.db"
        self.con = None
        # Ouvrir une connexion à la base de données SQLite (n'est pas exécuté si la connexion est déjà ouverte)
        self.con = sqlite3.connect(baseDB)
        self.cur = self.con.cursor()
        self.DB_connexion()  


        self.setWindowTitle(_("Boîte à correction"))
        self.setGeometry(50 , 50 , 600 , 700)
        app_icon = QtGui.QIcon()
        app_icon.addFile("Alice1.ico", QtCore.QSize(16,16))

        self.setWindowIcon(app_icon)

        
        # création d'un objet graphique QTreeWidget qui va contenir les opérations effectuées sur la journée
        self.table = QtWidgets.QTreeWidget(self)
        self.table.setGeometry(10 , 330 , 580 , 300)

        #Type de correction
        self.groupbox1 = QtWidgets.QGroupBox(self)
        self.groupbox1.setGeometry(10, 35, 580, 290)
        self.rbTransfert = QtWidgets.QRadioButton(self.groupbox1)
        self.rbTransfert.setText(_("Transfert de temps"))
        self.rbTransfert.setGeometry(5, 10, 200, 20)
        #self.rbTransfert.setChecked(True)
        #self.rbTransfert.toggled.connect(self.selection_grille)
        self.rbStop = QtWidgets.QRadioButton(self.groupbox1)
        self.rbStop.setText(_("Définir heure d'arrêt du soir"))
        self.rbStop.setGeometry(5, 110, 200, 20)
        #self.rbStop.toggled.connect(self.selection_grille)
        self.rbAjout = QtWidgets.QRadioButton(self.groupbox1)
        self.rbAjout.setText(_("Ajouter du temps"))
        self.rbAjout.setGeometry(5, 210, 200, 20)
        #self.rbAjout.toggled.connect(self.selection_grille)

        #combobox de corrections
        self.label_to = QtWidgets.QLabel(self)
        self.label_to.setText(_('Prendre du temps sur:'))
        self.label_to.setGeometry(50 , 70 , 200 , 20)
        self.transfert_origine = QtWidgets.QComboBox(self)
        self.transfert_origine.setGeometry(50 , 95 , 200     , 20)
        self.transfert_origine.currentIndexChanged.connect(self.selection_transfert)
        self.label_tr = QtWidgets.QLabel(self)
        self.label_tr.setText(_('Temps'))
        self.label_tr.setGeometry(260 , 50 , 200 , 20)        
        self.label_tr2 = QtWidgets.QLabel(self)
        self.label_tr2.setText('H         M         S')
        self.label_tr2.setGeometry(260 , 70 , 200 , 20)        
        self.transfert_heures = QtWidgets.QLineEdit(self)
        #saisie numérique uniquement d'autorisée
        self.transfert_heures.setValidator(QtGui.QIntValidator())
        self.transfert_heures.textChanged.connect(self.selection_transfert)
        ##sur apui de la touche entrée lors de la saisie de texte, appel ok_action
        self.transfert_heures.returnPressed.connect(self.appliquer)
        self.transfert_heures.setGeometry(260, 95, 30, 20)
        self.transfert_minutes = QtWidgets.QLineEdit(self)
        self.transfert_minutes.setValidator(QtGui.QIntValidator())
        self.transfert_minutes.textChanged.connect(self.selection_transfert)
        self.transfert_minutes.returnPressed.connect(self.appliquer)
        self.transfert_minutes.setGeometry(295, 95, 30, 20)
        self.transfert_secondes = QtWidgets.QLineEdit(self)
        self.transfert_secondes.setValidator(QtGui.QIntValidator())
        self.transfert_secondes.textChanged.connect(self.selection_transfert)
        self.transfert_secondes.returnPressed.connect(self.appliquer)
        self.transfert_secondes.setGeometry(330, 95, 30, 20)

        self.label_td = QtWidgets.QLabel(self)
        self.label_td.setText(_('Le mettre sur:'))
        self.label_td.setGeometry(370 , 70 , 200 , 20)
        self.transfert_destination = QtWidgets.QComboBox(self)
        self.transfert_destination.setGeometry(370 , 95 , 200 , 20)
        self.transfert_destination.currentIndexChanged.connect(self.selection_transfert)

        #heure stop 
        self.heure_stop = QtWidgets.QLineEdit(self)
        #masque de saisie (hh:mm:ss). Cf. doc sur les masques https://doc.qt.io/qtforpython-5/PySide2/QtWidgets/QLineEdit.html
        self.heure_stop.setInputMask("99:99:99")
        ##self.ajout_secondes.textChanged.connect(self.ok_action)
        ##sur apui de la touche entrée lors de la saisie de texte, appel ok_action
        #self.ajout_secondes.returnPressed.connect(self.ok_action)
        self.heure_stop.setGeometry(50, 175, 300, 20)
        self.heure_stop.textChanged.connect(self.selection_stop)

        #combo ajout (+ ou -)
        #combobox de corrections
        self.label_ajout_a = QtWidgets.QLabel(self)
        self.label_ajout_a.setText(_('Tache:'))
        self.label_ajout_a.setGeometry(50 , 265 , 200 , 20)
        self.ajout_activite = QtWidgets.QComboBox(self)
        self.ajout_activite.setGeometry(50 , 290 , 200     , 20)
        self.ajout_activite.currentIndexChanged.connect(self.selection_ajout)
        self.label_ajout_t = QtWidgets.QLabel(self)
        self.label_ajout_t.setText(_('Temps'))
        self.label_ajout_t.setGeometry(260 , 245 , 200 , 20)        
        self.label_ajout_t2 = QtWidgets.QLabel(self)
        self.label_ajout_t2.setText('H         M         S')
        self.label_ajout_t2.setGeometry(260 , 265 , 200 , 20)        
        self.ajout_heures = QtWidgets.QLineEdit(self)
        self.ajout_heures.setValidator(QtGui.QIntValidator())
        self.ajout_heures.setGeometry(260, 290, 30, 20)
        self.ajout_heures.textChanged.connect(self.selection_ajout)
        self.ajout_heures.returnPressed.connect(self.appliquer)
        self.ajout_minutes = QtWidgets.QLineEdit(self)
        self.ajout_minutes.setValidator(QtGui.QIntValidator())
        self.ajout_minutes.setGeometry(295, 290, 30, 20)
        self.ajout_minutes.textChanged.connect(self.selection_ajout)
        self.ajout_minutes.returnPressed.connect(self.appliquer)
        self.ajout_secondes = QtWidgets.QLineEdit(self)
        self.ajout_secondes.setValidator(QtGui.QIntValidator())
        self.ajout_secondes.setGeometry(330, 290, 30, 20)
        self.ajout_secondes.textChanged.connect(self.selection_ajout)
        self.ajout_secondes.returnPressed.connect(self.appliquer)


        # créer bouton OK (= appliquer puis annuler)
        self.button_ok = QtWidgets.QPushButton(_("OK"), self)
        self.button_ok.clicked.connect(self.valider)
        self.button_ok.setGeometry(10, 640, 150, 50)

        # créer bouton Annuler
        self.button_annuler = QtWidgets.QPushButton(_("Annuler"), self)
        self.button_annuler.clicked.connect(self.quitter_action)
        self.button_annuler.setGeometry(170, 640, 150, 50)

        # créer bouton Appliquer
        self.button_appliquer = QtWidgets.QPushButton(_("Appliquer"), self)
        self.button_appliquer.clicked.connect(self.appliquer)
        self.button_appliquer.setGeometry(330, 640, 150, 50)

        ## créer le champ de saisie de texte lineEdit
        #self.lineEdit = QtWidgets.QLineEdit(self)
        ##self.lineEdit.textChanged.connect(self.ok_action)
        ##sur apui de la touche entrée lors de la saisie de texte, appel ok_action
        #self.lineEdit.returnPressed.connect(self.ok_action)
        #self.lineEdit.setGeometry(170, 0, 150, 50)
        
        #chargement initial du tableau avec dernière date du tableau = date du jour
        #self.avant()

    def libelles(self):
        self.setWindowTitle(_("Boîte à correction"))
        self.rbTransfert.setText(_("Transfert de temps"))
        self.rbStop.setText(_("Définir heure d'arrêt du soir"))
        self.rbAjout.setText(_("Ajouter du temps"))
        self.label_to.setText(_('Prendre du temps sur:'))
        self.label_tr.setText(_('Temps'))
        self.label_tr2.setText('H         M         S')
        self.label_td.setText(_('Le mettre sur:'))
        self.label_ajout_a.setText(_('Tache:'))
        self.label_ajout_t.setText(_('Temps'))
        self.label_ajout_t2.setText('H         M         S')
        self.button_ok.setText(_("OK"))
        self.button_annuler.setText(_("Annuler"))
        self.button_appliquer.setText(_("Appliquer"))

    def resizeEvent(self, event):
        # Appeler la méthode resizeEvent de la classe parente
        super().resizeEvent(event)

        # Redimensionner le tableau pour occuper tout l'espace disponible
        self.table.setGeometry(10, 330, self.width() - 20, self.height() - 400)
        self.button_ok.setGeometry(10, self.height() - 60, 150, 50)
        self.button_annuler.setGeometry(170, self.height() - 60, 150, 50)
        self.button_appliquer.setGeometry(330, self.height() - 60, 150, 50)

    def selection_transfert(self):
        self.rbTransfert.setChecked(True)

    def selection_stop(self):
        self.rbStop.setChecked(True)

    def selection_ajout(self):
        self.rbAjout.setChecked(True)

    def setDate(self, dateCorrection):
        self.dateCorrection = datetime.strptime(dateCorrection, "%Y-%m-%d")
        self.setWindowTitle(_("Boîte à correction ") + str(dateCorrection))
        self.charge_ecran()        


    def keyPressEvent(self, event):
        #if event.key() == QtCore.Qt.Key_Enter:
        if event.key() in [QtCore.Qt.Key_Escape]:
            self.quitter_action()

    def quitter_action(self):
        self.hide()

    def appliquer(self):
        if self.rbTransfert.isChecked():
            duree = 0
            if self.transfert_secondes.text().isdigit():
                duree += int(self.transfert_secondes.text()) 
            if self.transfert_minutes.text().isdigit():
                duree += int(self.transfert_minutes.text()) * 60
            if self.transfert_heures.text().isdigit():
                duree += int(self.transfert_heures.text()) * 3600
            if duree != 0:
                libelle = self.transfert_origine.currentText()
                jour = date(self.dateCorrection.year, self.dateCorrection.month, self.dateCorrection.day)
                correction = -1
                self.DB_insert_C(libelle, jour, correction, duree)
                libelle = self.transfert_destination.currentText()
                jour = date(self.dateCorrection.year, self.dateCorrection.month, self.dateCorrection.day)
                correction = 1
                self.DB_insert_C(libelle, jour, correction, duree)
                #réinitialisation
                self.transfert_heures.setText("")
                self.transfert_minutes.setText("")
                self.transfert_secondes.setText("")
                self.rbTransfert.setChecked(False)
        if self.rbAjout.isChecked():
            #lstrip("-") sert à accepter le signe - devant comme un digit
            duree = 0
            if self.ajout_secondes.text().lstrip("-").isdigit():
                duree += int(self.ajout_secondes.text())
            if self.ajout_minutes.text().lstrip("-").isdigit():
                duree += int(self.ajout_minutes.text()) * 60
            if self.ajout_heures.text().lstrip("-").isdigit():
                duree += int(self.ajout_heures.text()) * 3600                            
            if duree != 0:
                libelle = self.ajout_activite.currentText()
                jour = date(self.dateCorrection.year, self.dateCorrection.month, self.dateCorrection.day)
                correction = 1
                self.DB_insert_C(libelle, jour, correction, duree)
                #réinitialisation
                self.ajout_heures.setText("")
                self.ajout_minutes.setText("")
                self.ajout_secondes.setText("")
                self.rbAjout.setChecked(False)
        if self.rbStop.isChecked():
            message_erreur = _("Saisir l'heure à ce format hh:mm:ss")
            heure = self.heure_stop.text().split(":")
            if len(heure) == 3:
                if heure[0].isdigit() and heure[1].isdigit() and heure[2].isdigit():
                    if int(heure[0]) < 24 and int(heure[1]) < 60 and int(heure[2]) < 60:
                        jour = date(self.dateCorrection.year, self.dateCorrection.month, self.dateCorrection.day)
                        jourheure = datetime(self.dateCorrection.year, self.dateCorrection.month, self.dateCorrection.day, int(heure[0]), int(heure[1]), int(heure[2]))
                        self.DB_update_A(str(jourheure), jour)
                        self.rbStop.setChecked(False)
                        self.heure_stop.setText("")
                    else:
                        QtWidgets.QMessageBox.about(self, _("Saisie incorrecte"), message_erreur)
                else:
                    QtWidgets.QMessageBox.about(self, _("Saisie incorrecte"), message_erreur)
            else:
                QtWidgets.QMessageBox.about(self, _("Saisie incorrecte"), message_erreur)
        self.rbAjout.setChecked(False)
        self.rbStop.setChecked(False)
        self.rbTransfert.setChecked(False)
        self.charge_ecran()
        
        #Rechargement du calendier des activités suite à l'application du correctif
        if trayIcon.fenAlice.semaine.isChecked() == True:
            trayIcon.fenAlice.chargeTableauSemaine(0, None)
        if trayIcon.fenAlice.mois.isChecked() == True:
            trayIcon.fenAlice.chargeTableauMois(0, None)
        if trayIcon.fenAlice.annee.isChecked() == True:
            trayIcon.fenAlice.chargeTableauAnnee(0, None)
        
    def valider(self):
        self.appliquer()
        self.quitter_action()

    def charge_ecran(self):
        d1 = date(self.dateCorrection.year, self.dateCorrection.month, self.dateCorrection.day)
        self.extraction = self.DB_select_S(str(d1))
        #nb d'enreg extraits
        nb_lignes = len(self.extraction)
        self.table.clear()
        self.table.setColumnCount(4)
        self.table.setHeaderLabels([_("Libellé"), _("début/tevt"), _("fin/sens"), _("/correction(s)")])
        rupture = 1
        items = []
        #Boucle d'alimentation des activités de la semaine
        item = QtWidgets.QTreeWidgetItem([_("activite")])
        for i in range(nb_lignes):
            activite = self.extraction[i]
            #self.table.addItem(str(activite[0]) + ';\t' + str(activite[1]) + ';\t' + str(activite[2]) + ';\t' + str(activite[3]))
            if rupture == 1 and (str(activite[0]) == '2'):
                rupture = 2
                items.append(item)
                item = QtWidgets.QTreeWidgetItem([_("corrections")])
            child = QtWidgets.QTreeWidgetItem([str(activite[1]), str(activite[2]), str(activite[3]), str(activite[4])])
            item.addChild(child)
        items.append(item)
        self.table.insertTopLevelItems(0, items)
        self.table.expandAll()

        #alim combobox
        self.extraction = self.DB_select_S2(str(d1))
        self.transfert_origine.clear()
        for i in range(len(self.extraction)):
            self.transfert_origine.addItem(self.extraction[i][0])
        #alim combobox
        self.extraction = self.DB_select_A()
        self.transfert_destination.clear()
        self.ajout_activite.clear()
        for i in range(len(self.extraction)):
            #on n'ajoute pas ce qui commence par un /
            if not (self.extraction[i][0][0] == "/" and self.extraction[i][0][1:3].isnumeric):
                self.transfert_destination.addItem(self.extraction[i][0])
                self.ajout_activite.addItem(self.extraction[i][0])

        self.rbAjout.setChecked(False)
        self.rbStop.setChecked(False)
        self.rbTransfert.setChecked(False)

        #arrêt à une heure donnée actif ou pas?
        if self.DB_select_NT(str(d1)) == None:
            self.rbStop.setDisabled(True)
            self.heure_stop.setDisabled(True)
        else:
            self.rbStop.setDisabled(False)
            self.heure_stop.setDisabled(False)

    def charge_ecran_old(self):
        d1 = date(self.dateCorrection.year, self.dateCorrection.month, self.dateCorrection.day)
        self.extraction = self.DB_select_S(str(d1))
        #nb d'enreg extraits
        nb_lignes = len(self.extraction)
        self.table.clear()
        #Boucle d'alimentation des activités de la semaine
        for i in range(nb_lignes):
            activite = self.extraction[i]
            self.table.addItem(str(activite[0]) + ';\t' + str(activite[1]) + ';\t' + str(activite[2]) + ';\t' + str(activite[3]))

        #alim combobox
        self.extraction = self.DB_select_S2(str(d1))
        self.transfert_origine.clear()
        for i in range(len(self.extraction)):
            self.transfert_origine.addItem(self.extraction[i][0])
        #alim combobox
        self.extraction = self.DB_select_A()
        self.transfert_destination.clear()
        self.ajout_activite.clear()
        for i in range(len(self.extraction)):
            self.transfert_destination.addItem(self.extraction[i][0])
            self.ajout_activite.addItem(self.extraction[i][0])

        self.rbAjout.setChecked(False)
        self.rbStop.setChecked(False)
        self.rbTransfert.setChecked(False)

        #arrêt à une heure donnée actif ou pas?
        if self.DB_select_NT(str(d1)) == None:
            self.rbStop.setDisabled(True)
            self.heure_stop.setDisabled(True)
        else:
            self.rbStop.setDisabled(False)
            self.heure_stop.setDisabled(False)


    #accès base de donnée
    def DB_connexion(self):
            try:
                #Vérifie existence de la table
                TAppr = self.cur.execute("""SELECT tbl_name FROM sqlite_master WHERE type='table' AND tbl_name='activite';""").fetchall()
                if TAppr == []:
                    #print('table a creer')
                    self.DB_create()

            except sqlite3.Error as e:
                if self.con:
                    self.con.rollback()

                #print(f"Error {e.args[0]}")
                QtWidgets.QMessageBox.about(self, "ERREUR", f"Error {e.args[0]}")
                sys.exit(1)
    #création si inexistante
    def DB_create(self):
        self.cur.execute("""CREATE TABLE activite (libelle  TEXT NOT NULL, debut TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, fin TIMESTAMP,  id INTEGER, PRIMARY KEY( id  AUTOINCREMENT));""")
        self.cur.execute("""CREATE TABLE correction (libelle TEXT NOT NULL, jour DATE, correction INTEGER, duree INTEGER, tevt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);""")
        self.cur.execute("""CREATE TABLE parametres (type TEXT,stype TEXT,valeur_a TEXT,valeur_n REAL,valeur_int INTEGER,visible INTEGER);""")
        self.cur.execute("""CREATE TABLE taches ( libelle TEXT, parent TEXT, niveau INTEGER, ordre_calendrier INTEGER, ordre_menu INTEGER, affichage_menu INTEGER);""")
    #sélection du détail d'une journée
    def DB_select_S(self, jour_debut):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select 1, libelle, debut, fin, 0 from activite 
                            where substr(debut , 1, 10) = ? 
                            union all 
                            select 2, libelle, tevt, case when correction = 1 then "C+" else "C-" end, correction * duree as secondes 
                            from correction 
                            where jour = ?
                            order by 1, 3""", (jour_debut, jour_debut ))
                            #where jour= ?""", (jour, )) --fonctionnel
                            #where jour='2023-01-25'""") --fonctionnel mais en dur!
        return (self.cur.fetchall())
    #sélection des noms d'activités réalisées sur la journée
    def DB_select_S2(self, jour_debut):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select distinct libelle from(
                            select libelle from activite 
                            where substr(debut , 1, 10) = ? 
                            union all 
                            select libelle from correction 
                            where jour = ?
                            ) a
                            order by 1""", (jour_debut, jour_debut ))
                            #where jour= ?""", (jour, )) --fonctionnel
                            #where jour='2023-01-25'""") --fonctionnel mais en dur!
        return (self.cur.fetchall())

    def DB_insert_C(self, libelle, jour, correction, duree):
        #insertion d'une correction
        self.cur.execute("""insert into correction (libelle, jour, correction, duree, tevt) values(?, ?, ?, ?, datetime('now', 'localtime'))""", (libelle, jour, correction, duree ))

        self.cur.execute("""commit""")

    #sélection des noms d'activités existantes
    def DB_select_A(self):
        self.cur.execute("""select libelle from taches 
                            order by ordre_menu""")
        return (self.cur.fetchall())

    #sélection d'une éventuelle activité non terminée
    def DB_select_NT(self, jour_debut):
        self.cur.execute("""select libelle from activite 
                            where substr(debut , 1, 10) = ? and fin is NULL""", (jour_debut, ))
        return (self.cur.fetchone())

    #arrêt activité
    def DB_update_A(self, heure, jour):
        #On arrête l'activité déjà en cours
        self.cur.execute("""update activite set fin = ? where fin is NULL and substr(debut , 1 , 10) = ?""", (heure, jour))

        self.cur.execute("""commit""")


class FAliceParametrages(QtWidgets.QWidget):
    """écran de gestion de divers parmétrages
    """

    #========================================================================
    def __init__(self, parent=None):
        super().__init__(parent)

        global parametre_jour
        global parametre_demi_jour
        self.DBAA = DB_Acces_Alice

        #
        self.dateCorrection = None
        #accès à une base de données
        baseDB = "Alice.db"
        self.con = None
        # Ouvrir une connexion à la base de données SQLite (n'est pas exécuté si la connexion est déjà ouverte)
        self.con = sqlite3.connect(baseDB)
        self.cur = self.con.cursor()
        self.DB_connexion()  

        #chargement des paramètres de police de caractère des 3 hiérarchies
        #tableau des 3 hiérarchies
        #sur chaque hiérarchie: police, taille, gras, italique, [R, V, B, transparence]
        self.polices = self.DBAA.charge_polices(self)

        self.setWindowTitle(_("Paramétrages"))
        self.setGeometry(50 , 50 , 600 , 700)
        app_icon = QtGui.QIcon()
        app_icon.addFile("Alice1.ico", QtCore.QSize(16,16))

        self.setWindowIcon(app_icon)

        #définition d'un jour
        self.label_general = QtWidgets.QLabel(self)
        self.label_general.setText(_("Définition de la durée d'une journée ou d'une demi-journée:"))
        self.label_general.setGeometry(50 , 70 , 400 , 20)

        self.label_un_jour = QtWidgets.QLabel(self)
        self.label_un_jour.setText(_("à partir de combien de secondes la journée est complète:"))
        self.label_un_jour.setGeometry(70 , 90 , 400 , 20)        

        self.label_demi_jour = QtWidgets.QLabel(self)
        self.label_demi_jour.setText(_("à partir de combien de secondes a-t'on passé une demi-journée:"))
        self.label_demi_jour.setGeometry(70 , 120 , 400 , 20)        

        self.label_zero_jour = QtWidgets.QLabel(self)
        self.label_zero_jour.setText(_("en dessous de ce seuil on reste à zéro jour."))
        self.label_zero_jour.setGeometry(70 , 130 , 400 , 20)  

        self.seuil_un_jour = QtWidgets.QLineEdit(self)
        #saisie numérique uniquement d'autorisée
        self.seuil_un_jour.setValidator(QtGui.QIntValidator())
        self.seuil_un_jour.setGeometry(480, 90, 40, 20)
        self.seuil_un_jour.setText(str(parametre_jour))

        self.seuil_demi_jour = QtWidgets.QLineEdit(self)
        #saisie numérique uniquement d'autorisée
        self.seuil_demi_jour.setValidator(QtGui.QIntValidator())
        self.seuil_demi_jour.setGeometry(480, 120, 40, 20)
        self.seuil_demi_jour.setText(str(parametre_demi_jour))

        self.label_transco_un_jour = QtWidgets.QLabel(self)
        self.label_transco_un_jour.setText("")
        self.label_transco_un_jour.setGeometry(530 , 90 , 70 , 20)        

        self.label_transco_demi_jour = QtWidgets.QLabel(self)
        self.label_transco_demi_jour.setText("")
        self.label_transco_demi_jour.setGeometry(530 , 120 , 70 , 20)        

        # créer bouton OK (= appliquer puis annuler)
        self.button_defaut = QtWidgets.QPushButton(_("Paramétrages par défaut"), self)
        self.button_defaut.clicked.connect(self.valeurs_par_defaut)
        self.button_defaut.setGeometry(50, 10, 150, 50)

        #Hiérarchie 00
        self.label_h00 = QtWidgets.QLabel(self)
        self.label_h00.setText(_("Hiérarchie 0:"))
        self.label_h00.setGeometry(50 , 170 , 120 , 20)
        # ComboBox pour sélectionner la police
        self.font_h00 = QtWidgets.QFontComboBox(self)
        self.font_h00.setCurrentFont(QtGui.QFont("freesansbold"))
        self.font_h00.setGeometry(10 , 190 , 130 , 20)
        self.font_h00.currentFontChanged.connect(self.changeFont)
        #choix taille police
        self.size_h00 = QtWidgets.QSpinBox(self)
        self.size_h00.setRange(1, 50)
        self.size_h00.setValue(int(self.polices[0][1]))
        self.size_h00.setGeometry(150 , 190 , 60 , 20)
        self.size_h00.valueChanged.connect(self.changeFont)
        # Boutons pour le gras
        self.bold_h00 = QtWidgets.QPushButton(_("Gras"), self)
        self.bold_h00.setCheckable(True)
        if self.polices[0][2]==0:
            self.bold_h00.setChecked(False)
        else:
            self.bold_h00.setChecked(True)
        self.bold_h00.setGeometry(220 , 190 , 80 , 20)
        self.bold_h00.clicked.connect(self.changeFont)
        #italique
        self.italic_h00 = QtWidgets.QPushButton(_("Italique"), self)
        self.italic_h00.setCheckable(True)
        self.italic_h00.setGeometry(310 , 190 , 80 , 20)
        self.italic_h00.clicked.connect(self.changeFont)
        # Boutons pour choisir la couleur du texte et du fond
        self.text_color_h00 = QtWidgets.QPushButton(_("Couleur du texte"), self)
        self.text_color_h00.setGeometry(400 , 190 , 90 , 20)
        self.text_color_h00.clicked.connect(self.changeTextColor00)
        # Couleur de fond
        self.bg_color_h00 = QtWidgets.QPushButton(_("Couleur de fond"), self)
        self.bg_color_h00.setGeometry(500 , 190 , 90 , 20)
        self.bg_color_h00.clicked.connect(self.changeBackgroundColor00)


        #Hiérarchie 01
        self.label_h01 = QtWidgets.QLabel(self)
        self.label_h01.setText(_("Hiérarchie 1:"))
        self.label_h01.setGeometry(50 , 210 , 120 , 20)
        # ComboBox pour sélectionner la police
        self.font_h01 = QtWidgets.QFontComboBox(self)
        self.font_h01.setCurrentFont(QtGui.QFont("freesansbold"))
        self.font_h01.setGeometry(10 , 230 , 130 , 20)
        self.font_h01.currentFontChanged.connect(self.changeFont)
        #choix taille police
        self.size_h01 = QtWidgets.QSpinBox(self)
        self.size_h01.setRange(1, 50)
        self.size_h01.setValue(int(self.polices[1][1]))
        self.size_h01.setGeometry(150 , 230 , 60 , 20)
        self.size_h01.valueChanged.connect(self.changeFont)
        # Boutons pour le gras
        self.bold_h01 = QtWidgets.QPushButton(_("Gras"), self)
        self.bold_h01.setCheckable(True)
        if self.polices[1][2]==0:
            self.bold_h01.setChecked(False)
        else:
            self.bold_h01.setChecked(True)
        self.bold_h01.setGeometry(220 , 230 , 80 , 20)
        self.bold_h01.clicked.connect(self.changeFont)
        #italique
        self.italic_h01 = QtWidgets.QPushButton(_("Italique"), self)
        self.italic_h01.setCheckable(True)
        self.italic_h01.setGeometry(310 , 230 , 80 , 20)
        self.italic_h01.clicked.connect(self.changeFont)
        # Boutons pour choisir la couleur du texte et du fond
        self.text_color_h01 = QtWidgets.QPushButton(_("Couleur du texte"), self)
        self.text_color_h01.setGeometry(400 , 230 , 90 , 20)
        self.text_color_h01.clicked.connect(self.changeTextColor01)
        # Couleur de fond
        self.bg_color_h01 = QtWidgets.QPushButton(_("Couleur de fond"), self)
        self.bg_color_h01.setGeometry(500 , 230 , 90 , 20)
        self.bg_color_h01.clicked.connect(self.changeBackgroundColor01)


        #Hiérarchie 02
        self.label_h02 = QtWidgets.QLabel(self)
        self.label_h02.setText(_("Hiérarchie 2:"))
        self.label_h02.setGeometry(50 , 250 , 120 , 20)
        # ComboBox pour sélectionner la police
        self.font_h02 = QtWidgets.QFontComboBox(self)
        self.font_h02.setCurrentFont(QtGui.QFont("freesansbold"))
        self.font_h02.setGeometry(10 , 270 , 130 , 20)
        self.font_h02.currentFontChanged.connect(self.changeFont)
        #choix taille police
        self.size_h02 = QtWidgets.QSpinBox(self)
        self.size_h02.setRange(1, 50)
        self.size_h02.setValue(int(self.polices[2][1]))
        self.size_h02.setGeometry(150 , 270 , 60 , 20)
        self.size_h02.valueChanged.connect(self.changeFont)
        # Boutons pour le gras
        self.bold_h02 = QtWidgets.QPushButton(_("Gras"), self)
        self.bold_h02.setCheckable(True)
        if self.polices[2][2]==0:
            self.bold_h02.setChecked(False)
        else:
            self.bold_h02.setChecked(True)
        self.bold_h02.setGeometry(220 , 270 , 80 , 20)
        self.bold_h02.clicked.connect(self.changeFont)
        #italique
        self.italic_h02 = QtWidgets.QPushButton(_("Italique"), self)
        self.italic_h02.setCheckable(True)
        self.italic_h02.setGeometry(310 , 270 , 80 , 20)
        self.italic_h02.clicked.connect(self.changeFont)
        # Boutons pour choisir la couleur du texte et du fond
        self.text_color_h02 = QtWidgets.QPushButton(_("Couleur du texte"), self)
        self.text_color_h02.setGeometry(400 , 270 , 90 , 20)
        self.text_color_h02.clicked.connect(self.changeTextColor02)
        # Couleur de fond
        self.bg_color_h02 = QtWidgets.QPushButton(_("Couleur de fond"), self)
        self.bg_color_h02.setGeometry(500 , 270 , 90 , 20)
        self.bg_color_h02.clicked.connect(self.changeBackgroundColor02)

        #tableau exemple décrivant le résultat des paramétrages
        self.table = QtWidgets.QTableWidget(self)
        #définition caractéristiques: position, dimensions, nombre de colonnes et lignes. fait pour que ça tienne dans un écran PC portable en hauteur sans ascenseur.
        self.table.setColumnCount(2)
        self.table.setRowCount(3)
        self.table.setGeometry(10 , 300 , 300 , 150)
        #largeur de la première colonne
        self.table.setColumnWidth(0, 100)
        self.table.setVerticalHeaderLabels(["Hiérarchie 00","Hiérarchie 01","Hiérarchie 02"])
        self.table.setHorizontalHeaderLabels(["Total","Détail"])         

        self.recharge_tableau_test()

        # créer bouton OK (= appliquer puis annuler)
        self.button_ok = QtWidgets.QPushButton(_("OK"), self)
        self.button_ok.clicked.connect(self.valider)
        self.button_ok.setGeometry(10, 640, 150, 50)

        # créer bouton Annuler
        self.button_annuler = QtWidgets.QPushButton(_("Annuler"), self)
        self.button_annuler.clicked.connect(self.quitter_action)
        self.button_annuler.setGeometry(170, 640, 150, 50)

        # créer bouton Appliquer
        self.button_appliquer = QtWidgets.QPushButton(_("Appliquer"), self)
        self.button_appliquer.clicked.connect(self.appliquer)
        self.button_appliquer.setGeometry(330, 640, 150, 50)

        self.recalcul_duree()


    def libelles(self):
        self.setWindowTitle(_("Paramétrages"))
        self.label_general.setText(_("Définition de la durée d'une journée:"))
        self.label_un_jour.setText(_("à partir de combien de secondes la journée est complète:"))
        self.label_demi_jour.setText(_("à partir de combien de secondes a-t'on passé une demi-journée:"))
        self.label_zero_jour.setText(_("en dessous de ce seuil on reste à zéro jour."))
        self.button_defaut.setText(_("Paramétrages par défaut"))
        self.label_h00.setText(_("Hiérarchie 1:"))
        self.label_h01.setText(_("Hiérarchie 1:"))
        self.label_h02.setText(_("Hiérarchie 1:"))

        self.button_ok.setText(_("OK"))
        self.button_annuler.setText(_("Annuler"))
        self.button_appliquer.setText(_("Appliquer"))

    def changeFont(self):
        self.polices[0][0] = self.font_h00.currentText()
        self.polices[0][1] = self.size_h00.value()
        self.polices[0][2] = 87 if self.bold_h00.isChecked() else 0
        self.polices[0][3] = 1 if self.italic_h00.isChecked() else 0

        self.polices[1][0] = self.font_h01.currentText()
        self.polices[1][1] = self.size_h01.value()
        self.polices[1][2] = 87 if self.bold_h01.isChecked() else 0
        self.polices[1][3] = 1 if self.italic_h01.isChecked() else 0

        self.polices[2][0] = self.font_h02.currentText()
        self.polices[2][1] = self.size_h02.value()
        self.polices[2][2] = 87 if self.bold_h02.isChecked() else 0
        self.polices[2][3] = 1 if self.italic_h02.isChecked() else 0
        
        self.recharge_tableau_test()

    def changeTextColor00(self):
        self.changeTextColor(0)

    def changeTextColor01(self):
        self.changeTextColor(1)

    def changeTextColor02(self):
        self.changeTextColor(2)

    def changeTextColor(self, niv):
        y = niv
        color = QtGui.QColor(int(self.polices[y][5][0]), int(self.polices[y][5][1]), int(self.polices[y][5][2]), int(self.polices[y][5][3]))
        color = QtWidgets.QColorDialog.getColor(color)
        self.polices[y][5][0] = color.red()
        self.polices[y][5][1] = color.green()
        self.polices[y][5][2] = color.blue()
        self.polices[y][5][3] = color.alpha()
        #self.text_area.setStyleSheet(f"background-color: {color.name()};")
        self.recharge_tableau_test()

    def changeBackgroundColor00(self):
        self.changeBackgroundColor(0)

    def changeBackgroundColor01(self):
        self.changeBackgroundColor(1)

    def changeBackgroundColor02(self):
        self.changeBackgroundColor(2)

    def changeBackgroundColor(self, niv):
        y = niv
        color = QtGui.QColor(int(self.polices[y][4][0]), int(self.polices[y][4][1]), int(self.polices[y][4][2]), int(self.polices[y][4][3]))
        color = QtWidgets.QColorDialog.getColor(color)
        self.polices[y][4][0] = color.red()
        self.polices[y][4][1] = color.green()
        self.polices[y][4][2] = color.blue()
        self.polices[y][4][3] = color.alpha()
        #self.text_area.setStyleSheet(f"background-color: {color.name()};")
        self.recharge_tableau_test()


    def recharge_tableau_test(self):
        for y in range(3):
            for x in range(2):
                item = QtWidgets.QTableWidgetItem(str("test 1234") )
                item.setBackground(QtGui.QColor(int(self.polices[y][4][0]), int(self.polices[y][4][1]), int(self.polices[y][4][2]), int(self.polices[y][4][3])))
                item.setTextAlignment(QtCore.Qt.AlignRight)
                item.setFont(QtGui.QFont(self.polices[y][0], int(self.polices[y][1]), self.polices[y][2], self.polices[y][3] ))
                item.setForeground(QtGui.QColor(int(self.polices[y][5][0]), int(self.polices[y][5][1]), int(self.polices[y][5][2]), int(self.polices[y][5][3])))
                self.table.setItem(y, x, item)

    def resizeEvent(self, event):
        # Appeler la méthode resizeEvent de la classe parente
        super().resizeEvent(event)

        self.button_ok.setGeometry(10, self.height() - 60, 150, 50)
        self.button_annuler.setGeometry(170, self.height() - 60, 150, 50)
        self.button_appliquer.setGeometry(330, self.height() - 60, 150, 50)

    def recalcul_duree(self):
        tDurActHeur = int(int(self.seuil_un_jour.text()) // 3600)
        tDurActMin = int((int(self.seuil_un_jour.text()) - (int(self.seuil_un_jour.text()) % 60) ) /60 % 60)
        tDurActSec = int(int(self.seuil_un_jour.text()) % 60)
        #inscrit 
        self.label_transco_un_jour.setText(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")

        tDurActHeur = int(int(self.seuil_demi_jour.text()) // 3600)
        tDurActMin = int((int(self.seuil_demi_jour.text()) - (int(self.seuil_demi_jour.text()) % 60) ) /60 % 60)
        tDurActSec = int(int(self.seuil_demi_jour.text()) % 60)
        #inscrit 
        self.label_transco_demi_jour.setText(str(tDurActHeur) + "h" + str(tDurActMin) + "m" + str(tDurActSec) + "s")

    def valeurs_par_defaut(self):
        global parametre_jour
        global parametre_demi_jour
        parametre_jour = 18000
        parametre_demi_jour = 1000
        self.seuil_un_jour.setText(str(parametre_jour))
        self.seuil_demi_jour.setText(str(parametre_demi_jour))
        self.DB_update_Param("calcul_jour", "un", None, None, parametre_jour, None)
        self.DB_update_Param("calcul_jour", "demi", None, None, parametre_demi_jour, None)
        self.recalcul_duree()

        self.DB_update_Param("hierarchie00", "police","freesansbold",10,87,0)
        self.DB_update_Param("hierarchie01", "police","freesansbold",10,0,0)
        self.DB_update_Param("hierarchie02", "police","freesansbold",8,0,0)
        self.DB_update_Param("hierarchie00", "couleur_fond", "112, 114, 110, 127",None,None,None)
        self.DB_update_Param("hierarchie01", "couleur_fond", "220, 220, 220, 127",None,None,None)
        self.DB_update_Param("hierarchie02", "couleur_fond", "255, 255, 255, 255",None,None,None)
        self.DB_update_Param("hierarchie00", "couleur_police", "0, 0, 0, 255", None, None, None)
        self.DB_update_Param("hierarchie01", "couleur_police", "0, 0, 0, 255", None, None, None)
        self.DB_update_Param("hierarchie02", "couleur_police", "0, 0, 0, 255", None, None, None)
        self.polices = self.DBAA.charge_polices(self)
        self.recharge_tableau_test()

    def quitter_action(self):
        self.hide()

    def appliquer(self):
        global parametre_jour
        global parametre_demi_jour
        if not self.seuil_un_jour == "":
            parametre_jour = int(self.seuil_un_jour.text())
            self.DB_update_Param("calcul_jour", "un", None, None, parametre_jour, None)
        if not self.seuil_demi_jour == "":
            parametre_demi_jour = int(self.seuil_demi_jour.text())
            self.DB_update_Param("calcul_jour", "demi", None, None, parametre_demi_jour, None)

        #chargement en base des paramètres de police de caractère des 3 hiérarchies
        #sur chaque hiérarchie: police, taille, gras, italique, [R, V, B, transparence]
        for i in range(3):
            type_param = "hierarchie0" + str(i)
            police = self.polices[i][0]
            taille = self.polices[i][1]
            gras = self.polices[i][2]
            italique = self.polices[i][3]
            self.DB_update_Param(type_param, "police",police,taille,gras,italique)
            #couleur du fond
            couleur = str(self.polices[i][4][0])
            for j in range(3):
                couleur += ", " + str(self.polices[i][4][j+1])
            self.DB_update_Param(type_param, "couleur_fond",couleur,None,None,None)
            #couleur de la police
            couleur = str(self.polices[i][5][0])
            for j in range(3):
                couleur += ", " + str(self.polices[i][5][j+1])
            self.DB_update_Param(type_param, "couleur_police",couleur,None,None,None)
        self.polices = self.DBAA.charge_polices(self)

       
    def valider(self):
        self.appliquer()
        self.quitter_action()

    #accès base de donnée
    def DB_connexion(self):
            try:
                #Vérifie existence de la table
                TAppr = self.cur.execute("""SELECT tbl_name FROM sqlite_master WHERE type='table' AND tbl_name='activite';""").fetchall()
                if TAppr == []:
                    #print('table a creer')
                    self.DB_create()

            except sqlite3.Error as e:
                if self.con:
                    self.con.rollback()

                #print(f"Error {e.args[0]}")
                QtWidgets.QMessageBox.about(self, "ERREUR", f"Error {e.args[0]}")
                sys.exit(1)
    #création si inexistante
    def DB_create(self):
        self.cur.execute("""CREATE TABLE activite (libelle  TEXT NOT NULL, debut TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, fin TIMESTAMP,  id INTEGER, PRIMARY KEY( id  AUTOINCREMENT));""")
        self.cur.execute("""CREATE TABLE correction (libelle TEXT NOT NULL, jour DATE, correction INTEGER, duree INTEGER, tevt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);""")
        self.cur.execute("""CREATE TABLE parametres (type TEXT,stype TEXT,valeur_a TEXT,valeur_n REAL,valeur_int INTEGER,visible INTEGER);""")
        self.cur.execute("""CREATE TABLE taches ( libelle TEXT, parent TEXT, niveau INTEGER, ordre_calendrier INTEGER, ordre_menu INTEGER, affichage_menu INTEGER);""")

    def DB_select_Param(self, type, stype):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select type, stype, valeur_a, valeur_n, valeur_int, visible
                            from parametres 
                            where type = ?
                              and stype = ?
                            order by type, stype""", (type, stype ))

        return (self.cur.fetchall())

    def DB_insert_Param(self, type, stype, valeur_a, valeur_n, valeur_int, visible):
        #
        #
        self.cur.execute("""insert into parametres (type, stype, valeur_a, valeur_n, valeur_int, visible)
                            values( ?, ?, ?, ?, ?, ?)""", (type, stype, valeur_a, valeur_n, valeur_int, visible ))

        self.cur.execute("""commit""")

    def DB_update_Param(self, type, stype, valeur_a, valeur_n, valeur_int, visible):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""update parametres 
                            set valeur_a = ?
                              , valeur_n = ?
                              , valeur_int = ?
                              , visible = ?
                            where type = ?
                              and stype = ?""", (valeur_a, valeur_n, valeur_int, visible, type, stype ))

        self.cur.execute("""commit""")

class DB_Acces_Alice:
    """ divers accès regroupés ici
    """

    #========================================================================
    def __init__(self, parent=None):
        super().__init__(parent)

        global parametre_jour
        global parametre_demi_jour

        #
        self.dateCorrection = None
        #accès à une base de données
        baseDB = "Alice.db"
        self.con = None
        # Ouvrir une connexion à la base de données SQLite (n'est pas exécuté si la connexion est déjà ouverte)
        self.con = sqlite3.connect(baseDB)
        self.cur = self.con.cursor()
        self.DB_connexion()  

    def charge_polices(self):
        #chargement des paramètres de police de caractère des 3 hiérarchies
        #tableau des 3 hiérarchies
        #sur chaque hiérarchie: police, taille, gras, italique, [R, V, B, transparence]
        self.polices = []
        for i in range(3):
            police = []
            type_param = "hierarchie0" + str(i)
            param = self.DB_select_Param(type_param, "police")
            if len(param) == 0:
                if i == 0:
                    self.DB_insert_Param(type_param, "police", "freesansbold", 10, 87, 0)
                elif i == 1:
                    self.DB_insert_Param(type_param, "police", "freesansbold", 10, 0, 0)
                else:
                    self.DB_insert_Param(type_param, "police", "freesansbold", 8, 0, 0)
                param = self.DB_select_Param(type_param, "police")
            #nom de la police
            police.append(param[0][2])
            #taille
            police.append(param[0][3])
            #gras
            police.append(param[0][4])
            #italique
            if param[0][5] == 0:
                police.append(False)
            else:
                police.append(True)
            #couleur du fond
            param = self.DB_select_Param(type_param, "couleur_fond")
            if len(param) == 0:
                if i == 0:
                    self.DB_insert_Param(type_param, "couleur_fond", "112, 114, 110, 127", None, None, None)
                elif i == 1:
                    self.DB_insert_Param(type_param, "couleur_fond", "220, 220, 220, 127", None, None, None)
                else:
                    self.DB_insert_Param(type_param, "couleur_fond", "255, 255, 255, 255", None, None, None)
                param = self.DB_select_Param(type_param, "couleur_fond")
            #couleur du fond
            police.append(param[0][2].split(", "))
            #couleur de police, par défaut noir
            param = self.DB_select_Param(type_param, "couleur_police")
            if len(param) == 0:
                if i == 0:
                    self.DB_insert_Param(type_param, "couleur_police", "0, 0, 0, 255", None, None, None)
                elif i == 1:
                    self.DB_insert_Param(type_param, "couleur_police", "0, 0, 0, 255", None, None, None)
                else:
                    self.DB_insert_Param(type_param, "couleur_police", "0, 0, 0, 255", None, None, None)
                param = self.DB_select_Param(type_param, "couleur_police")
            #couleur de police
            police.append(param[0][2].split(", "))
            self.polices.append(police)
        return self.polices

    #accès base de donnée
    def DB_connexion(self):
            try:
                #Vérifie existence de la table
                TAppr = self.cur.execute("""SELECT tbl_name FROM sqlite_master WHERE type='table' AND tbl_name='activite';""").fetchall()
                if TAppr == []:
                    #print('table a creer')
                    self.DB_create()

            except sqlite3.Error as e:
                if self.con:
                    self.con.rollback()

                #print(f"Error {e.args[0]}")
                QtWidgets.QMessageBox.about(self, "ERREUR", f"Error {e.args[0]}")
                sys.exit(1)
    #création si inexistante
    def DB_create(self):
        self.cur.execute("""CREATE TABLE activite (libelle  TEXT NOT NULL, debut TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, fin TIMESTAMP,  id INTEGER, PRIMARY KEY( id  AUTOINCREMENT));""")
        self.cur.execute("""CREATE TABLE correction (libelle TEXT NOT NULL, jour DATE, correction INTEGER, duree INTEGER, tevt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);""")
        self.cur.execute("""CREATE TABLE parametres (type TEXT,stype TEXT,valeur_a TEXT,valeur_n REAL,valeur_int INTEGER,visible INTEGER);""")
        self.cur.execute("""CREATE TABLE taches ( libelle TEXT, parent TEXT, niveau INTEGER, ordre_calendrier INTEGER, ordre_menu INTEGER, affichage_menu INTEGER);""")

    def DB_select_Param(self, type, stype):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""select type, stype, valeur_a, valeur_n, valeur_int, visible
                            from parametres 
                            where type = ?
                              and stype = ?
                            order by type, stype""", (type, stype ))

        return (self.cur.fetchall())

    def DB_insert_Param(self, type, stype, valeur_a, valeur_n, valeur_int, visible):
        #
        #
        self.cur.execute("""insert into parametres (type, stype, valeur_a, valeur_n, valeur_int, visible)
                            values( ?, ?, ?, ?, ?, ?)""", (type, stype, valeur_a, valeur_n, valeur_int, visible ))

        self.cur.execute("""commit""")

    def DB_update_Param(self, type, stype, valeur_a, valeur_n, valeur_int, visible):
        #select libelle, jour, cast(secondes / 3600 as int) as h, cast((secondes - (secondes % 60) ) /60 % 60 as int) as m, cast(secondes % 60 as int) as s from (select libelle, jour, sum(secondes) as secondes from (select libelle, substr(debut , 1, 10) as jour, sum(round((julianday(ifnull(fin, datetime('now', 'localtime'))) - julianday(debut)) * 86400.0)) as secondes from activite group by libelle, substr(debut , 1, 10) union all select libelle, jour, sum(correction * duree) as secondes from correction group by libelle , jour) as a  group by libelle, jour) as b where jour = ?
        #params = {"pjour": jour}
        self.cur.execute("""update parametres 
                            set valeur_a = ?
                              , valeur_n = ?
                              , valeur_int = ?
                              , visible = ?
                            where type = ?
                              and stype = ?""", (valeur_a, valeur_n, valeur_int, visible, type, stype ))

        self.cur.execute("""commit""")


        

#############################################################################
if __name__ == '__main__':

    #========================================================================
    app = QtWidgets.QApplication(sys.argv)



    #========================================================================
    # définition du style (à adapter selon l'OS)
    if sys.platform=="win32":
        app.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
    elif sys.platform=="linux":
        app.setStyle(QtWidgets.QStyleFactory.create("gtk"))
    elif sys.platform=="darwin":    
        app.setStyle(QtWidgets.QStyleFactory.create("macintosh"))

    # pour afficher les styles disponible sous l'OS choisi:
    # exemple pour Windows: ['Windows', 'WindowsXP', 'WindowsVista', 'Fusion']
    # print([st for st in QtWidgets.QStyleFactory.keys()])

    #========================================================================
    # indispensable pour utiliser QSystemTrayIcon
    # sinon: arrêt complet après fermeture d'un simple messagebox
    app.setQuitOnLastWindowClosed(False)

    #========================================================================
    # pour assurer la traduction automatique du conversationnel à la locale
    # pour que le messagebox demande "Oui"/ "Non" (et non "Yes" / "No")
    locale = QtCore.QLocale.system().name()
    translator = QtCore.QTranslator ()
    reptrad = QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath)
    translator.load("qtbase_" + locale, reptrad)
    app.installTranslator(translator)

    #========================================================================
    # mettre la même icone par défaut pour toutes les fenêtres de l'application
    # (mais le programme lancé peut avoir sa propre icône)
    qicone = QtGui.QIcon(iconeStop)  # icone est une variable globale
    app.setWindowIcon(qicone)

    #========================================================================
    # lancement du tray
    bulle = ""
    trayIcon = SystemTrayIcon(app, qicone, bulle)  # bulle est une variable globale
    trayIcon.show()

    #--------------------------------------------------------------------
    # message d'information affiché 1 seconde si l'OS le supporte
    # sous Windows, l'activation nécessite dans le registre:
    # HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\
    #              Explorer\Advanced\EnableBalloonTips => dword:0x00000001
    # et la désactivation: ..\EnableBalloonTips => dword:0x00000000
    #if trayIcon.supportsMessages():
    #    trayIcon.showMessage(programme, # programme est une variable globale
    #                         "Cliquez sur l'icône pour lancer une recherche",
    #                         QtWidgets.QSystemTrayIcon.Information,
    #                         1000)  # temps d'affichage en millisecondes

    #========================================================================
    # boucle des évènements
    sys.exit(app.exec_())
