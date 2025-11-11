#!/usr/bin/env python3
"""
Data Preprocessing Pipeline for NetSentinel ML Components

Provides comprehensive data cleaning, normalization, and transformation
capabilities for network security event data.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.impute import SimpleImputer
import logging
from collections import Counter
import warnings

# Import new core components
try:
    from ..core.base import BaseComponent
    from ..utils.centralized import create_logger
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from utils.centralized import create_logger

logger = create_logger("data_preprocessing", level="INFO")


@dataclass
class PreprocessingConfig:
    """Configuration for data preprocessing pipeline"""

    # Missing value handling
    missing_value_strategy: str = "mean"  # "mean", "median", "most_frequent", "constant"
    missing_value_fill_value: Optional[Any] = None

    # Outlier handling
    outlier_method: str = "iqr"  # "iqr", "zscore", "isolation_forest", "none"
    outlier_threshold: float = 1.5  # For IQR method
    outlier_zscore_threshold: float = 3.0  # For z-score method

    # Normalization/Scaling
    scaling_method: str = "standard"  # "standard", "minmax", "robust", "none"
    feature_range: Tuple[float, float] = (0, 1)  # For minmax scaling

    # Categorical encoding
    categorical_encoding: str = "label"  # "label", "onehot", "ordinal", "none"
    max_categories: int = 50  # Maximum categories to encode

    # Feature engineering
    create_time_features: bool = True
    create_statistical_features: bool = True
    create_interaction_features: bool = False

    # Data validation
    validate_data_integrity: bool = True
    remove_duplicates: bool = True
    handle_infinite_values: bool = True


@dataclass
class PreprocessingReport:
    """Report of preprocessing operations performed"""

    original_shape: Tuple[int, int]
    final_shape: Tuple[int, int]
    missing_values_handled: Dict[str, int]
    outliers_detected: Dict[str, int]
    features_scaled: List[str]
    categorical_features_encoded: List[str]
    features_created: List[str]
    duplicates_removed: int
    infinite_values_handled: int
    preprocessing_warnings: List[str]
    preprocessing_errors: List[str]


class DataPreprocessingPipeline(BaseComponent):
    """
    Comprehensive data preprocessing pipeline for ML training data

    Handles:
    - Missing value imputation
    - Outlier detection and handling
    - Feature scaling and normalization
    - Categorical variable encoding
    - Feature engineering
    - Data validation and cleaning
    """

    def __init__(
        self,
        name: str = "data_preprocessing",
        config: Optional[PreprocessingConfig] = None,
        config_dict: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize data preprocessing pipeline

        Args:
            name: Component name
            config: Preprocessing configuration object
            config_dict: Configuration as dictionary (alternative to config)
        """
        super().__init__(name, config_dict, logger)

        # Initialize configuration
        if config:
            self.config = config
        else:
            self.config = PreprocessingConfig()
            if config_dict:
                for key, value in config_dict.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)

        # Initialize preprocessing components
        self._initialize_preprocessors()

        # Track preprocessing state
        self.is_fitted = False
        self.feature_names = []
        self.categorical_encoders = {}
        self.numerical_features = []
        self.categorical_features = []

    def _initialize_preprocessors(self):
        """Initialize preprocessing components"""
        # Missing value imputers
        self.imputers = {}

        # Scalers
        self.scalers = {}

        # Outlier detectors
        self.outlier_detectors = {}

        # Categorical encoders
        self.label_encoders = {}
        self.onehot_encoders = {}

    def fit(self, data: Union[pd.DataFrame, np.ndarray], feature_names: Optional[List[str]] = None) -> 'DataPreprocessingPipeline':
        """
        Fit the preprocessing pipeline on training data

        Args:
            data: Training data
            feature_names: Feature names (if data is numpy array)

        Returns:
            Self for method chaining
        """
        try:
            logger.info("Fitting data preprocessing pipeline...")

            # Convert to DataFrame if needed
            if isinstance(data, np.ndarray):
                if feature_names:
                    self.feature_names = feature_names
                else:
                    self.feature_names = [f"feature_{i}" for i in range(data.shape[1])]
                df = pd.DataFrame(data, columns=self.feature_names)
            elif isinstance(data, pd.DataFrame):
                df = data.copy()
                self.feature_names = list(df.columns)
            else:
                raise ValueError("Data must be pandas DataFrame or numpy array")

            # Identify feature types
            self._identify_feature_types(df)

            # Fit preprocessing components
            self._fit_missing_value_handling(df)
            self._fit_outlier_detection(df)
            self._fit_scaling(df)
            self._fit_categorical_encoding(df)

            self.is_fitted = True
            logger.info("Data preprocessing pipeline fitted successfully")

            return self

        except Exception as e:
            logger.error(f"Failed to fit preprocessing pipeline: {e}")
            raise

    def transform(self, data: Union[pd.DataFrame, np.ndarray]) -> Tuple[np.ndarray, PreprocessingReport]:
        """
        Transform data using fitted preprocessing pipeline

        Args:
            data: Data to transform

        Returns:
            Tuple of (transformed_data, preprocessing_report)
        """
        if not self.is_fitted:
            raise ValueError("Pipeline must be fitted before transform")

        try:
            logger.info("Transforming data through preprocessing pipeline...")

            # Convert to DataFrame if needed
            if isinstance(data, np.ndarray):
                df = pd.DataFrame(data, columns=self.feature_names)
            elif isinstance(data, pd.DataFrame):
                df = data.copy()
            else:
                raise ValueError("Data must be pandas DataFrame or numpy array")

            original_shape = df.shape
            report = PreprocessingReport(
                original_shape=original_shape,
                final_shape=original_shape,  # Will be updated
                missing_values_handled={},
                outliers_detected={},
                features_scaled=[],
                categorical_features_encoded=[],
                features_created=[],
                duplicates_removed=0,
                infinite_values_handled=0,
                preprocessing_warnings=[],
                preprocessing_errors=[]
            )

            # Apply preprocessing steps
            df = self._apply_data_validation(df, report)
            df = self._apply_missing_value_handling(df, report)
            df = self._apply_outlier_handling(df, report)
            df = self._apply_feature_engineering(df, report)
            df = self._apply_scaling(df, report)
            df = self._apply_categorical_encoding(df, report)

            # Convert back to numpy array
            transformed_data = df.values
            report.final_shape = transformed_data.shape

            logger.info(f"Data transformation completed: {original_shape} -> {transformed_data.shape}")
            return transformed_data, report

        except Exception as e:
            logger.error(f"Failed to transform data: {e}")
            raise

    def fit_transform(self, data: Union[pd.DataFrame, np.ndarray], feature_names: Optional[List[str]] = None) -> Tuple[np.ndarray, PreprocessingReport]:
        """
        Fit and transform data in one step

        Args:
            data: Training data
            feature_names: Feature names (if data is numpy array)

        Returns:
            Tuple of (transformed_data, preprocessing_report)
        """
        return self.fit(data, feature_names).transform(data)

    def _identify_feature_types(self, df: pd.DataFrame):
        """Identify numerical and categorical features"""
        self.numerical_features = []
        self.categorical_features = []

        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                self.numerical_features.append(col)
            else:
                self.categorical_features.append(col)

        logger.info(f"Identified {len(self.numerical_features)} numerical and {len(self.categorical_features)} categorical features")

    def _fit_missing_value_handling(self, df: pd.DataFrame):
        """Fit missing value imputers for numerical features"""
        if self.config.missing_value_strategy != "none":
            for col in self.numerical_features:
                if df[col].isnull().any():
                    strategy = self.config.missing_value_strategy
                    if strategy == "constant":
                        fill_value = self.config.missing_value_fill_value or 0
                        imputer = SimpleImputer(strategy=strategy, fill_value=fill_value)
                    else:
                        imputer = SimpleImputer(strategy=strategy)

                    imputer.fit(df[[col]])
                    self.imputers[col] = imputer

    def _fit_outlier_detection(self, df: pd.DataFrame):
        """Fit outlier detection methods"""
        if self.config.outlier_method != "none":
            # This would be more sophisticated in production
            # For now, store statistical parameters for outlier detection
            for col in self.numerical_features:
                if self.config.outlier_method == "iqr":
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    self.outlier_detectors[col] = {
                        'method': 'iqr',
                        'Q1': Q1,
                        'Q3': Q3,
                        'IQR': IQR,
                        'lower_bound': Q1 - self.config.outlier_threshold * IQR,
                        'upper_bound': Q3 + self.config.outlier_threshold * IQR
                    }

    def _fit_scaling(self, df: pd.DataFrame):
        """Fit feature scalers"""
        if self.config.scaling_method != "none":
            for col in self.numerical_features:
                if self.config.scaling_method == "standard":
                    scaler = StandardScaler()
                elif self.config.scaling_method == "minmax":
                    scaler = MinMaxScaler(feature_range=self.config.feature_range)
                elif self.config.scaling_method == "robust":
                    scaler = RobustScaler()

                scaler.fit(df[[col]])
                self.scalers[col] = scaler

    def _fit_categorical_encoding(self, df: pd.DataFrame):
        """Fit categorical encoders"""
        if self.config.categorical_encoding != "none":
            for col in self.categorical_features:
                unique_vals = df[col].nunique()
                if unique_vals <= self.config.max_categories:
                    if self.config.categorical_encoding == "label":
                        encoder = LabelEncoder()
                        encoder.fit(df[col].astype(str))
                        self.label_encoders[col] = encoder
                    elif self.config.categorical_encoding == "onehot":
                        encoder = OneHotEncoder(sparse=False, handle_unknown='ignore')
                        encoder.fit(df[[col]])
                        self.onehot_encoders[col] = encoder

    def _apply_data_validation(self, df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
        """Apply data validation and cleaning"""
        if self.config.validate_data_integrity:
            # Remove duplicates
            if self.config.remove_duplicates:
                initial_rows = len(df)
                df = df.drop_duplicates()
                report.duplicates_removed = initial_rows - len(df)

            # Handle infinite values
            if self.config.handle_infinite_values:
                initial_count = df.select_dtypes(include=[np.number]).stack().isin([np.inf, -np.inf]).sum()
                df = df.replace([np.inf, -np.inf], np.nan)
                final_count = df.select_dtypes(include=[np.number]).stack().isin([np.inf, -np.inf]).sum()
                report.infinite_values_handled = initial_count - final_count

        return df

    def _apply_missing_value_handling(self, df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
        """Apply missing value imputation"""
        for col in self.numerical_features:
            if col in self.imputers:
                initial_missing = df[col].isnull().sum()
                df[col] = self.imputers[col].transform(df[[col]]).ravel()
                final_missing = df[col].isnull().sum()
                report.missing_values_handled[col] = initial_missing - final_missing

        return df

    def _apply_outlier_handling(self, df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
        """Apply outlier detection and handling"""
        if self.config.outlier_method != "none":
            for col in self.numerical_features:
                if col in self.outlier_detectors:
                    detector = self.outlier_detectors[col]
                    if detector['method'] == 'iqr':
                        outliers = (df[col] < detector['lower_bound']) | (df[col] > detector['upper_bound'])
                        report.outliers_detected[col] = outliers.sum()

                        # For now, just cap outliers (could also remove them)
                        df.loc[df[col] < detector['lower_bound'], col] = detector['lower_bound']
                        df.loc[df[col] > detector['upper_bound'], col] = detector['upper_bound']

        return df

    def _apply_feature_engineering(self, df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
        """Apply feature engineering"""
        new_features = []

        # Time-based features
        if self.config.create_time_features:
            if 'timestamp' in df.columns:
                df['hour_of_day'] = pd.to_datetime(df['timestamp'], unit='s').dt.hour
                df['day_of_week'] = pd.to_datetime(df['timestamp'], unit='s').dt.dayofweek
                df['month'] = pd.to_datetime(df['timestamp'], unit='s').dt.month
                df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
                new_features.extend(['hour_of_day', 'day_of_week', 'month', 'is_weekend'])

        # Statistical features
        if self.config.create_statistical_features:
            numerical_cols = [col for col in self.numerical_features if col in df.columns]
            if len(numerical_cols) > 1:
                df['feature_sum'] = df[numerical_cols].sum(axis=1)
                df['feature_mean'] = df[numerical_cols].mean(axis=1)
                df['feature_std'] = df[numerical_cols].std(axis=1)
                df['feature_min'] = df[numerical_cols].min(axis=1)
                df['feature_max'] = df[numerical_cols].max(axis=1)
                new_features.extend(['feature_sum', 'feature_mean', 'feature_std', 'feature_min', 'feature_max'])

        # Update numerical features list
        self.numerical_features.extend(new_features)
        report.features_created = new_features

        return df

    def _apply_scaling(self, df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
        """Apply feature scaling"""
        if self.config.scaling_method != "none":
            for col in self.numerical_features:
                if col in self.scalers and col in df.columns:
                    df[col] = self.scalers[col].transform(df[[col]]).ravel()
                    report.features_scaled.append(col)

        return df

    def _apply_categorical_encoding(self, df: pd.DataFrame, report: PreprocessingReport) -> pd.DataFrame:
        """Apply categorical encoding"""
        if self.config.categorical_encoding != "none":
            for col in self.categorical_features:
                if col in self.label_encoders and col in df.columns:
                    df[col] = self.label_encoders[col].transform(df[col].astype(str))
                    report.categorical_features_encoded.append(col)
                elif col in self.onehot_encoders and col in df.columns:
                    encoded = self.onehot_encoders[col].transform(df[[col]])
                    # Add encoded columns (simplified - would need proper column naming)
                    for i in range(encoded.shape[1]):
                        df[f"{col}_encoded_{i}"] = encoded[:, i]
                    df = df.drop(columns=[col])
                    report.categorical_features_encoded.append(col)

        return df

    def get_feature_importance_estimate(self, data: Union[pd.DataFrame, np.ndarray]) -> Dict[str, float]:
        """
        Get estimated feature importance based on preprocessing insights

        Args:
            data: Input data

        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_fitted:
            raise ValueError("Pipeline must be fitted before getting feature importance")

        importance = {}

        # Convert to DataFrame
        if isinstance(data, np.ndarray):
            df = pd.DataFrame(data, columns=self.feature_names)
        else:
            df = data

        # Basic importance based on variance and correlation
        for col in self.numerical_features:
            if col in df.columns:
                try:
                    # Use coefficient of variation as simple importance metric
                    mean_val = df[col].mean()
                    std_val = df[col].std()
                    if mean_val != 0:
                        importance[col] = std_val / abs(mean_val)
                    else:
                        importance[col] = std_val
                except:
                    importance[col] = 0.0

        return importance

    def get_preprocessing_summary(self) -> Dict[str, Any]:
        """Get summary of preprocessing configuration and state"""
        return {
            "config": self.config.__dict__,
            "is_fitted": self.is_fitted,
            "feature_names": self.feature_names,
            "numerical_features": self.numerical_features,
            "categorical_features": self.categorical_features,
            "imputers_fitted": list(self.imputers.keys()),
            "scalers_fitted": list(self.scalers.keys()),
            "label_encoders_fitted": list(self.label_encoders.keys()),
            "onehot_encoders_fitted": list(self.onehot_encoders.keys()),
        }

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize data preprocessing pipeline"""
        logger.info("Data preprocessing pipeline initialized")

    async def _start_internal(self):
        """Start preprocessing pipeline operations"""
        pass

    async def _stop_internal(self):
        """Stop preprocessing pipeline operations"""
        pass

    async def _cleanup(self):
        """Cleanup preprocessing resources"""
        self.imputers.clear()
        self.scalers.clear()
        self.outlier_detectors.clear()
        self.label_encoders.clear()
        self.onehot_encoders.clear()
        logger.info("Data preprocessing pipeline cleanup completed")
