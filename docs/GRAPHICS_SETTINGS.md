# Réglages graphiques Aero Stadium 2

Cette branche ajoute une couche graphique Aero au-dessus de RT64 sans modifier la logique NP3F.

## Point de retour stable

L'état stable validé 180 secondes est conservé dans :

```text
checkpoint/stable-runtime-180s-2026-09-27
8c537b748578ea2f600c74e669946965886262a7
```

Les expérimentations graphiques sont séparées dans `feature/graphics-quality`.

## Fichier graphics.ini

Au premier lancement, Aero crée :

```text
%LOCALAPPDATA%\AeroStadium2\graphics.ini
```

Les probes utilisant `--data-dir` reçoivent leur propre fichier dans ce dossier de test.

Réglages disponibles :

```ini
preset=1440p
msaa=4
upscale_2d=all
filtering=antialiased
three_point_filtering=true
color=high
buffering=triple
aspect=original
fullscreen=false
window_width=1280
window_height=960
texture_replacements=true
texture_pack=textures
dump_textures=false
texture_dump_dir=texture_dumps
```

### Presets de résolution

- `original` : 1x / hauteur N64 de référence 240 px.
- `1080p` : 4,5x.
- `1440p` : 6x, preset par défaut.
- `4k` : 9x / 2160p.

Le rendu reste en 4:3 par défaut afin de ne pas étirer les menus et les images. `aspect=expand` ou `aspect=16:9` peuvent être testés séparément.

## Amélioration 2D et texte

`upscale_2d=all` demande à RT64 de rendre les rectangles 2D à l'échelle haute résolution. Cela améliore les menus, HUD, éléments de texte et écrans 2D dans la limite de la résolution de leurs textures sources.

`filtering=antialiased` utilise le filtre de présentation anti-aliased pixel scaling de RT64.

Pour qu'une image basse résolution (par exemple le fond de l'écran titre) ou une police bitmap gagne de **vrais détails supplémentaires**, il faut fournir une texture HD de remplacement.

## Texture pack HD

RT64 sait remplacer les textures à partir d'un dossier ou pack. Aero réserve par défaut :

```text
%LOCALAPPDATA%\AeroStadium2\textures
```

Le dossier n'est chargé que lorsqu'il contient un `rt64.json` valide. Aucun asset propriétaire n'est fourni dans le dépôt.

Pour capturer les textures utilisées par le jeu, passer temporairement :

```ini
dump_textures=true
```

RT64 écrira alors les textures/hash dans `texture_dump_dir` (par défaut `texture_dumps`). Un run jusqu'à l'écran titre permettra d'identifier précisément le fond, les glyphes, le HUD et les textures importantes, puis de construire un pack HD spécifique NP3F.
