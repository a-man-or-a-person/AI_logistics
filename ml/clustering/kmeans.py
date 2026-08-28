"""Geography-only K-Means baseline."""

from __future__ import annotations

import os
from dataclasses import replace
from typing import Any

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from ml.clustering.base import Clusterer, ClusterPoint, ClusterResult, summarize_assignments
from ml.evaluation.geographic import point_compactness_metrics


class KMeansClusterer(Clusterer):
    algorithm = "kmeans"

    def fit(self, points: list[ClusterPoint], parameters: dict[str, Any]) -> ClusterResult:
        if not points:
            raise ValueError("K-Means requires at least one point")
        n_clusters = int(parameters.get("n_clusters", 0))
        if not 2 <= n_clusters <= len(points):
            raise ValueError("n_clusters must be between 2 and the number of points")
        weight_mode = str(parameters.get("weight_mode", "none"))
        if weight_mode not in {"none", "shipment_count"}:
            raise ValueError("weight_mode must be none or shipment_count")
        random_state = int(parameters.get("random_state", 42))
        matrix = np.array([(point.x, point.y) for point in points], dtype=float)
        sample_weight = None
        if weight_mode == "shipment_count":
            sample_weight = np.array(
                [max(point.shipment_count, 0) for point in points], dtype=float
            )
            if not sample_weight.any():
                raise ValueError("shipment_count weighting requires positive shipment volume")
        model = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
        labels = model.fit_predict(matrix, sample_weight=sample_weight)
        assignments = {point.id: int(labels[index]) for index, point in enumerate(points)}
        normalized_parameters = {
            "n_clusters": n_clusters,
            "weight_mode": weight_mode,
            "random_state": random_state,
        }
        result = summarize_assignments(
            points,
            assignments,
            algorithm=self.algorithm,
            parameters=normalized_parameters,
        )
        metrics = point_compactness_metrics(points, result)
        metrics["silhouette"] = (
            round(float(silhouette_score(matrix, labels)), 6)
            if 1 < len(set(labels)) < len(points)
            else None
        )
        return replace(result, metrics=metrics)
