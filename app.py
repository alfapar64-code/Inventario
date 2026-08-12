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

def llamar_google_directo(prompt, img_bytes):
    api_key = os.environ.get("GEMINI_API_KEY")
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    
    # 1. AUTO-DESCUBRIMIENTO: Le preguntamos a Google qué modelo acepta tu Llave exacta
    modelo_detectado = 'gemini-1.5-flash' # Valor por defecto
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        req_list = urllib.request.Request(list_url)
        with urllib.request.urlopen(req_list) as resp_list:
            list_data = json.loads(resp_list.read().decode('utf-8'))
            for m in list_data.get('models', []):
                methods = m.get('supportedGenerationMethods', [])
                m_name = m.get('name', '')
                if 'generateContent' in methods and 'gemini' in m_name:
                    modelo_detectado = m_name.replace('models/', '')
                    break
    except Exception:
        pass

    # 2. Intentamos conectar probando las rutas oficiales (v1beta y v1) con el modelo descubierto
    versiones = ['v1beta', 'v1']
    ultimo_error = ""
    
    for ver in versiones:
        try:
            url = f"https://generativelanguage.googleapis.com/{ver}/models/{modelo_detectado}:generateContent?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}}
                    ]
                }]
            }
            data_bytes = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return res_data['candidates'][0]['content']['parts'][0]['text']
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode('utf-8')
            try:
                ultimo_error = json.loads(err_msg)['error']['message']
            except:
                ultimo_error = str(e)
            continue
        except Exception as e:
            ultimo_error = str(e)
            continue
            
    raise Exception(f"Modelo ({modelo_detectado}): {ultimo_error}")

@app.route('/')
def index():
    return render_template('index.html')

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
                "Analiza la vitrina de empanadas. Carriles: 1: JQ, 2: HM, 3: CQ, 4: CA, 5: RJ, 6: BD, 7: CP, 8: PL, 9: CB, 10: CC, 11: CS, 12: JQ. "
                "Devuelve SOLO un JSON válido. Ejemplo: {\"JQ\": 5, \"HM\": 2, \"CQ\": 0, ...}."
                "Suma carril 1 y 12 en JQ."
            )
            
            texto_respuesta = llamar_google_directo(prompt, img_bytes_seguros)
            texto_limpio = texto_respuesta.strip().replace('```json', '').replace('```', '')
            datos = json.loads(texto_limpio)
            return jsonify({'tipo': 'mostrador', 'datos': datos})

        else:
            cajones = int(request.form.get('cajones', 0) or 0)
            bandejas = int(request.form.get('bandejas', 0) or 0)
            espera = int(request.form.get('espera', 0) or 0)
            
            total_manual = (cajones * (14 if 'Burrito' in sabor else 30)) + (bandejas * 40) + espera
            
            prompt = f"Cuenta las empanadas visibles de {sabor}. Devuelve SOLO un JSON: {{\"cantidad\": numero}}. Ejemplo: {{\"cantidad\": 24}}"
            
            texto_respuesta = llamar_google_directo(prompt, img_bytes_seguros)
            texto_limpio = texto_respuesta.strip().replace('```json', '').replace('```', '')
            
            try:
                data = json.loads(texto_limpio)
                total_ia = int(data.get('cantidad', 0))
            except:
                total_ia = 0
                    
            return jsonify({'tipo': 'individual', 'sabor': sabor, 'total': total_manual + total_ia})
            
    except Exception as e:
        return jsonify({'error': f'{str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
