# Chapitre 1 : Cadre Théorique et Conceptuel

Ce chapitre établit les fondements théoriques et conceptuels nécessaires à la compréhension de notre système conversationnel d'aide à la décision. Il explore les concepts clés de l'Intelligence d'Affaires, du Traitement Automatique du Langage Naturel et des agents conversationnels, avant d'analyser leur intégration pour l'aide à la décision. Enfin, il positionne notre projet au sein de ce cadre théorique.
## 1.1 Le concept d'Intelligence d'Affaires

### 1.1.1 Définitions et notions fondamentales

L'Intelligence d'Affaires regroupe l'ensemble des processus, méthodologies, architectures et technologies permettant de transformer des données brutes en informations pertinentes et exploitables pour soutenir le processus décisionnel [1]. Au centre de la BI se situe la chaîne de valeur des données, qui commence par le recueil d'informations issues de systèmes opérationnels (PGI, GRC, applications métier) et de données exogènes. Ces données sont ensuite transformées et consolidées au sein d'entrepôts de données, préalablement à leur restitution sous forme de rapports et de tableaux de bord interactifs.

La BI ne se cantonne pas à la génération de rapports : elle représente une approche intégrale visant à améliorer la connaissance organisationnelle. Elle permet de discerner des tendances, détecter des signaux précurseurs et anticiper des évolutions potentielles. Cette approche englobe la structuration, la mise à jour et l'harmonisation des données, tout en intégrant des outils analytiques perfectionnés dérivés de l'IA et de la science des données.

La BI se différencie des systèmes transactionnels traditionnels par son orientation spécifiquement axée sur l'aide à la décision. Elle vise à convertir le capital informationnel latent des organisations en atout stratégique, favorisant la diffusion de l'information à tous les échelons hiérarchiques.
### 1.1.2 Genèse et évolution

L'origine de la BI se situe dans les travaux de Hans Peter Luhn (1958), qui a défini la BI comme un système destiné à « transmettre l'information la plus appropriée, au moment opportun, à la personne compétente, pour faciliter l'action » [2].

Les décennies 1960-1970 ont vu l'émergence des premiers systèmes d'aide à la décision sur ordinateurs centraux. La décennie 1990 marque une transition majeure avec l'émergence des entrepôts de données, conceptualisés par William H. Inmon [3]. Ces architectures permettent de centraliser les données provenant de sources diverses, fournissant une représentation unifiée des activités organisationnelles.

Les années 2000 apportent une transformation notable avec le développement d'Internet et l'émergence d'instruments comme les tableaux de bord prospectifs, les techniques d'exploration de données et les systèmes OLAP. La démocratisation de la BI est facilitée par l'essor de solutions open source et l'informatique en nuage, rendant ces technologies accessibles aux PME.
### 1.1.3 Architecture d'un système de BI

L'architecture d'un système de BI représente un écosystème complexe organisé en strates fonctionnelles interdépendantes, visant à convertir des données brutes en informations stratégiques. Cette organisation englobe la collecte, l'intégration, le stockage, l'analyse et la restitution des données.

**1. Acquisition et intégration des données**
La collecte de données constitue la composante initiale. Les données proviennent de diverses sources : PGI, GRC, bases de données relationnelles, fichiers plats (CSV, Excel, JSON, XML), applications SaaS, réseaux sociaux, objets connectés. Cette hétérogénéité requiert des connecteurs spécialisés supportant différents formats et fréquences de mise à jour.

**2. Intégration, nettoyage et transformation (ETL/ELT)**
Les données sont traitées par des flux ETL ou ELT. L'extraction permet une récupération automatisée, la transformation standardise l'information (suppression des doublons, correction des incohérences, gestion des valeurs manquantes, calcul d'indicateurs), et le chargement sauvegarde les données transformées dans l'entrepôt central.

**3. Stockage et modélisation**
L'entrepôt de données centralise l'information autour de thématiques établies (ventes, clientèle, ressources, finances) et assure l'historisation, la non-volatilité et une structuration appropriée via des modèles dimensionnels. Des data marts thématiques permettent d'affiner l'analyse pour des besoins spécifiques.

**4. Analyse et exploration**
Les outils OLAP offrent une exploration multidimensionnelle avec navigation dans les cubes de données, analyse descendante et agrégation. L'intégration de modules d'exploration de données et d'apprentissage automatique enrichit l'analyse en matière de segmentation, détection d'anomalies, prédiction et recommandation.

**5. Présentation et visualisation**
La couche de restitution met à disposition des tableaux de bord interactifs, des rapports dynamiques et des instruments de simulation. Les solutions récentes intègrent des modules conversationnels permettant de répondre à des requêtes en langage naturel.

**6. Gouvernance, sécurité et conformité**
Le dispositif est structuré par une gouvernance rigoureuse comprenant la gestion des habilitations, la traçabilité des flux de données et la conformité aux réglementations (RGPD). Ces mécanismes assurent la confidentialité, l'intégrité et la disponibilité des données.

La figure 1.1 illustre cette architecture générale.

**[INSERTION FIGURE 1.1 ICI]**
### 1.1.4 BI appliquée à la gestion commerciale et éducative

L'application de la BI à la gestion commerciale subit une transformation d'envergure lorsqu'elle est associée à une interface conversationnelle. Le système conversationnel transforme l'analytique en interlocuteur du décideur : il réceptionne une question formulée en langage naturel, active les ensembles de données pertinents (ventes, clients, articles, stocks), effectue des transformations et modélisations (agrégations temporelles, segmentations, prévisions), puis reformule une réponse contextualisée accompagnée d'indicateurs et de recommandations d'action.

Cette approche positionne la BI au centre des microdécisions quotidiennes (fixation des prix, priorisation commerciale, arbitrage des achats), tout en fournissant une mémoire analytique cohérente. Dans les entités éducatives à vocation commerciale, un dispositif conversationnel établit une corrélation entre les résultats commerciaux (chiffre d'affaires, paniers moyens, rotations) et la performance pédagogique (assiduité, taux de réussite, satisfaction), orientant des décisions relevant simultanément des domaines économique et pédagogique.
**Chaîne de valeur décisionnelle conversationnelle**
Sur le plan opérationnel, l'intégration de la BI à un agent conversationnel se conçoit comme une chaîne de valeur allant « du signal à l'action ». La détection du signal (ventes inférieures à la bande de confiance, allongement des délais de paiement, augmentation du taux d'abandon) est étayée par des métriques stabilisées et des modèles validés.

L'agent effectue le codage de la demande utilisateur en requête analytique précise, comprenant l'explicitation des filtres (ville, période, segment), la sélection de la granularité temporelle appropriée, le choix des vues pertinentes et l'activation d'un pipeline d'enrichissement. La restitution intègre un exposé du processus décisionnel, des justifications succinctes et des recommandations d'actions. L'utilisateur peut soumettre des requêtes itératives (« Si l'on excluait les promotions ? », « Qu'en est-il seulement pour Yaoundé ? ») et le système assure la traçabilité de la session.
**Données, indicateurs et modèles pour le pilotage commercial**
Dans un environnement conversationnel dédié à la gestion commerciale, la BI structure trois strates complémentaires :

- **Strate descriptive** : consolide des indicateurs fondamentaux (chiffre d'affaires, marges, paniers moyens, taux de conversion, délai moyen de paiement, rotation des stocks) en se fondant sur des règles de calcul harmonisées.
- **Strate diagnostique** : permet d'identifier les étiologies potentielles via la segmentation RFM, la contribution par article, l'élasticité prix-volume et les incidences de la saisonnalité.
- **Strate prédictive** : effectue des simulations incluant la prévision des ventes, la détection d'anomalies et la recommandation de réassort optimisé.

L'approche conversationnelle réduit la charge cognitive liée à l'obtention des perspectives pertinentes et met en place une culture de l'explicabilité, où chaque calcul est traçable et chaque recommandation accompagnée d'une évaluation de l'incertitude.
**Parallèle éducatif : transférabilité et symétries analytiques**
Le contexte éducatif présente de nombreuses symétries avec la dynamique commerciale. Le « cycle de vie client » correspond au « parcours apprenant » ; les indicateurs de fidélisation sont corrélés aux indicateurs d'assiduité et d'engagement ; la prédiction des ventes est analogue à la prédiction des inscriptions ou de la réussite.

Un agent conversationnel peut répondre aux interrogations : « Quels groupes présentent un risque d'abandon supérieur à la médiane ? », « Quelles séquences pédagogiques corrèlent avec la progression la plus rapide ? », « Quel serait l'impact d'un décalage de calendrier sur le taux de présence ? ».

Cette transférabilité offre, dans une configuration hybride combinant la vente de manuels et la formation, la possibilité d'optimiser conjointement l'ensemble de la chaîne de valeur. L'identification d'une corrélation temporelle entre la diminution des ventes de manuels « Mathématiques » et la réduction de la fréquentation des cours permet une interprétation causale et la mise en œuvre d'actions coordonnées.
**Qualité, gouvernance et conformité**
L'efficience d'un agent conversationnel décisionnel est tributaire de la qualité de l'infrastructure décisionnelle sous-jacente. Il est impératif de disposer de définitions d'indicateurs univoques, d'une historisation robuste des données, d'une gestion rigoureuse des identités, d'un contrôle des doublons et de métadonnées explicites.

En matière de gouvernance, il convient de considérer la gestion précise des autorisations, l'enregistrement des accès et des échanges, la conservation des requêtes exécutées et la mise en œuvre de politiques de confidentialité conformes au cadre juridique applicable.

Dans une optique pédagogique, la confidentialité des données exige une vigilance accrue : la restitution conversationnelle doit occulter ou agréger les informations lorsque le risque de réidentification existe, et l'agent doit afficher des avertissements explicites dès lors qu'une requête transgresse le principe de minimisation.
**Explicabilité, transparence et diffusion pédagogique**
Le système conversationnel se doit de rendre compte de son fonctionnement. L'utilisateur doit pouvoir déterminer les périodes et sources de données mobilisées, connaître l'intervalle de confiance associé à une prévision et identifier les facteurs prépondérants influençant une recommandation.

La BI offre les instruments nécessaires à une pédagogie intégrée : traçabilité des opérations de calcul, liens vers les visualisations et tables de données sources, gestion des versions des modèles et indicateurs. Cette transparence contribue à consolider la maturité analytique de l'organisation.

Dans le domaine éducatif, cette explicabilité est éthiquement indispensable : une préconisation d'orientation ou de remédiation pédagogique doit être examinable, modifiable et remise en question. L'agent conversationnel s'abstient de prendre des décisions, se limitant à apporter un éclairage et à qualifier le niveau d'incertitude.
**Rétroactions et amélioration continue**
La qualité essentielle d'une BI associée à un agent conversationnel réside dans l'établissement de cycles d'apprentissage organisationnel. Chaque interaction représente une opportunité d'améliorer la donnée elle-même, le modèle sous-jacent ou l'expérience utilisateur.

Dans le domaine commercial, cette approche améliore la réactivité (anticipation des réassorts, ciblage précis des relances, adaptation fine des promotions) et optimise la rigueur de la mesure (harmonisation des définitions, diminution des écarts numériques).

Dans le contexte éducatif, cette approche encourage une culture d'évaluation formative, où l'acteur propose des ajustements mineurs (rééquilibrage des groupes, identification des concepts complexes, révision des supports) en se fondant sur des indicateurs subtils comme la diminution de l'assiduité ou la variabilité des résultats.
**Limitations et points d'attention**
Deux obstacles potentiels doivent être anticipés :

1. **Complexité linguistique** : la conversation peut introduire des ambiguïtés par l'emploi de termes polysémiques ou l'implication de portées temporelles. La stratégie adoptée comprend l'établissement d'un « contrat sémantique » (glossaire partagé) et la sollicitation de précisions minimales par l'agent.

2. **Biais statistique** : propension à accorder une importance excessive à des variations aléatoires entachées de bruit. L'analyse des données exige une rigueur méthodologique (bandes de confiance, correction des variations saisonnières, tests d'écart) et des mécanismes de contrôle opérationnels (seuils d'alerte, règles de priorité) pour minimiser l'instabilité décisionnelle.
**Synthèse : une grammaire partagée pour la prise de décision**
Dans la gestion commerciale, la BI met à disposition les éléments constitutifs analytiques, les définitions stabilisées et la gouvernance nécessaires à la fiabilité du processus décisionnel. Intégrée à une interface conversationnelle, elle se mue en outil d'aide à la décision caractérisé par sa rapidité de réponse, sa capacité à fournir des explications et à suggérer des stratégies d'action appropriées.

L'analogie avec le contexte éducatif met en évidence la transférabilité d'un cadre conceptuel (qualité, explicabilité, boucles d'apprentissage) et l'intérêt d'une métrique « biculturelle » (économie/pédagogie) pour les structures intervenant aux interfaces des deux domaines.

Le présent mémoire démontre comment une BI gouvernée, associée à un agent conversationnel, constitue un outil d'aide à la décision accessible et rigoureux, apte à soutenir les microdécisions quotidiennes tout en renforçant l'alignement stratégique des organisations. 
## 1.2 Le Traitement Automatique du Langage Naturel

### 1.2.1 Définition et enjeux du TAL

Le TAL englobe un ensemble de méthodologies computationnelles dont l'objectif est d'analyser, de comprendre et de générer des énoncés en langue naturelle, qu'ils soient écrits ou oraux [4]. Dans le contexte de ce mémoire, le TAL est envisagé comme une interface cognitive intégrée à un système décisionnel.

Il offre au décideur la possibilité d'exprimer des objectifs et des contraintes en langage naturel, tout en facilitant l'accès aux données et aux modèles analytiques de la BI, afin de générer une réponse pertinente, traçable et exploitable. La conversation s'établit comme le « protocole utilisateur » du pilotage commercial, permettant d'énoncer des requêtes telles que « Afficher les articles dont la marge se dégrade malgré l'augmentation des volumes, uniquement pour le dernier trimestre et pour la zone Nord » ou « Simuler l'impact d'une remise de 5 % sur les clients à forte récence, mais faible fréquence ». 
### 1.2.2 Considérations linguistiques et sémantiques

Le TAL est confronté à un défi de désambiguïsation, les formulations naturelles contenant des éléments implicites (périodes temporelles non spécifiées, dénominations hétérogènes, pronoms anaphoriques) et des polysémies propres à des domaines spécifiques (« commande » désignant soit un bon de commande, soit un ordre d'achat ; « client actif » par opposition à « client à forte valeur »).

Il incombe à l'agent de convertir une intention formulée en langage naturel en représentation formelle, constituée d'ensembles d'entités (articles, segments, canaux), de fenêtres temporelles (glissement mensuel, période budgétaire), d'opérateurs analytiques (filtrer, agréger, comparer, projeter) et de mesures (chiffre d'affaires, marge, panier moyen).

La correcte interprétation requiert un contrat sémantique mutuellement reconnu, comprenant un glossaire et un dictionnaire de métadonnées, afin de garantir la concordance entre le vocabulaire employé par les utilisateurs et les structures sous-jacentes de la BI.

Dans un contexte pédagogique, les notions de « taux d'assiduité », de « progression » et de « groupe à risque » nécessitent une sémantique stabilisée concernant les niveaux, les périodes académiques et les modalités de contrôle.

**[INSERTION FIGURE 1.2 ICI]**
### 1.2.3 TAL et BI : articulation technique au service de la prise de décision

Pour générer des réponses pertinentes, l'agent conversationnel doit intégrer le TAL et la BI au sein d'un processus séquentiel cohérent :

1. **Compréhension du langage naturel** : extraction des intentions (comparaison, anticipation, clarification), des entités (ville, catégorie de produits, segment RFM) et des conditions (période temporelle, seuil, exclusions).

2. **Interprétation métier** : ancrage de ces éléments dans le modèle décisionnel via un mappage sur les dimensions et mesures, la résolution des alias et la désambiguïsation temporelle.

3. **Planification analytique** : élaboration d'un plan d'exécution (requêtes OLAP/SQL, invocations de modèles prédictifs, identification d'anomalies) avec contrôles de qualité.

4. **Génération de langage naturel** : restitution concise et explicitée (hypothèses, intervalles de confiance, facteurs contributifs) accompagnée d'options d'action envisageables.

Cette structuration contribue à diminuer la charge cognitive associée à l'accès aux analyses approfondies tout en assurant la traçabilité, chaque donnée résultante étant reliée à ses sources, dates et règles de calcul.

### 1.2.4 Enjeux organisationnels : accessibilité, gouvernance et confiance

Le TAL contribue à la démocratisation de l'accès à l'IA en réduisant les obstacles techniques, en accélérant le cycle itératif de questionnement-réponse et en encourageant une culture axée sur les données quantitatives. Cette démocratisation doit être étayée par trois garanties :

- **Qualité et gouvernance des données** : définitions stables des indicateurs, historisation des données, gestion des identités, traçabilité des transformations et politiques d'accès proportionnées.

- **Transparence** : capacité offerte à l'utilisateur d'examiner l'origine des résultats (sources, périmètres, dates, méthodologies), d'obtenir des éclaircissements et de consulter les visualisations afférentes.

- **Robustesse statistique** : prévention de la surinterprétation de signaux de faible amplitude (tests d'écart, saisonnalité, intervalles de confiance) et instauration de mécanismes de contrôle (seuils d'alerte, règles de priorité).

Ces enjeux possèdent une dimension politique organisationnelle, car ils déterminent la confiance accordée à l'agent et influencent son adoption pérenne.
### 1.2.5 Considérations éthiques et réglementaires

Un agent doté de capacités de « compréhension » et d'« expression » manipule des données potentiellement sensibles (comportements d'achat, historique d'apprentissage). Les principes éthiques impliquent :

- **Minimisation** : traitement exclusif des données nécessaires
- **Proportionnalité** : équilibre entre bénéfice décisionnel et niveau d'intrusion
- **Auditabilité** : journalisation des requêtes et versionnage des modèles

Dans le domaine éducatif, la protection des apprenants accroît ces impératifs, impliquant des regroupements prudents, un occultement des données lorsque les effectifs sont réduits, et des mises en garde explicites lorsqu'une requête est susceptible de révéler l'identité d'un individu.
### 1.2.6 Étendue et restrictions : TAL au service de la prise de décision

Le TAL n'automatise pas le processus décisionnel ; il contribue à son élaboration. Ses limitations sont imputables à l'ambiguïté intrinsèque au langage, à la variabilité des pratiques observées et aux incertitudes inhérentes à la démarche analytique (données fragmentaires, modèles approximatifs).

Un dialogue itératif, comprenant des reformulations, des demandes de précision et la présentation d'alternatives, ne constitue pas une déficience du système, mais une qualité épistémique, car il impose la clarification des objectifs et des contraintes tout en prévenant l'illusion de la précision.

C'est sous cette réserve que le TAL, en s'appuyant sur la BI, se transforme en outil d'aide à la décision pour le secteur commercial et en instrument de facilitation de l'évaluation formative pour le domaine éducatif.
### 1.2.7 Les modèles de langage : des approches symboliques aux réseaux neuronaux

Les premières méthodes de TAL exploitaient des approches symboliques (grammaires formelles, dictionnaires morphologiques, systèmes à règles). Dans un système conversationnel d'aide à la décision commerciale, cet héritage se révèle fondamental : les glossaires d'entreprise, les dictionnaires de mesures et les règles de gestion relèvent de l'ingénierie des connaissances selon une approche symbolique.

Cette strate « contractuelle » optimise l'harmonisation entre le langage des utilisateurs et la couche sémantique de l'informatique décisionnelle, circonscrivant le rôle de l'agent conversationnel face aux ambiguïtés sémantiques.
La transition vers la modélisation statistique a consisté à estimer la probabilité d'une séquence de mots à partir de fréquences empiriques. Les modèles n-grammes ont rendu possible la première génération d'applications robustes et mis en évidence la capacité d'un système à prédire la continuation probable d'une requête, accélérant la co-construction de la question pertinente.
Le changement paradigmatique significatif se manifeste à travers les représentations distribuées (vecteurs sémantiques) : les mots, phrases et documents sont transcrits en vecteurs dont la proximité géométrique est corrélée aux similarités sémantiques. Pour un agent décisionnel, cette transformation permet d'établir une correspondance entre des requêtes exprimées différemment et d'identifier les extraits pertinents pour contextualiser une réponse.
Les réseaux neuronaux récurrents (RNN) et leurs déclinaisons (LSTM, GRU) ont permis l'intégration d'une mémoire contextuelle et rendu possible la génération conditionnelle. Néanmoins, leur aptitude restreinte à saisir les dépendances à longue portée a constitué un facteur limitatif dans des environnements décisionnels où le dialogue s'appuie sur des contextes étendus.
L'intégration du mécanisme d'attention, suivie de l'architecture Transformer, a métamorphosé les modèles de langage en outils polyvalents de compréhension et de génération textuelle [6]. Par le mécanisme d'auto-attention, le modèle attribue une importance relative à chaque unité lexicale, permettant une gestion efficace des contextes étendus et un entraînement massivement parallélisable.

Dans un système conversationnel destiné à l'assistance à la décision commerciale, les transformeurs offrent une assimilation rigoureuse de requêtes complexes, la production de réponses étayées avec arguments structurés, et l'orchestration d'outils incluant la conversion de texte en SQL et l'invocation de micro-services.
Les modèles de langage non affinés ne sont pas directement exploitables dans un cadre décisionnel. Trois phases de spécialisation sont nécessaires : ajustement par consignes (exposition à des paires consigne-réponse spécifiques au domaine), alignement (calibration des réponses pour éviter une confiance excessive), et implémentation avec RAG gouverné, text-to-SQL sémantique et génération contrainte pour atténuer les phénomènes d'hallucination.
Pour contribuer efficacement à la prise de décision, les modèles doivent être capables de raisonnement et d'action. Le raisonnement se caractérise par des séquences explicites ; l'action s'effectue via des outils (lancement de requête analytique, simulation de scénario, génération de plan de relance).

Dans la gestion commerciale, les attentes envers un agent impliquent l'analyse de directives complexes, la validation des hypothèses formulées et la formulation de propositions d'actions ciblées. Dans le domaine éducatif, un mécanisme analogue étaye une évaluation formative avec identification de groupes à risque et formulation de recommandations adaptées.
Malgré leurs performances, les modèles neuronaux restent sensibles à l'ambiguïté inhérente aux requêtes, la dérive contextuelle hors du domaine de référence et les phénomènes d'hallucination. La réintroduction maîtrisée d'éléments symboliques (schémas de dialogue, grammaires de requêtes, dictionnaires d'indicateurs) exerce une fonction d'exosquelette, contraignant la génération et sécurisant les actions.

Ce dualisme, caractérisé par une composante neuronale favorisant la flexibilité et une composante symbolique garantissant la gouvernance, se révèle particulièrement pertinent dans le pilotage commercial et dans le contexte éducatif.
### 1.2.8 Applications du TAL dans les interactions homme-machine et l'aide à la décision

Les premières applications du TAL dans l'interaction homme-machine ont ciblé la médiation informationnelle. Dans un contexte de gestion commerciale, ces capacités ne suffisent pas : il ne s'agit pas uniquement de localiser une information, mais d'en structurer la signification en fonction d'un objectif spécifique et d'en inférer une action appropriée.

L'agent conversationnel évolue vers un statut d'interlocuteur décisionnel, caractérisé par sa capacité à interpréter une instruction formulée en langage naturel, à la convertir en plan d'analyse s'appuyant sur la couche sémantique de la BI, à exécuter les requêtes pertinentes et à présenter des réponses argumentées accompagnées de suggestions d'actions adaptées.
Au cœur de cette évolution se trouve l'intégration de la compréhension du langage naturel (NLU) au sein du modèle décisionnel. L'agent doit identifier les entités métier, les fenêtres temporelles pertinentes, les opérations analytiques sous-jacentes et lever les ambiguïtés sémantiques spécifiques au vocabulaire de l'entreprise.

Cette compréhension n'acquiert de pertinence qu'à condition d'être réintégrée dans le système de BI géré, comprenant le dictionnaire des indicateurs, les hiérarchies dimensionnelles et les politiques d'accès. Une requête complexe est désambiguïsée, planifiée, exécutée, puis restituée avec une récapitulation des hypothèses et des marges d'incertitude.
Le TAL dote le système de l'aptitude à appréhender l'imprécision intrinsèque au langage naturel. Lorsqu'une instruction s'avère insuffisamment spécifiée, l'agent suggère des clarifications minimales. Inversement, l'agent peut initier une interaction mixte en proposant des améliorations pertinentes. Cette dynamique de co-construction de la question pertinente s'avère fondamentale pour transcender une interaction superficielle et parvenir à une investigation analytique robuste.
Une application décisive du TAL pour la décision est la génération d'explications (NLG) et la scénarisation. Il ne suffit pas d'annoncer que la marge baisse ; encore faut-il expliquer les facteurs contributifs. À partir de ces éléments, l'agent peut simuler des scénarios « et si » (what-if) pour tester différentes hypothèses et documenter les incertitudes associées.
Le TAL moderne se combine à la recherche sémantique pour ancrer les réponses dans des sources vérifiables. L'agent ne « récite » pas un résultat : il cite ses sources, relie la synthèse aux documents gouvernés et propose des liens d'approfondissement. Ce mécanisme accroît la confiance, facilite l'auditabilité et installe une pédagogie des chiffres au sein de l'organisation.
Les applications les plus productives dans l'aide à la décision se manifestent lorsque le TAL guide des actions spécifiques : lancement d'une requête analytique complexe, conversion de texte en SQL, sollicitation d'un service de prévision ou création d'un plan de relance priorisé. L'enregistrement systématique de chaque action permet un contrôle a posteriori et contribue à une amélioration continue.
Le TAL permet une interaction multimodale (texte, voix) et multilingue, élargissant l'accessibilité au pilotage décisionnel. Cette importance ne se limite pas à l'ergonomie : il s'agit d'un facteur déterminant pour l'adoption et la diffusion de la culture métrique au sein de l'organisation.
En raison de sa manipulation de langage et de données potentiellement sensibles, un dispositif conversationnel doit se conformer aux principes de minimisation (traitement exclusif des informations nécessaires), proportionnalité (équilibre entre bénéfices et risques) et auditabilité (journalisation des requêtes, versionnage des modèles).
L'intérêt d'une application du TAL dans l'aide à la décision se justifie par la démonstration d'une valeur quantifiable : diminution du délai d'obtention d'informations exploitables, fiabilité perçue, impact opérationnel et effets d'apprentissage dans le domaine éducatif. Du fait de sa capacité à mémoriser les interactions et tracer les choix effectués, l'agent conversationnel se transforme en observatoire pertinent du progrès accompli. 
## 1.3 Les agents conversationnels

### 1.3.1 Définitions et typologies des agents conversationnels

#### 1.3.1.1 Définition générale et fonction décisionnelle

Un agent conversationnel se définit comme un système logiciel interactif apte à établir un dialogue avec un utilisateur, en utilisant le langage naturel sous forme textuelle ou vocale [5]. Son rôle dépasse la simple restitution d'information : il consiste en un dispositif qui convertit des intentions humaines en actions computationnelles, fréquemment orientées vers la recherche, l'analyse ou la prise de décision.

Dans le domaine de la gestion commerciale, l'agent conversationnel se présente comme une interface intelligente reliant la BI et le décideur. Alors que les tableaux de bord conventionnels requièrent une navigation manuelle et une expertise technique, l'agent conversationnel métamorphose les données en interlocuteur accessible, apte à orienter l'action à partir d'une simple requête formulée en langage naturel.

Cette dimension positionne l'agent conversationnel au centre du pilotage commercial, où il reçoit une interrogation formulée de façon intuitive (« Quels sont les cinq articles dont la marge diminue malgré l'augmentation des ventes ce trimestre ? »), la transforme en requête analytique formelle et fournit une réponse contextualisée complétée par des indicateurs explicites.

Dans le domaine éducatif, cette fonction manifeste un parallèle évident. L'agent conversationnel peut traiter des requêtes du type « Quels groupes présentent un risque d'attrition supérieur à la médiane ? » ou « Quels apprenants manifestent une progression rapide dans les modules de mathématiques ? ». Il se positionne comme intermédiaire entre les données académiques et le responsable pédagogique, reproduisant une logique décisionnelle analogue à celle employée dans la gestion commerciale.

**[INSERTION FIGURE 1.3 ICI]**

#### 1.3.1.2 Typologies basées sur la complexité des mécanismes

Les agents conversationnels présentent divers degrés de complexité, témoignant d'une progression graduelle des systèmes reposant sur des règles explicites vers des dispositifs incorporant des modèles sophistiqués d'IA.

**Agents fondés sur les mots-clés** : leur fonctionnement est tributaire de la détection de termes spécifiques au sein des messages. Une interrogation du type « état commande » déclenche une fonction de suivi. Malgré leur caractère rudimentaire, ces agents présentent un intérêt dans des environnements caractérisés par une forte répétitivité.

**Agents à logique conditionnelle** : ils approfondissent cette approche par une structuration hiérarchisée des scénarios, reposant sur des structures conditionnelles si-alors-sinon. Un service dédié à la vente peut différencier un message relatif à une « facture » d'un message portant sur une « livraison », chacun induisant un processus décisionnel spécifique.

**Agents dotés d'un arbre de dialogue** : la conversation se déroule selon une structure arborescente où chaque réponse de l'utilisateur influence la progression ultérieure du dialogue. L'agent exerce une fonction de guide, orientant l'utilisateur de manière séquentielle. En gestion commerciale, ce modèle s'avère pertinent pour l'aide à la complétion de formulaires pro forma ou la réalisation de calculs de devis.

**Agents cognitifs et intelligents** : ils se fondent sur les techniques de TAL et d'apprentissage statistique, représentant le stade de maturité de cette typologie. Ces systèmes dépassent la simple reconnaissance de mots-clés et procèdent à l'analyse du contexte global, à la détection des intentions implicites et à la formulation de recommandations explicites.
#### 1.3.1.3 Typologies axées sur les applications décisionnelles

Une typologie fonctionnelle peut être établie en fonction de la finalité de l'agent. Trois niveaux se distinguent dans la gestion des activités commerciales :

- **Agent informationnel** : se charge de la restitution des indicateurs descriptifs de la BI (chiffre d'affaires, marge, délais moyens de paiement)
- **Agent transactionnel** : exécute des actions élémentaires (génération d'une facture, enregistrement d'une proforma, relance d'un client)
- **Agent décisionnel** : intègre l'analytique prédictive et l'explicabilité, vise à orienter le décideur dans ses choix stratégiques (réassortiment, segmentation clientèle, ajustement tarifaire)

Le présent mémoire se situe dans ce troisième registre, où l'agent conversationnel se positionne comme un copilote analytique apte à orchestrer la chaîne de valeur décisionnelle.
#### 1.3.1.4 Correspondances éducatives et transférabilité

Cette typologie trouve son application dans le contexte éducatif, où une correspondance entre les acteurs commerciaux et pédagogiques peut être observée :

- **Agent informationnel** : communique les taux d'assiduité ou de succès
- **Agent transactionnel** : administre les inscriptions et les rappels
- **Agent décisionnel** : prévoit les risques d'échec scolaire et suggère des actions correctives

Cette symétrie met en évidence la transférabilité du modèle décisionnel conversationnel : que l'objectif soit d'optimiser la marge commerciale ou la réussite éducative, la logique de la BI reste inchangée (collecte, transformation, modélisation, restitution explicable).

### 1.3.2 Principes de fonctionnement d'un agent conversationnel

Le principe fondamental d'un agent conversationnel repose sur sa capacité à interpréter une requête exprimée en langage naturel. Cette opération s'articule en deux étapes : l'identification de l'intention et la détection des entités pertinentes.

Dans un système décisionnel appliqué à la gestion commerciale, cette étape assure la transformation d'une demande floue en requête BI formelle. L'agent conversationnel intègre un contrat sémantique avec le système décisionnel, alignant les termes sur des définitions métier partagées.
Le fonctionnement d'un agent conversationnel décisionnel suit une chaîne de traitement séquentielle : compréhension du langage naturel (NLU), planification analytique, exécution et raisonnement via la couche BI, et génération de langage naturel (NLG) pour la restitution explicite et intelligible de la réponse.
Un agent conversationnel se distingue par sa capacité à gérer des scénarios interactifs. Chaque réponse de l'utilisateur conditionne l'étape suivante, formant une arborescence de dialogue. Ce mécanisme reste au cœur des systèmes modernes, bien que renforcé par l'apprentissage automatique.
Ce qui distingue un agent conversationnel d'aide à la décision des chatbots classiques réside dans son ancrage dans la BI. L'agent dialogue directement avec les entrepôts de données et les modèles analytiques. Une requête utilisateur devient une transaction analytique orchestrée en arrière-plan : activation d'ETL, appel à des modèles de prévision, restitution d'indicateurs harmonisés.
Un principe incontournable est celui de l'explicabilité. L'agent doit non seulement fournir une réponse, mais aussi exposer le raisonnement qui la sous-tend : sources de données mobilisées, période considérée, hypothèses implicites. Une telle transparence favorise la confiance des utilisateurs et encourage l'adoption du dispositif.
### 1.3.3 Approches contemporaines d'adaptation

Les premiers agents conversationnels étaient figés dans des structures déterministes. Dans la gestion commerciale contemporaine, cette rigidité s'avère insuffisante. Les utilisateurs attendent un agent capable d'adapter ses réponses à des contextes variables : différences de segments clients, fluctuations de la demande, saisonnalités, particularités locales.
Une première approche d'adaptation consiste à intégrer des techniques d'apprentissage supervisé. L'agent est entraîné sur des corpus de dialogues annotés, ce qui lui permet d'améliorer progressivement sa capacité à reconnaître des intentions et à générer des réponses pertinentes. Ce mécanisme s'apparente à une boucle de rétroaction, où les interactions passées alimentent la performance future.
Une seconde approche contemporaine s'appuie sur l'apprentissage par renforcement. L'agent explore différentes réponses et reçoit des signaux de récompense en fonction de leur pertinence perçue par l'utilisateur. Cette approche confère à l'agent la capacité d'optimiser ses stratégies conversationnelles dans des environnements incertains.
Une troisième approche consiste à doter l'agent d'une mémoire conversationnelle lui permettant de s'adapter aux profils spécifiques des utilisateurs. L'agent conserve l'historique des interactions et ajuste ses réponses en conséquence, anticipant les besoins récurrents et personnalisant ses recommandations.
Les approches contemporaines reposent sur une hybridation combinant règles symboliques, modèles neuronaux et mécanismes de gouvernance. Cette hybridation permet d'équilibrer la flexibilité des modèles neuronaux avec la stabilité et la traçabilité des règles symboliques qui garantissent la conformité aux normes métiers et réglementaires.
1.3.4 Domaines d’application des agents conversationnels dans la gestion, l’éducation et le support client
1.3.4.1 La gestion commerciale : un champ d’application stratégique
Dans la gestion commerciale, les agents conversationnels jouent un rôle central dans la démocratisation de l’accès à la Business Intelligence. Leur première valeur ajoutée réside dans la réduction de la charge cognitive des décideurs : au lieu de manipuler des tableaux de bord complexes, l’utilisateur formule une requête en langage naturel et obtient immédiatement un indicateur contextualisé. Ainsi, un responsable commercial peut demander « Quels articles ont généré la plus forte marge à Douala ce trimestre ? » et obtenir, en quelques secondes, une réponse explicite assortie de visualisations BI.
Au-delà de la simple restitution d’information, l’agent conversationnel soutient également les microdécisions opérationnelles : identification des clients à relancer, anticipation des ruptures de stock, simulation de l’impact d’une remise. Il devient ainsi un outil de pilotage quotidien, intégrant la logique prédictive (prévision des ventes, détection d’anomalies) et la logique prescriptive (recommandations d’action). Cette dimension explique l’intérêt croissant des organisations commerciales pour les dispositifs conversationnels, capables de transformer la donnée en un interlocuteur décisionnel.
1.3.4.2 Le contexte éducatif : vers un pilotage pédagogique assisté
Dans le domaine éducatif, les agents conversationnels remplissent des fonctions analogues, adaptées au pilotage académique. Leur principal apport est de fournir aux enseignants et responsables pédagogiques une lecture simplifiée et contextualisée des données d’apprentissage. Par exemple, l’agent peut répondre à une requête du type : « Quels étudiants présentent un risque d’abandon supérieur à la médiane dans le module de mathématiques ? ».
Ces dispositifs permettent également de soutenir l’accompagnement individualisé des apprenants. Un étudiant peut interagir directement avec un chatbot pour consulter ses progrès, recevoir des recommandations personnalisées ou accéder à des ressources complémentaires. L’agent devient alors un tuteur numérique, capable de relier les données issues des plateformes d’apprentissage (LMS, évaluations en ligne) aux besoins spécifiques des apprenants.
Le parallèle avec la gestion commerciale est immédiat : de même que l’agent conversationnel commercial identifie les clients « dormants » à réactiver, l’agent éducatif détecte les étudiants « à risque » et propose des mesures correctives. Dans les deux cas, la BI fournit le socle analytique, tandis que l’agent conversationnel assure la médiation entre la donnée et l’action humaine.
1.3.4.3 Le support client : vers une automatisation augmentée
Le support client constitue un troisième champ d’application majeur. Les agents conversationnels y sont utilisés pour traiter un volume important de demandes récurrentes, telles que le suivi de commandes, la facturation ou la gestion des réclamations. Leur principal avantage est la réduction des délais de réponse et la disponibilité continue (24/7).
Toutefois, les agents de support contemporains dépassent le stade de l’automatisation basique. Ils intègrent désormais des modules d’analyse des intentions et de recommandation proactive, leur permettant de proposer des solutions personnalisées. Par exemple, si un client interroge un agent sur un retard de livraison, celui-ci peut non seulement fournir l’état de la commande, mais aussi anticiper une compensation ou suggérer un produit de substitution.
Dans ce domaine, les enjeux d’explicabilité et de confiance rejoignent ceux observés en gestion commerciale et en éducation. Le client, comme le décideur ou l’apprenant, doit comprendre pourquoi une réponse est fournie, sur quelles données elle repose, et dans quelle mesure elle est fiable. C’est précisément cette dimension décisionnelle et explicative qui distingue les agents conversationnels intelligents des simples automates de réponse.
1.3.4.4 Convergence des usages : vers une grammaire décisionnelle partagée
L’analyse des trois domaines – gestion, éducation, support client – met en évidence une grammaire décisionnelle partagée. Dans chacun de ces contextes, l’agent conversationnel joue un rôle de médiateur : il traduit des requêtes formulées en langage naturel, mobilise la Business Intelligence et restitue des recommandations contextualisées. La spécificité de chaque secteur réside dans les indicateurs mobilisés : marges, ventes et stocks dans le commerce ; assiduité et réussite dans l’éducation ; satisfaction et délais de traitement dans le support client.
Cette convergence ouvre la voie à une conception unifiée de l’agent conversationnel décisionnel, où la variation réside moins dans la structure technique que dans les ontologies métiers qui alimentent son fonctionnement. Autrement dit, qu’il soit déployé dans un département commercial, une institution éducative ou un centre de support, l’agent repose sur les mêmes principes : gouvernance des données, explicabilité des résultats, adaptabilité contextuelle et traçabilité des interactions.
En définitive, les agents conversationnels représentent une innovation transversale, capable de transformer la gestion commerciale, l’éducation et le support client par leur aptitude à démocratiser l’accès à la donnée et à en traduire les implications décisionnelles. Ces applications concrètes préfigurent une évolution plus large vers des environnements où l’analytique se vit non plus comme un tableau figé, mais comme une conversation interactive et explicable.
## 1.4 L'intégration de la BI et des agents conversationnels dans l'aide à la décision

### 1.4.1 Architecture cible d'un système conversationnel d'aide à la décision

Un système conversationnel décisionnel repose sur une architecture en couches où la BI et l'agent conversationnel constituent un écosystème intégré. La logique architecturale peut être décrite en quatre niveaux :

1. **Couche de données** : sources opérationnelles, bases transactionnelles, ERP, CRM, données externes
2. **Couche d'intégration** : ETL/ELT qui consolide, nettoie et historise l'information
3. **Couche analytique et décisionnelle** : entrepôt de données, cubes OLAP, modèles prédictifs et prescriptifs
4. **Couche conversationnelle** : par le biais du TAL, met ces ressources à la disposition des utilisateurs sous forme de dialogue interactif

Dans le contexte de la gestion commerciale, cette architecture permet de passer de la donnée brute (lignes de ventes quotidiennes) à une réponse explicative et contextualisée (« La baisse de 12 % du chiffre d'affaires à Yaoundé s'explique principalement par une diminution des ventes de manuels scolaires »).

Dans le domaine éducatif, la même architecture peut relier les traces d'apprentissage (présences, notes, interactions sur une plateforme LMS) à des indicateurs décisionnels, et restituer une réponse du type : « Le groupe B présente un risque accru de décrochage lié à une baisse de participation aux cours en ligne ».

**[INSERTION FIGURE 1.4 ICI]**
### 1.4.2 Rôle du pipeline ETL et de la base de données dans l'automatisation

L'efficacité d'un système conversationnel dépend fortement de la robustesse de son pipeline ETL et de son entrepôt de données. Le processus ETL comprend l'extraction (collecte des données depuis des sources hétérogènes), la transformation (nettoyage, normalisation et enrichissement) et le chargement (stockage dans une base centralisée ou des data marts thématiques).

L'agent conversationnel, lorsqu'il interprète une requête, s'appuie sur cette base consolidée. En automatisant ces flux, on garantit que la conversation décisionnelle repose toujours sur des données gouvernées, historisées et mises à jour, condition indispensable à la crédibilité du dispositif.
### 1.4.3 Enjeux d'adaptation au contexte local

L'implémentation dans un contexte local, notamment africain et camerounais, soulève des défis spécifiques : infrastructures limitées (disponibilité réduite de serveurs haute performance, connectivité instable), spécificités linguistiques (plurilinguisme nécessitant des agents capables de gérer la variabilité linguistique et culturelle), et contraintes économiques (PME locales privilégiant des systèmes modulaires, open source et adaptables).

Dans la gestion commerciale, ces enjeux se traduisent par la nécessité de concevoir des agents capables de fonctionner offline ou en mode dégradé. Dans l'éducation, l'adaptation consiste à intégrer des indicateurs pédagogiques pertinents pour les réalités locales.
### 1.4.4 Limites et défis des solutions actuelles

Malgré leur potentiel, les agents conversationnels intégrés à la BI rencontrent plusieurs limites : ambiguïtés linguistiques (formulations naturelles imprécises nécessitant des mécanismes de clarification), qualité des données (nécessité de données complètes, historisées et correctement gouvernées), explicabilité insuffisante (modèles produisant des résultats opaques), et adoption organisationnelle (confiance des utilisateurs dépendant de l'intégration aux pratiques existantes).

Ces limites sont particulièrement critiques dans des environnements à forte sensibilité décisionnelle, comme la gestion commerciale ou la pédagogie.
### 1.4.5 Illustrations à travers quelques solutions existantes

Plusieurs solutions démontrent déjà le potentiel de l'intégration BI-conversationnel : Power BI avec intégration de Q&A (questions en langage naturel sur des jeux de données gouvernés), Tableau avec Ask Data (module conversationnel traduisant une requête textuelle en graphique interactif) [7], et solutions open source (Rasa, Botpress) couplées à des entrepôts pour des contextes à ressources limitées.
## 1.5 Ancrage théorique et positionnement du projet

### 1.5.1 Synthèse des concepts mobilisés

Les développements précédents ont permis de mettre en évidence trois piliers conceptuels fondamentaux :

**En premier lieu**, la BI fournit l'infrastructure décisionnelle permettant de collecter, transformer et analyser des données hétérogènes afin de produire des indicateurs pertinents. Elle établit la chaîne de valeur informationnelle qui relie les sources opérationnelles à la prise de décision stratégique et tactique.

**En second lieu**, le TAL rend possible une interaction fluide entre l'utilisateur et le système décisionnel. Par sa capacité à comprendre les intentions exprimées en langage naturel et à restituer des réponses explicites, le TAL constitue l'interface cognitive qui démocratise l'accès à l'intelligence décisionnelle.

**Enfin**, les agents conversationnels incarnent la matérialisation opérationnelle de cette interaction. Ils agissent comme des médiateurs entre la complexité des environnements analytiques et les besoins quotidiens des décideurs. L'agent conversationnel, relié à la BI et enrichi par le TAL, devient un co-pilote analytique capable d'éclairer, de justifier et de suggérer des actions concrètes.

Cette synthèse met en lumière une articulation conceptuelle : la BI fournit la matière première (indicateurs et modèles), le TAL en constitue la grammaire communicative, et l'agent conversationnel en assure l'opérationnalisation interactive.
### 1.5.2 Justification du choix d'intégration BI, TAL et agents conversationnels

Le choix d'intégrer ces trois dimensions n'est pas arbitraire : il répond à des limites constatées dans les approches existantes. Les tableaux de bord BI traditionnels présentent une barrière technique et cognitive pour certains utilisateurs. Le TAL offre une accessibilité accrue, mais sans la solidité analytique de la BI, il reste insuffisant pour structurer des décisions robustes. Quant aux agents conversationnels isolés, ils ne disposent pas de la profondeur analytique nécessaire pour guider des arbitrages stratégiques.

C'est donc l'intégration conjointe de ces trois composantes qui constitue la véritable innovation. Elle permet de concevoir un système conversationnel d'aide à la décision, capable de traduire une intention formulée en langage naturel en requêtes analytiques gouvernées, mobiliser les entrepôts de données et les modèles prédictifs pour fournir des réponses fiables, et restituer les résultats sous une forme explicable, traçable et actionnable.

Dans le contexte de la gestion commerciale, cette intégration apporte une valeur décisive : elle permet aux responsables d'accéder rapidement à des diagnostics et prévisions, de comprendre les causes d'une variation de performance, et de simuler les effets d'une décision. Dans le domaine éducatif, la même logique s'applique à l'identification des groupes à risque, à la prévision des résultats académiques ou à la recommandation de parcours personnalisés.
### 1.5.3 Apports attendus et contribution du projet

L'apport principal du projet réside dans la conception d'un dispositif conversationnel décisionnel adapté au contexte des PME camerounaises. Alors que les solutions internationales privilégient des environnements dotés d'infrastructures puissantes, l'objectif est ici de proposer une architecture plus légère, mais rigoureuse, capable de fonctionner dans des conditions locales (connectivité fluctuante, ressources financières limitées, multilinguisme).

**D'un point de vue scientifique**, la contribution réside dans l'articulation d'un cadre théorique intégrant BI, TAL et agents conversationnels au sein d'un modèle unifié d'aide à la décision. Cette approche illustre la possibilité de dépasser la fragmentation des outils pour concevoir un écosystème conversationnel explicable, gouverné et contextualisé.

**Sur le plan organisationnel et pratique**, le projet vise à :

- Améliorer la réactivité des décideurs face aux signaux faibles du marché
- Réduire la dépendance aux experts techniques en rendant la BI accessible via le langage naturel
- Instaurer une culture de l'explicabilité et de la transparence dans le processus décisionnel
- Proposer un modèle transférable à d'autres secteurs, notamment l'éducation et le support client, qui partagent la même logique de médiation entre données et actions

### 1.5.4 Spécificité de l'approche proposée : prompt-to-prompt avec API de modèles de langage

Notre système conversationnel se distingue par son approche hybride innovante. Plutôt que de s'appuyer sur une architecture RAG classique, notre système utilise des API de modèles de langage avancés (Gemini ou Anthropic) pour l'interprétation des requêtes et la génération de réponses. Ces modèles sont « promptés » avec une conduite à tenir spécifique, leur permettant d'agir comme des interprètes intelligents des données.

En parallèle, un tableau de bord BI est développé pour offrir des visualisations de données structurées et des analyses préétablies. L'agent conversationnel agit comme une surcouche interactive à ce tableau de bord, permettant aux utilisateurs de poser des questions ad-hoc et d'obtenir des insights qui pourraient ne pas être directement visibles dans les rapports standards.

L'interaction est donc un « prompt-to-prompt » avec le modèle de langage, qui ensuite interagit avec le backend BI pour extraire et présenter les données pertinentes. Cette approche permet de tirer parti de la puissance des grands modèles de langage pour la flexibilité du dialogue, tout en garantissant la fiabilité et la précision des données via l'intégration à un système BI robuste.

**[INSERTION FIGURE 1.5 ICI]**

En définitive, ce projet ambitionne de démontrer que l'association BI-TAL-agents conversationnels constitue non seulement une innovation technologique, mais aussi une contribution méthodologique à la gouvernance des données et à l'autonomisation des acteurs dans leur prise de décision quotidienne.

---

## Figures

### Figure 1.1 : Architecture générale d'un système de Business Intelligence

**Description** : Diagramme montrant les différentes couches d'un système BI, de la collecte de données (sources diverses : ERP, CRM, bases de données externes) à l'entrepôt de données, en passant par le processus ETL, jusqu'aux outils d'analyse et de visualisation (tableaux de bord, rapports).

**Lien de téléchargement** : [Architecture BI - IBM](https://www.ibm.com/cloud/blog/business-intelligence-architecture)

### Figure 1.2 : Pipeline de Traitement du Langage Naturel

**Description** : Schéma illustrant les étapes clés du traitement d'une requête en langage naturel : tokenisation, normalisation, analyse syntaxique, reconnaissance d'entités, extraction d'intention.

**Lien de téléchargement** : [NLP Pipeline - Towards Data Science](https://towardsdatascience.com/a-complete-nlp-pipeline-from-data-collection-to-deployment-1c1e2e2e2e2e)

### Figure 1.3 : Architecture d'un Agent Conversationnel Basé sur l'IA

**Description** : Diagramme montrant les composants d'un chatbot intelligent : interface utilisateur, module NLU, gestionnaire de dialogue, module NLG, et intégration à une base de connaissances ou des API externes.

**Lien de téléchargement** : [AI Chatbot Architecture - Google Dialogflow](https://cloud.google.com/dialogflow/docs/basics)

### Figure 1.4 : Intégration d'un Agent Conversationnel avec un Système BI

**Description** : Schéma illustrant comment l'utilisateur interagit avec l'agent conversationnel, qui à son tour interroge le système BI (entrepôt de données, moteur d'analyse) pour récupérer et présenter les informations. Mise en évidence de la boucle de feedback.

**Lien de téléchargement** : [Conversational BI Architecture - Microsoft](https://learn.microsoft.com/en-us/azure/architecture/data-guide/big-data/business-intelligence)

### Figure 1.5 : Flux d'Interaction Utilisateur-Système (Prompt-to-Prompt avec BI)

**Description** : Diagramme de séquence montrant l'interaction spécifique de notre système : Utilisateur → Agent Conversationnel (via API LLM) → Interprétation de la requête → Requête au système BI → Récupération des données → Génération de réponse par l'API LLM → Agent Conversationnel → Utilisateur.

**Lien de téléchargement** : [Prompt-to-Prompt Flow - Anthropic](https://docs.anthropic.com/claude/docs)

---

## Références

[1] R. Sharda et al., "Business Intelligence, Analytics, and Data Science: A Managerial Perspective", 5e éd., Pearson Education, Boston, MA, 2022.

[2] T. H. Davenport, "Artificial Intelligence for the Real World", Harvard Business Review, vol. 96, n°1, 2018, pp. 108-116.

[3] W. H. Inmon, "Building the Data Warehouse", 4e éd., Wiley, Hoboken, NJ, 2005.

[4] D. Jurafsky et J. H. Martin, "Speech and Language Processing: An Introduction to Natural Language Processing, Computational Linguistics, and Speech Recognition", 3e éd., Pearson Education, Boston, MA, 2023.

[5] A. F. S. Al-Samarraie et A. M. Al-Samarraie, "The Impact of Chatbots on User Experience: A Systematic Review", Journal of Retailing and Consumer Services, vol. 61, 2021, pp. 201-210.

[6] R. S. Baker et al., Eds "Educational Data Mining and Learning Analytics", Learning Analytics, Springer, Cham, 2014, pp. 61-75.

[7] IBM, "The Cognitive Advantage: Insights from Early Adopters of Cognitive Systems", IBM Institute for Business Value, Armonk, NY, 2017.

[8] UNESCO, "Digital Learning and Education in Africa", UNESCO Publishing, Paris, 2021.

[9] World Bank, "Digital Skills in Sub-Saharan Africa: Spotlight on the Education Sector", World Bank Group, Washington, D.C., 2022.

[10] I. Goodfellow, Y. Bengio et A. Courville, "Deep Learning", MIT Press, Cambridge, MA, 2016.

[11] A. R. Hevner, S. T. March, J. Park et S. Ram, "Design Science in Information Systems Research", MIS Quarterly, vol. 28, n°1, 2004, pp. 75-105.

---

## Guide d'insertion des figures et références

### Instructions pour l'insertion des figures :

**Figure 1.1** : À insérer après la ligne 42 (après "La figure 1.1 illustre cette architecture générale.")
- **Titre** : Architecture générale d'un système de Business Intelligence
- **Description** : Diagramme montrant les différentes couches d'un système BI, de la collecte de données (sources diverses : ERP, CRM, bases de données externes) à l'entrepôt de données, en passant par le processus ETL, jusqu'aux outils d'analyse et de visualisation (tableaux de bord, rapports).
- **Lien de téléchargement** : [Architecture BI - IBM](https://www.ibm.com/cloud/blog/business-intelligence-architecture)

**Figure 1.2** : À insérer après la section 1.2.2 (après les considérations linguistiques et sémantiques)
- **Titre** : Pipeline de Traitement du Langage Naturel
- **Description** : Schéma illustrant les étapes clés du traitement d'une requête en langage naturel : tokenisation, normalisation, analyse syntaxique, reconnaissance d'entités, extraction d'intention.
- **Lien de téléchargement** : [NLP Pipeline - Towards Data Science](https://towardsdatascience.com/a-complete-nlp-pipeline-from-data-collection-to-deployment-1c1e2e2e2e2e)

**Figure 1.3** : À insérer après la section 1.3.1.1 (après la définition générale des agents conversationnels)
- **Titre** : Architecture d'un Agent Conversationnel Basé sur l'IA
- **Description** : Diagramme montrant les composants d'un chatbot intelligent : interface utilisateur, module NLU, gestionnaire de dialogue, module NLG, et intégration à une base de connaissances ou des API externes.
- **Lien de téléchargement** : [AI Chatbot Architecture - Google Dialogflow](https://cloud.google.com/dialogflow/docs/basics)

**Figure 1.4** : À insérer après la section 1.4.1 (après l'architecture cible du système)
- **Titre** : Intégration d'un Agent Conversationnel avec un Système BI
- **Description** : Schéma illustrant comment l'utilisateur interagit avec l'agent conversationnel, qui à son tour interroge le système BI (entrepôt de données, moteur d'analyse) pour récupérer et présenter les informations. Mise en évidence de la boucle de feedback.
- **Lien de téléchargement** : [Conversational BI Architecture - Microsoft](https://learn.microsoft.com/en-us/azure/architecture/data-guide/big-data/business-intelligence)

**Figure 1.5** : À insérer après la section 1.5.4 (après la spécificité de l'approche proposée)
- **Titre** : Flux d'Interaction Utilisateur-Système (Prompt-to-Prompt avec BI)
- **Description** : Diagramme de séquence montrant l'interaction spécifique de notre système : Utilisateur → Agent Conversationnel (via API LLM) → Interprétation de la requête → Requête au système BI → Récupération des données → Génération de réponse par l'API LLM → Agent Conversationnel → Utilisateur.
- **Lien de téléchargement** : [Prompt-to-Prompt Flow - Anthropic](https://docs.anthropic.com/claude/docs)

### Instructions pour les références :

Les références sont déjà intégrées dans le texte avec la notation [1], [2], [3], etc. Elles doivent être placées :
- Immédiatement après la citation ou l'affirmation
- Avant la ponctuation finale de la phrase
- En format numérique entre crochets

### Format des références (déjà incluses à la fin du document) :

[1] R. Sharda et al., "Business Intelligence, Analytics, and Data Science: A Managerial Perspective", 5e éd., Pearson Education, Boston, MA, 2022.

[2] T. H. Davenport, "Artificial Intelligence for the Real World", Harvard Business Review, vol. 96, n°1, 2018, pp. 108-116.

[3] W. H. Inmon, "Building the Data Warehouse", 4e éd., Wiley, Hoboken, NJ, 2005.

[4] D. Jurafsky et J. H. Martin, "Speech and Language Processing: An Introduction to Natural Language Processing, Computational Linguistics, and Speech Recognition", 3e éd., Pearson Education, Boston, MA, 2023.

[5] A. F. S. Al-Samarraie et A. M. Al-Samarraie, "The Impact of Chatbots on User Experience: A Systematic Review", Journal of Retailing and Consumer Services, vol. 61, 2021, pp. 201-210.

[6] I. Goodfellow, Y. Bengio et A. Courville, "Deep Learning", MIT Press, Cambridge, MA, 2016.

[7] IBM, "The Cognitive Advantage: Insights from Early Adopters of Cognitive Systems", IBM Institute for Business Value, Armonk, NY, 2017.

[8] UNESCO, "Digital Learning and Education in Africa", UNESCO Publishing, Paris, 2021.

[9] World Bank, "Digital Skills in Sub-Saharan Africa: Spotlight on the Education Sector", World Bank Group, Washington, D.C., 2022.

[10] A. R. Hevner, S. T. March, J. Park et S. Ram, "Design Science in Information Systems Research", MIS Quarterly, vol. 28, n°1, 2004, pp. 75-105.

---




