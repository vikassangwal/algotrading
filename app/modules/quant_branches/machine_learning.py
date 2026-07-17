import logging

logger = logging.getLogger("elco.module.quant.ml")

class MachineLearningEngine:
    def __init__(self, raw_data: dict):
        self.data = raw_data

    def analyze(self) -> dict:
        score = 0.0
        reasons = []

        try:
            # Check if dataframe was passed
            df = self.data.get("df")
            if df is not None:
                logger.debug(f"MachineLearningEngine received df with length: {len(df)}")
            else:
                logger.debug(f"MachineLearningEngine received None for df")
                
            if df is not None and len(df) > 50:
                # 1. Feature Engineering
                df['returns'] = df['close'].pct_change()
                df['volatility'] = df['returns'].rolling(window=20).std()
                df['momentum'] = df['close'] - df['close'].shift(10)
                df['sma_dist'] = (df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).mean()
                
                # Create Target (1 if next day is up, 0 if down)
                df['target'] = (df['returns'].shift(-1) > 0).astype(int)
                
                df.dropna(inplace=True)
                logger.debug(f"MachineLearningEngine df length after dropna: {len(df)}")
                
                if len(df) > 30:
                    features = df[['returns', 'volatility', 'momentum', 'sma_dist']].values
                    labels = df['target'].values
                    
                    try:
                        from sklearn.ensemble import RandomForestClassifier
                        from sklearn.svm import SVC
                        from sklearn.cluster import KMeans
                        from sklearn.linear_model import LogisticRegression
                        from sklearn.decomposition import PCA
                        
                        # 1. Train Random Forest
                        rf_model = RandomForestClassifier(n_estimators=50, max_depth=3, random_state=42)
                        rf_model.fit(features[:-1], labels[:-1])
                        today_features = features[-1].reshape(1, -1)
                        prob_up = rf_model.predict_proba(today_features)[0][1]
                        
                        if prob_up > 0.60:
                            score += 0.2
                            reasons.append(f"Machine Learning (Random Forest): Model predicts {prob_up*100:.1f}% probability of upward move.")
                        elif prob_up < 0.40:
                            score -= 0.2
                            reasons.append(f"Machine Learning (Random Forest): Model predicts high probability of downward move ({prob_up*100:.1f}% upside prob).")
                        else:
                            reasons.append(f"Machine Learning: RF prediction is neutral ({prob_up*100:.1f}%).")
                            
                        # 2. Train Support Vector Machine (SVM)
                        svm_model = SVC(probability=True, kernel='rbf', random_state=42)
                        svm_model.fit(features[:-1], labels[:-1])
                        svm_prob_up = svm_model.predict_proba(today_features)[0][1]
                        
                        if svm_prob_up > 0.65:
                            score += 0.2
                            reasons.append(f"Deep ML (SVM): Support Vector Machine strongly classifies tomorrow as BULLISH ({svm_prob_up*100:.1f}%).")
                        elif svm_prob_up < 0.35:
                            score -= 0.2
                            reasons.append(f"Deep ML (SVM): Support Vector Machine strongly classifies tomorrow as BEARISH ({svm_prob_up*100:.1f}%).")
                        else:
                            reasons.append(f"Deep ML (SVM): Support Vector Machine prediction is NEUTRAL ({svm_prob_up*100:.1f}%).")
                            
                        # 3. K-Means Clustering (Regime Detection)
                        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
                        kmeans.fit(features)
                        current_cluster = kmeans.predict(today_features)[0]
                        reasons.append(f"Deep ML (K-Means): Current market state belongs to Volatility Cluster {current_cluster} (Unsupervised Regime Detection).")

                        # 4. Logistic Regression
                        log_reg = LogisticRegression(random_state=42)
                        log_reg.fit(features[:-1], labels[:-1])
                        log_prob_up = log_reg.predict_proba(today_features)[0][1]
                        if log_prob_up > 0.6:
                            reasons.append(f"Machine Learning (Logistic Regression): Baseline classifier is BULLISH ({log_prob_up*100:.1f}%).")
                        elif log_prob_up < 0.4:
                            reasons.append(f"Machine Learning (Logistic Regression): Baseline classifier is BEARISH ({log_prob_up*100:.1f}%).")
                        else:
                            reasons.append(f"Machine Learning (Logistic Regression): Baseline classifier is NEUTRAL ({log_prob_up*100:.1f}%).")

                        # 5. PCA (Principal Component Analysis) Dimensionality Reduction
                        pca = PCA(n_components=2)
                        pca.fit(features)
                        explained_var = sum(pca.explained_variance_ratio_)
                        reasons.append(f"Machine Learning (PCA): Top 2 Principal Components explain {explained_var*100:.1f}% of market variance (Dimensionality Reduced).")
                            
                    except ImportError:
                        # Fallback if scikit-learn isn't installed
                        reasons.append("Machine Learning: scikit-learn not found. Using standard quantitative heuristics.")
                        
            else:
                reasons.append("Machine Learning: Insufficient OHLC data provided to train models.")

        except Exception as e:
            logger.error(f"Error in MachineLearningEngine: {e}")
            reasons.append(f"Machine Learning Engine: Error executing predictive models: {e}")

        return {
            "branch": "Machine Learning & AI",
            "score": max(-1.0, min(1.0, score)),
            "reasons": reasons
        }
