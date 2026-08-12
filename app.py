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

def analizar_con_ia(prompt, img_bytes):
    modelos_respaldo = ['gemini-1.5-flash', 'gemini-1.5-pro']
    ultimo_error = ""
    for nombre in modelos_respaldo:
        try:
            modelo_temporal = genai.GenerativeModel(nombre)
            # Enviar la imagen como datos binarios JPEG puros para evitar que Google la rechace
            imagen_segura = {
                "mime_type": "image/jpeg",
                "data": img_bytes
            }
            respuesta = modelo_temporal.generate_content([prompt, imagen_segura])
            return respuesta
        except Exception as e:
            ultimo_error = str(e)
            continue
            
    # Si todo falla, mostramos el error EXACTO de Google para no adivinar más
    raise Exception(f"Último error de Google: {ultimo_error}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calcular', methods=['POST'])
def calcular():
    sabor = request.form.get('sabor')
    foto = request.files.get('foto') or request.files.get('foto_galeria')

    def preparar_imagen_segura(archivo_foto):
        # 1. Leemos la foto (sea HEIC, PNG o JPG)
        img = Image.open(io.BytesIO(archivo_foto.read()))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((800, 800))
        
        # 2. La transformamos obligatoriamente a un JPEG estándar en la memoria
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        return buffer.getvalue()

    try:
        if sabor == 'MOSTRADOR_COMPLETO':
            if not foto or foto.filename == '':
                return jsonify({'error': 'Falta la foto'})
            
            img_bytes = preparar_imagen_segura(foto)
            prompt = (
                "Analiza la vitrina de empanadas. Carriles: 1: JQ, 2: HM, 3: CQ, 4: CA, 5: RJ, 6: BD, 7: CP, 8: PL, 9: CB, 10: CC, 11: CS, 12: JQ. "
                "Devuelve SOLO un JSON válido. Ejemplo: {\"JQ\": 5, \"HM\": 2, \"CQ\": 0, ...}."
                "Suma carril 1 y 12 en JQ."
            )
            
            response = analizar_con_ia(prompt, img_bytes)
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
                img_bytes = preparar_imagen_segura(foto)
                prompt = f"Cuenta las empanadas visibles de {sabor}. Devuelve SOLO un JSON: {{\"cantidad\": numero}}. Ejemplo: {{\"cantidad\": 24}}"
                
                response = analizar_con_ia(prompt, img_bytes)
                texto = response.text.strip().replace('```json', '').replace('```', '')
                try:
                    data = json.loads(texto)
                    total_ia = int(data.get('cantidad', 0))
                except:
                    total_ia = 0
                    
            return jsonify({'tipo': 'individual', 'sabor': sabor, 'total': total_manual + total_ia})
            
    except Exception as e:
        return jsonify({'error': f'{str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
