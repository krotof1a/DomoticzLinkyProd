#           Linky Plugin
#
#           Authors:
#                       Copyright (C) 2016 Baptiste Candellier
#                       Modified (C) 2017 Asdepique777
#                       Corrected (C) 2017 epierre
#                       Modified (C) 2017 Asdepique777
#                       Modified (C) 2018 Barberousse
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
<plugin key="linkyProd" name="LinkyProd" author="krotof1a" version="1.1.6" externallink="https://github.com/krotof1a/DomoticzLinkyProd">
    <params>
        <param field="Username" label="Adresse e-mail" width="200px" required="true" default=""/>
        <param field="Password" label="Mot de passe" width="200px" required="true" default="" password="true"/>
        <param field="Mode5" label="Production à montrer sur le tableau de bord" width="200px">
            <options>
                <option label="Journée dernière" value="day"  default="true" />
                <option label="Semaine en cours" value="week" />
                <option label="Semaine dernière" value="lweek"  />
                <option label="Mois en cours" value="month" />
                <option label="Mois dernier" value="lmonth"  />
                <option label="Année en cours" value="year"  />
            </options>
        </param>
        <param field="Mode4" label="Accepter automatiquement les conditions d'utilisation" width="75px">
            <options>
                <option label="Oui" value="True"/>
                <option label="Non" value="False"  default="true" />
            </options>
        </param>
        <param field="Mode2" label="Nombre de jours à récupérer pour les vues (28 min)" width="50px" required="false" default="366"/>
        <param field="Mode3" label="Debug" width="75px">
            <options>
                <option label="Non" value="0"  default="true" />
                <option label="Oui" value="1"/>
                <option label="Avancé" value="2"/>
            </options>
        </param>
    </params>
</plugin>
"""

# https://www.domoticz.com/wiki/Developing_a_Python_plugin

import Domoticz
from base64 import b64encode
import json
from urllib.parse import quote
import re
from datetime import datetime
from datetime import timedelta
import time
#from random import randint
import html

LOGIN_BASE_URI = 'espace-client-connexion.enedis.fr'
API_BASE_URI = 'espace-client-particuliers.enedis.fr'
BASE_PORT = '443'

API_ENDPOINT_LOGIN = '/auth/UI/Login'
API_ENDPOINT_DATA = '/group/espace-particuliers/mes-donnees-de-production-prod'
API_ACCEPT_TERMS = '/c/portal/update_terms_of_use'

#HEADERS = {
    #'Accept':'application/json, text/javascript, */*; q=0.01',
    #'Accept-Language':'fr,fr-FR;q=0.8,en;q=0.6',
    #"Content-Type": "application/x-www-form-urlencoded",
    #"Connection": "keep-alive",
    #"X-Requested-With": "XMLHttpRequest",
    #'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Mobile Safari/537.36'
#}
HEADERS = {
    "Accept" : "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept-Language" : "fr,fr-FR;q=0.8,en;q=0.6",
    "User-Agent" : "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0"
}

class BasePlugin:
    # boolean: to check that we are started, to prevent error messages when disabling or restarting the plugin
    isStarted = None
    # object: http connection
    httpConn = None
    # integer: index of the Linky device
    iIndexUnit = 1
    # string: name of the Linky device
    sDeviceName = "LinkyProd"
    # string: description of the Linky device
    sDescription = "Compteur Linky Production"
    # integer: type (pTypeGeneral)
    iType = 0xF3
    # integer: subtype (sTypeManagedCounter)
    iSubType = 0x21
    # integer: switch type (Energy Generated)
    iSwitchType = 4
    # string: step name of the state machine
    sConnectionStep = None
    # boolean: true if a step failed
    bHasAFail = None
    # dict: cookies
    dCookies = None
    # datetime: start date for short log
    dateBeginHours = None
    # datetime: end date for short log
    dateEndHours = None
    # datetime: start date for history
    dateBeginDays = None
    # datetime: end date for history
    dateEndDays = None
    # integer: number of days of data to grab for short log
    iHistoryDaysForHoursView = None
    # integer: number of days of data to grab for history
    iHistoryDaysForDaysView = None
    # integer: number of days left fot next batch of data
    iDaysLeft = None
    # datetime: backup end date for next batch of data
    savedDateEndDays = None
    # boolean: is this the batch of the most recent history
    bFirstMonths = None
    # string: username for Enedis website
    sUser = None
    # string: password for Enedis website
    sPassword = None
    # string: consumption to show = current week ("week"), the previous week ("lweek", the current month ("month"), the previous month ("lmonth"), or year ("year")
    sConsumptionType = None
    # boolean: auto accept terms
    bAutoAcceptTerms = None
    # integer: number of days for hours view
    iHistoryDaysForHoursView = None
    # integer: number of other view
    iHistoryDaysForDaysView = None
    # boolean: debug mode
    iDebugLevel = None
    
    def __init__(self):
        self.isStarted = False
        self.httpConn = None
        self.sConnectionStep = "idle"
        self.bHasAFail = False
        
    def myDebug(self, message):
        if self.iDebugLevel:
            Domoticz.Log(message)

    # Reset saved cookies
    def resetCookies(self):
        self.dCookies = {}

    # Grab cookies found in Data["Headers"] and saves them for later user
    def getCookies(self, Data):
        if Data and ("Headers" in Data) and ("Set-Cookie" in Data["Headers"]):
            # lCookies = re.findall("^(.*?)=(.*?)[;$]", Data["Headers"]["Set-Cookie"], re.MULTILINE)
            for match in re.finditer("^(.*?)=(.*?)[;$]", Data["Headers"]["Set-Cookie"], re.MULTILINE):
                self.dCookies[match.group(1)] = match.group(2)

    # Write saved cookies in headers["Cookie"]
    def setCookies(self, headers):
        headers["Cookie"] = ""        
        for sKey, sValue in self.dCookies.items():
            # Concatenate cookies
            if headers["Cookie"]:
                headers["Cookie"] += "; "
            headers["Cookie"] += sKey + "=" + sValue

    # get default headers
    def initHeaders(self):
        return dict(HEADERS)

    # send login details though http connection
    def login(self, username, password):
        payload = {
            'IDToken1': username,
            'IDToken2': password,
            'SunQueryParamsString': b64encode(b'realm=particuliers').decode(),
            'encoded': 'true',
            'gx_charset': 'UTF-8'
        }
        
        headers = self.initHeaders()
        headers["Host"] = LOGIN_BASE_URI + ":" + BASE_PORT
        
        sendData = {
                    "Verb" : "POST",
                    "URL"  : API_ENDPOINT_LOGIN,
                    "Headers" : headers,
                    "Data" : dictToQuotedString(payload)
        }
        
        #self.dumpDictToLog(sendData)
        # Reset cookies to get authentication cookie later
        self.resetCookies()
        # Send data
        self.httpConn.Send(sendData)

    # accept terms of use
    def acceptTerms(self):
        req_part = 'lincspartdisplaycdc_WAR_lincspartcdcportlet'

        payload = {
            'fm': 'Accepter'
        }
        
        headers = self.initHeaders()
        headers["Host"] = API_BASE_URI + ":" + BASE_PORT
        
        #Copy cookies
        self.setCookies(headers)
        
        sendData = {
                    "Verb" : "POST",
                    "URL"  : API_ACCEPT_TERMS,
                    "Headers" : headers,
                    "Data" : dictToQuotedString(payload)
        }
        
        #self.dumpDictToLog(sendData)
        self.httpConn.Send(sendData)
        
    # ask data to Enedis website, based on a resource_id ("urlCdcHeure" or "urlCdcJour") and date (max 28 days at once)
    def getData(self, resource_id, start_date, end_date, ):
        #Domoticz.Log(resource_id + " " + str(end_date))
        #req_part = 'lincspartdisplaycdc_WAR_lincspartcdcportlet'
        req_part = 'partproddonneesprod_WAR_lincspartportlet_INSTANCE_prodDonneesProd'

        payload = {
            '_' + req_part + '_beginDate': datetimeToEnderdisDateString(start_date),
            '_' + req_part + '_endDate': datetimeToEnderdisDateString(end_date)
        }
        
        headers = self.initHeaders()
        headers["Host"] = API_BASE_URI + ":" + BASE_PORT
        
        #Copy cookies
        self.setCookies(headers)
        
        params = {
            'p_p_id': req_part,
            'p_p_lifecycle': 2,
            'p_p_state': 'normal',
            'p_p_mode': 'view',
            'p_p_resource_id': resource_id,
            'p_p_cacheability': 'cacheLevelPage',
            'p_p_col_id': 'column-1',
            'p_p_col_pos': 1,
            'p_p_col_count': 2
        }
        
        sendData = {
                    "Verb" : "POST",
                    "URL"  : API_ENDPOINT_DATA + "?" + dictToQuotedString(params),
                    "Headers" : headers,
                    "Data" : dictToQuotedString(payload)
        }
        
        #self.dumpDictToLog(sendData)
        self.httpConn.Send(sendData)

    # Create Domoticz device
    def createDevice(self):
        # Only if not already done
        if not self.iIndexUnit in Devices:
            Domoticz.Device(Name=self.sDeviceName,  Unit=self.iIndexUnit, Type=self.iType, Subtype=self.iSubType, Switchtype=self.iSwitchType, Description=self.sDescription, Used=1).Create()
            if not (self.iIndexUnit in Devices):
                Domoticz.Error("Ne peut ajouter le dispositif Linky à la base de données. Vérifiez dans les paramètres de Domoticz que l'ajout de nouveaux dispositifs est autorisé")
                return False
        return True

    # Create device and insert usage in Domoticz DB
    def createAndAddToDevice(self, usage, Date):
        if not self.createDevice():
            return False
        # -1.0 for counter because Linky doesn't provide absolute counter value via Enedis website
        sValue = "-1.0;"+ str(usage) + ";"  + str(Date)
        self.myDebug("Mets dans la BDD la valeur " + sValue)
        Devices[self.iIndexUnit].Update(nValue=0, sValue=sValue, Type=self.iType, Subtype=self.iSubType, Switchtype=self.iSwitchType,)
        return True

    # Update value shown on Domoticz dashboard
    def updateDevice(self, usage):
        if not self.createDevice():
            return False
        # -1.0 for counter because Linky doesn't provide absolute counter value via Enedis website
        sValue="-1.0;"+ str(usage)
        self.myDebug("Mets sur le tableau de bord la valeur " + sValue)
        Devices[self.iIndexUnit].Update(nValue=0, sValue=sValue, Type=self.iType, Subtype=self.iSubType, Switchtype=self.iSwitchType)
        return True

    # Show error in state machine context
    def showStepError(self, hours, logMessage):
        if hours:
            Domoticz.Error(logMessage + " durant l'étape " + self.sConnectionStep + " de " + datetimeToEnderdisDateString(self.dateBeginHours) + " à " + datetimeToEnderdisDateString(self.dateEndHours))
        else:
            Domoticz.Error(logMessage + " durant l'étape " + self.sConnectionStep + " de " + datetimeToEnderdisDateString(self.dateBeginDays) + " à " + datetimeToEnderdisDateString(self.dateEndDays))

    
    def resetDayAccumulate(self, endDate):
        endDate = endDate.replace(hour=0, minute=0, second=0, microsecond=0)
        self.daysAccumulate = 0.0
        self.fdmonth = endDate.replace(day=1)
        self.ldpmonth = self.fdmonth - timedelta(days=1)
        self.fdpmonth = self.ldpmonth.replace(day=1)
        self.fdweek = endDate - timedelta(days=endDate.weekday())
        self.ldpweek = self.fdweek - timedelta(days=1)
        self.fdpweek = self.ldpweek - timedelta(days=6)
        self.fdyear = endDate.replace(day=1,month=1)
        
    def dayAccumulate(self, curDate, val):
        if self.sConsumptionType == "week":
            if (curDate >= self.fdweek):
                #Domoticz.Log(str(curDate) + " " + str(val))
                self.daysAccumulate = self.daysAccumulate + val
        elif self.sConsumptionType == "lweek":
            if (self.fdpweek <= curDate <= self.ldpweek):
                #Domoticz.Log(str(curDate) + " " + str(val))
                self.daysAccumulate = self.daysAccumulate + val
        elif self.sConsumptionType == "month":
            if (curDate >= self.fdmonth):
                #Domoticz.Log(str(curDate) + " " + str(val))
                self.daysAccumulate = self.daysAccumulate + val
        elif self.sConsumptionType == "lmonth":
            if (self.fdpmonth <= curDate <= self.ldpmonth):
                #Domoticz.Log(str(curDate) + " " + str(val))
                self.daysAccumulate = self.daysAccumulate + val
        elif self.sConsumptionType == "year":
            if (curDate >= self.fdyear):
                #Domoticz.Log(str(curDate) + " " + str(val))
                self.daysAccumulate = self.daysAccumulate + val
        else:
            self.daysAccumulate = val;
    
    # Grab days data inside received JSON data for history
    def exploreDataDays(self, Data, bLocalFirstMonths):
        self.dumpDictToLog(Data)
        if Data and "Data" in Data:
            try:
                dJson = json.loads(Data["Data"].decode())
            except ValueError as err:
                self.showStepError(False, "Les données reçues ne sont pas du JSON : " + str(err))
                return False
            except TypeError as err:
                self.showStepError(False, "Le type de données reçues n'est pas JSON : " + str(err))
                return False
            except:
                self.showStepError(False, "Erreur dans les données JSON : " + sys.exc_info()[0])
                return False
            else:
                if dJson and ("prodValueList" in dJson) and ("timestampsInterval" in dJson):
                    try:
                        self.myDebug("test1")
                        beginDate = datetime(*(time.localtime(dJson['timestampsInterval'][0])))
                        self.myDebug("test2")
                        endDate   = datetime(*(time.localtime(dJson['timestampsInterval'][1])))
                        self.myDebug("test3")
                    except ValueError as err:
                        self.showStepError(False, "Erreur dans le format de donnée de date JSON : " + str(err))
                        return False
                    except:
                        self.showStepError(False, "Erreur dans la donnée de date JSON : " + sys.exc_info()[0])
                        return False
                    for index,valeur in enumerate(dJson['prodValueList']):
                        try:
                            val = float(valeur) * 1000.0
                        except:
                            val = -1.0
                        if (val >= 0.0):
                            curDate = beginDate + timedelta(days=index)
                            self.dayAccumulate(curDate, val)
                            if not self.createAndAddToDevice(val, datetimeToSQLDateString(curDate)):
                                return False
                            # If we are on the most recent batch and end date, use the mose recent data for Domoticz dashboard
                            if bLocalFirstMonths and (curDate == endDate):
                                bLocalFirstMonths = False
                                if not self.updateDevice(self.daysAccumulate):
                                    return False
                    return True
                else:
                    self.showStepError(False, "Erreur à la réception de données JSON")
        else:
            self.showStepError(False, "Aucune donnée reçue")
        return False

    # Calculate days and date left for next batch
    def calculateDaysLeft(self):
        # No more than 28 days at once
        self.iDaysLeft = self.iDaysLeft - 28
        if self.iDaysLeft <= 0:
            daysToGet = self.iDaysLeft + 28
        else:
            daysToGet = 28
        self.dateBeginDays = self.savedDateEndDays - timedelta(days=daysToGet+2)
        self.dateEndDays = self.savedDateEndDays - timedelta(days=1)
        self.savedDateEndDays = self.dateBeginDays

    # Calculate next complete grab, for tomorrow between 5 and 6 am if tomorrow is true, for next hour otherwise
    def setNextConnection(self, tomorrow):
        if tomorrow:
            self.nextConnection = datetime.now() + timedelta(days=1)
            self.nextConnection = self.nextConnection.replace(hour=5)
        else:
            self.nextConnection = datetime.now() + timedelta(hours = 1)
        # Randomize minutes to lower load on Enedis website
        #randint makes domoticz crash on RPI
        #self.nextConnection = self.nextConnection + timedelta(minutes=randint(0, 59), seconds=randint(0, 59))
        # We take microseconds to randomize
        minutesRand = round(datetime.now().microsecond / 10000) % 60
        self.nextConnection = self.nextConnection + timedelta(minutes=minutesRand)

    # Handle the connection state machine
    def handleConnection(self, Data = None):
        # First and last step
        if self.sConnectionStep == "idle":
            Domoticz.Log("Récupération des données...")
            # Reset failed state
            self.bHasAFail = False
            if self.httpConn and self.httpConn.Connected():
                self.httpConn.Disconnect()

            self.httpConn = Domoticz.Connection(Name="HTTPS connection", Transport="TCP/IP", Protocol="HTTPS", Address=LOGIN_BASE_URI, Port=BASE_PORT)

            self.myDebug("Connect")
            self.sConnectionStep = "logconnecting"
            self.httpConn.Connect()

        # Connected, we need to log in
        elif self.sConnectionStep == "logconnecting":
            if not self.httpConn.Connected():
                Domoticz.Error("Connexion échouée au login")
                self.sConnectionStep = "idle"
                self.bHasAFail = True
            else:
                self.sConnectionStep = "logconnected"
                self.login(self.sUser, self.sPassword)
                
        # Connected, check that the authentication cookie has been received
        elif self.sConnectionStep == "logconnected":
            if self.httpConn and self.httpConn.Connected():
                self.httpConn.Disconnect()
            self.dumpDictToLog(Data)
            
            # Grab cookies from received data, if we have "iPlanetDirectoryPro", we're good
            self.getCookies(Data)
            if ("iPlanetDirectoryPro" in self.dCookies) and self.dCookies["iPlanetDirectoryPro"]:
                # Proceed to data page
                self.sConnectionStep = "getcookies"
                self.httpConn = Domoticz.Connection(Name="HTTPS connection", Transport="TCP/IP", Protocol="HTTPS", Address=API_BASE_URI, Port=BASE_PORT)
                self.httpConn.Connect()
            else:
                Domoticz.Error("Login échoué, réessaiera plus tard")
                self.sConnectionStep = "idle"
                self.bHasAFail = True

        # If we are connected, we must show the authentication cookie
        elif self.sConnectionStep == "getcookies":
            if not self.httpConn.Connected():
                Domoticz.Error("Connexion échouée à la lecture des cookies")
                self.sConnectionStep = "idle"
                self.bHasAFail = True
            else:
                self.getCookies(Data)
                self.sConnectionStep = "dataconnecting"
                # Dummy action to show that we have the authentication cookie
                self.getData("urlCdcJour", self.dateBeginDays, self.dateEndDays)

        # We are now connected to data page, ask for hours data
        elif self.sConnectionStep == "dataconnecting" or self.sConnectionStep == "dataconnecting2":
            if not self.httpConn.Connected():
                Domoticz.Error("Connexion échouée à la réception des premières données")
                self.sConnectionStep = "idle"
                self.bHasAFail = True
            else:
                self.getCookies(Data)
                strData = ""
                if Data and ("Data" in Data):
                    strData = Data["Data"].decode();
                if "terms_of_use" in strData:
                    if self.bAutoAcceptTerms:
                        Domoticz.Status("Auto-accepting new terms of use")
                        self.acceptTerms()
                        self.sConnectionStep = "dataconnecting"
                    else:
                        Domoticz.Error("Vous devez acceptez les conditions d'utilisation en vous rendant sur https://"  + LOGIN_BASE_URI)
                        self.sConnectionStep = "idle"
                        self.bHasAFail = True
                else:
                    self.dumpDictToLog(Data)
                    # Dummy action again to show that we have the authentication cookie
                    if self.sConnectionStep == "dataconnecting":
                        self.sConnectionStep = "dataconnecting2"
                    else:
                        self.sConnectionStep = "getdatadays"
                        self.bFirstMonths = True
                        self.resetDayAccumulate(self.dateEndDays)
                    # Ask data for days
                    self.getData("urlCdcJour", self.dateBeginDays, self.dateEndDays)
                
        # Now we should received data for real
        elif self.sConnectionStep == "getdatadays":
            if not self.httpConn.Connected():
                self.showStepError(False, "Récupération des données pour la vue par jours")
                self.sConnectionStep = "idle"
                self.bHasAFail = True
            else:
                # Analyse data for days
                if not self.exploreDataDays(Data, self.bFirstMonths):
                    self.bHasAFail = True
                if self.iDaysLeft > 0:
                    self.calculateDaysLeft()
                    self.bFirstMonths = False
                    self.sConnectionStep = "getdatadays"
                    self.getData("urlCdcJour", self.dateBeginDays, self.dateEndDays)
                else:
                    self.sConnectionStep = "idle"
                    Domoticz.Log("Done")
                
        # Next connection time depends on success
        if self.sConnectionStep == "idle":
            if self.bHasAFail:
                self.setNextConnection(False)            
            Domoticz.Log("Prochaine connexion : " + datetimeToSQLDateTimeString(self.nextConnection))

    def dumpDictToLog(self, dictToLog):
        if self.iDebugLevel:
            if isinstance(dictToLog, dict):
                self.myDebug("Dict details ("+str(len(dictToLog))+"):")
                for x in dictToLog:
                    if isinstance(dictToLog[x], dict):
                        self.myDebug("--->'"+x+" ("+str(len(dictToLog[x]))+"):")
                        for y in dictToLog[x]:
                            if isinstance(dictToLog[x][y], dict):
                                for z in dictToLog[x][y]:
                                    self.myDebug("----------->'" + z + "':'" + str(dictToLog[x][y][z]) + "'")
                            else:
                                self.myDebug("------->'" + y + "':'" + str(dictToLog[x][y]) + "'")
                    else:
                        self.myDebug("--->'" + x + "':'" + str(dictToLog[x]) + "'")
            else:
                self.myDebug("Received no dict: " + str(dictToLog))
                        
    def onStart(self):
        self.myDebug("onStart called")
        
        Domoticz.Log("Ce plugin est compatible avec Domoticz version 3.9517 et plus récent, mais la vue par heure peut ne pas fonctionner avec la version 4.9700")
        
        self.sUser = Parameters["Username"]
        self.sPassword = Parameters["Password"]
        self.iHistoryDaysForHoursView = 0
        self.iHistoryDaysForDaysView = Parameters["Mode2"]
        self.bAutoAcceptTerms = Parameters["Mode4"] == "True"
        self.sConsumptionType = Parameters["Mode5"]
        try:
            self.iDebugLevel = int(Parameters["Mode3"])
        except ValueError:
            self.iDebugLevel = 0
    
        if self.iDebugLevel > 1:
            Domoticz.Debugging(1)

        # History for short log is 7 days max (default to 7)
        try:
            self.iHistoryDaysForHoursView = int(self.iHistoryDaysForHoursView)
        except:
            self.iHistoryDaysForHoursView = 7
        if self.iHistoryDaysForHoursView < 0:
            self.iHistoryDaysForHoursView = 0
        elif self.iHistoryDaysForHoursView > 7:
            self.iHistoryDaysForHoursView = 7
            
        # History for short log is 7 days max (default to 366)
        try:
            self.iHistoryDaysForDaysView = int(self.iHistoryDaysForDaysView)
        except:
            self.iHistoryDaysForDaysView = 366
        if self.iHistoryDaysForDaysView < 28:
            self.iHistoryDaysForDaysView = 28
        elif self.iHistoryDaysForDaysView > 100000:
            self.iHistoryDaysForDaysView = 100000

        if (self.sConsumptionType == "month") and (self.iHistoryDaysForDaysView < 32) :
            self.iHistoryDaysForDaysView = 32

        if (self.sConsumptionType == "lmonth") and (self.iHistoryDaysForDaysView < 63) :
            self.iHistoryDaysForDaysView = 63

        if (self.sConsumptionType == "year") and (self.iHistoryDaysForDaysView < 366) :
            self.iHistoryDaysForDaysView = 366

        Domoticz.Log("Adresse e-mail mise à " + self.sUser)
        if self.sPassword:
            Domoticz.Log("Mot de passe entré")
        else:
            Domoticz.Log("Mot de passe laissé vide")
        Domoticz.Log("Production à montrer sur le tableau de bord mis à " + self.sConsumptionType)
        Domoticz.Log("Accepter automatiquement les conditions d'utilisation mis à " + str(self.bAutoAcceptTerms))
        Domoticz.Log("Nombre de jours à récupérer pour la vue par heures mis à " + str(self.iHistoryDaysForHoursView))
        Domoticz.Log("Nombre de jours à récupérer pour les autres vues mis à " + str(self.iHistoryDaysForDaysView))
        Domoticz.Log("Debug mis à " + str(self.iDebugLevel))
        
        # most init
        self.__init__()

        Domoticz.Log("Si vous ne voyez pas assez de données dans la vue par heures, augmentez le paramètre Log des capteurs qui se trouve dans Réglages / Paramètres / Historique des logs")
        
        if self.createDevice():
            self.nextConnection = datetime.now()
        else:
            self.setNextConnection(False)            
        
        # Now we can enabling the plugin
        self.isStarted = True

    def onStop(self):
        Domoticz.Debug("onStop called")
        # prevent error messages during disabling plugin
        self.isStarted = False

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called")
        if self.isStarted and (Connection == self.httpConn):
            self.handleConnection()

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")
        
        # if started and not stopping
        if self.isStarted and (Connection == self.httpConn):
            self.handleConnection(Data)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called")
        
    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat() called")
        
        if datetime.now() > self.nextConnection:
            self.savedDateEndDays = self.nextConnection
            # We immediatly program next connection for tomorrow, if there is a problem, we will reprogram it sooner
            self.setNextConnection(True)

            self.dateBeginHours = self.savedDateEndDays - timedelta(days=(self.iHistoryDaysForHoursView + 1))
            self.dateEndHours = self.savedDateEndDays

            self.iDaysLeft = self.iHistoryDaysForDaysView
            self.calculateDaysLeft()
            self.handleConnection()

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onDeviceAdded(Unit):
    global _plugin

def onDeviceModified(Unit):
    global _plugin

def onDeviceRemoved(Unit):
    global _plugin

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def dictToQuotedString(dParams):
    result = ""
    for sKey, sValue in dParams.items():
        if result:
            result += "&"
        result += sKey + "=" + quote(str(sValue))
    return result

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            self.myDebug( "'" + x + "':'" + str(Parameters[x]) + "'")
    self.myDebug("Device count: " + str(len(Devices)))
    for x in Devices:
        self.myDebug("Device:           " + str(x) + " - " + str(Devices[x]))
        self.myDebug("Device ID:       '" + str(Devices[x].ID) + "'")
        self.myDebug("Device Name:     '" + Devices[x].Name + "'")
        self.myDebug("Device iValue:    " + str(Devices[x].iValue))
        self.myDebug("Device sValue:   '" + Devices[x].sValue + "'")
        self.myDebug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

# Convert Enedis date string to datetime object
def enerdisDateToDatetime(datetimeStr):
    #Buggy
    #return datetime.strptime(datetimeStr, dateFormat)
    #Not buggy
    return datetime(*(time.strptime(datetimeStr, "%d/%m/%Y")[0:6]))

# Convert datetime object to Enedis date string
def datetimeToEnderdisDateString(datetimeObj):
    return datetimeObj.strftime("%d/%m/%Y")

# Convert datetime object to Domoticz date string
def datetimeToSQLDateString(datetimeObj):
    return datetimeObj.strftime("%Y-%m-%d")

# Convert datetime object to Domoticz date and time string
def datetimeToSQLDateTimeString(datetimeObj):
    return datetimeObj.strftime("%Y-%m-%d %H:%M:%S")
