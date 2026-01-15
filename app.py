from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
import requests # Neu: Für den Aufruf der echten Job-API
from dotenv import load_dotenv
from bot_config import SYSTEM_ANWEISUNG # Neu: Wir laden die Regeln aus der bot_config.py

# 1. SETUP: API-Keys laden
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)

# Ein einfacher Speicher für die gefundenen Jobs in dieser Sitzung
aktuelle_jobs = []

# --- DIE ECHTE API-FUNKTION ---

def jobs_suchen(begriff, ort="Deutschland"):
    """
    Ruft echte Jobs von der Agentur für Arbeit ab.
    Diese Funktion wird von der KI aufgerufen.
    """
    print(f"DEBUG: Suche echte Jobs für '{begriff}' in '{ort}'...")
    
    # API Details der Bundesagentur für Arbeit
    url = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
    headers = {"X-API-Key": "jobboerse-jobsuche"}
    params = {
        "was": begriff, 
        "wo": ort, 
        "umkreis": 20, 
        "size": 10
    }

    try:
        # Anfrage abschicken
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # Fehler werfen, falls die API nicht antwortet
        daten = response.json()

        # Ergebnisse verarbeiten
        neue_gefundene_jobs = []
        for job in daten.get('stellenangebote', []):
            # Wir bauen uns ein einfaches Format für unsere Website
            ref_nr = job.get('refnr')
            job_url = f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref_nr}" if ref_nr else "#"
            
            neue_gefundene_jobs.append({
                "titel": job.get('titel', 'Kein Titel'),
                "firma": job.get('arbeitgeber', 'Unbekannt'),
                "ort": job.get('arbeitsort', {}).get('ort', ort),
                "url": job_url
            })
        
        # Liste aktualisieren: Wir leeren die Liste vorher, damit nur die neuesten Ergebnisse angezeigt werden
        global aktuelle_jobs
        aktuelle_jobs = neue_gefundene_jobs
        
        return f"Ich habe {len(neue_gefundene_jobs)} echte Stellenanzeigen gefunden."

    except Exception as e:
        print(f"Fehler bei der API: {e}")
        return "Es gab ein Problem bei der Suche nach echten Jobs."

def liste_leeren():
    """Löscht alle Jobs aus der aktuellen Liste."""
    global aktuelle_jobs
    aktuelle_jobs = []
    return "Liste wurde geleert."

# --- KI INITIALISIERUNG ---

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    system_instruction=SYSTEM_ANWEISUNG, # Hier nutzen wir die importierte Anweisung
    tools=[jobs_suchen, liste_leeren]
)

# Chat-Session starten (Wichtig: Automatic Function Calling ist an!)
chat_session = model.start_chat(enable_automatic_function_calling=True)

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    nutzer_nachricht = request.json.get("message")
    if not nutzer_nachricht:
        return jsonify({"error": "Keine Nachricht"}), 400

    # KI schickt Nachricht und entscheidet selbst, ob sie 'jobs_suchen' aufruft
    antwort = chat_session.send_message(nutzer_nachricht)
    
    return jsonify({
        "response": antwort.text,
        "jobs": aktuelle_jobs
    })

if __name__ == '__main__':
    print("Jobscout Lite (mit echter API) läuft!")
    app.run(debug=True)
