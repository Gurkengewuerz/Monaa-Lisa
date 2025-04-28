# Beitrag-Regeln für dieses Projekt

Willkommen! Damit unsere Zusammenarbeit reibungslos klappt, beachte bitte folgende Regeln:

## Branch-Strategie

- **Feature-Branches**: Erstelle für jede neue Funktion oder Bugfix einen neuen Branch. Namensschema:
  - `feature/<name>` für neue Features
  - `bugfix/<name>` für Fehlerbehebungen
  - `hotfix/<name>` für dringende Korrekturen
- **Entwicklungszweig**: Alle Pull Requests (PRs) müssen gegen `dev` gestellt werden, niemals direkt gegen `main`.
- **Main-Branch**: Direkte Commits auf `main` sind nicht erlaubt. `main` enthält nur getestete und freigegebene Versionen.

## Pull Requests (PR)

- PRs müssen mindestens **einen Review** erhalten.
- Alle **automatischen Tests** müssen bestanden sein.
- Halte PRs klein und thematisch fokussiert.
- Verfasse eine klare Beschreibung, was geändert wurde und warum.

## Commits

- Schreibe **aussagekräftige Commit-Nachrichten** nach folgendem Schema:
  - `feat: neue Login-Funktion hinzugefügt`
  - `fix: Fehler bei Passwortvalidierung behoben`
- Mehrere Änderungen? Lieber mehrere kleine Commits statt einen großen.

## Tests

- Vor einem PR sicherstellen, dass alle lokalen Tests erfolgreich laufen.
- Ein PR wird nur gemerged, wenn alle **CI-Tests** in GitHub Actions erfolgreich sind.

## Code-Dokumentation

- **Wichtige Stellen im Code** (z.B. komplexe Logik, Sonderfälle) müssen kommentiert werden.
- **Jede öffentliche Funktion (public)** muss eine kurze Beschreibung am Anfang haben:
  - Welche Parameter erwartet werden (inklusive Typ und Bedeutung).
  - Was zurückgegeben wird.
- Beispiel für Dokumentation:
  ```ts
  /**
   * Berechnet die Summe zweier Zahlen.
   *
   * @param {number} a - Erste Zahl
   * @param {number} b - Zweite Zahl
   * @returns {number} - Die Summe von a und b
   */
  function add(a, b) {
    return a + b;
  }
  ``` 

  ## Codequalitöt
  - Beachte vereinbarte Standards
  - Reviews umsetzen wenn nötig
 
  ## Testing
  - **Jede Methode** (öffentlich und privat), die eine wesentliche Funktionalität bietet, sollte **durch Unit-Tests abgedeckt** werden. Ausnahmen bilden hier Getter und Setter, wenn diese nur ein Attribut zurückgeben.
