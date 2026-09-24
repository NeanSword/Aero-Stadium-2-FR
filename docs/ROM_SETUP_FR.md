# Préparer la ROM française NP3F

Le projet nécessite une copie locale de la ROM française de Pokémon Stadium 2 correspondant à la région NP3F.

## 1. Utiliser sa propre copie légale

Le dépôt ne fournit pas la ROM.

Utilise uniquement une copie dont tu disposes légalement. Pour créer ton fichier de travail, effectue un dump de ta propre cartouche avec ton matériel de sauvegarde autorisé et suis sa documentation pour exporter l'image brute.

Respecte les règles applicables dans ton pays concernant les copies de sauvegarde et l'utilisation de ton matériel.

## 2. Obtenir le fichier baserom.z64

Le projet attend :

    baseroms/fr/baserom.z64

Le nom Z64 correspond ici à l'ordre d'octets big-endian utilisé comme représentation de travail.

Le dépôt fournit un outil de conversion pour les dumps N64 courants. Exemple PowerShell :

    .\windows\convert_to_z64.ps1 -SourceRom "C:\chemin\vers\ton_dump.v64"

La destination par défaut sera automatiquement :

    baseroms/fr/baserom.z64

Ne renomme pas une ROM d'une autre région en baserom.z64 : la région doit réellement être NP3F.

## 3. Vérifier le dump

Depuis la racine du dépôt :

    .\windows\verify_np3f.ps1

ou :

    python tools/verify_np3f_rom.py baseroms/fr/baserom.z64

Le vérificateur normalise automatiquement l'ordre des octets avant de calculer les hashes.

Valeurs attendues :

- Taille : 67 108 864 octets
- MD5 : 4748d96916ae2bcc5fc1630515ee2561
- SHA-1 : d7e13535b671024a92822db01507e87bd42f68ec
- SHA-256 : b661d92a94eb3c7a00cd27acc1e93d1e52299bf85a76397ee38e998a84af68ea

## 4. Confidentialité du dump

Ne commit pas baseroms/fr/baserom.z64.

Le fichier est volontairement ignoré par .gitignore et doit rester sur ta machine locale.

## 5. Résultat attendu

    Aero-Stadium-2-FR/
    ├── baseroms/
    │   └── fr/
    │       ├── baserom.z64        # local uniquement
    │       └── checksum.md5
    └── ...

Les étapes suivantes utiliseront ce fichier local sans le publier dans le dépôt.
