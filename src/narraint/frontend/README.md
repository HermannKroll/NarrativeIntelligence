# Narrative Intelligence WebService Deployment

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
    2. ``export PYTHONPATH="~/PubMedSnorkel"``
5. Statische Dateien anlegen
    1. Verzeichnis ``/var/www/static`` erstellen
    2. Rechte und Modus anpassen (`chgrp -R www-data /var && chmod -R 775 /var/www`
    3. Staticfiles kopieren: `python manage.py collectstatic`
4. Index aufbauen
    5. `python tools.py --build-index`
7. Server im `screen` starten: `gunicorn -b 127.0.0.1:8080 --timeout 90 frontend.wsgi`
8. Nginx-Konfigurationsdatei nach `/etc/nginx/nginx.conf` kopieren
9. Nginx neu starten: `sudo service nginx restart`

## Index aufbauen

Da das Erstellen des Index' zur Laufzeit zu lange dauert, wird dieser vorher erstellt und serialisiert. Der
serialisierte Index wird dann beim Serverstart in den Speicher geladen.

Der Index muss neu aufgebaut werden, wenn sich die `Descriptor`-Klasse aus dem `mesh`-Paket ändert oder die
Deskriptor-Datei selbst. Die Pfade zum Index stehen in `frontend.settings.base`.

# Hierzu muss man sich in der Conda Environment befinden

		cd ~/PubMedSnorkel/utils
		python tools.py --build-index

## Server neu starten

Nach einem Server-Neustart muss der Gunicorn Server manuell gestartet werden.

	screen
	source ~/PubMedSnorkel/venv/bin/activate
	export DJANGO_SETTINGS_MODULE="frontend.settings.prod"
	export PYTHONPATH="/home/kroll/PubMedSnorkel"
	cd ~/PubMedSnorkel/frontend
	gunicorn -b 127.0.0.1:8080 --timeout 90 frontend.wsgi

## Projekt aktualisieren

Das Projekt kann mit `git pull` aktualisiert werden. Damit die Änderungen wirksam werden, muss der Webserver
neugestartet werden. Falls die Deskriptoren aktualisiert wurden, muss der Index neu aufgebaut werden. Mehr dazu unter: *
Index aufbauen*.

	  # Projekt aktualisieren
	  cd ~/PubMedSnorkel
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
