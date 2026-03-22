"""
czoi.neural Neural components for the CZOI toolkit.

This module provides an abstract base class for all neural components,
along with concrete implementations for anomaly detection and role mining.
"""

import pickle
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

import numpy as np

# ----------------------------------------------------------------------
# Abstract base class
# ----------------------------------------------------------------------

class NeuralComponent(ABC):
    """Abstract base class for all neural components in the CZOI toolkit.

    Subclasses must implement the train, predict, save, and load methods.
    """

    @abstractmethod
    def train(self, data: Any) -> None:
        """Train the component on the provided data.

        Args:
            data: Training data. Format depends on the concrete component.
        """
        pass

    @abstractmethod
    def predict(self, input: Any) -> Any:
        """Make a prediction on the given input.

        Args:
            input: Input data for inference.

        Returns:
            Prediction result (type depends on the concrete component).
        """
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """Save the component's state to a file.

        Args:
            path: File path where the component should be saved.
        """
        pass

    @classmethod
    @abstractmethod
    def load(cls, path: str) -> "NeuralComponent":
        """Load a component from a saved file.

        Args:
            path: File path from which to load the component.

        Returns:
            An instance of the component.
        """
        pass


# ----------------------------------------------------------------------
# Anomaly detector using Isolation Forest (scikit-learn)
# ----------------------------------------------------------------------

class AnomalyDetector(NeuralComponent):
    """Anomaly detector based on Isolation Forest.

    Requires scikit-learn to be installed.
    """

    def __init__(
        self,
        contamination: float = 0.05,
        random_state: Optional[int] = 42,
        **kwargs
    ):
        """Initialize the anomaly detector.

        Args:
            contamination: Expected proportion of outliers in the data.
            random_state: Random seed for reproducibility.
            **kwargs: Additional parameters passed to sklearn.ensemble.IsolationForest.
        """
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError as e:
            raise ImportError(
                "scikit-learn is required for AnomalyDetector. "
                "Install it with: pip install scikit-learn"
            ) from e

        self.params = {
            "contamination": contamination,
            "random_state": random_state,
            **kwargs
        }
        self.model: Optional[IsolationForest] = None

    def train(self, data: np.ndarray) -> None:
        """Fit the Isolation Forest model to the data.

        Args:
            data: 2D array-like of shape (n_samples, n_features).
        """
        if data is None or len(data) == 0:
            raise ValueError("Training data cannot be empty.")

        try:
            from sklearn.ensemble import IsolationForest
        except ImportError as e:
            raise ImportError("scikit-learn is required for training.") from e

        self.model = IsolationForest(**self.params)
        self.model.fit(data)

    def predict(self, input: np.ndarray) -> np.ndarray:
        """Predict whether each sample in input is an anomaly.

        Returns -1 for anomalies, 1 for normal samples.

        Args:
            input: 2D array-like of shape (n_samples, n_features).

        Returns:
            Array of predictions, each entry is -1 or 1.
        """
        if self.model is None:
            raise RuntimeError("Model has not been trained. Call train() first.")
        return self.model.predict(input)

    def decision_function(self, input: np.ndarray) -> np.ndarray:
        """Return the anomaly score (the opposite of the decision function).

        Lower values indicate more anomalous.

        Args:
            input: 2D array-like.

        Returns:
            Anomaly scores (the negative of the decision function).
        """
        if self.model is None:
            raise RuntimeError("Model has not been trained. Call train() first.")
        return -self.model.decision_function(input)

    def save(self, path: str) -> None:
        """Save the trained model to a file using pickle."""
        if self.model is None:
            raise RuntimeError("Model not trained; nothing to save.")
        with open(path, "wb") as f:
            pickle.dump(self.model, f)

    @classmethod
    def load(cls, path: str) -> "AnomalyDetector":
        """Load a saved model from a file and return a new AnomalyDetector instance."""
        with open(path, "rb") as f:
            model = pickle.load(f)

        # Extract parameters from the model (if possible)
        # IsolationForest stores its parameters in attributes.
        params = {
            "contamination": getattr(model, "contamination", 0.05),
            "random_state": getattr(model, "random_state", 42),
        }
        detector = cls(**params)
        detector.model = model
        return detector


# ----------------------------------------------------------------------
# Role miner using HDBSCAN clustering
# ----------------------------------------------------------------------

class RoleMiner(NeuralComponent):
    """Role miner that discovers latent roles by clustering users or actions.

    Uses HDBSCAN, a density‑based clustering algorithm that can find
    clusters of varying density and does not require the number of clusters
    to be specified.

    Requires hdbscan to be installed.
    """

    def __init__(
        self,
        min_cluster_size: int = 5,
        min_samples: Optional[int] = None,
        cluster_selection_epsilon: float = 0.0,
        **kwargs
    ):
        """Initialize the role miner.

        Args:
            min_cluster_size: Minimum size of a cluster.
            min_samples: Number of samples in a neighbourhood for a point
                         to be considered a core point.
            cluster_selection_epsilon: Parameter for cluster selection.
            **kwargs: Additional parameters passed to hdbscan.HDBSCAN.
        """
        try:
            import hdbscan
        except ImportError as e:
            raise ImportError(
                "hdbscan is required for RoleMiner. "
                "Install it with: pip install hdbscan"
            ) from e

        self.params = {
            "min_cluster_size": min_cluster_size,
            "min_samples": min_samples,
            "cluster_selection_epsilon": cluster_selection_epsilon,
            **kwargs
        }
        self.model: Optional["hdbscan.HDBSCAN"] = None

    def train(self, data: np.ndarray) -> None:
        """Fit the HDBSCAN model to the data.

        After training, the cluster labels are stored in the model.

        Args:
            data: 2D array-like of shape (n_samples, n_features).
        """
        if data is None or len(data) == 0:
            raise ValueError("Training data cannot be empty.")

        try:
            import hdbscan
        except ImportError as e:
            raise ImportError("hdbscan is required for training.") from e

        self.model = hdbscan.HDBSCAN(**self.params)
        self.model.fit(data)

    def predict(self, input: np.ndarray) -> np.ndarray:
        """Predict cluster labels for new points using approximate prediction.

        This method uses hdbscan.approximate_predict if available,
        otherwise it raises NotImplementedError.

        Args:
            input: 2D array-like of new points.

        Returns:
            Array of cluster labels (integer labels, -1 indicates noise).
        """
        if self.model is None:
            raise RuntimeError("Model has not been trained. Call train() first.")

        try:
            import hdbscan
        except ImportError:
            raise ImportError("hdbscan is required for prediction.")

        if hasattr(hdbscan, "approximate_predict"):
            labels, _ = hdbscan.approximate_predict(self.model, input)
            return labels
        else:
            raise NotImplementedError(
                "predict is not implemented for this version of hdbscan. "
                "Use the model's labels_ attribute for training data, "
                "or update hdbscan to a version that supports approximate_predict."
            )

    def get_cluster_labels(self) -> Optional[np.ndarray]:
        """Return the cluster labels for the training data (if trained)."""
        if self.model is None:
            return None
        return self.model.labels_

    def save(self, path: str) -> None:
        """Save the trained model to a file using pickle."""
        if self.model is None:
            raise RuntimeError("Model not trained; nothing to save.")
        with open(path, "wb") as f:
            pickle.dump(self.model, f)

    @classmethod
    def load(cls, path: str) -> "RoleMiner":
        """Load a saved model from a file and return a new RoleMiner instance."""
        with open(path, "rb") as f:
            model = pickle.load(f)

        # Attempt to recover parameters from the model.
        params = {}
        if hasattr(model, "min_cluster_size"):
            params["min_cluster_size"] = model.min_cluster_size
        if hasattr(model, "min_samples"):
            params["min_samples"] = model.min_samples
        if hasattr(model, "cluster_selection_epsilon"):
            params["cluster_selection_epsilon"] = model.cluster_selection_epsilon

        miner = cls(**params)
        miner.model = model
        return miner

