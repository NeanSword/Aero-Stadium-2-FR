# Politique du dépôt

## À versionner

- code source original du projet ;
- scripts de build et de test ;
- outils de reverse engineering développés pour le projet ;
- documentation ;
- fichiers de configuration ;
- métadonnées et hashes de vérification ;
- petits fichiers texte de cartographie.

## À ne pas versionner

- ROM complète ;
- dumps binaires du jeu ;
- archives d'extraction contenant des assets du jeu ;
- exécutables reconstruits lorsqu'ils embarquent des données propriétaires ;
- clés, tokens ou identifiants.

## Travail local

Les fichiers nécessaires à une reconstruction à partir de la ROM sont générés localement.

Les scripts doivent privilégier une approche reproductible : une installation propre de Windows doit pouvoir recréer les fichiers générés sans dépendre d'une archive manuelle produite par ChatGPT.
