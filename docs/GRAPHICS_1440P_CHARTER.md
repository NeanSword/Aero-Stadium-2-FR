# LastProgressLogs — Aero-Stadium-2-FR

Dernière mise à jour : **27 septembre 2026 — chantier graphique 1440p**.


## Chantier graphique 1440p — plan détaillé

### Décision de phase

Le jeu est considéré fonctionnel pour le chantier actuel. **Le runtime est gelé** : aucune modification du scheduler, des fragments, des entrées, de l'audio, du pipeline RT64 ou de la logique de jeu ne doit être faite pour l'instant. La priorité est exclusivement l'amélioration graphique.

Cible principale : **2560×1440**.

L'objectif n'est pas de moderniser artificiellement Pokémon Stadium 2, mais d'obtenir un rendu **« N64 premium »** : mêmes formes, mêmes silhouettes, mêmes compositions et même identité visuelle, avec davantage de définition, des contours plus propres et une interface réellement lisible en 1440p.

### Dump NP3F reçu et analysé

Archive utilisateur : `NP3F_texture_dumps.zip`. Seul le nom du ZIP extérieur a été changé ; le dossier interne `texture_dumps/` est intact.

Première analyse :

- 11 269 entrées dans l'archive ;
- 2 817 textures uniques ;
- chaque texture possède quatre fichiers : `.rice.json`, `.rice.rdram`, `.tile.json`, `.tmem`.

Formats observés :

- RGBA16 : 2 474 ;
- IA8 : 228 ;
- I4 : 66 ;
- I8 : 33 ;
- IA4 : 10 ;
- IA16 : 4 ;
- RGBA32 : 2.

Les textures I/IA sont souvent des masques d'intensité/alpha. **Ne pas les recolorer automatiquement** : la couleur finale peut être appliquée par le rendu.

Principales dimensions :

- 16×16 : 1 601 ;
- 40×40 : 245 ;
- 32×32 : 116 ;
- 56×26 : 114 ;
- 56×28 : 113 ;
- 24×20 : 77 ;
- 376×4 : 49 ;
- 24×24 : 46 ;
- 32×64 : 32 ;
- 136×14 : 31 ;
- 128×16 : 30 ;
- 144×28 : 29 ;
- 112×36 : 28 ;
- 256×8 : 27 ;
- 64×32 : 26.

### Direction artistique verrouillée

Deux niveaux d'amélioration :

**A — UI / textes / menus : amélioration forte autorisée**

Pour les glyphes, labels, boutons, cadres, bandeaux, menus, HUD et pictogrammes, la reconstruction peut être très propre et détaillée. Priorités : netteté, lisibilité, alpha propre, contours précis et couleurs cohérentes avec l'original. Le résultat peut être sensiblement plus détaillé que la texture N64 d'origine.

**B — Pokémon / stades / gameplay : amélioration fidèle**

Pour les Pokémon, sols, murs et décors, priorité à la fidélité. Augmenter la définition, nettoyer les défauts et stabiliser les couleurs, mais ne pas inventer de micro-détails réalistes, de matière photoréaliste ou de rendu incompatible avec la géométrie simple du jeu.

Règle : **fidélité avant richesse**.

### Politique de résolution

Le 1440p est la résolution d'affichage, pas la taille de chaque texture.

Recommandations de départ :

- glyphes 24×20 : master ×8, export ×4 ou ×8 selon test ;
- icônes 40×40 : master ×8, export ×4 ou ×8 ;
- UI 56×26 / 56×28 : master ×8, export ×4 ou ×8 ;
- UI 112×36 / 136×14 / 144×28 : master ×4 à ×8, export ×4 ;
- petites textures UI : ×8 possible ;
- Pokémon : master ×4, export ×2 à ×4 ;
- stades : master ×4, export ×2 à ×4.

Ne jamais appliquer ×8 à tout le pack : le coût mémoire serait disproportionné. Utiliser ×8 surtout sur les petits éléments UI réellement visibles.

### Pipeline de travail

1. conserver le runtime stable ;
2. conserver le ZIP source localement et ne pas le publier ;
3. cataloguer chaque hash : dimensions, format, preview, catégorie, priorité, scènes observées ;
4. générer une preview brute nearest-neighbor et ne jamais l'écraser ;
5. classer les textures en `ui/text`, `ui/labels`, `ui/icons`, `pokemon`, `stadium`, `effects`, `backgrounds`, `microtiles`, `unknown` ;
6. valider le mécanisme de remplacement avec quatre textures pilotes : un texte, une RGBA, une I/IA et une texture répétée ;
7. vérifier orientation, UV, alpha, wrapping/clamping et rendu 1440p ;
8. commencer la production massive uniquement après ce test ;
9. capturer systématiquement avant/après ;
10. mesurer le bénéfice visuel et éviter les tailles inutiles.

### Traitement UI

- reconstruire proprement les diagonales et coins ;
- conserver proportions et composition ;
- préférer des aplats propres plutôt que du bruit ajouté ;
- nettoyer l'alpha ;
- tester sur fond clair et sombre ;
- juger à taille réelle en 1440p, pas seulement au zoom.

### Traitement des icônes

- conserver silhouette et aplats ;
- nettoyer les pixels accidentels ;
- lisser les courbes avec retenue ;
- corriger les couleurs seulement si la quantification source les a réellement dégradées ;
- éviter les halos autour des silhouettes.

### Traitement Pokémon

- comparer source, preview et rendu en jeu ;
- ne pas peindre un éclairage dynamique dans la texture ;
- conserver motifs, teintes et transitions stylisées ;
- ne pas ajouter poils, pores ou relief réaliste ;
- vérifier de près et à distance normale.

Le résultat doit sembler être **le même Pokémon Stadium 2, simplement plus propre**.

### Traitement des stades

- vérifier les répétitions et raccords ;
- préserver la fréquence des motifs ;
- éviter le moiré ;
- ne pas utiliser de photos de matériaux ;
- améliorer lignes, motifs, panneaux et logos avec retenue ;
- rester cohérent avec la faible densité polygonale.

### Couleurs

Pas de saturation/contraste global automatique.

- travailler en sRGB ;
- préserver les teintes dominantes ;
- corriger uniquement les dérives utiles ;
- éviter noirs bouchés et blancs brûlés ;
- tester sous l'éclairage réel du jeu ;
- pour I/IA, traiter intensité/alpha sans imposer une couleur finale.

### Alpha / contours

Contrôler :

- halos blancs/noirs ;
- franges d'upscale ;
- RGB parasite dans les pixels transparents ;
- perte d'un contour volontairement dur ;
- semi-transparence ajoutée inutilement.

### Validation 1440p

Scènes minimales :

1. écran titre ;
2. menu principal ;
3. écran riche en texte ;
4. sélection Pokémon ;
5. Pokémon en gros plan ;
6. Pokémon à distance normale ;
7. plan large d'un stade ;
8. surface de stade proche ;
9. transparence/effets ;
10. écran combinant plusieurs types d'UI.

Pour chaque scène : capture originale et capture pack avec paramètres identiques. Contrôle principal à 100 % en 2560×1440. Faire également un test rapide en 1080p.

### Performance

À chaque lot :

- surveiller chargements et stutters ;
- surveiller la VRAM si possible ;
- redescendre de ×8 à ×4 si le gain est invisible ;
- ne pas privilégier le nombre de pixels au détriment du résultat réel.

### Ordre de production

**Phase 1 — UI / texte / menus**

Priorités :
- 24×20 : 77 ;
- 56×26 : 114 ;
- 56×28 : 113 ;
- 112×36 : 28 ;
- 136×14 : 31 ;
- 144×28 : 29 ;
- puis les strips 128×16, 120×16, 152×12, 164×12, 180×10, 196×10, 104×18, 256×8 et 376×4 après identification.

**Phase 2 — icônes / éléments 2D**

- 40×40 : 245 ;
- 24×24 ;
- 32×32 ;
- autres petites illustrations identifiées.

**Phase 3 — Pokémon**

Construire d'abord le mapping :
`hash -> scène -> Pokémon -> partie du modèle`.

Traiter ensuite par petits lots avec captures comparatives.

**Phase 4 — stades**

Construire :
`hash -> stade -> surface/objet -> wrapping/clamping -> importance visuelle`.

Priorité aux sols, murs/panneaux proches, grandes surfaces répétées et logos basse résolution.

**Phase 5 — micro-tiles 16×16**

Les 1 601 textures 16×16 sont repoussées jusqu'à ce que leur usage soit identifié et leur gain visuel prouvé.

### Lissage des polygones

Le pack texture peut améliorer la perception des contours et motifs, mais **ne modifie pas la géométrie**. Aucun changement de maillage, normales ou nombre de polygones pendant cette phase.

### Critères d'acceptation

UI :
- netteté réellement supérieure en 1440p ;
- texte fidèle ;
- alpha propre ;
- absence de halo ;
- cohérence avec Stadium 2.

Pokémon :
- silhouette et grands motifs inchangés ;
- pas de détail réaliste inventé ;
- pas de changement fort de teinte ;
- amélioration visible mais discrète.

Stades :
- raccords invisibles ;
- pas de matériau photographique ;
- pas de moiré notable ;
- ambiance originale conservée.

Tous :
- aucun remplacement de mauvais hash ;
- aucune régression runtime ;
- aucun coût de performance disproportionné.

### Risques à surveiller

1. masques I/IA teintés dynamiquement ;
2. alpha limité de certaines textures source ;
3. coutures sur textures répétées ;
4. volume énorme des 16×16 ;
5. faux mapping par simple similarité de dimensions ;
6. confusion entre texture et éclairage ;
7. coût VRAM du ×8 ;
8. texture superbe isolément mais incohérente dans le jeu ;
9. hashes correspondant à des états/dumps dynamiques ;
10. perte du ZIP lors d'un changement d'environnement : dans ce cas demander simplement à l'utilisateur de le renvoyer.

### Prochaines actions exactes

1. ne toucher à aucun code runtime ;
2. figer le checkpoint graphique stable ;
3. rendre le catalogue reproductible ;
4. générer les previews par hash ;
5. créer les manifests Phase 1/2/3/4 ;
6. vérifier le chemin exact de remplacement RT64 déjà intégré ;
7. valider les quatre textures pilotes ;
8. tester en 2560×1440 ;
9. traiter les glyphes 24×20 ;
10. traiter les labels 56×26 / 56×28 ;
11. traiter les bandeaux larges ;
12. traiter les icônes 40×40 ;
13. mapper puis traiter un premier petit lot Pokémon ;
14. mapper puis traiter un premier petit lot stade ;
15. capturer avant/après ;
16. ajuster les multiplicateurs selon qualité et VRAM ;
17. ne revenir aux 16×16 qu'après les familles à fort impact ;
18. documenter dans ce journal les hashes, tailles source/export, scènes testées et commits de chaque lot.

### Définition de succès

Le chantier est réussi si, en 1440p :

- texte et menus paraissent réellement haute définition ;
- icônes propres et lisibles ;
- Pokémon plus nets tout en restant visuellement ceux de Stadium 2 ;
- stades plus propres sans photoréalisme ;
- aucune texture ne semble stylistiquement étrangère ;
- runtime toujours stable ;
- performances acceptables.

---


