# Future ML Roadmap & Improvement Backlog

This document tracks planned improvements and architectural alternatives to enhance the SC2 MMR Intelligence system. Use these items as prompts for future development sessions.

## 1. Sequence-Based Build Classification (Phase 4.5)
*   **Current State**: K-Means clustering based on "totals" (unit counts at 5 mins).
*   **Improvement**: Implement **GRU or LSTM (Recurrent Neural Network)** for build sequence analysis.
*   **Why**: Unit *order* matters. (e.g., "Marine then Medic" vs "Medic then Marine").
*   **Prompt**: *"Transition the BuildOrderClassifier from K-Means to a GRU-based sequence model to capture unit production order."*

## 2. Unit-Level Efficiency & Micro Analysis (Phase 5)
*   **Current State**: Aggregate combat scores per player.
*   **Improvement**: Track **Unit-Specific ROI (Return on Investment)**.
*   **Why**: Identify which units a player is best at using (e.g., "Disruptor Efficiency: 2.4x cost").
*   **Prompt**: *"Extend the advanced parser to calculate resource-kill-ratios for specific units and visualize this in the Match Detail view."*

## 3. Form & "Tilt" Detection (Phase 6)
*   **Current State**: Static win-rate tracking.
*   **Improvement**: Use **ML Variance Tracking** to detect performance "momentum" or "tilt."
*   **Why**: Provide psychological insights into player performance trends.
*   **Prompt**: *"Implement a 'Player Form' service that uses XGBoost prediction variance to detect when a player is performing significantly above or below their baseline."*

## 4. Architectural Enhancements
*   **Model Security**: Replace `pickle` with **Joblib** or **ONNX** for safer model persistence.
*   **Scalability**: Implement **Database Partitioning** for the `performance_features` table if match counts exceed 100k.
*   **Mobile UX**: Optimize the `MLIntelligence.tsx` dashboard for mobile tactical review.

## 5. Known Trade-offs to Re-evaluate
*   **JSON Storage**: Storing SHAP values as JSON blobs is convenient but prevents SQL-level querying of feature impacts. Consider a dedicated `feature_impacts` table for global analytics.
*   **Normalization**: Currently normalized to a fixed 600s game window. Consider dynamic normalization for ultra-short (cheese) or ultra-long games.

---
*Last Updated: Sat Dec 27 2025*
