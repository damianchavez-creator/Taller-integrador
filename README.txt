SIMULADOR MONTE CARLO DE CONCENTRACION DE MERCADO
==================================================

Aplicacion web (Streamlit) que simula estructuras de mercado aleatorias,
calcula el IHH o el CRk, permite analizar un "Caso Particular" y evalua al
usuario sobre el nivel de concentracion de ese caso.


ARCHIVOS
--------
app.py            Interfaz de la aplicacion (Streamlit).
motor.py          Funciones de calculo y simulacion: cr_k, ihh,
                  generar_cuotas, simular_mercado.
requirements.txt  Librerias necesarias.
README.txt        Este archivo.

IMPORTANTE: app.py importa motor.py, por lo que ambos deben estar en la
misma carpeta.


REQUISITOS
----------
- Python 3.10 o superior
- Librerias (se instalan con requirements.txt):
    streamlit, numpy, pandas, plotly


EJECUCION LOCAL
---------------
1. Abre una terminal en la carpeta del proyecto.

2. (Recomendado) Crea y activa un entorno virtual:

     python -m venv venv

     Windows:      venv\Scripts\activate
     Mac / Linux:  source venv/bin/activate

3. Instala las librerias:

     pip install -r requirements.txt

4. Ejecuta la aplicacion:

     streamlit run app.py

5. Se abrira el navegador en http://localhost:8501


USO BASICO
----------
1. En la barra lateral elige el indicador (IHH o CRk), el numero de
   empresas N (2 a 100) y las iteraciones (por defecto 1000).
2. Pulsa "Ejecutar simulacion".
3. En "Caso particular" ingresa las cuotas a mano (deben sumar 100%) o
   genera un caso aleatorio.
4. Revisa el histograma, donde una linea roja marca el caso particular.
5. En "Evaluacion" responde si la concentracion es Baja, Moderada o Alta
   y pulsa "Verificar respuesta".

Nota: un numero muy alto de iteraciones aumenta el tiempo de calculo y el
consumo de recursos.


DESPLIEGUE PUBLICO (Streamlit Community Cloud)
----------------------------------------------
1. Sube a un repositorio de GitHub: app.py, motor.py y requirements.txt.
2. Entra a https://share.streamlit.io e inicia sesion con GitHub.
3. Crea una nueva app, selecciona el repositorio y como archivo principal
   indica app.py.
4. Pulsa "Deploy".
