# Préparer la ROM française NP3F

Le projet nécessite une copie locale de la ROM française de Pokémon Stadium 2 correspondant à la région **NP3F**.

## 1. Utiliser sa propre copie légale

Le dépôt ne fournit pas la ROM.

Utilise uniquement une copie dont tu disposes légalement. Pour créer ton fichier de travail, effectue un dump de ta propre cartouche avec ton matériel de sauvegarde autorisé et exporte une image brute de la cartouche.

Respecte les règles applicables dans ton pays concernant les copies de sauvegarde et l'utilisation de ton matériel.

## 2. Obtenir le fichier baserom.z64

L'objectif est d'obtenir une image ROM brute correspondant exactement à la version française NP3F.

Le fichier attendu par le projet est :

    baseroms/fr/baserom.z64

Le projet utilise l'ordre d'octets Z64 / big-endian. Si ton matériel produit un dump dans un autre ordre N64, convertis-le vers cet ordre avant de le placer dans le dossier baseroms/fr/.

Ne renomme pas une ROM d'une autre région en baserom.z64 : la région doit réellement être NP3F.

## 3. Vérifier le dump

Depuis la racine du dépôt :

    python tools/verify_np3f_rom.py baseroms/fr/baserom.z64

Les valeurs attendues sont :

- Taille : 67 108 864 octets
- MD5 : 4748d96916ae2bcc5fc1630515ee2561
- SHA-1 : d7e13535b671024a92822db01507e87bd42f68ec
- SHA-256 : b661d92a94eb3c7a00cd27acc1e93d1e52299bf85a76397ee38e998a84af68ea

Le hash est une vérification d'identité du dump. Il ne permet pas de reconstruire la ROM.

## 4. Confidentialité du dump

Ne commit pas baseroms/fr/baserom.z64.

Le fichier est volontairement ignoré par .gitignore. Il doit rester sur ta machine locale.

## 5. Résultat attendu

    Aero-Stadium-2-FR/
    ├── baseroms/
    │   └── fr/
    │       ├── baserom.z64        # local uniquement
    │       └── checksum.md5
    └── ...

Les étapes suivantes du développement utiliseront ce fichier local sans le publier dans le dépôt.
