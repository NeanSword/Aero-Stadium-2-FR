# Aero-Stadium-2-FR

Reconstruction et futur portage Windows natif de **Pokémon Stadium 2 – région française NP3F**.

## Ce dépôt

Le projet sépare volontairement trois couches :

1. **reconstruction NP3F** : retrouver une représentation exploitable du binaire français ;
2. **recompilation native** : produire du C/C++ natif à partir de métadonnées/ELF stables ;
3. **runtime Windows moderne** : entrées, audio, rendu et cadence de présentation indépendants de la logique de jeu.

La reconstruction publique de référence est [pret/pokestadiumgs](https://github.com/pret/pokestadiumgs), incluse ici comme sous-module et épinglée sur le commit utilisé pendant notre analyse NP3F.

## ROM française requise

La ROM française n'est pas distribuée dans ce dépôt.

Tu dois fournir **ta propre copie légale** de la région NP3F et la placer localement ici :

    baseroms/fr/baserom.z64

Consulte [docs/ROM_SETUP_FR.md](docs/ROM_SETUP_FR.md) pour la procédure et les vérifications.

Le dump est volontairement ignoré par Git.

## Mise en place

Après clonage :

    git submodule update --init --recursive

Puis, avec Python installé :

    python tools/verify_np3f_rom.py baseroms/fr/baserom.z64

Pour une vérification Windows :

    .\windows\verify_np3f.ps1

## Outils NP3F

Comparer deux ROMs après normalisation automatique de l'ordre des octets :

    python tools/np3f/compare_roms.py chemin\vers\us.n64 chemin\vers\fr.v64 --min-run 4096

Relocaliser un offset US lorsque le fragment concerné est connu :

    python tools/np3f/relocate_offset.py 31 0x0277B4

Les deltas actuellement connus sont documentés dans [config/np3f_fragments.json](config/np3f_fragments.json).

## État actuel

La carte ROM NP3F est maintenant figée dans `yamls/fr/splat.yaml` comme layout canonique vérifié.

- 88/88 en-têtes de fragments correspondent aux signatures `FRAGMENT` observées directement dans NP3F ;
- 335/335 frontières de code soutenues par des ancres directes NP3E↔NP3F correspondent au layout canonique ;
- 15 frontières supplémentaires ont été vérifiées explicitement par comparaison binaire ;
- aucune frontière de code ne reste non résolue dans le validateur de layout.

Le fichier `yamls/fr/splat.seed.yaml` conserve l'ancien layout de reconstruction. Les outils de relocation utilisent ce seed historique afin de pouvoir reproduire l'analyse sans appliquer deux fois les deltas.

Les VRAM marquées `guessed` dans `config/np3f_fragments.json` restent, elles, à valider indépendamment.

Voir [docs/NP3F_MAPPING.md](docs/NP3F_MAPPING.md).

## Windows

Le dépôt upstream actuel utilise un Makefile qui rejette explicitement les builds natifs Windows. Aero-Stadium-2-FR conserve donc son propre workflow Windows au lieu de masquer cette différence derrière des scripts fragiles.

Le but final est une application Windows x64 native ; la reconstruction N64 et la couche de runtime restent des étapes séparées.

## Règles de dépôt

Les ROMs complètes, dumps et sorties binaires générées à partir de la copie personnelle de l'utilisateur ne sont pas stockés dans Git.

Le dépôt contient le code, les outils, les métadonnées, les cartes de relocation et la documentation nécessaires au développement.

## Licence et ayants droit

Les fichiers du projet upstream restent soumis à leurs conditions propres via le sous-module. Pokémon Stadium 2 et ses éléments originaux restent la propriété de leurs ayants droit.
