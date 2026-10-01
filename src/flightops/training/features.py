"""Train-fitted sklearn transformers for feature-mart inputs."""

from __future__ import annotations

from typing import Self

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from flightops.training.config import RAW_CALENDAR_COLUMNS


class CalendarFeatureTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X: pd.DataFrame, y: object = None) -> Self:
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        result = X.copy()
        for column, period in zip(RAW_CALENDAR_COLUMNS, [24, 7, 12], strict=True):
            result[f"{column}_sin"] = np.sin(2 * np.pi * result[column] / period)
            result[f"{column}_cos"] = np.cos(2 * np.pi * result[column] / period)
        return result


class HistoryFeatureTransformer(BaseEstimator, TransformerMixin):
    def fit(self, X: pd.DataFrame, y: object = None) -> Self:
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        result = X.copy()
        rate_columns = [
            column for column in X if column.startswith("historical_") and column.endswith("_rate")
        ]
        for rate_column in rate_columns:
            count_column = rate_column.replace("_delay_rate", "_completed_count")
            result[f"{rate_column}_missing"] = result[rate_column].isna().astype(int)
            result[f"{count_column}_cold_start"] = (result[count_column] == 0).astype(int)
        return result


class FeatureDropper(BaseEstimator, TransformerMixin):
    def __init__(self, columns: tuple[str, ...] = tuple(RAW_CALENDAR_COLUMNS)) -> None:
        self.columns = columns

    def fit(self, X: pd.DataFrame, y: object = None) -> Self:
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return X.drop(columns=list(self.columns)).copy()
