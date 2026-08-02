# Backup Scripts (SSH)

Script Python modulaire pour:
- se connecter en SSH,
- exécuter une commande distante optionnelle,
- récupérer le dernier fichier modifié d'un répertoire distant,
- télécharger ce fichier en local,
- produire un rapport d'exécution (`report.json`).

## Fonctionnement

Le flux d'exécution est le suivant:
1. Chargement des variables depuis `.env`.
2. Connexion SSH sécurisée (mot de passe ou clé privée).
3. Si `REMOTE_COMMAND` est défini:
	1. création d'un marqueur temporel distant,
	2. exécution de la commande,
	3. recherche du dernier fichier modifié après ce marqueur.
4. Si aucun fichier n'est trouvé après commande, fallback sur le dernier fichier global du répertoire.
5. Téléchargement en local dans un dossier de run horodaté.
6. Génération du rapport JSON.

## Arborescence

- [backup_scripts/main.py](main.py): point d'entrée.
- [backup_scripts/config.py](config.py): chargement/validation des variables `.env`.
- [backup_scripts/modules/ssh_connection.py](modules/ssh_connection.py): connexion SSH + exécution de commandes.
- [backup_scripts/modules/remote_files.py](modules/remote_files.py): logique marqueur, commande distante, recherche du dernier fichier.
- [backup_scripts/modules/transfer.py](modules/transfer.py): téléchargement SFTP.
- [backup_scripts/.env.example](.env.example): exemple de configuration.

## Prérequis

1. Python 3.10+.
2. Dépendances Python:
	1. `paramiko`
	2. `python-dotenv`

Installation rapide:

```bash
pip install paramiko python-dotenv
```

## Configuration `.env`

1. Copier [backup_scripts/.env.example](.env.example) vers `.env` (dans `backup_scripts`).
2. Renseigner au minimum:
	1. `SSH_HOST`
	2. `SSH_USER`
	3. `REMOTE_DIR`
	4. `SSH_PASSWORD` ou `SSH_KEY_PATH`

Variables principales:

- `SSH_HOST`: hôte distant.
- `SSH_PORT`: port SSH (défaut `22`).
- `SSH_USER`: utilisateur SSH.
- `SSH_PASSWORD`: mot de passe (optionnel si clé).
- `SSH_KEY_PATH`: chemin de clé privée (optionnel si mot de passe).
- `SSH_KEY_PASSPHRASE`: passphrase de la clé (optionnel).
- `SSH_KNOWN_HOSTS`: fichier known_hosts local.
- `STRICT_HOST_KEY_CHECKING`: `true/false`.
- `REMOTE_DIR`: répertoire distant cible.
- `REMOTE_COMMAND`: commande distante optionnelle.
- `FILE_PATTERNS`: filtres de fichiers, séparés par virgule (ex: `*.log,*.txt`).
- `LOCAL_OUTPUT_DIR`: dossier local de sortie.

## Exécution

Important: les imports actuels utilisent le package `backup_scripts.modules`, donc lancez le script depuis la racine du projet.

Depuis `/Users/zantoine/dev_project/GNOC_MOOV_PROJECT`:

```bash
python -m backup_scripts.main
```

## Sortie

Chaque run crée un dossier:

```text
<LOCAL_OUTPUT_DIR>/run_YYYYMMDD_HHMMSS/
```

Avec:
- fichier téléchargé,
- `report.json` contenant:
  - paramètres de run,
  - résultat de commande distante (si exécutée),
  - fichier sélectionné,
  - chemin local téléchargé,
  - timestamps de début/fin,
  - erreur éventuelle.

## Dépannage rapide

1. `No file found in remote directory with current filters`:
	1. vérifier `REMOTE_DIR`.
	2. vérifier `FILE_PATTERNS`.
	3. tester sans `FILE_PATTERNS`.
2. `Remote command failed`:
	1. tester la commande en SSH manuel.
	2. vérifier les droits dans `REMOTE_DIR`.
3. Erreurs de clé SSH:
	1. vérifier `SSH_KNOWN_HOSTS`.
	2. mettre `STRICT_HOST_KEY_CHECKING=false` temporairement pour diagnostic.
