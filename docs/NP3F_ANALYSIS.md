# Analyse NP3F

Cette note consigne uniquement les résultats vérifiés lors de l'analyse locale de la ROM française NP3F.

## ROM

- Région : NP3F
- Taille : 64 MiB
- MD5 normalisé : `4748d96916ae2bcc5fc1630515ee2561`
- SHA-1 normalisé : `d7e13535b671024a92822db01507e87bd42f68ec`
- SHA-256 normalisé : `b661d92a94eb3c7a00cd27acc1e93d1e52299bf85a76397ee38e998a84af68ea`

## Comparaison US / FR

La comparaison octet par octet effectuée précédemment donne :

- identiques : 31 810 284 octets (47,40 %)
- différents : 35 298 580 octets (52,60 %)

Les plus grandes zones identiques observées comprennent notamment :

- `0x02589400..0x04000000`
- `0x0225A817..0x023A5001`
- `0x016061C0..0x016FC000`

## Fragments

88 fragments ont été reconstruits à partir des en-têtes NP3F.

Constat important : les bases VRAM des fragments restent identiques entre US et FR, alors que les offsets ROM se déplacent par plages cumulatives.

Plages de delta ROM FR par rapport à l'US :

| Fragments | Delta |
| --- | ---: |
| 1–11 | +32 |
| 12–31 | +48 |
| 32–34 | +432 |
| 35–36 | +496 |
| 37–45 | +608 |
| 46–68 | +1136 |
| 69–71 | +1152 |
| 72–77 | +1184 |
| 78–79 | +1040 |
| 80–85 | +1200 |
| 86–88 | +3184 |

## Fonctions

8 233 fonctions françaises ont été associées à des adresses US connues pendant l'analyse.

Correspondance exacte des premiers octets à l'emplacement US attendu :

- 16 premiers octets : 6 039 / 8 233 (73,4 %)
- 32 premiers octets : 5 026 / 8 233 (61,0 %)
- 64 premiers octets : 3 841 / 8 233 (46,7 %)

Ces chiffres sont des résultats de cartographie et ne constituent pas encore une preuve de reconstruction complète ou de build natif fonctionnel.

## Prochaine étape

Utiliser cette cartographie comme couche de correspondance, puis reconstruire la structure du projet NP3F sans recopier aveuglément les offsets US dans les fichiers français.
