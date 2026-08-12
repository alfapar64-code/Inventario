from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from PIL import Image
import io
import json
import os
from pillow_heif import register_heif_opener

# Habilitar soporte para fotos .heic
register_heif_opener()

app = Flask(__name__)

# CONFIGURACIÓN DE TU API KEY
api_key_segura = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key_segura)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calcular', methods=['POST'])
def calcular():
    sabor = request.form.get('sabor')
    foto = request.files.get('foto')

    # LÓGICA 1: MOSTRADOR COMPLETO (1 Foto -> 12 Carriles)
    if sabor == 'MOSTRADOR_COMPLETO':
        if not foto or foto.filename == '':
            return jsonify({'error': 'Necesitas adjuntar la foto de la vitrina.'})
        
        image = Image.open(io.BytesIO(foto.read()))
        prompt = (
            "Eres un asistente experto en inventarios. Analiza esta vitrina de empanadas que tiene 12 carriles físicos. "
            "De izquierda a derecha, los carriles corresponden a: 1: JQ, 2: HM, 3: CQ, 4: CA, 5: RJ, 6: BD, 7: CP, 8: PL, 9: CB, 10: CC, 11: CS, 12: JQ. "
            "Cuenta minuciosamente la cantidad de empanadas visibles en cada carril. "
            "Devuelve ÚNICAMENTE un objeto JSON válido donde las claves sean las iniciales y el valor sea el conteo de unidades. "
            "IMPORTANTE: Suma el conteo del carril 1 y el carril 12 juntos bajo la clave 'JQ'. "
            "Formato estricto requerido de ejemplo: {\"JQ\": 9, \"HM\": 2, \"CQ\": 1, \"CA\": 1, \"RJ\": 2, \"BD\": 2, \"CP\": 4, \"PL\": 6, \"CB\": 7, \"CC\": 4, \"CS\": 6}"
        )
        
        response = model.generate_content([prompt, image])
        
        try:
            # Limpiar la respuesta para asegurar que sea un JSON puro
            texto = response.text.strip().strip('```json').strip('```')
            datos_mostrador = json.loads(texto)
            return jsonify({'tipo': 'mostrador', 'datos': datos_mostrador})
        except Exception as e:
            return jsonify({'error': 'No se pudo leer correctamente la vitrina. Intenta con una foto más clara.'})

    # LÓGICA 2: CARGA INDIVIDUAL POR SABOR (Manual + Foto Incompletos)
    else:
        cajones = int(request.form.get('cajones', 0) or 0)
        bandejas = int(request.form.get('bandejas', 0) or 0)
        espera = int(request.form.get('espera', 0) or 0)
        
        multiplicador_cajon = 14 if 'Burrito' in sabor else 30
        total_manual = (cajones * multiplicador_cajon) + (bandejas * 40) + espera
        
        total_ia = 0
        if foto and foto.filename != '':
            image = Image.open(io.BytesIO(foto.read()))
            prompt = (
                f"Eres un asistente de inventario. En la imagen hay empanadas/burritos de {sabor}. "
                "Cuenta cuidadosamente la cantidad exacta de unidades. "
                "Responde ÚNICAMENTE con el número final, sin texto."
            )
            response = model.generate_content([prompt, image])
            try:
                total_ia = int(''.join(filter(str.isdigit, response.text)))
            except ValueError:
                total_ia = 0
                
        total_final = total_manual + total_ia
        
        return jsonify({
            'tipo': 'individual',
            'sabor': sabor,
            'total': total_final
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
