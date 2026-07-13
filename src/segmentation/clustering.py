from dataclasses import dataclass

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm

from src.common.logging_conf import get_logger

logger = get_logger(__name__)


@dataclass
class SegmentationResult:
    predictions: pd.DataFrame
    model: KMeans
    scaler: StandardScaler
    k: int
    silhouette_score: float


def run_kmeans(
    df: pd.DataFrame,
    feature_cols: list[str],
    k_min: int,
    k_max: int,
    seed: int,
    max_iter: int,
    tol: float,
    fixed_k: int | None = None,
) -> SegmentationResult:
    features = df[feature_cols].to_numpy()
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)

    candidate_ks = [fixed_k] if fixed_k else list(range(k_min, k_max + 1))

    best: SegmentationResult | None = None
    for k in tqdm(candidate_ks, desc="K-Means", unit="k"):
        model = KMeans(
            n_clusters=k, random_state=seed, max_iter=max_iter, tol=tol, n_init=10
        )
        labels = model.fit_predict(scaled)
        score = silhouette_score(scaled, labels) if k > 1 else float("nan")
        logger.info("KMeans k=%d -> silhouette=%.4f", k, score)

        if best is None or (score == score and score > best.silhouette_score):
            predictions = df.copy()
            predictions["segment"] = labels
            best = SegmentationResult(
                predictions=predictions,
                model=model,
                scaler=scaler,
                k=k,
                silhouette_score=score,
            )

    logger.info(
        "Meilleur k retenu: %d (silhouette=%.4f)", best.k, best.silhouette_score
    )
    return best
