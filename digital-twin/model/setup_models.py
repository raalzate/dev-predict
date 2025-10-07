import pandas as pd
from scipy.sparse import hstack
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor

print("Iniciando el proceso de entrenamiento FINAL con el modelo OPTIMIZADO...")

# 1. Cargar el dataset
try:
    df = pd.read_csv('stories_dataset.csv')
    print(f"Dataset 'stories_dataset.csv' cargado. Contiene {len(df)} registros.")
except FileNotFoundError:
    print("ERROR: No se encontró el archivo 'stories_dataset.csv'. Por favor, asegúrate de que exista.")
    exit()

# 2. Combinar textos y aplicar Feature Engineering
df['full_text'] = df['gherkin'] + " " + df['unit_tests']

def extract_features(df_to_feature):
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

df_featured = extract_features(df)
print("Ingeniería de características aplicada.")


# 3. Preparación de Datos para el Modelo
y = df_featured[['effort', 'time']]

# Vectorización del texto
spanish_stop_words = [
    'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por', 'un', 
    'para', 'con', 'no', 'una', 'su', 'al', 'lo', 'como', 'más', 'pero', 'sus', 
    'le', 'ya', 'o', 'este', 'ha', 'sí', 'porque', 'esta', 'cuando', 'muy', 'sin', 
    'sobre', 'también', 'me', 'hasta', 'hay', 'donde', 'quien', 'desde', 'todo', 
    'nos', 'durante', 'todos', 'uno', 'les', 'ni', 'contra', 'otros', 'ese', 'eso', 
    'ante', 'ellos', 'e', 'esto', 'mí', 'antes', 'algunos', 'qué', 'entre', 'ser', 
    'esa', 'estos', 'este', 'estoy'
]
vectorizer = TfidfVectorizer(stop_words=spanish_stop_words, max_features=500)
X_text_vectorized = vectorizer.fit_transform(df_featured['full_text'])

# Obtener las características numéricas
feature_columns = ['gherkin_steps', 'num_unit_tests', 'has_frontend', 'has_backend', 'has_security', 'has_performance', 'has_devops', 'has_data_migration', 'has_payment']
X_numerical_features = df_featured[feature_columns].values

# Combinar todas las características
X_final = hstack([X_text_vectorized, X_numerical_features]).tocsr()
print("Características de texto y numéricas combinadas para el set de datos completo.")


# 4. Entrenamiento del Modelo Final con los mejores parámetros
print("Configurando y entrenando el modelo final con los hiperparámetros óptimos...")

# Usamos los mejores parámetros encontrados por GridSearchCV
best_params = {
    'n_estimators': 200,
    'learning_rate': 0.1,
    'max_depth': 5,
    'random_state': 42
}

base_optimized_model = GradientBoostingRegressor(**best_params)

final_model = MultiOutputRegressor(estimator=base_optimized_model)

# Entrenamos con TODOS los datos disponibles
final_model.fit(X_final, y)
print("Modelo final entrenado exitosamente con el 100% de los datos.")


# 5. Guardar los artefactos del modelo
joblib.dump(final_model, 'effort_model.pkl')
joblib.dump(vectorizer, 'text_vectorizer.pkl')

print("\n¡Proceso de producción del modelo completado!")
print("Archivos 'effort_model.pkl' y 'text_vectorizer.pkl' han sido generados con la versión más optimizada.")
print("¡Tu sistema de agentes está listo para usar su cerebro más potente!")

