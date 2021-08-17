# timetracking-enhanced

Pour que ça marche 👀

Prérequis:

- Aller sur https://id.atlassian.com/manage-profile/security/api-tokens pour créer un token api Jira
- Remplir le fichier de config avec votre username jira (adresse mail), votre token de l'étape 1 et remplacez '0' par votre nombre d'HEURES pour chaque tâche (ex: `"timePerDay": { "ONE-6652": 0, "ONE-6653": 0, "ONE-6654": 8, "ONE-6657": 0.5, "ONE-6658": 0 }`
- Installer requests `python3 -m pip install requests`

Usage:

`./timetracking.py` => Remplit les heures pour la semaine courante du lundi au vendredi peu importe quel jour vous lancez le script

pour l'utiliser en cronjob `./timetracking.py --setup` et suivre les instructions

pour afficher l'ensemble des commandes disponible : `./timetracking.py --help`

le script utilise `timeOffPerIssue` pour les vacances contribués sur le calendar confluence :heavy_check_mark: (default 8h en off)

Enjoy :rocket:
