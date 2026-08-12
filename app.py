from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from PIL import Image
import io
import json
import os
from pillow_heif import register_heif_opener

register_heif_opener()
app = Flask(__name__)

api_key_segura = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key_segura)

# CAMBIO DEFINITIVO: Usaremos la versión "Pro" que es universal y más potente
model = genai.GenerativeModel('gemini-1.5-pro')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calcular', methods=['POST'])
def calcular():
    sabor = request.form.get('sabor')
    foto = request.files.get('foto') or request.files.get('foto_galeria')

    def preparar_imagen(archivo_foto):
        img = Image.open(io.BytesIO(archivo_foto.read()))
        if img.mode in ("RGBA", "P", "CMYK"):
            img = img.convert("RGB")
        # Reducimos un poco el tamaño para que sea ultra rápido
        img.thumbnail((800, 800)) 
        return img

    try:
        if sabor == 'MOSTRADOR_COMPLETO':
            if not foto or foto.filename == '':
                return jsonify({'error': 'Falta la foto'})
            
            image = preparar_imagen(foto)
            prompt = (
                "Analiza la vitrina de empanadas. Carriles: 1: JQ, 2: HM, 3: CQ, 4: CA, 5: RJ, 6: BD, 7: CP, 8: PL, 9: CB, 10: CC, 11: CS, 12: JQ. "
                "Devuelve SOLO un JSON válido. Ejemplo: {\"JQ\": 5, \"HM\": 2, \"CQ\": 0, ...}."
                "Suma carril 1 y 12 en JQ."
            )
            response = model.generate_content([prompt, image])
            texto = response.text.strip().replace('```json', '').replace('```', '')
            datos = json.loads(texto)
            return jsonify({'tipo': 'mostrador', 'datos': datos})

        else:
            cajones = int(request.form.get('cajones', 0) or 0)
            bandejas = int(request.form.get('bandejas', 0) or 0)
            espera = int(request.form.get('espera', 0) or 0)
            
            total_manual = (cajones * (14 if 'Burrito' in sabor else 30)) + (bandejas * 40) + espera
            total_ia = 0
            
            if foto and foto.filename != '':
                image = preparar_imagen(foto)
                prompt = f"Cuenta las empanadas visibles de {sabor}. Devuelve SOLO un JSON: {{\"cantidad\": numero}}. Ejemplo: {{\"cantidad\": 24}}"
                response = model.generate_content([prompt, image])
                texto = response.text.strip().replace('```json', '').replace('```', '')
                try:
                    data = json.loads(texto)
                    total_ia = int(data.get('cantidad', 0))
                except:
                    total_ia = 0
                    
            return jsonify({'tipo': 'individual', 'sabor': sabor, 'total': total_manual + total_ia})
    except Exception as e:
        return jsonify({'error': f'Error procesando foto: {str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
