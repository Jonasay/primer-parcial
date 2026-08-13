from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from datetime import datetime, timedelta, date
from supabase import create_client, Client
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
CORS(app)


SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/usuarios', methods=['GET'])
def obtener_usuarios():
    if not supabase:
        return jsonify({"error": "error"}), 500
    try:
        response = supabase.table('usuarios').select('id, nombre, racha_actual, racha_maxima, ultima_fecha_login').order('racha_actual', desc=True).execute()
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/registrar', methods=['POST'])
def registrar_usuario():
    """Registra un nuevo usuario con contraseña hasheada."""
    if not supabase:
        return jsonify({"error": "Supabase no está configurado (revisar SUPABASE_URL y SUPABASE_KEY)"}), 500
    data = request.get_json() or {}
    nombre = data.get('nombre')
    password = data.get('password')
    
    if not nombre or not password:
        return jsonify({"error": "El nombre de usuario y la contraseña son obligatorios"}), 400
        
    try:
        # Verificar si existe
        user_check = supabase.table('usuarios').select('*').eq('nombre', nombre).execute()
        if user_check.data:
            return jsonify({"error": "El usuario ya existe"}), 400
            
        password_hash = generate_password_hash(password)

        nuevo_usuario = {
            "nombre": nombre,
            "password_hash": password_hash,
            "racha_actual": 0,
            "racha_maxima": 0,
            "ultima_fecha_login": None
        }
        response = supabase.table('usuarios').insert(nuevo_usuario).execute()
        return jsonify({"mensaje": f"Usuario '{nombre}' registrado exitosamente.", "data": response.data[0]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/login', methods=['POST'])
def login():
 
    if not supabase:
        return jsonify({"error": "Supabase no está configurado "}), 500
    data = request.get_json() or {}
    nombre = data.get('nombre')
    password = data.get('password')
    
    if not nombre or not password:
        return jsonify({"error": "El nombre de usuario y la contraseña son requeridos"}), 400

    try:
        user_res = supabase.table('usuarios').select('*').eq('nombre', nombre).execute()
        if not user_res.data:
            return jsonify({"error": "Usuario no encontrado"}), 404
            
        usuario = user_res.data[0]
        
    
        stored_hash = usuario.get('password_hash')
        if stored_hash and not check_password_hash(stored_hash, password):
            return jsonify({"error": "Contraseña incorrecta"}), 401
        
        hoy = date.today()
        ayer = hoy - timedelta(days=1)
        
        racha_actual = usuario.get('racha_actual', 0)
        racha_maxima = usuario.get('racha_maxima', 0)
        ultima_fecha_str = usuario.get('ultima_fecha_login')
        
        nueva_racha = 1
        mensaje_racha = ""
        
        if ultima_fecha_str:
            ultima_fecha = datetime.strptime(ultima_fecha_str, "%Y-%m-%d").date()
            if ultima_fecha == hoy:
                # Ya había iniciado sesión hoy
                nueva_racha = racha_actual
                mensaje_racha = "¡Hola de nuevo hoy! Tu racha se mantiene."
            elif ultima_fecha == ayer:
                # La racha continúa e incrementa
                nueva_racha = racha_actual + 1
                mensaje_racha = "¡Excelente! Has iniciado sesión en días consecutivos. Racha incrementada."
            else:
                # Rompió racha (pasaron 2 o más días)
                nueva_racha = 1
                mensaje_racha = "Pasaron más de 24h desde tu último inicio de sesión. La racha se ha reiniciado a 1."
        else:
            # Primer inicio de sesión
            nueva_racha = 1
            mensaje_racha = "¡Bienvenido a tu primer inicio de sesión! Tu racha inicia en 1 día."

     
        nueva_racha_maxima = max(racha_maxima, nueva_racha)

    
        update_data = {
            "racha_actual": nueva_racha,
            "racha_maxima": nueva_racha_maxima,
            "ultima_fecha_login": hoy.strftime("%Y-%m-%d")
        }
        
        supabase.table('usuarios').update(update_data).eq('nombre', nombre).execute()
        
        return jsonify({
            "mensaje": "Login exitoso",
            "detalle_racha": mensaje_racha,
            "usuario": nombre,
            "racha_actual": nueva_racha,
            "racha_maxima": nueva_racha_maxima,
            "ultima_fecha_login": hoy.strftime("%Y-%m-%d")
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
