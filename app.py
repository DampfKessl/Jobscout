from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
import requests
from dotenv import load_dotenv
from bot_config import SYSTEM_ANWEISUNG

# API-Keys und Konfiguration
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

JOB_API_KEY = "jobboerse-jobsuche"

app = Flask(__name__)

# Ein einfacher globaler Speicher für die Jobs
aktuelle_jobs = []

def jobs_suchen(begriff, ort="Deutschland", anzahl=10):
    """
    Diese Funktion wird von der KI aufgerufen, wenn sie Jobs suchen möchte.
    Sie ruft echte Daten von der Bundesagentur für Arbeit ab.
    """
    print(f"DEBUG: Suche Jobs für '{begriff}' in '{ort}'...")
    
    url = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
    headers = {"X-API-Key": JOB_API_KEY}
    
    # Sicherstellen, dass anzahl eine Ganzzahl ist (KI schickt manchmal 20.0 als Text)
    anzahl_int = int(float(anzahl)) if anzahl else 10
    
    params = {
        "was": begriff, 
        "wo": ort, 
        "umkreis": 20, 
        "size": anzahl_int
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # Stoppt hier, falls die API einen Fehler meldet
        daten = response.json()

        # Ergebnisse verarbeiten
        neue_gefundene_jobs = []
        for job in daten.get('stellenangebote', []):
            ref_nr = job.get('refnr')
            job_url = f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref_nr}" if ref_nr else "#"
            
            neue_gefundene_jobs.append({
                "titel": job.get('titel', 'Kein Titel'),
                "firma": job.get('arbeitgeber', 'Unbekannt'),
                "ort": job.get('arbeitsort', {}).get('ort', ort),
                "url": job_url
            })
        
        # Den globalen Speicher aktualisieren
        global aktuelle_jobs
        aktuelle_jobs = neue_gefundene_jobs
        
        return f"Ich habe {len(neue_gefundene_jobs)} echte Stellenanzeigen gefunden."

    except Exception as e:
        print(f"Fehler bei der API: {e}")
        return "Es gab ein Problem bei der Suche nach echten Jobs. Bitte versuche es später noch einmal."

def liste_leeren():
    """Löscht alle Jobs aus der globalen Liste."""
    global aktuelle_jobs
    aktuelle_jobs = []
    return "Liste wurde geleert."

# KI-Initialisierung

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=SYSTEM_ANWEISUNG,
    tools=[jobs_suchen, liste_leeren]
)

# Chat-Sitzung
chat_session = model.start_chat(enable_automatic_function_calling=True)

# Routen

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    """Anfrage-Endpunkt für den Chatbot."""
    nutzer_nachricht = request.json.get("message")
    if not nutzer_nachricht:
        return jsonify({"error": "Keine Nachricht"}), 400

    # Die KI verarbeitet die Nachricht und entscheidet selbstständig über Tool-Aufrufe
    antwort = chat_session.send_message(nutzer_nachricht)
    
    return jsonify({
        "response": antwort.text,
        "jobs": aktuelle_jobs
    })

if __name__ == '__main__':
    print("Jobscout ist online!")
    app.run(debug=True)
