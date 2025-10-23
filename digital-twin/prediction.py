import os
import logging
import joblib
import pandas as pd
import spacy
from config import extract_features
from config import NUMERICAL_FEATURES

logger = logging.getLogger(__name__)

class PredictionService:
    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model pipeline file not found at: {model_path}")
        self.pipeline = joblib.load(model_path)
        try:
            self.nlp = spacy.load('es_core_news_sm')
        except OSError:
            logger.info("Downloading 'es_core_news_sm' spacy model.")
            os.system("python -m spacy download es_core_news_sm")
            self.nlp = spacy.load('es_core_news_sm')
        logger.info("[PredictionService] Prediction pipeline loaded successfully.")

    def lemmatize_text(self, text: str) -> str:
        doc = self.nlp(text.lower())
        return " ".join([token.lemma_ for token in doc if not token.is_stop and not token.is_punct])

    def predict(self, story_data: dict) -> tuple[float, float]:
        single_story_df = pd.DataFrame([story_data])
        df_featured = extract_features(single_story_df)
        df_featured['full_text_lemmatized'] = df_featured['full_text'].apply(self.lemmatize_text)
        
        # Reorder columns to match model's expectations
        df_featured = df_featured.reindex(columns=NUMERICAL_FEATURES, fill_value=0)
        
        prediction = self.pipeline.predict(df_featured)
        effort, time = prediction[0]
        return effort, time
