"""
SHAP Feature Importance Calculator

Calculates feature importance for XGBoost MMR model using SHAP values.

This enables:
- Explainable ML: Understand which features drive MMR predictions
- Feature optimization: Remove noise features
- Model debugging: Identify bias or overfitting
"""

from typing import Dict, List, Optional, Any
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Use lazy imports for heavy ML libraries
pd: Any = None
shap: Any = None

SHAP_AVAILABLE = False

try:
    import pandas as pd  # type: ignore
    import shap  # type: ignore

    SHAP_AVAILABLE = True
except ImportError:
    logger.warning(
        "SHAP or Pandas library not installed. ML explainability will be limited."
    )


class SHAPFeatureImportance:
    """
    Calculate feature importance using SHAP values.
    """

    def __init__(self, model: Any, feature_names: List[str]):
        """
        Initialize SHAP explainer.
        """
        self.model = model
        self.feature_names = feature_names
        self.explainer: Any = None

    def fit(self, X_train: Any, background_size: int = 100):
        """
        Fit SHAP explainer on training data.
        """
        if not SHAP_AVAILABLE or shap is None:
            raise ImportError("SHAP library not installed. Run: pip install shap")

        # Choose explainer based on model type
        model_type = str(type(self.model).__name__).lower()

        if (
            "xgboost" in model_type
            or "lightgbm" in model_type
            or "randomforest" in model_type
        ):
            self.explainer = shap.TreeExplainer(self.model)
            logger.info(f"Using TreeExplainer for {model_type} model")
        else:
            logger.warning(
                f"Unknown model type: {model_type}, using KernelExplainer (slower)"
            )
            background = shap.kmeans(X_train, background_size)
            self.explainer = shap.KernelExplainer(self.model, background)

        logger.info(f"SHAP explainer fitted with {background_size} background samples")

    def explain(self, X: Any, output_format: str = "dataframe") -> Any:
        """
        Calculate SHAP values for predictions.
        """
        if self.explainer is None:
            raise ValueError("Must call fit() before explain()")

        # Calculate SHAP values
        shap_values = self.explainer.shap_values(X)

        if output_format == "dataframe" and pd is not None:
            return pd.DataFrame(shap_values, columns=self.feature_names)
        return shap_values

    def get_feature_importance(self, shap_values: Any) -> Any:
        """
        Calculate overall feature importance from SHAP values.
        """
        if self.explainer is None:
            raise ValueError("Must call fit() before calling get_feature_importance()")

        # Mean absolute SHAP value per feature
        importance = np.abs(shap_values).mean(axis=0)

        if pd is not None:
            df = pd.DataFrame(
                {
                    "feature": self.feature_names,
                    "importance": importance,
                }
            ).sort_values("importance", ascending=False)
            return df

        return importance

    def plot_summary(self, shap_values: Any, save_path: Optional[str] = None):
        """
        Create SHAP summary plot.
        """
        if not SHAP_AVAILABLE or shap is None:
            logger.error("SHAP library not available for plotting")
            return

        if self.explainer is None:
            raise ValueError("Must call fit() before calling plot_summary()")

        shap.summary_plot(
            shap_values,
            plot_type="bar",
            show=False,
        )

        if save_path:
            try:
                import matplotlib.pyplot as plt  # type: ignore

                plt.savefig(save_path, dpi=300, bbox_inches="tight")
                logger.info(f"SHAP summary plot saved to {save_path}")
                plt.close()
            except ImportError:
                logger.error("Matplotlib not available for saving plot")

    def get_top_features(self, shap_values: Any, n: int = 10) -> List[Dict[str, Any]]:
        """
        Get top N features by importance.
        """
        importance_data = self.get_feature_importance(shap_values)

        if pd is not None and isinstance(importance_data, pd.DataFrame):
            top_n = importance_data.head(n)
            return [
                {"feature": str(row["feature"]), "importance": float(row["importance"])}
                for _, row in top_n.iterrows()
            ]

        # Fallback if pandas not available
        indices = np.argsort(importance_data)[::-1][:n]
        return [
            {"feature": self.feature_names[i], "importance": float(importance_data[i])}
            for i in indices
        ]


def prepare_shap_dataset_from_database(db_session: Any, limit: int = 1000):
    """
    Prepare dataset for SHAP analysis from database.
    """
    from ..models import MatchPlayer, Player, PlayerMatchMetrics

    query = (
        db_session.query(MatchPlayer, Player, PlayerMatchMetrics)
        .join(Player, MatchPlayer.player_id == Player.id)
        .join(PlayerMatchMetrics, PlayerMatchMetrics.match_player_id == MatchPlayer.id)
        .limit(limit)
    )

    dataset = []
    feature_names = [
        "apm",
        "combat_score",
        "economic_score",
        "efficiency_score",
        "overall_impact",
        "team_fight_participation",
        "win_rate",
    ]

    for match_player, player, metrics in query:
        features = [
            float(getattr(metrics, "apm", 0) or 0),
            float(getattr(metrics, "combat_score", 0) or 0),
            float(getattr(metrics, "economic_score", 0) or 0),
            float(getattr(metrics, "efficiency_score", 0) or 0),
            float(getattr(metrics, "overall_impact", 0) or 0),
            float(getattr(metrics, "team_fight_participation", 0) or 0),
            float(getattr(player, "win_rate", 0.5) or 0.5),
        ]

        outcome = 1 if match_player.won else 0
        dataset.append({"features": features, "outcome": outcome})

    if not dataset:
        return np.array([]), np.array([]), feature_names

    X = np.array([d["features"] for d in dataset])
    y = np.array([d["outcome"] for d in dataset])

    return X, y, feature_names


def calculate_feature_importance(
    model: Any, X_train: Any, X_test: Any, feature_names: List[str]
):
    """
    Calculate feature importance.
    """
    if not SHAP_AVAILABLE:
        logger.error("SHAP library not installed")
        return None

    shap_analyzer = SHAPFeatureImportance(model, feature_names)
    shap_analyzer.fit(X_train)
    shap_values = shap_analyzer.explain(X_test)
    return shap_analyzer.get_feature_importance(shap_values)
