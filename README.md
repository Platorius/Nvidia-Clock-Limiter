# Nvidia-Clock-Limiter

(Englisch Below)

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

Englisch with Translator:

This tool is designed to reduce the power consumption of NVIDIA graphics cards in low-load scenarios or when idle, particularly for graphics cards from the Blackwell generation onwards (for older cards, the Multi-Display Power Saver in NVIDIA Inspector also works).
It works (for me) with MSI Afterburner undervolting and overclocking (as of 18 December 2025, version 4.6.6 Beta 7).
Note: I am not providing any support here. Feel free to submit bug reports or suggestions for improvements. Whether I implement them is not guaranteed. I definitely will not provide support. I am simply making it available in case others might find it useful.
Usage:

Under "Allowed Clock Rates", the permitted clock rates should be queried. For each VRAM clock rate, the allowed GPU clock rate will then be listed. These combinations may then be used.
Using the clock rates from step 1, various clock profiles can be created (1, 2, 3 – i.e., green, yellow, orange).
At the bottom, there are three lists. Applications (from running processes or .exe files) can be added to each list. If one of the applications is running, the corresponding clock profile will be selected. The profile with the highest clocks always takes priority. The list with the red title is the one used to remove all clock restrictions (Unlock).

The option "Control based on GPU and VID utilisation": This option allows the profiles to be controlled based on GPU or VID utilisation (Video Engine for watching videos). The hierarchy/priority here is: 1: Unlock list, 2: GPU utilisation, 3: the 3rd limit, 4: VID utilisation, 5: the 2nd limit, 6: the 1st limit (default limit).
Defining GPU utilisation:

When the load decreases, it never drops directly to the default limit profile (green), but always to the next lower profile (Unlock → 3rd limit → 2nd limit → 1st limit).
Under "Activate", you define when this profile is activated. Under "Deactivate", you define when the profile is deactivated (and it automatically switches to the next lower one).
If you set the same load threshold for "Activate" across all lists, or the lowest for "Unlock", it will first switch to the Unlock profile under load, then step down to profile 3, 2, 1 as the clocks fall below the threshold.


Under the list with the red title, you define from which GPU utilisation the limits are completely removed (Unlock). If an application is in the list with the red title (Unlock), GPU utilisation is irrelevant – the limits will still be removed. VID utilisation is always irrelevant here.
Under the 3rd list (orange), you define at which GPU load or VID utilisation the GPU switches to this profile. Either GPU or VID utilisation must exceed the threshold. For deactivation, both (GPU and VID utilisation) must fall below the threshold before switching to the next lower profile.
Under the 2nd list (yellow), the same principle applies as for the 3rd list (orange). The 3rd profile naturally takes priority over the 2nd. When GPU and VID utilisation both fall below the threshold, it switches to the next lower profile (i.e., the default profile).
The time (ms) is the duration for which the threshold must be active (a form of hysteresis).

Other options: These are self-explanatory (use the translation). Enabling all is recommended. → Do not move the .exe file after enabling autostart.
Tray icon: The colours correspond to the profile colours, and blue means no profile is active at all.
