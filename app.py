from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from PIL import Image
import io
from pillow_heif import register_heif_opener

# Habilitar soporte para procesar las fotos .heic de tu teléfono
register_heif_opener()

app = Flask(__name__)

# Configura tu NUEVA API Key aquí (separada de la de los remitos)
genai.configure(api_key="TU_NUEVA_API_KEY_AQUI")

# Modelo optimizado para análisis rápido
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calcular', methods=['POST'])
def calcular():
    sabor = request.form.get('sabor', 'Empanada')
    cajones = int(request.form.get('cajones', 0) or 0)
    bandejas = int(request.form.get('bandejas', 0) or 0)
    espera = int(request.form.get('espera', 0) or 0)
    
    # 1. Cálculos fijos automatizados
    multiplicador_cajon = 14 if sabor == 'Burrito' else 30
    total_manual = (cajones * multiplicador_cajon) + (bandejas * 40) + espera
    
    total_ia = 0
    foto = request.files.get('foto')
    
    # 2. Procesamiento visual de cajones/bandejas/vitrinas incompletas
    if foto and foto.filename != '':
        image = Image.open(io.BytesIO(foto.read()))
        
        prompt = (
            f"Eres un asistente experto en inventarios. En la imagen hay un contenedor o exhibidor con {sabor.lower()}s. "
            "Cuenta minuciosamente la cantidad exacta de unidades visibles. "
            "Responde ÚNICAMENTE con el número final del conteo, sin letras ni texto adicional."
        )
        
        response = model.generate_content([prompt, image])
        
        try:
            # Extracción estricta del número devuelto por la IA
            total_ia = int(''.join(filter(str.isdigit, response.text)))
        except ValueError:
            total_ia = 0
            
    # 3. Consolidación de datos
    total_final = total_manual + total_ia
    
    return jsonify({
        'total': total_final,
        'manual': total_manual,
        'ia': total_ia
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')