frankSpikes - versione standalone (senza Siril)
================================================

Cos'e'
------
frankSpikes aggiunge spike di diffrazione realistici (e regolazioni di
luce/colore) a una singola immagine astrofotografica. Questa versione
funziona da sola, senza bisogno di avere Siril aperto: apri direttamente
un file FITS o TIFF, regoli con gli slider, e salvi il risultato.

Come si usa
-----------
1. Estrai questa cartella dove preferisci (es. sul Desktop).
2. Fai doppio click su "run_frankspikes.bat".
   - Alla primissima esecuzione, se sul computer non e' installato
     Python, lo script prova a installarlo automaticamente (serve una
     connessione a Internet). Al termine ti chiedera' di rilanciare
     run_frankspikes.bat una seconda volta.
   - Le dipendenze Python necessarie (numpy, Pillow, astropy, photutils,
     tifffile) vengono installate automaticamente in un ambiente virtuale
     dentro questa stessa cartella (".venv") - non toccano altre
     installazioni Python sul computer.
3. Nella finestra di frankSpikes: File -> Apri... per caricare
   un'immagine (.fits/.fit/.fts o .tif/.tiff), regola gli slider, poi
   "Process and Save As..." per salvare il risultato.

Note
----
- Le esecuzioni successive sono molto piu' veloci: l'ambiente virtuale e
  le dipendenze restano gia' pronte nella cartella ".venv".
- Per reinstallare da zero le dipendenze, cancella semplicemente la
  cartella ".venv" e rilancia run_frankspikes.bat.
- Questa e' la prima versione distribuibile della modalita' standalone -
  la modalita' "dentro Siril" (script Python di Siril) resta il modo
  d'uso principale e piu' testato; qui il rilevamento stelle usa
  photutils al posto del findstar di Siril.
