"""
Smart Public Transport Operations — Chennai MTC ETM Analysis
PHASE 3: PREDICTION PIPELINE (XGBoost Regressor & Classifier)

1. Load route-hour aggregated capacity dataset (349k rows).
2. Construct full temporal grid (705 routes x 744 hours) to calculate leak-free lags:
   - lag_1h, lag_2h, lag_1d (24h), lag_7d (168h)
   - rolling 7-day mean & std for the same route and hour
   - cyclical time features (sin/cos hour, sin/cos day-of-week)
   - target-encoded historical route mean ridership from train set
3. Time-based chronological split:
   - Train: March 8 – March 21, 2026 (14 days, full lags available)
   - Val:   March 22 – March 26, 2026 (5 days)
   - Test:  March 27 – March 31, 2026 (5 days out-of-time evaluation)
4. Train Models:
   - Regression: XGBoost Regressor for Next-Hour Passenger Demand (D_{r, t})
   - Classification: XGBoost Classifier for Overcrowding Risk P(Load Factor > 1.0)
   - Baseline Benchmark: Lag 7-Day (Same hour previous week) persistence baseline
5. Evaluation:
   - Regressor: MAE, RMSE, MAPE, R2 vs Baseline
   - Classifier: Accuracy, Precision, Recall, F1, ROC-AUC vs Baseline
6. Feature Importance & Interpretability:
   - Feature weights, gain, and cover export
7. Visualizations:
   - phase3_actual_vs_predicted.png
   - phase3_feature_importance.png
   - phase3_roc_curve.png
   - phase3_hourly_error_profile.png
8. Artifacts:
   - models/xgboost_ridership.json
   - models/xgboost_overcrowding.json
   - outputs/tables/phase3_model_metrics.csv
   - outputs/tables/phase3_predictions_test.csv
   - outputs/tables/phase3_feature_importance.csv
"""

import os, sys, time, warnings
from pathlib import Path

_mpl_dir = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'mpl_cfg')
os.makedirs(_mpl_dir, exist_ok=True)
os.environ['MPLCONFIGDIR'] = _mpl_dir

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

import xgboost as xgb
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, roc_curve
)

warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path("c:/Users/nivet/Downloads/Theme 4/Theme 4")
DATA_CLEAN = ROOT / "data" / "clean"
MODELS_DIR = ROOT / "models"
OUT_CHARTS = ROOT / "outputs" / "charts"
OUT_TABLES = ROOT / "outputs" / "tables"
FINDINGS   = ROOT / "outputs" / "findings.md"

for d in [DATA_CLEAN, MODELS_DIR, OUT_CHARTS, OUT_TABLES]:
    d.mkdir(parents=True, exist_ok=True)

BUS_RATED_CAPACITY = 70.0 # MoHUA standard urban bus (40 seated + 30 standing)

def calculate_mape(y_true, y_pred, min_val=5.0):
    """Calculates Mean Absolute Percentage Error for values >= min_val to prevent div by zero."""
    mask = y_true >= min_val
    if np.sum(mask) == 0:
        return 0.0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0


def main():
    print("=" * 80, flush=True)
    print("MTC CHENNAI ETM DATASET — PHASE 3: PREDICTIVE MODELING PIPELINE", flush=True)
    print("=" * 80, flush=True)
    t0 = time.time()

    # ── 1. LOAD DATA & BUILD TIME SERIES GRID ─────────────────────────────────
    print("\n[Step 1/6] Loading Route-Hour Capacity dataset...", flush=True)
    rh_file = DATA_CLEAN / "route_hour_capacity.parquet"
    if not rh_file.exists():
        raise FileNotFoundError(f"Missing {rh_file}. Run Phase 2 first.")

    df = pd.read_parquet(rh_file)
    print(f"Loaded {len(df):,} route-hour records.", flush=True)

    df['timestamp'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
    df['route_id'] = df['route_id'].astype(str)

    # ── 2. FEATURE ENGINEERING ON REGULAR GRID ────────────────────────────────
    print("\n[Step 2/6] Building full regular temporal grid for leak-free lag generation...", flush=True)
    routes = df['route_id'].unique()
    timestamps = pd.date_range('2026-03-01 00:00:00', '2026-03-31 23:00:00', freq='h')
    full_idx = pd.MultiIndex.from_product([routes, timestamps], names=['route_id', 'timestamp'])
    grid_df = pd.DataFrame(index=full_idx).reset_index()

    # Merge actual observed values
    grid_df = grid_df.merge(
        df[['route_id', 'timestamp', 'pax', 'active_buses', 'tickets', 'revenue']],
        on=['route_id', 'timestamp'],
        how='left'
    )
    # Fill non-operating slots with 0
    grid_df['pax'] = grid_df['pax'].fillna(0.0).astype(np.float32)
    grid_df['active_buses'] = grid_df['active_buses'].fillna(0.0).astype(np.float32)

    # Sort strictly by route and timestamp
    grid_df = grid_df.sort_values(['route_id', 'timestamp']).reset_index(drop=True)

    print("Computing temporal lags and rolling statistics...", flush=True)
    # Autoregressive lags within route
    grid_df['lag_1h_pax'] = grid_df.groupby('route_id')['pax'].shift(1)
    grid_df['lag_2h_pax'] = grid_df.groupby('route_id')['pax'].shift(2)
    grid_df['lag_1d_pax'] = grid_df.groupby('route_id')['pax'].shift(24)
    grid_df['lag_7d_pax'] = grid_df.groupby('route_id')['pax'].shift(168)

    # Rolling 7-day stats for the SAME hour
    hour_series = grid_df['timestamp'].dt.hour
    grid_df['rolling_mean_7d'] = grid_df.groupby(['route_id', hour_series])['pax'].transform(
        lambda s: s.shift(1).rolling(7, min_periods=1).mean()
    ).astype(np.float32)

    grid_df['rolling_std_7d'] = grid_df.groupby(['route_id', hour_series])['pax'].transform(
        lambda s: s.shift(1).rolling(7, min_periods=1).std().fillna(0.0)
    ).astype(np.float32)

    # Add date column
    grid_df['date'] = grid_df['timestamp'].dt.strftime('%Y-%m-%d')
    # Time features
    grid_df['hour'] = hour_series.astype(np.int8)
    grid_df['dow_num'] = grid_df['timestamp'].dt.dayofweek.astype(np.int8)
    grid_df['is_weekend'] = grid_df['dow_num'].isin([5, 6]).astype(np.int8)

    # Cyclical representations
    grid_df['sin_hour'] = np.sin(2 * np.pi * grid_df['hour'] / 24.0).astype(np.float32)
    grid_df['cos_hour'] = np.cos(2 * np.pi * grid_df['hour'] / 24.0).astype(np.float32)
    grid_df['sin_dow']  = np.sin(2 * np.pi * grid_df['dow_num'] / 7.0).astype(np.float32)
    grid_df['cos_dow']  = np.cos(2 * np.pi * grid_df['dow_num'] / 7.0).astype(np.float32)

    # Target & Capacity calculations
    grid_df['deployed_capacity'] = (grid_df['active_buses'] * BUS_RATED_CAPACITY).astype(np.float32)
    grid_df['load_factor'] = np.where(
        grid_df['deployed_capacity'] > 0,
        grid_df['pax'] / grid_df['deployed_capacity'],
        0.0
    ).astype(np.float32)
    
    # Classification target: Overcrowded if Load Factor > 1.0 (Demand exceeds rated capacity)
    grid_df['overcrowded'] = (grid_df['load_factor'] > 1.0).astype(np.int8)

    # Filter to active operational slots only (where buses operated)
    active_mask = grid_df['active_buses'] > 0
    clean_ml_df = grid_df[active_mask].copy()

    # Drop early records with NaN 7-day lags (March 1 to 7)
    clean_ml_df = clean_ml_df.dropna(subset=['lag_7d_pax', 'lag_1d_pax', 'lag_1h_pax']).reset_index(drop=True)

    # ── 3. HISTORICAL ROUTE STATISTICS (FROM TRAIN ONLY) ──────────────────────
    print("\n[Step 3/6] Splitting Chronologically into Train, Validation, and Test sets...", flush=True)
    # Train: March 8 to March 21
    # Val:   March 22 to March 26
    # Test:  March 27 to March 31
    train_mask = (clean_ml_df['timestamp'] >= '2026-03-08') & (clean_ml_df['timestamp'] < '2026-03-22')
    val_mask   = (clean_ml_df['timestamp'] >= '2026-03-22') & (clean_ml_df['timestamp'] < '2026-03-27')
    test_mask  = (clean_ml_df['timestamp'] >= '2026-03-27')

    train_df = clean_ml_df[train_mask].copy()
    val_df   = clean_ml_df[val_mask].copy()
    test_df  = clean_ml_df[test_mask].copy()

    print(f"  Train set: {len(train_df):,} slots ({train_df['timestamp'].min().date()} to {train_df['timestamp'].max().date()})")
    print(f"  Val set:   {len(val_df):,} slots ({val_df['timestamp'].min().date()} to {val_df['timestamp'].max().date()})")
    print(f"  Test set:  {len(test_df):,} slots ({test_df['timestamp'].min().date()} to {test_df['timestamp'].max().date()})")

    # Compute historical route mean demand from train set only (prevent leakage)
    route_stats = train_df.groupby('route_id')['pax'].agg(
        hist_route_pax='mean',
        hist_route_std='std'
    ).reset_index()
    overall_mean = train_df['pax'].mean()
    route_stats['hist_route_std'] = route_stats['hist_route_std'].fillna(0.0)

    train_df = train_df.merge(route_stats, on='route_id', how='left')
    val_df   = val_df.merge(route_stats, on='route_id', how='left')
    test_df  = test_df.merge(route_stats, on='route_id', how='left')

    for df_split in [train_df, val_df, test_df]:
        df_split['hist_route_pax'] = df_split['hist_route_pax'].fillna(overall_mean).astype(np.float32)
        df_split['hist_route_std'] = df_split['hist_route_std'].fillna(0.0).astype(np.float32)

    # Feature List
    feature_cols = [
        'hour', 'sin_hour', 'cos_hour',
        'dow_num', 'sin_dow', 'cos_dow', 'is_weekend',
        'active_buses', 'deployed_capacity',
        'lag_1h_pax', 'lag_2h_pax', 'lag_1d_pax', 'lag_7d_pax',
        'rolling_mean_7d', 'rolling_std_7d',
        'hist_route_pax', 'hist_route_std'
    ]
    print(f"\nModel Features ({len(feature_cols)}): {feature_cols}")

    X_train, y_train_reg, y_train_clf = train_df[feature_cols], train_df['pax'], train_df['overcrowded']
    X_val,   y_val_reg,   y_val_clf   = val_df[feature_cols],   val_df['pax'],   val_df['overcrowded']
    X_test,  y_test_reg,  y_test_clf  = test_df[feature_cols],  test_df['pax'],  test_df['overcrowded']

    # ── 4. BASELINE BENCHMARKS ────────────────────────────────────────────────
    print("\n[Step 4/6] Evaluating Previous-Week Lag Baseline (t - 168h)...", flush=True)
    baseline_pred_pax = test_df['lag_7d_pax'].values
    baseline_pred_clf = (baseline_pred_pax > test_df['deployed_capacity'].values).astype(int)

    base_mae  = mean_absolute_error(y_test_reg, baseline_pred_pax)
    base_rmse = np.sqrt(mean_squared_error(y_test_reg, baseline_pred_pax))
    base_r2   = r2_score(y_test_reg, baseline_pred_pax)
    base_mape = calculate_mape(y_test_reg.values, baseline_pred_pax)

    base_acc  = accuracy_score(y_test_clf, baseline_pred_clf)
    base_prec = precision_score(y_test_clf, baseline_pred_clf, zero_division=0)
    base_rec  = recall_score(y_test_clf, baseline_pred_clf, zero_division=0)
    base_f1   = f1_score(y_test_clf, baseline_pred_clf, zero_division=0)
    base_auc  = roc_auc_score(y_test_clf, baseline_pred_pax / (test_df['deployed_capacity'].values + 1e-5))

    print(f"  BASELINE (7d Lag) -> Reg: MAE={base_mae:.2f}, RMSE={base_rmse:.2f}, R2={base_r2:.4f}, MAPE={base_mape:.2f}%")
    print(f"  BASELINE (7d Lag) -> Clf: Acc={base_acc:.4f}, Prec={base_prec:.4f}, Rec={base_rec:.4f}, F1={base_f1:.4f}, AUC={base_auc:.4f}")

    # ── 5. TRAIN XGBOOST REGRESSOR ───────────────────────────────────────────
    print("\n[Step 5/6] Training XGBoost Regressor for Next-Hour Ridership...", flush=True)
    reg_model = xgb.XGBRegressor(
        n_estimators=180,
        learning_rate=0.08,
        max_depth=7,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=2,
        tree_method='hist'
    )
    reg_model.fit(
        X_train, y_train_reg,
        eval_set=[(X_val, y_val_reg)],
        verbose=False
    )
    test_pred_reg = reg_model.predict(X_test)
    test_pred_reg = np.clip(test_pred_reg, 0, None) # Passenger boardings cannot be negative

    xgb_mae  = mean_absolute_error(y_test_reg, test_pred_reg)
    xgb_rmse = np.sqrt(mean_squared_error(y_test_reg, test_pred_reg))
    xgb_r2   = r2_score(y_test_reg, test_pred_reg)
    xgb_mape = calculate_mape(y_test_reg.values, test_pred_reg)

    mae_imp  = ((base_mae - xgb_mae) / base_mae) * 100.0
    rmse_imp = ((base_rmse - xgb_rmse) / base_rmse) * 100.0
    print(f"  XGBOOST REGRESSOR -> MAE={xgb_mae:.2f} ({mae_imp:+.1f}% vs base), RMSE={xgb_rmse:.2f} ({rmse_imp:+.1f}%), R2={xgb_r2:.4f}, MAPE={xgb_mape:.2f}%")

    # Save model
    reg_model.save_model(str(MODELS_DIR / "xgboost_ridership.json"))
    print(f"  Saved {MODELS_DIR / 'xgboost_ridership.json'}")

    # ── 6. TRAIN XGBOOST CLASSIFIER ──────────────────────────────────────────
    print("\n[Step 6/6] Training XGBoost Classifier for Overcrowding Risk P(LF > 1.0)...", flush=True)
    # Check class imbalance
    pos_weight = (len(y_train_clf) - np.sum(y_train_clf)) / max(np.sum(y_train_clf), 1)
    print(f"  Class balance: Positive (Overcrowded) = {np.sum(y_train_clf):,} ({np.mean(y_train_clf)*100:.1f}%), scale_pos_weight = {pos_weight:.2f}")

    clf_model = xgb.XGBClassifier(
        n_estimators=180,
        learning_rate=0.08,
        max_depth=6,
        scale_pos_weight=pos_weight,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=2,
        eval_metric='logloss',
        tree_method='hist'
    )
    clf_model.fit(
        X_train, y_train_clf,
        eval_set=[(X_val, y_val_clf)],
        verbose=False
    )
    test_pred_proba = clf_model.predict_proba(X_test)[:, 1]
    test_pred_clf   = (test_pred_proba >= 0.50).astype(int)

    xgb_acc  = accuracy_score(y_test_clf, test_pred_clf)
    xgb_prec = precision_score(y_test_clf, test_pred_clf, zero_division=0)
    xgb_rec  = recall_score(y_test_clf, test_pred_clf, zero_division=0)
    xgb_f1   = f1_score(y_test_clf, test_pred_clf, zero_division=0)
    xgb_auc  = roc_auc_score(y_test_clf, test_pred_proba)

    f1_imp  = ((xgb_f1 - base_f1) / base_f1) * 100.0
    auc_imp = ((xgb_auc - base_auc) / base_auc) * 100.0
    print(f"  XGBOOST CLASSIFIER -> Acc={xgb_acc:.4f}, Prec={xgb_prec:.4f}, Rec={xgb_rec:.4f}, F1={xgb_f1:.4f} ({f1_imp:+.1f}%), AUC={xgb_auc:.4f} ({auc_imp:+.1f}%)")

    # Save model
    clf_model.save_model(str(MODELS_DIR / "xgboost_overcrowding.json"))
    print(f"  Saved {MODELS_DIR / 'xgboost_overcrowding.json'}")

    # ── 7. SAVE OUTPUT TABLES ─────────────────────────────────────────────────
    print("\nCompiling metrics and predictions tables...", flush=True)
    # Metrics table
    metrics_data = [
        {"Model": "Baseline (Lag-7d Persistence)", "Task": "Regression (Demand)", "MAE": base_mae, "RMSE": base_rmse, "MAPE": base_mape, "R2": base_r2, "Accuracy": None, "Precision": None, "Recall": None, "F1": None, "ROC_AUC": None},
        {"Model": "XGBoost Regressor", "Task": "Regression (Demand)", "MAE": xgb_mae, "RMSE": xgb_rmse, "MAPE": xgb_mape, "R2": xgb_r2, "Accuracy": None, "Precision": None, "Recall": None, "F1": None, "ROC_AUC": None},
        {"Model": "Baseline (Lag-7d Persistence)", "Task": "Classification (Overcrowding)", "MAE": None, "RMSE": None, "MAPE": None, "R2": None, "Accuracy": base_acc, "Precision": base_prec, "Recall": base_rec, "F1": base_f1, "ROC_AUC": base_auc},
        {"Model": "XGBoost Classifier", "Task": "Classification (Overcrowding)", "MAE": None, "RMSE": None, "MAPE": None, "R2": None, "Accuracy": xgb_acc, "Precision": xgb_prec, "Recall": xgb_rec, "F1": xgb_f1, "ROC_AUC": xgb_auc},
    ]
    metrics_df = pd.DataFrame(metrics_data)
    metrics_df.to_csv(OUT_TABLES / "phase3_model_metrics.csv", index=False)
    print(f"  Saved {OUT_TABLES / 'phase3_model_metrics.csv'}")

    # Test set predictions table
    test_results = test_df[['route_id', 'timestamp', 'date', 'hour', 'active_buses', 'deployed_capacity', 'pax', 'load_factor', 'overcrowded']].copy()
    test_results['pred_pax_xgb'] = np.round(test_pred_reg, 1)
    test_results['pred_load_factor_xgb'] = np.round(test_pred_reg / (test_results['deployed_capacity'] + 1e-5), 3)
    test_results['pred_overcrowd_proba_xgb'] = np.round(test_pred_proba, 4)
    test_results['pred_overcrowd_xgb'] = test_pred_clf
    test_results['baseline_pred_pax'] = np.round(baseline_pred_pax, 1)
    test_results['pax_error_xgb'] = np.round(test_results['pred_pax_xgb'] - test_results['pax'], 1)
    test_results['pax_abs_error_xgb'] = np.abs(test_results['pax_error_xgb'])

    test_results.to_csv(OUT_TABLES / "phase3_predictions_test.csv", index=False)
    print(f"  Saved {OUT_TABLES / 'phase3_predictions_test.csv'} ({len(test_results):,} test rows)")

    # Feature Importance Table
    reg_importances = reg_model.get_booster().get_score(importance_type='gain')
    clf_importances = clf_model.get_booster().get_score(importance_type='gain')

    feat_df = pd.DataFrame({
        'feature': feature_cols,
        'reg_gain': [reg_importances.get(f, 0.0) for f in feature_cols],
        'clf_gain': [clf_importances.get(f, 0.0) for f in feature_cols]
    })
    feat_df['reg_rank'] = feat_df['reg_gain'].rank(ascending=False).astype(int)
    feat_df['clf_rank'] = feat_df['clf_gain'].rank(ascending=False).astype(int)
    feat_df.sort_values('reg_gain', ascending=False).to_csv(OUT_TABLES / "phase3_feature_importance.csv", index=False)
    print(f"  Saved {OUT_TABLES / 'phase3_feature_importance.csv'}")

    # ── 8. PLOT HIGH-RESOLUTION CHARTS ───────────────────────────────────────
    print("\nRendering Phase 3 Visualizations...", flush=True)
    sns.set_theme(style='whitegrid', font='sans-serif')

    # Chart 1: Actual vs Predicted Demand (Hexbin + Residuals)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), dpi=200)
    
    # Ax1: Hexbin
    max_val = np.percentile(y_test_reg, 99.5)
    hb = ax1.hexbin(y_test_reg, test_pred_reg, gridsize=50, cmap='YlGnBu', mincnt=1, bins='log')
    ax1.plot([0, max_val], [0, max_val], 'r--', lw=2, label='Perfect Forecast Line (45°)')
    cb = fig.colorbar(hb, ax=ax1)
    cb.set_label('Log10 Count of Slots', fontsize=11)
    ax1.set_xlim(0, max_val)
    ax1.set_ylim(0, max_val)
    ax1.set_title(f'Actual vs. Predicted Ridership (XGBoost)\n$R^2 = {xgb_r2:.4f}$ | MAE = {xgb_mae:.1f} pax | Test Set (Mar 27-31)', fontsize=13, fontweight='bold')
    ax1.set_xlabel('Actual Passengers per Route-Hour', fontsize=11)
    ax1.set_ylabel('Predicted Passengers per Route-Hour', fontsize=11)
    ax1.legend(loc='upper left', frameon=True)

    # Ax2: Error distribution comparison (Baseline vs XGBoost)
    residuals_xgb = test_pred_reg - y_test_reg
    residuals_base = baseline_pred_pax - y_test_reg
    sns.kdeplot(residuals_base, ax=ax2, label=f'Baseline Lag-7d (MAE={base_mae:.1f})', color='gray', linestyle='--', lw=2)
    sns.kdeplot(residuals_xgb, ax=ax2, label=f'XGBoost Regressor (MAE={xgb_mae:.1f})', color='#1f77b4', lw=2.5)
    ax2.axvline(0, color='red', linestyle=':', lw=1.5)
    ax2.set_xlim(-250, 250)
    ax2.set_title('Residual Error Distribution (Actual vs Pred)\nSharp Peak at Zero Indicates Near-Zero Systematic Bias', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Prediction Error (Passengers)', fontsize=11)
    ax2.set_ylabel('Density', fontsize=11)
    ax2.legend(loc='upper right', frameon=True)

    plt.tight_layout()
    chart1_path = OUT_CHARTS / "phase3_actual_vs_predicted.png"
    plt.savefig(chart1_path, dpi=200)
    plt.close()
    print(f"  Chart 1: Saved {chart1_path}")

    # Chart 2: Feature Importance (Gain)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8), dpi=200)
    
    # Sort for regressor
    f_reg = feat_df.sort_values('reg_gain', ascending=True)
    ax1.barh(f_reg['feature'], f_reg['reg_gain'], color='#2b5c8f')
    ax1.set_title('Top Drivers: Ridership Regressor (Gain)', fontsize=13, fontweight='bold')
    ax1.set_xlabel('Relative Gain', fontsize=11)
    
    # Sort for classifier
    f_clf = feat_df.sort_values('clf_gain', ascending=True)
    ax2.barh(f_clf['feature'], f_clf['clf_gain'], color='#c0392b')
    ax2.set_title('Top Drivers: Overcrowding Risk Classifier (Gain)', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Relative Gain', fontsize=11)

    plt.suptitle('Chennai MTC Predictive Models — Feature Importance Analysis', fontsize=15, fontweight='bold', y=0.98)
    plt.tight_layout()
    chart2_path = OUT_CHARTS / "phase3_feature_importance.png"
    plt.savefig(chart2_path, dpi=200)
    plt.close()
    print(f"  Chart 2: Saved {chart2_path}")

    # Chart 3: ROC Curve (Classification)
    fig, ax = plt.subplots(figsize=(9, 7), dpi=200)
    fpr_xgb, tpr_xgb, _ = roc_curve(y_test_clf, test_pred_proba)
    fpr_base, tpr_base, _ = roc_curve(y_test_clf, baseline_pred_pax / (test_df['deployed_capacity'].values + 1e-5))

    ax.plot(fpr_xgb, tpr_xgb, color='#27ae60', lw=2.5, label=f'XGBoost Classifier (AUC = {xgb_auc:.4f})')
    ax.plot(fpr_base, tpr_base, color='navy', linestyle='--', lw=2, label=f'Lag-7d Persistence Baseline (AUC = {base_auc:.4f})')
    ax.plot([0, 1], [0, 1], color='gray', linestyle=':', lw=1.5, label='Random Guess (AUC = 0.5000)')

    ax.set_title('ROC Curve: Overcrowding Risk Prediction (Load Factor > 100%)\nEvaluated on Out-of-Time Test Set (March 27-31, 2026)', fontsize=13, fontweight='bold')
    ax.set_xlabel('False Positive Rate (Type I Error)', fontsize=11)
    ax.set_ylabel('True Positive Rate (Sensitivity / Recall)', fontsize=11)
    ax.legend(loc='lower right', frameon=True, fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    chart3_path = OUT_CHARTS / "phase3_roc_curve.png"
    plt.savefig(chart3_path, dpi=200)
    plt.close()
    print(f"  Chart 3: Saved {chart3_path}")

    # Chart 4: Hourly Error Profile (Peak vs Off-Peak Error Analysis)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), dpi=200, sharex=True)
    hourly_records = []
    for hr in range(24):
        g = test_results[test_results['hour'] == hr]
        if len(g) > 0:
            hourly_records.append({
                'hour': hr,
                'mae_xgb': mean_absolute_error(g['pax'], g['pred_pax_xgb']),
                'mae_base': mean_absolute_error(g['pax'], g['baseline_pred_pax']),
                'f1_xgb': f1_score(g['overcrowded'], g['pred_overcrowd_xgb'], zero_division=0),
                'f1_base': f1_score(g['overcrowded'], (g['baseline_pred_pax'] > g['deployed_capacity']).astype(int), zero_division=0),
                'slots': len(g)
            })
    hourly_eval = pd.DataFrame(hourly_records)

    ax1.plot(hourly_eval['hour'], hourly_eval['mae_base'], 's--', color='gray', label='Baseline Lag-7d MAE')
    ax1.plot(hourly_eval['hour'], hourly_eval['mae_xgb'], 'o-', color='#1f77b4', lw=2.5, label='XGBoost Regressor MAE')
    ax1.fill_between(hourly_eval['hour'], hourly_eval['mae_xgb'], hourly_eval['mae_base'], color='#1f77b4', alpha=0.15, label='Error Reduction')
    ax1.set_ylabel('MAE (Passengers)', fontsize=11)
    ax1.set_title('Diurnal Forecast Accuracy: Mean Absolute Error by Hour of Day', fontsize=13, fontweight='bold')
    ax1.legend(loc='upper right', frameon=True)
    ax1.grid(True, linestyle='--', alpha=0.6)

    ax2.plot(hourly_eval['hour'], hourly_eval['f1_base'], 's--', color='gray', label='Baseline Overcrowding F1')
    ax2.plot(hourly_eval['hour'], hourly_eval['f1_xgb'], 'o-', color='#27ae60', lw=2.5, label='XGBoost Overcrowding F1')
    ax2.set_xlabel('Hour of Day (0 to 23)', fontsize=11)
    ax2.set_ylabel('Overcrowding F1-Score', fontsize=11)
    ax2.set_title('Diurnal Overcrowding Detection: F1-Score by Hour of Day', fontsize=13, fontweight='bold')
    ax2.legend(loc='lower right', frameon=True)
    ax2.set_xticks(range(0, 24))
    ax2.grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    chart4_path = OUT_CHARTS / "phase3_hourly_error_profile.png"
    plt.savefig(chart4_path, dpi=200)
    plt.close()
    print(f"  Chart 4: Saved {chart4_path}")

    elapsed = time.time() - t0
    print("\n" + "=" * 80, flush=True)
    print(f"PHASE 3 COMPLETE: Models trained, evaluated & visualised in {elapsed:.1f}s.", flush=True)
    print("=" * 80, flush=True)

if __name__ == '__main__':
    main()
