from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from PIL import Image
import io
import json
import os
import traceback
from pillow_heif import register_heif_opener

# Habilitar soporte para fotos .heic
register_heif_opener()

app = Flask(__name__)

api_key_segura = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key_segura)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calcular', methods=['POST'])
def calcular():
    sabor = request.form.get('sabor')
    foto = request.files.get('foto') or request.files.get('foto_galeria')

    def preparar_imagen(archivo_foto):
        try:
            # Usar io.BytesIO para que Pillow lea correctamente el archivo subido desde Flask
            img = Image.open(io.BytesIO(archivo_foto.read()))
            if img.mode in ("RGBA", "P", "CMYK"):
                img = img.convert("RGB")
            img.thumbnail((800, 800)) 
            return img
        except Exception as e:
            print(f"Error crítico en preparar_imagen: {traceback.format_exc()}")
            raise e

    if sabor == 'MOSTRADOR_COMPLETO':
        if not foto or foto.filename == '':
            return jsonify({'error': 'Por favor, toma una foto o selecciona una de la galería.'})
        
        try:
            image = preparar_imagen(foto)
            prompt = (
                "Analiza esta vitrina. Carriles: 1: JQ, 2: HM, 3: CQ, 4: CA, 5: RJ, 6: BD, 7: CP, 8: PL, 9: CB, 10: CC, 11: CS, 12: JQ. "
                "Devuelve SOLO un objeto JSON válido con las iniciales (JQ, HM, etc.) y conteo de unidades. Suma carril 1 y 12 en 'JQ'. "
                "Ejemplo: {\"JQ\": 5, \"HM\": 2, \"CQ\": 1, \"CA\": 1, \"RJ\": 2, \"BD\": 2, \"CP\": 4, \"PL\": 6, \"CB\": 7, \"CC\": 4, \"CS\": 6}"
            )
            response = model.generate_content([prompt, image])
            texto = response.text.strip().strip('```json').strip('```')
            datos_mostrador = json.loads(texto)
            return jsonify({'tipo': 'mostrador', 'datos': datos_mostrador})
        except Exception as e:
            print(f"Error procesando vitrina: {e}")
            return jsonify({'error': 'No pude leer la foto. Asegúrate de que sea clara.'})

    else:
        cajones = int(request.form.get('cajones', 0) or 0)
        bandejas = int(request.form.get('bandejas', 0) or 0)
        espera = int(request.form.get('espera', 0) or 0)
        
        multiplicador = 14 if 'Burrito' in sabor else 30
        total_manual = (cajones * multiplicador) + (bandejas * 40) + espera
        
        total_ia = 0
        if foto and foto.filename != '':
            try:
                image = preparar_imagen(foto)
                prompt = f"Cuenta solo la cantidad exacta de unidades de {sabor} en la imagen. Responde solo el número."
                response = model.generate_content([prompt, image])
                total_ia = int(''.join(filter(str.isdigit, response.text)))
            except Exception as e:
                print(f"Error en conteo individual: {e}")
                total_ia = 0
                
        return jsonify({'tipo': 'individual', 'sabor': sabor, 'total': total_manual + total_ia})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
