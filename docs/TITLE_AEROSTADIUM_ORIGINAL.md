# Écran titre original AeroStadium 2 — 28 septembre 2026

L'utilisateur a rejeté la restauration neuronale de l'ancien fond pour ses
déformations. Il a ensuite demandé **une illustration originale propre au
portage, uniquement avec des Pokémon introduits en deuxième génération**,
puis **un logo AeroStadium 2 reprenant le style de l'ancien avec la même qualité
que le nouveau fond**. Ces demandes autorisent le changement de composition
de cet écran. Le reste de la charte reste applicable : runtime gelé, interface
seule, aucune modification de géométrie/jeu/renderer.

## Artwork et logo

Les deux créations utilisent l'outil imagegen intégré (pas l'API/CLI).
Le refus du premier essai de restauration de l'ancien fond ne concerne pas
ces créations originales, qui ont abouti normalement.

- Fond : stade de Johto, Germignon, Héricendre, Kaiminus, Pharamp, Scarhino,
  Mentali, Noctali, Lugia et Ho-Oh. Aucun Pokémon d'une autre génération.
- Logo : AERO doré/bleu, STADIUM rouge en relief, 2 sur médaillon métallique,
  contour blanc et noir, fond réellement transparent.
- Prompts exacts : `TITLE_JOHTO_ORIGINAL_PROMPT.txt` et
  `TITLE_AEROSTADIUM_LOGO_PROMPT.txt` dans ce dossier.
- Sortie native du service : fond **1448×1086**, logo **1737×905**.
  Ne pas les présenter comme des sorties natives 1440p.
- Masters exportés : fond **1920×1440**, logo **2256×1176**. Lanczos pour le
  dimensionnement, alpha prémultiplié pour le logo, sans recadrage ni étirement.
- Les pixels totalement transparents du logo ont un RGB nul. Export sRGB.

Hashes SHA-256 des masters :

```text
Fond : 2fbcdb58e76def3121fb725791a53aec636bb441d18dc7a5457f7e5e4518a0a2
Logo : f23e0e0309cbfe4a2f28f3832ed1d86519819936264f7d573cd374a1794b4323
```

## Pack et correction des raccords

Le pack final contient **349 entrées uniques** : 300 tuiles de fond 96×96,
et 49 bandes de logo 2256×24. Chaque master est réassemblé pixel par pixel
après découpage ; alpha inclus, la comparaison est strictement identique.

**Utiliser `defaultShift: "none"` pour ces assets.** Le réglage précédent
`half` créait des discontinuités aux raccords du fond, particulièrement
visibles sur l'œil de Kaiminus et les contours de Germignon. La comparaison
avec le master puis le test A/B du pack démontre leur disparition avec
`none`. C'est uniquement un réglage JSON du pack, sans patch runtime.
Ne pas généraliser automatiquement ce choix aux autres assets/scènes.

Le logo HD et sa transparence sont observés dans le jeu avec ce réglage,
superposés au nouveau fond. Le texte d'interface et les mentions d'origine
ne font pas partie de ce lot.

## Reproduction

Pillow est nécessaire aux exports ; NumPy est utilisé pour l'alpha du logo.
Les deux images créées et la ROM/dump source restent locales.

```powershell
python tools/graphics/export_np3f_background_master.py --source generated-background.png --output johto-original-v1
python tools/graphics/export_np3f_logo_master.py --source generated-logo.png --output aerostadium-v1
python tools/graphics/build_np3f_background_pack.py --dump-zip build/rt64-test-userdata/NP3F_texture_dumps.zip --master johto-original-v1/title-background-1920x1440.png --logo aerostadium-v1/aerostadium-2-logo-2256x1176.png --output rt64-title-aerostadium-v1 --shift none
```

Les sorties existantes sont refusées pour préserver les versions précédentes.
Le générateur réutilise le mapping vérifié de `build_np3f_title_pack_from_dump.py`.

## Installation et retour arrière

Dans le projet local Downloads :

```text
build/np3f/graphics-workbench/title-background/johto-original-v1/
build/np3f/graphics-workbench/title-logo/aerostadium-v1/
build/np3f/graphics-workbench/rt64-title-aerostadium-v1/
```

`build/rt64-test-userdata/graphics.ini` pointe vers le dernier dossier via
`texture_pack`. Le plein écran 1440p/4:3 et MSAA 4 sont conservés.

Sauvegardes dans le même dossier que `graphics.ini` :

- `graphics.ini.before-title-aerostadium-v1-20260928` : fond Johto avec ancien logo.
- `graphics.ini.before-title-johto-original-v1-20260928` : ancien fond v1.
- `graphics.ini.before-title-background-v1-20260928` : réglages initiaux.

EXE inchangé, aucun rebuild :
`AB2AB13B121B24993A060003BC4074AFB7FFB4FF4AC83AD29F213C223B7745E9`.

## Limites de validation

Les captures prouvent le remplacement au titre, l'alpha et les raccords.
Le résultat précis des probes est consigné dans `LastProgressLogs.md`.
Pack fond + logo : probe `20260928-005953-090`, demandé pour 120 s, fermeture
demandée après environ 20,37 s, exit 0. Le visuel est vérifié, les 120 s ne
sont pas validées. Le probe fond seul `20260928-005257-712` atteignait
environ 101 s avant l'arrêt combat préexistant. Le test de raccords
`20260928-005554-147` était demandé pour 30 s, fermeture vers 14,77 s, exit 0.
Ne pas déduire 120 secondes réussies du paramètre `seconds: 120` : un arrêt
anticipé est possible, notamment l'erreur combat préexistante `0x80263890`.
L'utilisateur a explicitement refusé sa correction pour ce chantier.

Les assets, captures, ROM, dumps, modèles neuronaux et binaires ne sont pas
publiés avec ces outils/documents. Leur état local et les prompts permettent
la reprise sans annoncer comme acceptée une version rejetée.
