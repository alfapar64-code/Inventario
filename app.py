from flask import Flask, request, jsonify, render_template
from PIL import Image
import io
import json
import os
import base64
import urllib.request
import urllib.error
from pillow_heif import register_heif_opener

register_heif_opener()
app = Flask(__name__)

# Modificamos la función para que acepte tanto imágenes como audios
def llamar_google_directo(prompt, file_bytes, mime_type="image/jpeg"):
    api_key = os.environ.get("GEMINI_API_KEY")
    modelo = 'gemini-flash-latest'
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
    
    b64_data = base64.b64encode(file_bytes).decode("utf-8")
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": mime_type, "data": b64_data}}
            ]
        }]
    }
    
    data_bytes = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['candidates'][0]['content']['parts'][0]['text']
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8')
        raise Exception(f"Google dice: {error_msg}")
    except Exception as e:
        raise Exception(f"Error de conexión: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

# --- NUEVA SECCIÓN: PROCESAR AUDIO DE VOZ ---
@app.route('/dictar', methods=['POST'])
def dictar():
    if 'audio' not in request.files:
        return jsonify({'error': 'No se recibió ningún audio'})
    
    try:
        audio_file = request.files['audio']
        audio_bytes = audio_file.read()
        
        # Le decimos a Google que es un archivo de voz
        mime_type = audio_file.mimetype if audio_file.mimetype else 'audio/webm'
        
        prompt = (
            "Eres un asistente de inventario. Escucha este audio donde dicto las cantidades de empanadas en mi mostrador. "
            "Extrae qué cantidad corresponde a qué sabor. "
            "Usa ESTRICTAMENTE estos nombres exactos como claves en el JSON: "
            "'Jamón y Queso (JQ)', 'Humita (HM)', 'Cebolla y Queso (CQ)', 'Capresse (CA)', 'Roquefort y Jamón (RJ)', "
            "'Bondiola (BD)', 'Carne Picante (CP)', 'Pollo (PL)', 'Cheese Burger (CB)', 'Carne Cuchillo (CC)', 'Carne Suave (CS)'. "
            "Devuelve SOLO un JSON válido. Ejemplo: {\"Jamón y Queso (JQ)\": 12, \"Humita (HM)\": 5, \"Carne Cuchillo (CC)\": 8}"
        )
        
        texto_respuesta = llamar_google_directo(prompt, audio_bytes, mime_type)
        texto_limpio = texto_respuesta.strip().replace('```json', '').replace('```', '')
        datos = json.loads(texto_limpio)
        
        return jsonify({'tipo': 'dictado', 'datos': datos})
    except Exception as e:
        return jsonify({'error': str(e)})
# ---------------------------------------------

@app.route('/calcular', methods=['POST'])
def calcular():
    sabor = request.form.get('sabor')
    foto = request.files.get('foto') or request.files.get('foto_galeria')

    if not foto or foto.filename == '':
        return jsonify({'error': 'Falta la foto'})

    try:
        img = Image.open(io.BytesIO(foto.read()))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((800, 800))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        img_bytes_seguros = buffer.getvalue()

        if sabor == 'MOSTRADOR_COMPLETO':
            prompt = (
                "Actúa como auditor de inventario. Esta imagen es una vitrina de empanadas dividida por barras de metal en 12 carriles verticales exactos. "
                "De izquierda a derecha, los carriles corresponden a: 1: JQ, 2: HM, 3: CQ, 4: CA, 5: RJ, 6: BD, 7: CP, 8: PL, 9: CB, 10: CC, 11: CS, 12: JQ. "
                "Tu tarea es mirar CADA carril individualmente, de izquierda a derecha, y contar cuántas empanadas hay en cada uno. "
                "Presta atención a las empanadas superpuestas hacia el fondo. "
                "IMPORTANTE: Suma las cantidades del carril 1 y el carril 12 bajo la misma clave 'JQ'. "
                "Devuelve SOLO un JSON válido con los totales. Ejemplo: {\"JQ\": 15, \"HM\": 4, \"CQ\": 0, \"CA\": 2, \"RJ\": 5, \"BD\": 8, \"CP\": 1, \"PL\": 3, \"CB\": 6, \"CC\": 9, \"CS\": 12}"
            )
            texto_respuesta = llamar_google_directo(prompt, img_bytes_seguros, "image/jpeg")
            texto_limpio = texto_respuesta.strip().replace('```json', '').replace('```', '')
            datos = json.loads(texto_limpio)
            return jsonify({'tipo': 'mostrador', 'datos': datos})

        elif sabor == 'CAJON_CONGELADOS':
            prompt = (
                "Actúa como un auditor de inventario experto. Analiza este cajón verde dividido en 4 filas horizontales. "
                "Cada fila contiene un sabor diferente de empanadas. Cuenta meticulosamente las empanadas visibles en cada fila. "
                "Ten en cuenta que la capacidad máxima por fila es de 6 empanadas. "
                "Fila 1 (Superior): Puerro y Hongos. "
                "Fila 2: Choclo y Calabaza. "
                "Fila 3: Pollo al Curry (masa color amarillo). "
                "Fila 4 (Inferior): Carne Criolla. "
                "Devuelve SOLO un JSON válido con la cantidad exacta de cada sabor. Ejemplo: {\"Puerro y Hongos\": 5, \"Choclo y Calabaza\": 5, \"Pollo al Curry\": 6, \"Carne Criolla\": 4}"
            )
            texto_respuesta = llamar_google_directo(prompt, img_bytes_seguros, "image/jpeg")
            texto_limpio = texto_respuesta.strip().replace('```json', '').replace('```', '')
            datos = json.loads(texto_limpio)
            return jsonify({'tipo': 'cajon_multiple', 'datos': datos})

        else:
            cajones = int(request.form.get('cajones', 0) or 0)
            bandejas = int(request.form.get('bandejas', 0) or 0)
            espera = int(request.form.get('espera', 0) or 0)
            
            total_manual = (cajones * (14 if 'Burrito' in sabor else 30)) + (bandejas * 40) + espera
            
            prompt = f"Cuenta las empanadas visibles de {sabor}. Devuelve SOLO un JSON: {{\"cantidad\": numero}}. Ejemplo: {{\"cantidad\": 24}}"
            texto_respuesta = llamar_google_directo(prompt, img_bytes_seguros, "image/jpeg")
            texto_limpio = texto_respuesta.strip().replace('```json', '').replace('```', '')
            
            try:
                data = json.loads(texto_limpio)
                total_ia = int(data.get('cantidad', 0))
            except:
                total_ia = 0
                    
            return jsonify({'tipo': 'individual', 'sabor': sabor, 'total': total_manual + total_ia})
            
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
