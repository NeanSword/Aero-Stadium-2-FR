# Outillage de développement

## Normalisation ROM

`tools/np3f/n64rom.py` détecte les trois ordres N64 courants :

- Z64 / big-endian ;
- V64 / byte-swapped 16 bits ;
- N64 / little-endian 32 bits.

Les outils d'analyse utilisent automatiquement la représentation Z64 en mémoire afin que les comparaisons US/FR ne dépendent pas du format du dump fourni.

## Comparaison US / FR

`tools/np3f/compare_roms.py` compare deux images de même taille et peut exporter les grandes zones identiques en JSON/CSV.

Cette sortie est utile pour :

- retrouver des zones de code identiques malgré les décalages ;
- repérer les changements de localisation ;
- produire des ancres pour de futures correspondances de symboles.

Le seuil par défaut est de 4096 octets.

## Relocation des fragments

`config/np3f_fragments.json` contient les deltas ROM établis pour les 88 fragments analysés.

`tools/np3f/relocate_offset.py` applique un delta à un offset de référence lorsqu'on connaît le fragment.

Exemple :

    python tools/np3f/relocate_offset.py 88 0x0434720

Le résultat est un **candidat de position française** et ne constitue pas une preuve de correspondance de code.

## Vérification

Les outils sont testés par GitHub Actions au niveau syntaxique et configuration. La présence d'une ROM n'est pas requise pour la CI publique.
