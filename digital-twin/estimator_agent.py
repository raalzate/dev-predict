import spade
from spade.behaviour import CyclicBehaviour
import joblib
import json
import pandas as pd
from scipy.sparse import hstack
import os

# La misma función de extracción de características que en train_model.py
def extract_features(df_to_feature):
    """
    Función de extracción de características mejorada, basada en el análisis del nuevo dataset.
    """
    df_featured = df_to_feature.copy()
    
    # Características estructurales
    gherkin_keywords = ['Given', 'When', 'Then', 'And', 'Dado', 'Cuando', 'Entonces', 'Y']
    df_featured['gherkin_steps'] = df_featured['gherkin'].apply(lambda x: sum(x.count(word) for word in gherkin_keywords))
    df_featured['num_unit_tests'] = df_featured['unit_tests'].apply(lambda x: x.lower().count('def test_'))

    # Características temáticas/de dominio
    df_featured['has_frontend'] = df_featured['full_text'].str.contains('frontend|UI|interfaz|CSS|React|Angular|Vue', case=False).astype(int)
    df_featured['has_backend'] = df_featured['full_text'].str.contains('backend|servidor|database|base de datos|bd|API', case=False).astype(int)
    df_featured['has_security'] = df_featured['full_text'].str.contains('seguridad|security|JWT|OAuth|token|autenticación', case=False).astype(int)
    df_featured['has_performance'] = df_featured['full_text'].str.contains('performance|rendimiento|cache|optimización|índice|vistas materializadas', case=False).astype(int)
    df_featured['has_devops'] = df_featured['full_text'].str.contains('devops|CI/CD|Docker|pipeline|deployment|monitoreo', case=False).astype(int)
    df_featured['has_data_migration'] = df_featured['full_text'].str.contains('migración|migration|schema', case=False).astype(int)
    df_featured['has_payment'] = df_featured['full_text'].str.contains('pago|payment|stripe|paypal', case=False).astype(int)

    return df_featured


class EstimatorAgent(spade.agent.Agent):
    def __init__(self, jid, password):
        super().__init__(jid, password)
        self.model = None
        self.vectorizer = None

    class EstimationBehav(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10) 
            if msg and msg.metadata.get("performative") == "request":
                story_data = json.loads(msg.body)
                title = story_data.get('title', 'N/A')
                print(f"[Estimator] Recibida solicitud de estimación para: '{title}'")

                try:
                    # 1. Crear un DataFrame de una sola fila
                    single_story_df = pd.DataFrame([story_data])
                    single_story_df['full_text'] = single_story_df['gherkin'] + " " + single_story_df['unit_tests']

                    # 2. Aplicar la ingeniería de características avanzada
                    df_featured = extract_features(single_story_df)

                    # 3. Vectorizar el texto
                    X_text = self.agent.vectorizer.transform(df_featured['full_text'])

                    # 4. Obtener las características numéricas
                    feature_columns = [
                        'gherkin_steps', 'num_unit_tests', 'has_frontend', 'has_backend', 
                        'has_security', 'has_performance', 'has_devops', 'has_data_migration', 'has_payment'
                    ]
                    X_numerical = df_featured[feature_columns].values

                    # 5. Combinar todo en un único vector de características
                    X_final_story = hstack([X_text, X_numerical]).tocsr()

                    # 6. Realizar la predicción
                    prediction = self.agent.model.predict(X_final_story)
                    effort, time = prediction[0]
                    
                    print(f"[Estimator] Predicción para '{title}': Esfuerzo={effort:.1f}, Tiempo={time:.1f}h")

                    # 7. Enviar respuesta
                    reply = spade.message.Message(
                        to=str(msg.sender),
                        body=json.dumps({"effort": round(effort, 2), "time": round(time, 2)}),
                        metadata={"performative": "inform"},
                        thread=msg.thread
                    )
                    await self.send(reply)

                except Exception as e:
                    print(f"Exception running behaviour {type(self).__name__}: {e}")
                    error_reply = spade.message.Message(
                        to=str(msg.sender),
                        body=json.dumps({"error": str(e)}),
                        metadata={"performative": "failure"},
                        thread=msg.thread
                    )
                    await self.send(error_reply)


    async def setup(self):
        print("[Estimator] Agente iniciado. Cargando modelos...")
        model_path = 'model/effort_model.pkl'
        vectorizer_path = 'model/text_vectorizer.pkl'
        if os.path.exists(model_path) and os.path.exists(vectorizer_path):
            self.model = joblib.load(model_path)
            self.vectorizer = joblib.load(vectorizer_path)
            print("[Estimator] Modelos cargados correctamente.")
            self.add_behaviour(self.EstimationBehav())
        else:
            print(f"[Estimator] ERROR: No se encontraron los archivos '{model_path}' o '{vectorizer_path}'.")
            print("[Estimator] Por favor, ejecuta 'python train_model.py' primero.")
            await self.stop()

