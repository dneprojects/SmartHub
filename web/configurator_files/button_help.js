var button_help_dict = {};
button_help_dict["Updates"] = "Firmware von Router oder Modulen updaten";
button_help_dict["Systemkonfiguration"] = "Systemeinstellungen der Anlage sichern oder wiederherstellen";
button_help_dict["Datei auswählen"] = "Dialog zur Auswahl der Datei öffnen";
button_help_dict["schließen"] = "Aktuelles Fenster schließen";
button_help_dict["Upload"] = "Ausgewählte Datei in den Configurator laden";
button_help_dict["Start"] = "Einlernen aktiv für die eingestellte Zeit (LED orange)";
button_help_dict["Download"] = "Einstellungen unter dem angegebenen Namen als Download sichern";
button_help_dict["Einstellungen"] = "Einstellungen für aktuelles Modul ansehen oder anpassen";
button_help_dict["Automatisierungen"] = "Automatisierungen im Habitron-System ansehen oder anpassen";
button_help_dict["Konfigurationsdatei"] = "Router- oder Moduleinstellungen sichern oder wiederherstellen";
button_help_dict["zurück"] = "Zur vorherigen Einstellungsseite wechseln";
button_help_dict["weiter"] = "Zur nächsten Einstellungsseite wechseln";
button_help_dict["Weiter"] = "Externe Automatisierung anlegen";
button_help_dict["Abbruch"] = "Geänderte Einstellungen verwerfen";
button_help_dict["Speichern"] = "Geänderte Einstellungen im Router oder Modul speichern";
button_help_dict["OK"] = "Einstellungen übernehmen";
button_help_dict["Module entfernen"] = "Ausgewählte Module aus der Liste des Routers entfernen";
button_help_dict["Modul testen"] = "Testseite für Modul Ein- und Ausgänge";
button_help_dict["Neue Abfrage"] = "Status der Ein- und Ausgänge erneut abfragen";
button_help_dict["Modultest beenden"] = "Testseite schließen";
button_help_dict["anlegen"] = "Neuen Eintrag unter der gewählten Nummer anlegen";
button_help_dict["entfernen"] = "Ausgewählten Eintrag löschen";
button_help_dict["Neu"] = "Neue Regel auf Basis der ausgewählten Automatisierungsregel anlegen";
button_help_dict["Ändern"] = "Ausgewählte Automatisierungsregel ändern";
button_help_dict["Löschen"] = "Ausgewählte Automatisierungsregel löschen";
button_help_dict["Übernehmen"] = "Alle Änderungen von Modulen, Adressen und Kanälen im Configurator intern ablegen";
button_help_dict["Übertragen"] = "Alle Änderungen von Modulen, Adressen und Kanälen ins System übertragen";
button_help_dict["Protokoll"] = "Zugangsprotokoll anzeigen und verwalten";
button_help_dict["Protokoll löschen"] = "Zugangsprotokoll im Smart Key löschen";
button_help_dict["Protokoll sichern"] = "Protokoll als Download speichern";
button_help_dict["Beenden"] = "Zurück zur Modulübersicht";
button_help_dict["Exit"] = "Beenden des Programms";

var button_acceskey_dict = {};
button_acceskey_dict["Neu"] = "n";
button_acceskey_dict["Ändern"] = "ä";
button_acceskey_dict["Löschen"] = "l";
button_acceskey_dict["schließen"] = "s";
button_acceskey_dict["zurück"] = "z";
button_acceskey_dict["weiter"] = "w";
button_acceskey_dict["Weiter"] = "w";
button_acceskey_dict["Abbruch"] = "a";
button_acceskey_dict["anlegen"] = "a";
button_acceskey_dict["Beenden"] = "b";

const buttons = document.getElementsByTagName("button")
for (let i = 0; i < buttons.length; i++) {
    if (button_help_dict[buttons[i].innerHTML.trim()]) {
        buttons[i].title = button_help_dict[buttons[i].innerHTML.trim()];
    }
    if (button_acceskey_dict[buttons[i].innerHTML.trim()]) {
        buttons[i].accessKey = button_acceskey_dict[buttons[i].innerHTML.trim()];
    }
}
