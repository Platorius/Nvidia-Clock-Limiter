# Nvidia-Clock-Limiter
Deutsch: Dieses Tool soll den Stromverbrauch von Nvidia Grafikkarten in Niedriglast-Szenarien bzw. Idle senken, vor allem für Grafikkarten ab Blackwell (bei älteren geht auch der Multi Display PowerSaver im nvidia Insepctor). Funktioniert (bei mir) mit MSI Afterburner Undervolting und Overclocking (Stand 18.12.2025 Version 4.6.6 Beta7)

Hinweis: Ich leiste hier keinen Support. Bei Fehler oder Verbesserungsvorschlägen darf gerne einer gemacht werden. Ob ich den umsetze, ist damit nicht gesagt. Ich leiste aber auf jeden Fall keinen Support. Ich stelle es hier nur bereit, falls andere es auch brauchen können.

Anwendung:
1. Unter "Erlaubte Taktraten" sollten die erlaubten Taktraten abgefragt werden. Für jede VRAM-Taktrate wird dann die erlaubte GPU-Taktrate aufgelistet. Diese Kombinationen dürfen dann genutzt werden
2. Mit den Taktraten aus Schritt 1 kann man dann verschiedene Taktprofile erstellen (1, 2, 3 bzw. grün, gelb, orange).
3. Unten hat man 3 Listen. Man kann zu jeder Liste Anwendungen (aus laufenden Prozessen oder .exe Dateien) hinzufügen. Ist eine der Anwendungen am laufen, wird das Taktoprofil ausgewählt. Es hat immer das Profil Vorrang mit dem höchsten Takt. Die Liste mit dem roten Titel ist die Liste, um alle Taktbeschränkungen aufzuheben (Unlock)

Die Option "Anhand GPU- und VID-Auslastung steuern":
Diese Option erlaubt es, dass die Profile anhand der GPU bzw. VID-Auslastung (Video Engine für Video schauen) gesteuert werden. Die Hierarchie/Priorität ist hier: 1: Unlock-Liste, 2: GPU-Auslastung, 3: das 3. Limit, 4: VID-Auslastung, 5: das 2. Limit, 6: Das 1. Limit (Standart-limit)

GPU-Auslastung definieren:
--> Sinkt die Last, fällt man niemals direkt in das Standart-Limit-Profil (grün), sondern immer in das nächste kleinere Profil ( Unlock -> 3. Limit -> 2. Limit -> 1. Limit).
--> Unter "aktivieren", definiert man, wann dieses Profil aktiviert wird. Unter "deaktivieren", definiert man, wann das Profil deaktiviert wird (und automatisch in das nächst kleinere Gewechselt wird).
--> Wählt man unter "aktivieren" bei allen Listen die gleiche Last bzw. bei "Unlock" die niedrigste, wird es immer zuerst in das Unlock-Profil gehen bei Auslastung und dann Schrittweise zu Profil 3, 2, 1 zurücktakten, wenn der Takt unter die Schwelle sinkt.
1. Unter der Liste mit dem roten Titel definiert man, ab welcher GPU-Auslastung die Limits komplett aufgehoben werden (Unlock). Wenn eine Anwendung in der Liste mit dem roten Titel ist (unlock), ist die GPU-Auslastung egal. Die Limits werden dann trotzdem aufgehoben. Die VID-Auslastung ist hier sowieso immer egal. 
2. Unter der 3. Liste (Orange) definiert man, bei welcher GPU-Last oder VID-Auslastung die GPU in dieses Profil wechselt. Entweder GPU- oder VID-Auslastung muss den Schwellenwert Überschreiten. Bei Deaktivieren müssen hier beide (GPU- und VID- Auslastung) unter den Schwellenwert sinken, damit in das nächst kleinere Profil gewechselt wird.
3. Unter der 2. Liste (Gelb) ist es das gleiche Prinzip, wie in der 3. Liste (Orange). Das 3. Profil hat natürlich Vorrang vor dem 2. Profil. Sinkt GPU- UND VID-Auslastung unter den Schwellenwert, wechselt es in das nächst kleinere Profil (Also Standartprofil).
4. Die Zeit (ms) ist die Zeit, wie lange der Grenzwert aktiv sein muss (eine Art Hysterese).

Andere Optionen:
Sind selbsterklärend (Übersetzung nutzen). Alle aktivieren, ist empfohlen.
--> .exe Datei nicht verschieben, nachdem man den Autostart aktiviert hat.

Tray-Symbol: Die Farben entsprechen den Farben der Profile und Blau heisst, dass gar kein Profil aktiv ist.
