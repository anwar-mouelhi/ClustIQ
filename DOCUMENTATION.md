# DOCUMENTATION — ClustIQ : Customer 360 & Segmentation Intelligente des Clients

**Projet de stage de fin d'études** — STB (Société Tunisienne de Banque)  
**Sujet** : Customer 360 et segmentation intelligente des clients  
**Durée** : 2 mois  
**Date** : 2024-2025

---

## Table des matières

1. [Contexte et objectifs](#1-contexte-et-objectifs)
2. [Architecture générale](#2-architecture-générale)
3. [Choix techniques et justifications](#3-choix-techniques-et-justifications)
4. [Démarche et méthodologie](#4-démarche-et-méthodologie)
5. [Indicateurs (KPI) du dashboard](#5-indicateurs-kpi-du-dashboard)
6. [Généricité et adaptabilité à la STB](#6-généricité-et-adaptabilité-à-la-stb)
7. [Limites et axes d'amélioration](#7-limites-et-axes-damélioration)

---

## 1. Contexte et objectifs

### 1.1 Le problème métier

Une banque moderne doit comprendre ses clients de manière **holistique** pour :

- **Réduire le risque crédit** : prédire les défauts de paiement en analysant les habitudes de transaction et l'endettement
- **Augmenter la rentabilité par client** : identifier les opportunités de cross-sell (crédits supplémentaires, assurances, produits d'investissement) basées sur le profil réel d'utilisation
- **Améliorer la rétention** : détecter les clients à risque d'attrition (peu actifs, fort endettement) et intervenir proactivement
- **Optimiser les ressources** : segmenter la clientèle pour adapter les stratégies marketing, de pricing et de support par segment

Une **vue 360° du client** fédère toutes les données (transactions, comptes, crédits, cartes, produits) pour offrir une **vision unifiée** de chaque client, indépendamment de la canalisation ou de l'historique fragmenté des systèmes legacy.

### 1.2 Choix du dataset Berka comme proxy

Le projet utilise le **dataset PKDD'99 Berka**, données anonymisées d'une banque tchèque, pour deux raisons stratégiques :

1. **Confidentialité bancaire** : les données réelles STB sont sensibles ; Berka est public, complet (clients, comptes, transactions, crédits, cartes, produits) et structurellement proche d'une banque réelle.
2. **Démonstration et validation** : concevoir et tester l'architecture sur Berka permet de valider le pipeline, les métriques et les segments *avant* de brancher les vraies données.

**La clé du projet** : l'architecture est **entièrement générique**. Un simple fichier de mapping YAML (voir [mapping_stb.yaml](#62-brancher-les-données-stb)) permet de passer de Berka à la STB sans toucher à une seule ligne de code SQL, pandas ou Streamlit.

---

## 2. Architecture générale

### 2.1 Vue d'ensemble du pipeline

ClustIQ s'exécute en **5 étapes séquentielles**, chacune une cible `make` du même nom :

```
①  make database       → provision.py
    Création du schéma MySQL vide
    ↓
②  make ingestion      → ingest.py
    Chargement CSV → tables staging (stg_*)
    ↓
③  make transformation → transform.py
    Nettoyage, jointures, agrégations
    Écriture des tables customer_attributes, agg_loans/cards/products
    ↓
④  make segmentation   → segment.py
    Feature engineering + K-Means clustering
    Écriture de customer_segments
    ↓
⑤  make dashboard      → app.py (Streamlit)
    Serveur web interactif
    Lecture de customer_360 et customer_segments
```

La commande `make all` enchaîne automatiquement les 4 premières étapes. Le dashboard se lance séparément (`make dashboard`), car c'est un serveur long-running, pas une étape ponctuelle.

### 2.2 Le schéma canonique : contrat fixe entre étapes

Le fichier [config/schema.yaml](config/schema.yaml) définit la structure **immuable** que doit respecter chaque ligne de la vue `customer_360`. Cette vue est le **contrat** entre :

- L'**ingestion** et la **transformation** (tables staging → agrégations)
- La **transformation** et la **segmentation** (agrégations → features client)
- La **segmentation** et le **dashboard** (segments + features → visualisations)

Grâce à ce contrat, **changer de source de données (Berka → STB) n'affecte que le mapping YAML**, jamais la logique métier.

Colonnes du schéma canonique (chaque ligne = 1 transaction du client) :

| Groupe | Colonnes | Type | Rôle |
|--------|----------|------|-----|
| **Client** | `customer_id`, `age_range`, `gender`, `region`, `customer_category` | string | Identité et profil démographique |
| **Compte** | `account_id`, `account_type`, `account_open_date`, `account_balance` | string, date, decimal | Gestion de compte |
| **Transaction** | `transaction_id`, `transaction_date`, `transaction_amount`, `transaction_type`, `transaction_frequency` | string, date, decimal, int | Activité transactionnelle (fréquence = agrégat client) |
| **Produit** | `product_type`, `product_subscription_date` | string, date | Produits souscrits |
| **Crédit** | `loan_amount`, `loan_status` | decimal, string | Endettement |
| **Carte** | `card_type` | string | Moyens de paiement |

### 2.3 Tables et vues MySQL

Tous les noms de tables sont paramétrés dans [config/database.yaml](config/database.yaml) — **aucun n'est codé en dur** dans le SQL ou Python.

| Table / Vue | Type | Écrite par | Rôle |
|-------------|------|-----------|------|
| **stg_customers** | Table staging | ② Ingestion | Clients bruts (id, sexe, date de naissance, région) |
| **stg_accounts** | Table staging | ② Ingestion | Comptes (id, type, date d'ouverture, région) |
| **stg_transactions** | Table staging | ② Ingestion | Transactions (id, montant, solde, date, type) |
| **stg_loans** | Table staging | ② Ingestion | Crédits (id, montant, statut, date) |
| **stg_cards** | Table staging | ② Ingestion | Cartes bancaires (id, type, date d'émission) |
| **stg_products** | Table staging | ② Ingestion | Produits souscrits (id, type, montant, date) |
| **stg_districts** | Table staging | ② Ingestion | Régions/districts (id, libellé) |
| **stg_dispositions** | Table staging | ② Ingestion | Liaisons client-compte (id, client_id, account_id, type) |
| **customer_attributes** | Table | ③ Transformation | **1 client par ligne** : âge, sexe, région, catégorie, fréquence de transaction (agrégé sur tous ses comptes) |
| **agg_loans** | Table | ③ Transformation | **1 compte par ligne** : dernier crédit associé (montant, statut) |
| **agg_cards** | Table | ③ Transformation | **1 compte par ligne** : dernière carte utilisée (type) |
| **agg_products** | Table | ③ Transformation | **1 compte par ligne** : dernier produit souscrit (type, date) |
| **customer_360** | VUE SQL | ① Provision (DDL) | **CONTRAT FIXE** : jointure de stg_transactions, stg_accounts, stg_dispositions, customer_attributes, agg_* ; 1 ligne = 1 transaction d'1 client (voir [02_create_customer_360_view.sql](src/database/02_create_customer_360_view.sql)) |
| **customer_segments** | Table | ④ Segmentation | **Résultats du clustering** : 1 client par ligne, avec segment assigné + features numériques utilisées pour K-Means |

### 2.4 Flux de données

```
CSV bruts (data/raw/<source>/*.csv)
    ↓
[mapping_<source>.yaml]  ← Décrit la transformation colonne par colonne
    ↓
ingest.py              ← Lit CSV, applique le mapping, écrit tables staging
    ↓
stg_* (tables staging)
    ↓
transform.py           ← Nettoyage, agrégations, jointures
    ↓
customer_attributes, agg_loans, agg_cards, agg_products
    ↓
VUE customer_360       ← JOIN des staging + attributs + agrégations
    ↓
segment.py             ← Extrait features numériques, normalise, K-Means
    ↓
customer_segments
    ↓
app.py (Streamlit)     ← Visualise et filtre par segment, région, âge, etc.
```

---

## 3. Choix techniques et justifications

### 3.1 MySQL (Base de données relationnelle)

**Qu'elle fait** : stockage persistant et requête ACID pour tables transactionnelles structurées.

**Pourquoi ici** :
- **Données relationnelles** : clients, comptes, transactions ont des liens naturels (1-N, N-N)
- **Scalabilité** : millions de transactions ; MySQL avec bons indices gère bien
- **Flexibilité** : vues SQL + JOIN puissants pour construire le schéma canonique dynamiquement
- **Standard bancaire** : MySQL est de facto standard en informatique de gestion

**Implémentation** : [src/common/db.py](src/common/db.py)
- `get_connection()` : connexion mysql.connector
- `get_engine()` : SQLAlchemy engine pour pandas
- `ensure_database_exists()` : création automatique de la DB
- `run_sql_file(path)` : exécution du schéma ([src/database/*.sql](src/database/))

### 3.2 SQLAlchemy + mysql-connector-python

**Qu'elles font** : abstraction Python pour base de données relationnelle.

**Pourquoi** :
- **Pandas ↔ MySQL** : `df.to_sql()` et `pd.read_sql()` unifiées, indépendantes du dialecte SQL
- **Pool de connexions** : `pool_pre_ping=True` détecte les connexions mortes et reconnnecte
- **ORM optionnel** : SQLAlchemy peut faire de l'ORM complexe si besoin futur

**Utilisation clé** :
```python
# Depuis segment.py
engine = get_engine()
customer_360 = pd.read_sql(f"SELECT * FROM {db_config['customer_360_view']}", engine)
output_df.to_sql(output_table, engine, if_exists="append", ...)
```

### 3.3 Pandas (Manipulation de données tabulaires)

**Qu'elle fait** : chargement en mémoire, transformation et écriture de DataFrames.

**Pourquoi ici** :
- **ETL élégant** : filtrage `.loc[]`, groupby `.groupby().agg()`, merge `.merge()` très lisibles
- **Itération facile** : boucles sur lignes, colonnes, agrégations sans SQL complexe
- **Vectorisé** : opérations sur colonnes entières, optimisées en C/NumPy

**Exemples clés du projet** :

1. **[src/transformation/transform.py](src/transformation/transform.py)** — construction de `customer_attributes` :
   ```python
   owners = dispositions.loc[dispositions["disposition_type"] == "OWNER", ...]
   base = customers.merge(districts, on="district_id", how="left")
   tx_frequency = transactions.merge(owners, ...).groupby("customer_id", as_index=False).agg(...)
   result = base.merge(tx_frequency, ...).merge(nb_products, ...)
   ```

2. **[src/segmentation/feature_engineering.py](src/segmentation/feature_engineering.py)** — agrégation client → features :
   ```python
   account_features = account_level.groupby("customer_id").agg(
       avg_account_balance=("latest_account_balance", "mean"),
       nb_products=("product_type", "nunique"),
       account_age_days=("account_open_date", lambda s: (reference_date - s.min()).days),
   )
   ```

### 3.4 Scikit-learn + K-Means (Clustering non supervisé)

**Qu'il fait** : partitionne les clients en k groupes homogènes basés sur leurs features numériques.

**Principe du clustering non supervisé** :
- **Entrée** : n clients × m features (ex. 5000 clients × 6 features)
- **Algorithme** : K-Means cherche k centroïdes qui minimisent la distance intra-cluster
- **Sortie** : pour chaque client, 1 segment (0 à k-1)

**Utilité bancaire** : sans étiquettes (pas de "bon" ou "mauvais" client pré-défini), découvrir naturellement des **groupes homogènes** aux comportements similaires.

**Implémentation** : [src/segmentation/clustering.py](src/segmentation/clustering.py)

```python
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

# 1. Normalisation (crucial : sinon les features à grande échelle dominent)
scaler = StandardScaler()
scaled = scaler.fit_transform(features)  # moyenne=0, écart-type=1

# 2. Sélection du k optimal via score de silhouette
for k in range(k_min, k_max + 1):
    model = KMeans(n_clusters=k, random_state=seed, max_iter=max_iter, ...)
    labels = model.fit_predict(scaled)
    score = silhouette_score(scaled, labels)  # -1 ≤ score ≤ 1, 1=parfait
    # Retenir le k avec le meilleur score
```

**Paramètres** ([config/segmentation.yaml](config/segmentation.yaml)) :
- `k_min`, `k_max` : plage de k à tester (ex. 2 à 8)
- `seed` : reproductibilité
- `max_iter`, `tol` : convergence

**Score de silhouette** : mesure si chaque client est plus proche de son cluster que des autres. Automatise le choix de k.

### 3.5 Streamlit (Dashboard interactif)

**Qu'il fait** : crée une app web en Python pur (pas HTML/CSS/JavaScript manuel).

**Pourquoi ici** :
- **Rapidité** : `st.metric()`, `st.plotly_chart()`, `st.multiselect()` buildent l'UI en quelques lignes
- **Réactivité** : les filtres (segment, région, âge) recalculent les graphes au vol
- **Moderne** : thème sombre/clair, responsive, emojis
- **Collab** : parfait pour démo avec métier (STB) sans déploiement complexe

**Implémentation** : [src/dashboard/app.py](src/dashboard/app.py)

Structure :
```
st.set_page_config(...)        # Titre, layout
load_customer_level_data()     # Charge customer_360 + customer_segments
render_sidebar_filters()       # Filtres : segment, région, âge
render_kpis()                  # Cartes KPI : clients actifs, solde moyen, etc.
render_overview_tab()          # Graphes : répartition segments/régions/âges
render_segment_profile_tab()   # Heatmap : profil comportemental par segment
```

**KPIs affichés** (détail en section 5) :
- Clients actifs (nombre distinct)
- Solde moyen
- Produits / client
- Fréquence de transaction
- Potentiel cross-sell

### 3.6 PyYAML (Configuration déclarative)

**Qu'il fait** : charge des fichiers YAML structurés en dictionnaires Python.

**Pourquoi ici** :
- **Mapping générique** : décrit la transformation colonne par colonne **sans coder**
- **Multi-source** : Berka, Berka_sample, STB — différents mappings, même code
- **Lisibilité** : YAML est human-friendly pour métier, PMs, analystes

**Structure d'un mapping** ([config/mapping_berka.yaml](config/mapping_berka.yaml)) :

```yaml
source: berka
base_path: data/raw/berka
entities:
  customers:
    source_file: client.csv
    columns:
      client_id: customer_id              # Renommage
      district_id: district_id
    transforms:
      - function: berka_split_birth_number  # Fonction personnalisée (Berka spécifique)
        input: birth_number
        outputs: [birth_date, gender]

  transactions:
    source_file: trans.csv
    columns:
      trans_id: transaction_id
      amount: transaction_amount
      ...
    transforms:
      - function: yymmdd_to_date          # Conversion format date Berka (YYMMDD)
        input: date
        output: transaction_date
```

**Utilisation** : [src/ingestion/ingest.py](src/ingestion/ingest.py)

```python
mapping = get_mapping("berka")  # Charge config/mapping_berka.yaml
for entity_name, entity_cfg in mapping["entities"].items():
    df = pd.read_csv(entity_cfg["source_file"], sep=mapping["delimiter"])
    for transform_cfg in entity_cfg.get("transforms"):
        df = apply_transform(df, transform_cfg)  # Applique yymmdd_to_date, etc.
    df = df.rename(columns=entity_cfg["columns"])
    df.to_sql(...)
```

**Transformations personnalisées** ([src/ingestion/column_transforms.py](src/ingestion/column_transforms.py)) :

- `yymmdd_to_date` : convertit format date Berka (entier YYMMDD) en date ISO
- `berka_split_birth_number` : décode le numéro de naissance Berka pour extraire date + genre

### 3.7 Makefile (Orchestration)

**Qu'il fait** : définit les étapes du pipeline comme cibles `make`.

**Pourquoi** :
- **Ordre d'exécution** : force la séquence correcte (database avant ingestion, etc.)
- **Dépendances implicites** : `make all` enchaîne automatiquement
- **Reproductibilité** : commandes lisibles et idempotentes
- **Cross-platform** : script shell unifié (Linux, macOS, Windows avec Git Bash)

**Contenu** ([Makefile](Makefile)) :

```makefile
SOURCE ?= $(DATA_SOURCE)  # Lit from .env : export DATA_SOURCE=berka

database:
	$(VENV_PY) -B -m src.database.provision

ingestion:
	$(VENV_PY) -B -m src.ingestion.ingest --source $(SOURCE)

transformation:
	$(VENV_PY) -B -m src.transformation.transform

segmentation:
	$(VENV_PY) -B -m src.segmentation.segment

dashboard:
	$(VENV_PY) -B -m streamlit run src/dashboard/app.py

all: database ingestion transformation segmentation  # Enchaîne les 4 étapes
```

**Utilisation** :
```bash
export DATA_SOURCE=berka  # ou berka_sample, ou stb (futur)
make all              # Exécute database + ingestion + transformation + segmentation
make dashboard        # Lance l'app Streamlit
```

---

## 4. Démarche et méthodologie

### 4.1 Étape ① : Création du schéma MySQL

**Commande** : `make database`  
**Script** : [src/database/provision.py](src/database/provision.py)  
**Fichiers SQL** : [src/database/*.sql](src/database/)

**Actions** :
1. Crée la base MySQL (depuis [config/database.yaml](config/database.yaml))
2. Exécute dans l'ordre alphabétique les scripts .sql :
   - [01_create_tables.sql](src/database/01_create_tables.sql) : crée 8 tables staging (stg_*) + 4 tables agrégées + 1 table segments
   - [02_create_customer_360_view.sql](src/database/02_create_customer_360_view.sql) : crée la VUE customer_360
   - [03_create_segmentation_table.sql](src/database/03_create_segmentation_table.sql) : crée la table customer_segments

**Schéma des tables** ([01_create_tables.sql](src/database/01_create_tables.sql)) :

Tables staging (une par entité métier) :
```sql
CREATE TABLE stg_customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    district_id VARCHAR(20),
    birth_date DATE,
    gender CHAR(1)
);

CREATE TABLE stg_accounts (
    account_id VARCHAR(20) PRIMARY KEY,
    district_id VARCHAR(20),
    account_type VARCHAR(50),
    account_open_date DATE
);

CREATE TABLE stg_transactions (
    transaction_id VARCHAR(20) PRIMARY KEY,
    account_id VARCHAR(20),
    transaction_date DATE,
    transaction_amount DECIMAL(15,2),
    account_balance DECIMAL(15,2),
    transaction_type VARCHAR(50),
    INDEX idx_trans_account (account_id)
);

-- stg_loans, stg_cards, stg_products, stg_districts, stg_dispositions...
```

**Vue customer_360** ([02_create_customer_360_view.sql](src/database/02_create_customer_360_view.sql)) :

```sql
CREATE VIEW customer_360 AS
SELECT
    -- Attributs client
    ca.customer_id, ca.age_range, ca.gender, ca.region, ca.customer_category,
    
    -- Données de compte
    acc.account_id, acc.account_type, acc.account_open_date, t.account_balance,
    
    -- Données de transaction (1 ligne par transaction)
    t.transaction_id, t.transaction_date, t.transaction_amount, t.transaction_type,
    ca.transaction_frequency,  -- Agrégé client (même valeur répétée)
    
    -- Données de produit, crédit, carte (dernière)
    ap.product_type, ap.product_subscription_date,
    al.loan_amount, al.loan_status,
    ac_card.card_type
FROM stg_transactions t
JOIN stg_accounts acc ON acc.account_id = t.account_id
JOIN stg_dispositions d ON d.account_id = acc.account_id 
    AND d.disposition_type = 'OWNER'
JOIN customer_attributes ca ON ca.customer_id = d.customer_id
LEFT JOIN agg_loans al ON al.account_id = acc.account_id
LEFT JOIN agg_cards ac_card ON ac_card.account_id = acc.account_id
LEFT JOIN agg_products ap ON ap.account_id = acc.account_id;
```

**Résultat** : schéma vide, prêt à recevoir les données.

---

### 4.2 Étape ② : Ingestion des données brutes

**Commande** : `make ingestion`  
**Script** : [src/ingestion/ingest.py](src/ingestion/ingest.py)

**Flux** :
```
CSV brut (data/raw/<source>/<entity>.csv)
    ↓ [Lecture avec pandas]
    ↓ [Application du mapping : renommages + transformations]
    ↓ [Conversion IDs en chaîne]
    ↓ [Écriture par chunks dans table staging]
```

**Exemple concret** (Berka `customers`) :

**Fichier source** : `data/raw/berka/client.csv`
```
client_id;district_id;birth_number
1;1;700101
2;1;750415
...
```

**Mapping** ([config/mapping_berka.yaml](config/mapping_berka.yaml)) :
```yaml
entities:
  customers:
    source_file: client.csv
    columns:
      client_id: customer_id
      district_id: district_id
    transforms:
      - function: berka_split_birth_number
        input: birth_number
        outputs: [birth_date, gender]
```

**Transformation personnalisée** ([src/ingestion/column_transforms.py](src/ingestion/column_transforms.py)) :
```python
def berka_split_birth_number(df, input_col, output_cols):
    # Berka encode : YYMMDD où MM ∈ [01,12] pour H, [51,62] pour F
    raw = df[input_col].astype(str).str.zfill(6)
    month_raw = raw.str.slice(2, 4).astype(int)
    is_female = month_raw > 50
    month_real = month_raw.where(~is_female, month_raw - 50)
    
    df["birth_date"] = pd.to_datetime("19" + ..., ...).dt.date
    df["gender"] = is_female.map({True: "F", False: "M"})
    return df
```

**Résultat** (dans `stg_customers`) :
```
customer_id | district_id | birth_date | gender
1           | 1           | 1970-01-01 | M
2           | 1           | 1975-04-15 | F
...
```

**Optimisations** :
- **Chunking** : charge par chunks de 5000 lignes (configurable en [config/database.yaml](config/database.yaml)) pour ne pas saturer la RAM
- **Indices** : crée des indices sur clés étrangères (ex. `idx_trans_account` sur stg_transactions)
- **Vérification** : log du nombre de lignes chargées par entité

**Gestion des sources** : les CSV sont cherchés via `mapping["base_path"]` — pour STB, ce sera `data/raw/stb/`, sans modification du code.

---

### 4.3 Étape ③ : Transformation et agrégation

**Commande** : `make transformation`  
**Script** : [src/transformation/transform.py](src/transformation/transform.py)

**Flux** :
```
Tables staging (stg_*)
    ↓ [Jointures, groupby, agrégations avec pandas]
    ↓ [Construction de 3 tables agrégées]
    ↓ [Construction de la table customer_attributes]
```

#### 4.3.1 Agrégations par compte : agg_loans, agg_cards, agg_products

**Objectif** : pour chaque compte, retenir le **dernier** crédit/carte/produit (le plus pertinent pour le moment présent).

**agg_loans** (derniers emprunts par compte) :
```python
def build_agg_loans(loans: pd.DataFrame) -> pd.DataFrame:
    latest_status = loans.sort_values("loan_date", ascending=False).drop_duplicates(
        "account_id", keep="first"
    )[["account_id", "loan_status"]]
    totals = loans.groupby("account_id", as_index=False)["loan_amount"].sum()
    return totals.merge(latest_status, on="account_id", how="left")
```
Résultat : 1 ligne par compte, avec `loan_amount` (somme) et `loan_status` (dernier).

**agg_cards** (dernière carte par compte) :
```python
def build_agg_cards(cards: pd.DataFrame, dispositions: pd.DataFrame) -> pd.DataFrame:
    merged = cards.merge(
        dispositions[["disposition_id", "account_id"]], on="disposition_id", how="inner"
    )
    return merged.sort_values("card_issue_date", ascending=False).drop_duplicates(
        "account_id", keep="first"
    )[["account_id", "card_type"]]
```
Résultat : 1 ligne par compte, avec le type de la dernière carte.

**agg_products** (dernier produit souscrit par compte) :
```python
def build_agg_products(products: pd.DataFrame) -> pd.DataFrame:
    return products.sort_values(
        ["product_subscription_date", "product_id"], ascending=[False, False]
    ).drop_duplicates("account_id", keep="first")[
        ["account_id", "product_type", "product_subscription_date"]
    ]
```
Résultat : 1 ligne par compte, avec le type et la date du dernier produit.

#### 4.3.2 Table customer_attributes : 1 client par ligne

**Objectif** : déduplier clients (qui peuvent avoir plusieurs comptes) et calculer leurs attributs.

```python
def build_customer_attributes(
    customers, districts, dispositions, transactions, 
    agg_loans, agg_cards, agg_products, reference_date
) -> pd.DataFrame:
    # 1. Filtre : seuls les propriétaires de compte (disposition_type = 'OWNER')
    owners = dispositions.loc[
        dispositions["disposition_type"] == "OWNER", ["customer_id", "account_id"]
    ]
    
    # 2. Démographie : clients + régions
    base = customers.merge(districts, on="district_id", how="left")
    base["age_range"] = _age_range(base["birth_date"], reference_date)
    
    # 3. Fréquence de transaction (agrégée sur tous les comptes du client)
    tx_frequency = (
        transactions.merge(owners, on="account_id", how="inner")
        .groupby("customer_id", as_index=False)
        .agg(transaction_frequency=("transaction_id", "count"))
    )
    
    # 4. Présence de crédit, carte, produits
    loan_customer_ids = set(owners.merge(agg_loans[["account_id"]], ...).["customer_id"])
    card_customer_ids = set(owners.merge(agg_cards[["account_id"]], ...).["customer_id"])
    nb_products = owners.merge(agg_products, ...).groupby("customer_id").agg(
        nb_products=("product_type", "nunique")
    )
    
    # 5. Catégorie client (basée sur produits)
    result["customer_category"] = "Basic"  # Défaut
    has_any_product = (
        result["has_loan"] | result["has_card"] | (result["nb_products"] > 0)
    )
    result.loc[has_any_product, "customer_category"] = "Standard"
    result.loc[
        result["has_loan"] & result["has_card"], "customer_category"
    ] = "Premium"
    
    return result[
        ["customer_id", "age_range", "gender", "region", "customer_category", 
         "transaction_frequency"]
    ]
```

**Définition des catégories** :
- **Basic** : aucun produit (crédit, carte, produit) — client passif
- **Standard** : au moins 1 produit — client engagé
- **Premium** : crédit ET carte — client à forte valeur

#### 4.3.3 Date de référence

Pour comparaison dans le temps, le code utilise **la date max des transactions** comme référence. Cela permet de :
- Calculer l'âge au moment de la dernière transaction
- Calculer l'ancienneté du compte (jours depuis ouverture)

```python
reference_date = pd.to_datetime(tables["transactions"]["transaction_date"]).max().date()
```

---

### 4.4 Étape ④ : Segmentation (Clustering K-Means)

**Commande** : `make segmentation`  
**Script** : [src/segmentation/segment.py](src/segmentation/segment.py)

**Flux** :
```
Vue customer_360 (toutes les transactions)
    ↓ [Lecture]
    ↓ [Feature engineering : agrégation par client]
    ↓ [Normalisation StandardScaler]
    ↓ [K-Means avec sélection auto de k via silhouette]
    ↓ [Écriture dans customer_segments]
```

#### 4.4.1 Feature engineering : de transactions à features client

**Source** : [src/segmentation/feature_engineering.py](src/segmentation/feature_engineering.py)

**Objective** : extraire 6 features numériques caractérisant le **profil comportemental** de chaque client.

```python
def build_customer_features(customer_360: pd.DataFrame) -> pd.DataFrame:
    reference_date = pd.to_datetime(customer_360["transaction_date"]).max()
    
    # Niveau compte : solde, products, ancienneté
    account_level = customer_360[[
        "customer_id", "account_id", "account_open_date", "loan_amount", "product_type"
    ]].drop_duplicates("account_id")
    
    latest_balance = customer_360.sort_values(
        "transaction_date", ascending=False
    ).drop_duplicates("account_id", keep="first")[
        ["account_id", "account_balance"]
    ].rename(columns={"account_balance": "latest_account_balance"})
    
    account_level = account_level.merge(latest_balance, on="account_id", how="left")
    
    # Agrégation client
    account_features = account_level.groupby("customer_id", as_index=False).agg(
        avg_account_balance=("latest_account_balance", "mean"),
        nb_products=("product_type", "nunique"),
        account_age_days=(
            "account_open_date",
            lambda s: (reference_date - s.min()).days
        ),
        total_loan_amount=("loan_amount", "sum"),
    )
    
    transaction_features = customer_360.groupby("customer_id", as_index=False).agg(
        avg_transaction_amount=("transaction_amount", "mean"),
        transaction_frequency=("transaction_frequency", "max"),  # Agrégé client
    )
    
    features = account_features.merge(transaction_features, on="customer_id", how="inner")
    features = features.fillna({...})  # Remplace NaN par 0
    return features
```

**6 Features numériques** ([config/segmentation.yaml](config/segmentation.yaml)) :

| Feature | Calcul | Interprétation |
|---------|--------|-----------------|
| **avg_transaction_amount** | Moyenne des montants de transaction | Clients "gros", "petits" montants |
| **transaction_frequency** | Nombre total de transactions par client | Actifs vs peu actifs |
| **avg_account_balance** | Moyenne des soldes finaux de compte | Clients riches vs "trésorerie zéro" |
| **nb_products** | Nombre de produits uniques souscrits | Engagés vs basiques |
| **account_age_days** | Jours depuis la première ouverture de compte | Clients anciens vs nouveaux |
| **total_loan_amount** | Somme des encours de crédit | Endettement du client |

#### 4.4.2 Normalisation

**Critère** : si on n'applique pas StandardScaler, les features à grande échelle dominent. Ex. :
- `total_loan_amount` : 0 à 1,000,000
- `transaction_frequency` : 0 à 1000

K-Means serait biaisé vers les crédits.

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
scaled = scaler.fit_transform(features)  # Moyenne=0, écart-type=1 par colonne
```

#### 4.4.3 Sélection automatique de k via score de silhouette

**K-Means classique** : on doit spécifier k à l'avance, mais on ne sait pas combien de segments "vrais" existent. ClustIQ automatise ce choix.

**Score de silhouette** : pour chaque point, mesure :
- Distance à son propre cluster vs distance au cluster le plus proche
- Valeur ∈ [-1, 1] : 1 = parfait, 0 = neutre, -1 = mauvais

**Algorithme** ([src/segmentation/clustering.py](src/segmentation/clustering.py)) :

```python
def run_kmeans(df, feature_cols, k_min=2, k_max=8, seed=42, fixed_k=None, ...):
    scaled = StandardScaler().fit_transform(df[feature_cols])
    
    candidate_ks = [fixed_k] if fixed_k else list(range(k_min, k_max + 1))
    
    best = None
    for k in candidate_ks:
        model = KMeans(n_clusters=k, random_state=seed, max_iter=50, ...)
        labels = model.fit_predict(scaled)
        score = silhouette_score(scaled, labels)
        
        logger.info(f"k={k} -> silhouette={score:.4f}")
        
        if best is None or score > best.silhouette_score:
            best = SegmentationResult(
                predictions=df.copy(),
                model=model,
                k=k,
                silhouette_score=score
            )
    
    logger.info(f"Meilleur k retenu: {best.k} (silhouette={best.silhouette_score:.4f})")
    return best
```

**Exemple** :
```
K-Means k=2 -> silhouette=0.4521
K-Means k=3 -> silhouette=0.5234
K-Means k=4 -> silhouette=0.5892  ← Meilleur score
K-Means k=5 -> silhouette=0.5156
K-Means k=6 -> silhouette=0.4823
```

#### 4.4.4 Résultats écrits

Table `customer_segments` ([03_create_segmentation_table.sql](src/database/03_create_segmentation_table.sql)) :

```sql
CREATE TABLE customer_segments (
    customer_id VARCHAR(20) PRIMARY KEY,
    segment INT,  -- 0, 1, 2, ... (k-1)
    avg_transaction_amount DECIMAL(15,2),
    transaction_frequency INT,
    avg_account_balance DECIMAL(15,2),
    nb_products INT,
    account_age_days INT,
    total_loan_amount DECIMAL(15,2),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Contenu** : 1 ligne par client unique, avec son segment et ses features (utile pour analyse post-hoc).

---

### 4.5 Étape ⑤ : Dashboard interactif

**Commande** : `make dashboard`  
**Script** : [src/dashboard/app.py](src/dashboard/app.py)

**Architecture Streamlit** :

```python
# 1. Chargement des données
customer_level = load_customer_level_data()  # Fusionne customer_360 + customer_segments

# 2. Configuration UI
st.set_page_config(page_title="ClustIQ", ...)

# 3. Filtrage (sidebar)
render_sidebar_filters(customer_level)  # Segments, région, âge

# 4. KPIs (cartes résumé)
render_kpis(filtered_df)

# 5. Onglets (visualisations)
tab1, tab2 = st.tabs(["Vue d'ensemble", "Profils par segment"])
with tab1:
    render_overview_tab(...)  # Graphes répartition
with tab2:
    render_segment_profile_tab(...)  # Heatmap profils
```

**Thème** : couleurs adaptatif (light/dark), palette de 8 couleurs catégoriques pour segments.

---

## 5. Indicateurs (KPI) du dashboard

Chaque KPI répond à une **question métier** et utilise les données de `customer_360` + `customer_segments` filtrées par l'utilisateur.

### 5.1 Clients actifs

**Définition** : nombre de clients distincts dans la sélection filtrée.

**Mode de calcul** :
```python
active_clients = df["customer_id"].nunique()
```

**Utilité métier** :
- Mesure l'**ampleur du portefeuille** visé
- Permet de segmenter : ex. "combien de clients Premium ?" ou "en Île-de-France ?"
- Base pour calculer d'autres métriques par client

### 5.2 Solde moyen

**Définition** : moyenne des soldes finaux de compte des clients.

**Mode de calcul** :
```python
avg_balance = df.groupby("customer_id")["avg_account_balance"].mean().mean()
```
(On prend la moyenne par client d'abord, puis la moyenne globale, pour éviter que les clients multi-compte faussent le résultat.)

**Utilité métier** :
- Indicateur de **trésorerie/liquidité** du segment
- Clients à fort solde = potentiel d'épargne élevé, risque de départ faible
- Clients à solde zéro/négatif = risque crédit, opportunité de crédit court-terme

### 5.3 Produits / client

**Définition** : nombre moyen de produits souscrits par client.

**Mode de calcul** :
```python
avg_products = df["nb_products"].mean()
```

**Utilité métier** :
- Mesure le **taux de penetration** des produits
- Cross-sell potentiel : clients avec 0-1 produit sont des **cibles de cross-sell**
- Clients avec 3+ produits = **clients fidèles**, risque d'attrition faible

### 5.4 Fréquence de transaction

**Définition** : nombre moyen de transactions par client sur la période observée.

**Mode de calcul** :
```python
avg_frequency = df["transaction_frequency"].mean()
```

**Utilité métier** :
- Mesure l'**engagement** du client (activité)
- Clients peu actifs (< médiane) = **churners** potentiels → interventions rétention
- Clients très actifs (> médiane) = bons candidats pour produits premium

### 5.5 Répartition des segments

**Définition** : nombre et % de clients par segment.

**Mode de calcul** :
```python
counts = df["segment"].value_counts()
```

**Visualisation** : graphe en barres avec % affichés.

**Utilité métier** :
- Voir si la segmentation est **équilibrée** ou concentrée
- Valider que chaque segment est suffisamment peuplé pour justifier une action marketing distincte
- Monitorer les shifts (ex. migration de clients entre segments après campagne)

### 5.6 Potentiel cross-sell

**Définition** : % de clients avec fréquence de transaction ≥ médiane AND nb_products ≤ 1.

**Mode de calcul** :
```python
median_frequency = df["transaction_frequency"].median()
high_activity = df["transaction_frequency"] >= median_frequency
low_products = df["nb_products"] <= 1
high_potential = (high_activity & low_products).mean()
```

**Interprétation** : ces clients sont **actifs mais peu engagés** en produits → gisement pour :
- Crédits supplémentaires
- Assurances emprunteur
- Produits d'investissement

**Utilité métier** :
- Cible prioritaire pour campagne marketing
- ROI potentiel élevé (clients actifs = taux conversion élevé)
- Facile à identifier et à segmenter dans une CRM

---

### 5.7 Visualisations supplémentaires (Overview tab)

#### Répartition par région

**Graph** : barres horizontales (Top 10 des régions).

**Utilité** : voir où se concentrent les clients (ex. Île-de-France vs province).

#### Répartition par tranche d'âge

**Graph** : barres (tranches <25, 25-34, ..., 65+).

**Utilité** : démographie du portefeuille, adapter le messaging par âge.

#### Répartition par catégorie (Basic/Standard/Premium)

**Graph** : barres.

**Utilité** : voir le mix de clients actifs vs passifs, justifier budget support/marketing.

### 5.8 Profils comportementaux par segment (Segment Profile tab)

**Heatmap** : chaque segment × chaque feature, colores selon **écart à la moyenne globale en écarts-types**.

**Exemple** :
```
           avg_tx | frequency | balance | products | age_days | loans
Segment 0  +2.1   | +1.8      | -0.5    | +0.3     | -1.2     | +0.8
Segment 1  -0.8   | -2.3      | +1.5    | +2.1     | +0.2     | +2.5
Segment 2  +0.1   | +0.4      | +0.3    | -1.8     | +2.0     | -0.9
```

**Interprétation** :
- **Rouge** = au-dessus de la moyenne (segment "fort" sur cette feature)
- **Bleu** = au-dessous de la moyenne (segment "faible")

**Utilité** : portrait-robot de chaque segment, justifier les noms (ex. "Segment 1 = investisseurs", "Segment 2 = clients prudents").

---

## 6. Généricité et adaptabilité à la STB

### 6.1 Principe : un seul fichier de mapping à remplir

L'architecture sépare **schéma (SQL/pandas/Streamlit) et données (mapping YAML)**. Pour brancher la STB :

1. Créer `config/mapping_stb.yaml` avec les colonnes réelles STB
2. Mettre les CSV STB dans `data/raw/stb/`
3. `export DATA_SOURCE=stb`
4. `make all`
5. **Aucune modification** du code

### 6.2 Brancher les données STB

**Template** ([config/mapping_stb.yaml](config/mapping_stb.yaml)) — à compléter :

```yaml
source: stb
base_path: data/raw/stb
delimiter: ";"
encoding: "utf-8"
quote_char: "\""

entities:
  customers:
    source_file: clients.csv        # ← Remplir
    columns:
      # ← Remplir avec colonnes réelles STB
      clt_id: customer_id
      clt_age: age_range             # ← Ou date de naissance + formule
      clt_sex: gender
      clt_region: region
    transforms: []                    # ← Ajouter si transformations nécessaires

  accounts:
    source_file: comptes.csv
    columns:
      cpte_id: account_id
      cpte_type: account_type
      cpte_open: account_open_date
    transforms: []

  transactions:
    source_file: transactions.csv
    columns:
      tx_id: transaction_id
      cpte_id: account_id
      tx_date: transaction_date
      tx_amount: transaction_amount
      tx_solde: account_balance
      tx_type: transaction_type
    transforms: []

  # ... loans, cards, products, districts, dispositions
```

**Étapes concrtètes** :

1. **Identifier les fichiers CSV STB** : clients, comptes, transactions, crédits, cartes, produits, régions, liaisons client-compte
2. **Pour chaque fichier**, remplir [mapping_stb.yaml](config/mapping_stb.yaml) :
   - `source_file` : nom du CSV
   - `columns` : dictionnaire {colonne_STB: colonne_canonique}
   - `transforms` : si nécessaire (ex. si date STB est en format différent)
3. **Tester sur échantillon** : `export DATA_SOURCE=stb; make all`
4. **Valider les résultats** : vérifier que customer_360 contient tous les clients STB, nombre correct de transactions, etc.

### 6.3 Transformations personnalisées (si besoin)

Si le format des dates STB diffère de Berka, ou si le numéro de naissance encode le genre différemment, ajouter une fonction [src/ingestion/column_transforms.py](src/ingestion/column_transforms.py) :

```python
def stb_decode_birth_gender(df: pd.DataFrame, input_col: str, output_cols: list[str]) -> pd.DataFrame:
    # Décode le format spécifique STB
    ...
    return df

TRANSFORMS["stb_decode_birth_gender"] = stb_decode_birth_gender
```

Puis l'utiliser dans [mapping_stb.yaml](config/mapping_stb.yaml) :
```yaml
transforms:
  - function: stb_decode_birth_gender
    input: birth_field
    outputs: [birth_date, gender]
```

### 6.4 Schéma MySQL : pas de modifications

Le schéma SQL ([src/database/*.sql](src/database/)) est **indépendant de la source**. Les noms de tables sont lus de [config/database.yaml](config/database.yaml), les colonnes sont définies par le mapping. Aucune modification nécessaire.

---

## 7. Limites et axes d'amélioration

### 7.1 Limites connues du POC Berka

#### Taille du dataset
- **Berka** : ~5M transactions, ~5k clients (années 1993-1998)
- **STB réelle** : potentiellement 100M+ transactions, 1M+ clients

**Impact** : tests de scalabilité critiques en production.

#### Qualité des données
- **Berka** : données anonymisées + nettoyées pour la recherche
- **STB** : données opérationnelles = NaN, doublons, incohérences probables

**Impact** : stratégie de nettoyage à adapter (ex. gestion des null dans loan_amount).

#### Représativité
- **Berka** : banque tchèque années 1990 ≠ STB 2024
- Structures de produits, moyennes de transaction, profils clients différents
- Segmentation Berka ne s'applique pas forcément à STB

**Implication** : retester la segmentation K-Means sur données réelles STB.

#### Interprétabilité
- K-Means choisit k automatiquement via silhouette, mais **pas de labels** aux segments
- Risk : segments ne correspondent pas à la réalité métier STB
- Solution : after-clustering, nommer les segments manuellement (ex. "Segment 0 = investisseurs") en analysant leurs profils comportementaux

#### Données temporelles
- **Berka** : snapshot statique (courant 1998)
- **STB** : flux continu (live transactions)

**Impact** : en production, modèle doit être **retrained** périodiquement (hebdo/mois) pour capturer drift comportemental.

### 7.2 Axes d'amélioration pour mise en production

#### 1. Monitoring et alertes
- Dashboard actuel : **statique** (snapshot)
- Production : ajouter **série temporelle** des segments (évolution mensuelle)
- Alertes si % d'un segment dépasse seuil, ou silhouette score dégradé

**Implémentation** : table `segments_history` enregistrant k, silhouette_score, distribution segment à chaque run.

#### 2. Modèle supervisé post-segmentation
- K-Means est **non supervisé** → pas de prédiction sur nouveaux clients
- Pour nouveaux clients : entraîner un classifieur (ex. Random Forest) sur données K-Means
- Permet scoring rapide en production sans re-clustering

**Implémentation** : ajouter `src/segmentation/classifier.py` avec `scikit-learn.RandomForestClassifier`.

#### 3. Feature engineering enrichi
- Actuellement : 6 features simples (moyennes, sommes)
- Production : intégrer ratio (ex. utilisation crédit = utilisé/accordé), volatilité (écart-type solde), saisonnalité (pics transaction en décembre)

**Impact** : segments plus nuancés, meilleur pouvoir prédictif.

#### 4. Données externes
- Actuellement : seules données internes (transactions, comptes, crédits)
- Production : intégrer **données externes** (score de crédit externe, info cadastrale, données macro-économiques)
- Améliore risk modeling et cross-sell

#### 5. Validation métier
- Actuellement : validation technique uniquement (silhouette score)
- Production : **focus group** métier STB pour valider que segments ont sens business
- Renommer segments après validation

#### 6. API REST + ML Ops
- Actuellement : pipeline batch seul
- Production : exposer scoring via API REST (pour scoring transactionnel temps réel)
- Ajouter versionning modèles, A/B testing, rollback capacités

**Architecture** :
```
Customer 360 pipeline (batch, Airflow/Prefect)
    ↓
ML Ops (versionning modèles, registry)
    ↓
API REST (Flask/FastAPI)
    ↓
Scoring transactionnel (temps réel)
```

#### 7. Intégration CRM
- Actuellement : dashboard Streamlit read-only
- Production : **bidirectionnelle CRM** (lire résultats segmentation, retourner actions marketing exécutées, mesurer ROI)

#### 8. Compliance et audit trail
- Actuellement : pas de traçabilité complète
- Production : logger **chaque transformation** (qui, quand, quoi, impact)
- RGPD : right to explanation (expliquer pourquoi un client en segment X)

#### 9. Optimisation coût infra
- Actuellement : MySQL simple host
- Production : architecture scalable (ex. Data Lake, Spark pour traitement massif, columnar DB pour analytics)

#### 10. Retour d'information (feedback loop)
- Actuellement : no closed loop
- Production : tracker outcomes réels (ex. client segment "high churn" a-t-il vraiment churné ?)
- Réentraîner le modèle intégrant outcomes → amélioration continue

---

## Annexe : Commandes et workflows

### Installation et setup

```bash
# 1. Créer l'environnement virtuel
make setup

# 2. Configurer les variables d'environnement (.env)
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=password
export MYSQL_DATABASE=clustiq_poc
export DATA_SOURCE=berka

# 3. Exécuter le pipeline complet
make all

# 4. Lancer le dashboard
make dashboard
# → Ouvre http://localhost:8501
```

### Workflows complets

**POC Berka complet** :
```bash
export DATA_SOURCE=berka
make clean
make setup
make all
make dashboard
```

**Test rapide (échantillon Berka)** :
```bash
export DATA_SOURCE=berka_sample
make all
```

**Transition vers STB** (futur) :
```bash
export DATA_SOURCE=stb
# (après avoir rempli config/mapping_stb.yaml et mis CSV dans data/raw/stb/)
make all
make dashboard
```

### Tests

```bash
make test
# Exécute pytest sur tests/ avec sortie verbose
```

### Nettoyage

```bash
make clean
# Efface .venv, .pytest_cache, __pycache__
```

---

## Conclusion

ClustIQ démontre une **architecture générique et maintenable** pour construire une vue Customer 360 et segmenter automatiquement une base cliente. Les principes clés :

1. **Séparation des concerns** : SQL (schéma) ≠ Python (ETL) ≠ YAML (données)
2. **Contrat fixe** : schéma canonique = contrat immuable entre étapes
3. **Paramétrisation** : zéro code-hard ; tout configurable via YAML
4. **Automatisation** : K-Means choisit k sans intervention manuelle
5. **Visualisation** : dashboard interactif pour insight métier

Pour **mise en production STB**, les étapes clés :
- Remplir `config/mapping_stb.yaml`
- Valider sur échantillon
- Monitorer qualité + historique segments
- Ajouter modèle supervisé + API REST
- Boucle feedback et réentraînement continu

L'architecture est **prête** pour cette transition — aucune refonte majeure requise.

---

**Fin de la documentation**

---

*Document généré automatiquement à partir de l'analyse du code source ClustIQ.*
