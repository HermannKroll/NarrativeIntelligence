# Narrative Service Deployment

## Architektur

Die Django-Anwendung wird mittels des Servers Gunicorn auf dem `localhost` gestartet. Nginx agiert als
Reverse-Proxy-Server; er liefert die statischen Dateien aus und leitet die Requests an Gunicorn weiter.

Der Gunicorn-Server wird in einem Screen gestartet. Nginx läuft als Dienst.

### Django

Django bietet die WSGI-Schnittstelle an, welche von Gunicorn verwendet wird. Wichtige Pfade im
Django-Projekt `frontend`:

- HTML-Seite: `ui/templates/ui/search.html`
- JavaScript: `ui/static/js/search.js`
- Logik und LibraryGraph-Initialisierung: `ui/views.py`

Der Index der MeSHDB befindet sich im `data`-Verzeichnis, sofern er erstellt wurde.

### Gunicorn

Gunicorn wird mit dem Parameter ``--timeout 90`` gestartet, um den Timeout auf 90 Sekunden zu setzen, da die Berechnung
bis zu einer Minute dauern kann.

## Deployment

1. Pakete installieren
   ``git virtualenv nginx screen``
2. Repository klonen
3. Virtuelle Umgebung erstellen und Abhängigkeiten installieren
4. Umgebungsvariablen setzen
    1. ``export DJANGO_SETTINGS_MODULE="frontend.settings.prod"``
    2. ``export PYTHONPATH="~/NarrativeIntelligence"``
5. Statische Dateien anlegen
    1. Verzeichnis ``/var/www/static`` erstellen
    2. Rechte und Modus anpassen (`chgrp -R www-data /var && chmod -R 775 /var/www`
    3. Staticfiles kopieren: `python manage.py collectstatic`
4. Index aufbauen
    5. `python tools.py --build-index`
7. Server im `screen` starten: `gunicorn -b 127.0.0.1:8080 --timeout 90 frontend.wsgi`
8. Nginx-Konfigurationsdatei nach `/etc/nginx/nginx.conf` kopieren
9. Nginx neu starten: `sudo service nginx restart`


## Server neu starten

Nach einem Server-Neustart muss der Gunicorn Server manuell gestartet werden.

	screen
	source ~/NarrativeIntelligence/venv/bin/activate
	export DJANGO_SETTINGS_MODULE="frontend.settings.prod"
	export PYTHONPATH="/home/kroll/NarrativeIntelligence/src:/home/kroll/NarrativeIntelligence/lib/NarrativeAnnotation/src"
	cd ~/NarrativeIntelligence/src/narraint/frontend
	gunicorn -b 127.0.0.1:8080 --timeout 90 frontend.wsgi

## Projekt aktualisieren

Das Projekt kann mit `git pull` aktualisiert werden. Damit die Änderungen wirksam werden, muss der Webserver
neugestartet werden. Falls die Deskriptoren aktualisiert wurden, muss der Index neu aufgebaut werden. Mehr dazu unter: *
Index aufbauen*.

	  # Projekt aktualisieren
	  cd ~/NarrativeIntelligence
	  git pull

	 # Dateien kopieren (falls html oder js verändert)
	  cd frontend/
	  sudo chmod -R 777 /var/www
	  python manage.py collectstatic
	  sudo chmod -R 775 /var/www	  

	  # Server neustarten
	  screen -r
	  CTRL + C
	  gunicorn -b 127.0.0.1:8080 --timeout 90 frontend.wsgi


# PyCharm Configuration
Create a new PyCharm Runtime Configuration. 

Select 'Django Server'.

Make sure that your local Python interpreter is used. Not the server SSH interpreter!

Set environment variable to:
```
PYTHONUNBUFFERED=1;DJANGO_SETTINGS_MODULE=frontend.settings.dev
```

Go to PyCharm -> Settings -> Languages & Frameworks -> Django

Use the following settings
```
Enable Django Support: true
Django Project root: NarrativeIntelligence\src\narraint\frontend
Settings: frontend\settings\dev.py
```
