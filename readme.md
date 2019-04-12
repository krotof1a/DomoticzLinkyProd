# Plugin Linky pour Domoticz

Ceci est un plugin pour [Domoticz](https://domoticz.com), récupérant les données de production Linky. Les données sont collectées du compte utilisateur [Enedis](http://www.enedis.fr) et stockées dans le log d'un dispositif compteur électrique.


## Prérequis

Vous devez avoir un compteur Linky, créer un compte utilisateur sur [Enedis](http://www.enedis.fr), accepter les conditions d'utilisation et vérifier que vous visualisez bien les courbes sur le site. Les données peuvent ne pas être disponibles après l'installation ou l'activation de Linky, soyez patient et vérifiez que vous recevez les données sur le site [Enedis](http://www.enedis.fr) avant de rejetter la faute sur le plugin.

## Installation

Copiez plugin.py dans le sous-répertoire plugins/DomoticzLinkyProd de Domoticz ou placez vous dans le sous répertoire plugins de Domoticz and tapez la commande suivante :

```
git clone https://github.com/krotof1a/DomoticzLinkyProd
```

Pour mettre à jour, écrasez plugin.py placez vous dans le sous répertoire plugins de Domoticz and tapez la commande suivante :
```
git pull
```

Donnez la permission d'exécution si vous êtes sous Linux :
```
chmod ugo+x plugin.py
```

Redémarrez Domoticz.

## Configuration

A la première installation, commencez par vérifier dans les paramètres de Domoticz que "Accepter de nouveaux dispositifs matériels" est activé au moins temporairement (Réglages / Paramètres / Système / Matériel/dispositifs).

Ajoutez le matériel Linky dans l'onglet de configuration Réglages / Matériel, en mettant l'adresse e-mail et le mot de passe de votre compte Enedis. Vous pouvez choisir le nombre de jours à récupérer pour les autres vues. 

Après avoir activé le matériel, vous devriez avoir un nouveau dispositif Linky dans l'onglet Mesures, et vous devriez pouvoir visualiser les courbes de production via le bouton Log de ce dispositif.

A partir de la version 1.0.9, le plugin a une option permettant de choisir si vous voulez afficher sur le tableau de bord la production de la veille, de la semaine en cours, de la semaine dernière, du mois en cours, du mois dernier, ou de l'année.

## Auteurs

* **Baptiste Candellier** - *Kindle Linky plugin* - [linkindle](https://github.com/outadoc/linkindle)
* **Asdepique777** - *Jeedom Linky plugin* - [jeedom_linky](https://github.com/Asdepique777/jeedom_linky)
* **epierre** - *Linky external script for Domoticz* - [domoticz_linky](https://github.com/empierre/domoticz_linky)
* **Guillaume Zin** - *Port to Domoticz plugin framework* - [DomoticzLinky](https://github.com/guillaumezin/DomoticzLinky)
* **krotof1a** - *Adapt for production side* - [DomoticzLinkyProd](https://github.com/krotof1a/DomoticzLinkyProd)

See also the list of [contributors](https://github.com/guillaumezin/DomoticzLinky/contributors) who participated in this project.

## Licence

Ce projet est sous licence GPLv3 - cf. fichier [LICENSE](LICENSE) pour plus de détails.

## Remerciements

* Baptiste Candellier
* Asdepique777
* empierre
* Domoticz team
