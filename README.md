# Portafoglio Mobile

Dashboard statica pensata per GitHub Pages.

## Come funziona

Il sito pubblicato legge solo:

```text
encrypted_snapshot.json / encrypted_snapshot.js
```

I dati sono cifrati localmente con il codice scelto. Il file `portfolio_snapshot.json` e solo un intermedio locale e non va pubblicato.

Lo snapshot viene generato in locale dagli script:

```powershell
python .\tools\export_mobile_snapshot.py
node .\tools\encrypt_snapshot.mjs --code=IL_TUO_CODICE
```

Lo snapshot cifrato e aggregato: non contiene workbook Excel, movimenti, screenshot, log o lista completa dei titoli.

## Aggiornamento dati

Dopo aver aggiornato `portafoglio.xlsx`, esegui:

```powershell
.\aggiorna_dashboard.bat
```

Il batch rigenera lo snapshot, chiede il codice, cifra i dati e poi prepara la pubblicazione Git.
