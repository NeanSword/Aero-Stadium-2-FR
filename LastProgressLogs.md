# LastProgressLogs — Aero-Stadium-2-FR

> Point de reprise technique pour ChatGPT Work / Codex / futurs agents.
> Mis à jour le 27 septembre 2026 après le dernier runtime probe NP3F.
>
> **Toujours lire ce fichier avant de reprendre le projet.**
> L'objectif immédiat n'est plus l'extraction/recompilation générale : le projet produit déjà un exécutable Windows natif qui entre profondément dans le boot. Le blocage actuel est un **softlock de synchronisation / message queues après la 61e tâche graphique**.

---

## 1. Objectif du projet

Portage natif Windows x64 de **Pokémon Stadium 2 FR / NP3F**, dans l'esprit de Ship of Harkinian / recompilation statique moderne :

```text
AeroStadium2.exe
  -> code NP3F statiquement recompilé MIPS -> C/C++ -> x64
  -> N64ModernRuntime
  -> RT64
  -> couche Aero (fenêtre, input, audio, config, etc.)
```

Important : le runtime reproduit toujours des sémantiques matérielles/N64 OS et RT64 traite le rendu N64. Ne pas présenter le résultat comme « zéro émulation » au sens absolu.

ROM propriétaire non distribuée. La ROM FR légale locale attendue reste :

```text
baseroms/fr/baserom.z64
```

Hash NP3F runtime validé :

```text
0x93AC31A17326F35B
```

Référence JP correcte si une comparaison redevient nécessaire :

```text
Pocket Monsters Stadium Kin Gin (Japan).n64
```

---

## 2. Environnement utilisateur / workflow à respecter

- OS utilisateur : **Windows uniquement**.
- Dossier local historique :
  ```text
  C:\Users\dofus\Downloads\PokemonStadium2_FR_Windows_Next\pokestadiumgs-fr
  ```
- Repo :
  ```text
  https://github.com/NeanSword/Aero-Stadium-2-FR
  ```
- Branche de travail : `main`.
- L'utilisateur ne veut pas travailler avec des milliers de ZIP.
- Préférer les modifications directes sur GitHub.
- Ne demander une action Windows manuelle que lorsqu'un test local est réellement requis.
- L'utilisateur n'utilise pas `git pull` localement : quand un fichier doit être récupéré manuellement, fournir un `Invoke-WebRequest` vers un commit épinglé.
- Toujours vérifier le contenu/diff avant d'envoyer une commande de téléchargement.

### Discipline de modification

Avant de déclarer un fichier prêt :

1. inspecter le fichier avant modification ;
2. faire une modification ciblée ;
3. inspecter le diff exact ;
4. vérifier qu'aucune fonction existante n'a disparu accidentellement ;
5. vérifier signatures, includes, références et dépendances ;
6. vérifier le fichier réellement présent sur `main` ;
7. pour les fichiers critiques fraîchement modifiés, préférer une URL raw épinglée au commit ;
8. ne supprimer une fonction que volontairement et après vérification qu'elle n'est plus utilisée.

---

## 3. État global déjà validé

### Extraction / symboles / recompilation

Le pipeline NP3F n'est plus au stade expérimental initial.

Validé :

- layout Splat FR canonique dans `yamls/fr/splat.yaml` ;
- 88/88 fragment headers reconnus ;
- 335/335 boundaries supportées par anchors + 15 boundaries explicitement vérifiées ;
- symbol map générée :
  - **10 911 fonctions** ;
  - **89 sections contenant des fonctions** ;
  - 24 rejets ;
  - 283 fonctions libultra relocalisées ;
- N64Recomp génère **214 unités `funcs_*.c`** ;
- bibliothèque générée :
  ```text
  build\np3f\generated-smoke-vs2022-x64\lib\AeroNP3FGenerated.lib
  ```
- exécutable lié :
  ```text
  build\np3f\link-smoke-prebuilt-vs2022-x64\bin\AeroStadium2.exe
  ```

### Dépendances épinglées

```text
N64ModernRuntime cdf5abbd5026fef5c364c676e4667c45e42b6863
N64Recomp        ffb39cdad1da5de07eaaa48bd1db4a89a7986771
RT64             23cab603c4f9f4a8b369b38e036f1aa484603878
```

### Runtime natif déjà prouvé

Le runtime :

- valide et charge la ROM NP3F ;
- crée la fenêtre Win32 ;
- initialise RT64 D3D12 ;
- force le PAL ;
- démarre le code recompilé ;
- crée/exécute les threads N64 principaux ;
- reçoit les tâches RSP ;
- envoie les display lists à RT64 ;
- charge/enregistre des overlays dynamiques ;
- détecte la manette SDL2 ;
- ferme proprement dans le dernier état testé.

---

## 4. RSP audio NP3F : maintenant réel

Le microcode audio français a été extrait/généré via RSPRecomp.

Fichier généré local attendu :

```text
generated/rsp/np3f/aspMain_np3f.cpp
```

Signature validée :

```text
ucode ROM       0x1060
ucode size      0x1000
IMEM            0x04001000
ucode_data      0x80087010
ucode_data ROM  0x87C10
ucode_data_size 0x2DF
```

24 handlers indirects distincts ont été validés.

Le runtime sélectionne `aspMain_np3f` uniquement pour la signature audio NP3F exacte.

Logs attendus/observés :

```text
[runtime-probe] Microcode audio NP3F reel actif: aspMain_np3f.
```

Conclusion :

- le faux `RspExitReason::Broke` audio n'est plus utilisé pour cette tâche ;
- **le RSP audio n'était pas la cause principale du softlock**.

Commits d'intégration importants :

```text
5af1337b0c02c2b235ec6562791f152b9212b1fe  CMake: compile aspMain_np3f si présent
c4530b053fcc5f346741c9555542ff08c3293f9d  runtime: dispatch audio NP3F réel
```

---

## 5. AI direct MMIO : bridge ajouté

Pokémon Stadium 2 écrit directement dans les registres AI au lieu de s'appuyer uniquement sur `osAiSetNextBuffer`.

Fonction NP3F vérifiée :

```text
func_80019550
```

Sites exacts :

```text
0x8001958C  lecture AI_STATUS
0x800195AC  écriture AI_DRAM_ADDR
0x800195B4  écriture AI_LEN
0x800195B8  hook placé juste après les deux écritures
```

Le hook appelle :

```cpp
aerostadium2_np3f_ai_submit_buffer(
    rdram,
    (uint32_t)ctx->r10,
    (uint32_t)ctx->r5
);
```

Puis :

```cpp
ultramodern::queue_audio_buffer(...)
```

Des buffers de 2496 octets sont réellement soumis.

Commit logique principal :

```text
0256bc90b3dc3fdf1362516f012d7f8dc25beedb
```

Conclusion :

- le chemin AI n'est plus totalement factice ;
- **le bridge AI n'a pas supprimé le softlock** ;
- le callback hôte `queue_samples()` du probe reste encore minimal/vide, donc le backend audio complet n'est pas fini, mais ce n'est pas le verrou de boot actuellement identifié.

---

## 6. Shutdown Windows : use-after-free RDRAM identifié et contourné

Ancien crash à la fermeture :

- un thread recompilé continuait brièvement ;
- `recomp::start()` n'avait pas complètement terminé ;
- N64ModernRuntime libérait le RDRAM ;
- `func_80035594` accédait ensuite à une zone devenue `MEM_FREE`.

Cause validée : **shutdown use-after-free du RDRAM**.

Workaround Windows actuel :

- le bootstrap patch le runtime épinglé pour **ne pas `VirtualFree` le RDRAM** pendant cette fermeture mono-session ;
- Windows récupère la mémoire à la fin du processus.

Ce n'est pas une solution générale à un futur restart in-process.

Commit :

```text
26901c08e8e5a68e0620c5bf759a9a2e489f9198
```

Le dernier runtime test se ferme proprement.

---

## 7. Instrumentation runtime actuellement présente

Le bootstrap N64ModernRuntime contient actuellement de nombreuses traces diagnostiques temporaires :

```text
[mq-ext-fail]
[mq-event-reg]
[mq-block-recv]
[mq-wake-recv]
[mq-noblock-full]
[mq-vi-reg]
[gfx-submit]
[rcp-produce] SP
[rcp-produce] DP
```

Version bootstrap au dernier état :

```text
2026-09-27.7
```

Commit bootstrap important :

```text
b2caa8101496a078e3103fdd9e594be5f550eb44
```

Le probe possède aussi :

- snapshot threads à 3 s ;
- snapshot threads à 6 s ;
- snapshot ciblé de plusieurs `OSMesgQueue`.

Dernier commit avant ce document :

```text
d3b6247e95e56f497d8ce35f33833df6cc2ffec1
runtime: snapshot suspicious NP3F message queues at softlock
```

---

## 8. État exact du softlock — DERNIER RUN

### 8.1 Graphique / RCP

Le dernier run corrige une conclusion d'un run précédent :

- `gfx-submit #61` **existe** ;
- `SP #184` est produit pour cette phase ;
- `DP #61` **est produit** ;
- aucune `gfx-submit #62` n'a été observée ensuite ;
- RT64 reste ensuite bloqué à **61 display lists** alors que les scanouts continuent.

Séquence observée :

```text
[gfx-submit] #60
[rcp-produce] SP #181
[rcp-produce] DP #60
...
[gfx-submit] #61
[rcp-produce] SP #184
[rcp-produce] DP #61
...
[rt64-progress] screens=300  lists=61
[rt64-progress] screens=600  lists=61
[rt64-progress] screens=900  lists=61
[rt64-progress] screens=1200 lists=61
[rt64-progress] screens=1500 lists=61
[rt64-progress] screens=1800 lists=61
```

**Conclusion actuelle :**

RT64 ne semble pas perdre la completion DP de la dernière tâche graphique connue. Le jeu/scheduler cesse de produire la tâche graphique suivante après que #61 a été complétée.

### 8.2 Queue scheduler RCP

```text
0x800CDA30
```

Enregistrée pour :

```text
VI      msg 0x66
SP done msg 0x64
DP done msg 0x65
PRENMI  msg 0x68
```

À 3 s ET 6 s :

```text
valid=0
count=16
blocked_recv=0x800CD040  (thread id=3)
blocked_send=0
```

Donc le scheduler `id=3` finit bloqué sur une queue RCP vide.

### 8.3 Queue thread RSP / loader id=20

```text
0x800D047C
```

À 3 s ET 6 s :

```text
valid=0
count=16
blocked_recv=0x800CE190  (thread id=20)
blocked_send=0
```

### 8.4 Trois petites queues suspectes

#### 0x801221E0 — id4-mailbox

À 3 s et 6 s :

```text
valid=1
count=1
head=0x00000000
blocked_recv=0
blocked_send=0
```

Donc queue pleine et **aucun consommateur actuellement bloqué dessus**.

Le thread `id=4` tente ensuite de nombreux :

```text
osSendMesg(..., OS_MESG_NOBLOCK)
```

vers cette queue, avec des valeurs croissantes.

Nombre de rejets observés dans le dernier stderr :

```text
65
```

#### 0x80122A6C — reply-A6C

À 3 s et 6 s :

```text
valid=1
count=1
head=0x444F4E45  ("DONE")
blocked_recv=0
blocked_send=0
```

Nombre de nouveaux `DONE` NOBLOCK rejetés observés :

```text
32
```

Envoyeur observé :

```text
thread id=3 / scheduler
```

#### 0x80122AD4 — reply-AD4

À 3 s et 6 s :

```text
valid=1
count=1
head=0x444F4E45  ("DONE")
blocked_recv=0
blocked_send=0
```

Nombre de nouveaux `DONE` NOBLOCK rejetés observés :

```text
31
```

Envoyeur observé :

```text
thread id=3 / scheduler
```

### 8.5 Conclusion la plus importante du dernier run

Les deux reply queues contiennent déjà un ancien `DONE` à 3 s et le contiennent toujours à 6 s.

Cela suggère davantage :

> **le consommateur de ces reply queues ne les vide plus**

que :

> « le dernier DONE envoyé a simplement été perdu ».

Ne pas transformer aveuglément tous les `OS_MESG_NOBLOCK` en envois forcés avant d'avoir identifié le propriétaire/consommateur de ces queues.

---

## 9. Hypothèses déjà écartées ou fortement affaiblies

Ne pas repartir de zéro sur ces pistes.

### Écarté comme cause principale

- extraction NP3F invalide ;
- génération N64Recomp globalement cassée ;
- link Windows impossible ;
- absence de fenêtre/RT64 ;
- faux RSP audio comme verrou principal ;
- absence de soumission AI comme verrou principal ;
- absence de SP completion de la dernière GFX ;
- absence de DP completion de la dernière GFX ;
- simple drop d'un événement RCP **externe** dû à une queue pleine : les diagnostics `[mq-ext-fail]` n'ont pas révélé ce scénario sur les runs concernés.

### Toujours possible / à distinguer

- logique de handshake interne avec `OSMesgQueue` de profondeur 1 ;
- consommateur qui cesse d'appeler `osRecvMesg` ;
- ordre de scheduling coopératif différent du hardware ;
- send NOBLOCK attendu mais non consommé assez vite ;
- corruption ou réutilisation d'une structure/queue ;
- étape de boot qui attend un autre thread avant de produire GFX #62.

---

## 10. Parallèle utile avec pokemonStadiumGSRecomp

Repo de référence étudié :

```text
michiiik/pokemonStadiumGSRecomp
```

Cette référence a documenté des problèmes de boot Stadium 2 autour :

- des `OSMesgQueue` ;
- des reply queues ;
- des `DONE` ;
- des envois NOBLOCK sur queue temporairement pleine ;
- d'une chaîne de boot décrite comme :
  ```text
  t3 -> t5 -> t6 -> t10 -> t7
  ```
- de completions RCP fiables vs événements coalescibles.

Mais **ne pas recopier mécaniquement leurs adresses US/JP ni leurs hacks**. Les adresses NP3F doivent être vérifiées localement.

Leur code actuel conserve d'ailleurs la sémantique NOBLOCK de `osSendMesg` : il logue les drops mais ne transforme pas automatiquement tous les NOBLOCK en BLOCK.

---

## 11. PROCHAINE ÉTAPE RECOMMANDÉE

Priorité : **identifier qui crée et surtout qui consomme les queues**
`0x801221E0`, `0x80122A6C`, `0x80122AD4`.

### Étape A — instrumentation ciblée `osCreateMesgQueue`

Logger uniquement quand `mq` vaut une des trois adresses :

```text
0x801221E0
0x80122A6C
0x80122AD4
```

À enregistrer :

- thread courant / id ;
- adresse queue ;
- adresse buffer ;
- capacité ;
- moment de création.

But : identifier leur propriétaire initial.

### Étape B — instrumentation ciblée des RECEIVES

Tracer tous les `osRecvMesg` sur ces trois queues, pas seulement les blocages.

Pour chaque receive :

```text
avant: validCount / first / head
thread id / thread addr
flags BLOCK ou NOBLOCK
après: validCount / message reçu
```

But principal :

> savoir quel thread a consommé ces queues auparavant, puis à quel moment il cesse de le faire.

### Étape C — corréler au dernier GFX #61

Ajouter si nécessaire un compteur/horodatage logique commun afin de savoir :

- dernier receive sur A6C ;
- dernier receive sur AD4 ;
- dernier receive sur 221E0 ;
- `gfx-submit #61` ;
- `DP #61` ;
- moment exact où les trois queues deviennent durablement pleines.

### Étape D — seulement ensuite décider d'un correctif

Selon le résultat :

1. **consommateur bloqué sur mauvaise queue**  
   → chercher le handshake précédent / message manquant ;

2. **consommateur jamais réveillé alors qu'un message est présent**  
   → problème scheduler / blocked_on_recv / wakeup ;

3. **consommateur ne fait simplement plus de recv**  
   → remonter sa logique de boot / attente précédente ;

4. **structure queue corrompue/réutilisée**  
   → placer un watch/tripwire sur les champs de la queue ;

5. **ordre coopératif différent du hardware et NOBLOCK réellement critique**  
   → expérimenter un correctif extrêmement ciblé, jamais global, sur la queue/callsite prouvée.

---

## 12. Commandes de test selon le type de modification

### Si seul `np3f_runtime_probe.cpp` change

Pas de bootstrap, pas de N64Recomp.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\windows\build_np3f_link_smoke.ps1 -SkipRun

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\windows\run_np3f_runtime_probe.ps1
```

### Si le bootstrap N64ModernRuntime / ultramodern change

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\windows\bootstrap_n64modernruntime.ps1

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\windows\build_np3f_link_smoke.ps1 -SkipRun

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\windows\run_np3f_runtime_probe.ps1
```

### Si `recomp/np3f.toml` ou un hook N64Recomp change

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\windows\run_np3f_recomp_prepare.ps1 -SkipExtract

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\windows\build_np3f_generated_smoke.ps1

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\windows\build_np3f_link_smoke.ps1 -SkipRun

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\windows\run_np3f_runtime_probe.ps1
```

Le runner N64Recomp et le bootstrap runtime possèdent des heartbeats/progressions visibles pour éviter les longues phases silencieuses.

---

## 13. Fichiers clés à lire avant de modifier

```text
recomp/np3f.toml
cmake/np3f_generated_smoke/np3f_memory_compat.h
cmake/np3f_link_smoke/CMakeLists.txt
cmake/np3f_link_smoke/main.cpp
cmake/np3f_link_smoke/np3f_runtime_probe.cpp
cmake/np3f_link_smoke/np3f_runtime_compat.cpp
cmake/np3f_link_smoke/np3f_register_overlays.cpp
cmake/np3f_link_smoke/np3f_rt64_renderer.cpp
cmake/np3f_link_smoke/np3f_sdl_input.cpp

windows/bootstrap_n64modernruntime.ps1
windows/run_np3f_recomp_prepare.ps1
windows/build_np3f_generated_smoke.ps1
windows/build_np3f_link_smoke.ps1
windows/run_np3f_runtime_probe.ps1
windows/build_np3f_rsp_audio.ps1
```

Docs utiles :

```text
README.md
windows/README.md
recomp/README.md
docs/DEVELOPMENT_STATUS.md
docs/NATIVE_RUNTIME_ARCHITECTURE.md
docs/DEPENDENCIES.md
PORTING_PLAN.md
```

---

## 14. Commits jalons utiles

```text
588c71a206b672e42155f0237672d218e1b2fd71  cleanup/docs bridge obsolète
4eadf802c73c9767f5265f419c589a7d27289b5a  documentation état/architecture
a2bb91a6c8bd7df0e10e5e69e4209b38b5247bb4  diagnostic func_80035594
a3915e0e1e5df5b65f0fac7b96a3aa0386380a43  shutdown/crash lifecycle instrumentation
675496939a054a4b0338b7d6c8ca1d38e8bbe8f5  build link -SkipRun
26901c08e8e5a68e0620c5bf759a9a2e489f9198  Windows RDRAM lifetime workaround
5af1337b0c02c2b235ec6562791f152b9212b1fe  compile RSP audio généré
c4530b053fcc5f346741c9555542ff08c3293f9d  dispatch RSP audio NP3F
0256bc90b3dc3fdf1362516f012d7f8dc25beedb  AI bridge + recomp config/runner
b2caa8101496a078e3103fdd9e594be5f550eb44  diagnostics RCP/NOBLOCK bootstrap .7
d3b6247e95e56f497d8ce35f33833df6cc2ffec1  snapshots queues suspectes
```

---

## 15. Résumé ultra-court pour reprise immédiate

Si tu ne lis qu'une section, lis celle-ci :

```text
- AeroStadium2.exe compile et link.
- ROM NP3F FR validée.
- RT64 fonctionne et présente des scanouts.
- RSP audio FR réel aspMain_np3f fonctionne.
- AI direct MMIO est bridgé.
- GFX #61 est soumise.
- SP/DP completion de GFX #61 est produite.
- Aucune GFX #62 ensuite.
- Scheduler id=3 finit bloqué sur 0x800CDA30 vide.
- id20 finit bloqué sur 0x800D047C vide.
- 0x801221E0 reste pleine avec head=0.
- 0x80122A6C reste pleine avec "DONE".
- 0x80122AD4 reste pleine avec "DONE".
- Ces trois états sont identiques à 3 s et 6 s.
- Nombre de NOBLOCK full observés : 65 / 32 / 31.
- Ne PAS forcer tous les NOBLOCK.
- Prochaine étape : instrumenter osCreateMesgQueue + osRecvMesg UNIQUEMENT
  pour 0x801221E0 / 0x80122A6C / 0x80122AD4 afin d'identifier leurs consommateurs.
```

---

## 16. Règle de mise à jour de ce fichier

Après chaque jalon significatif :

1. remplacer la section **État exact du softlock — DERNIER RUN** par les résultats les plus récents ;
2. déplacer les hypothèses invalidées vers **Hypothèses déjà écartées** ;
3. actualiser **PROCHAINE ÉTAPE RECOMMANDÉE** ;
4. ajouter les nouveaux commits jalons ;
5. conserver les faits vérifiés des anciens jalons sans réécrire l'historique de manière ambiguë.

Le but de ce fichier est d'empêcher Work/Codex/ChatGPT de repartir à l'aveugle ou de répéter des diagnostics déjà effectués.
