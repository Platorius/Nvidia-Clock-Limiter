# Nvidia-Clock-Limiter

(Englisch Below)

## Deutsch

Dieses Tool soll den Stromverbrauch von Nvidia Grafikkarten in Niedriglast-Szenarien bzw. Idle senken, vor allem für Grafikkarten ab Blackwell (bei älteren geht auch der Multi Display PowerSaver im Nvidia Inspector).

Funktioniert (bei mir) mit MSI Afterburner Undervolting und Overclocking  
(Stand 18.12.2025 – Version 4.6.6 Beta 7).

### Wichtiger Hinweis

**Ich leiste hier keinen Support.**  
Bei Fehler oder Verbesserungsvorschlägen darf gerne einer gemacht werden. Ob ich den umsetze, ist damit nicht gesagt.  
Ich leiste aber auf jeden Fall keinen Support. Ich stelle es hier nur bereit, falls andere es auch brauchen können.

### Anwendung

#### 1. Erlaubte Taktraten abfragen
Unter **"Erlaubte Taktraten"** sollten die erlaubten Taktraten abgefragt werden.  
Für jede VRAM-Taktrate wird dann die erlaubte GPU-Taktrate aufgelistet. Diese Kombinationen dürfen dann genutzt werden.

#### 2. Taktprofile erstellen
Mit den Taktraten aus Schritt 1 kann man verschiedene Taktprofile erstellen:
- Profil 1 (grün – niedrigste Taktraten / Standard-Limit)
- Profil 2 (gelb)
- Profil 3 (orange – höchste eingeschränkte Taktraten)
- Unlock-Profil (Rot = keine Takteinschränkung)

#### 3. Anwendungsbasierte Steuerung
Unten hat man 3 Listen:
- Man kann zu jeder Liste Anwendungen (aus laufenden Prozessen oder .exe-Dateien) hinzufügen.
- Ist eine der Anwendungen am Laufen, wird das entsprechende Takprofil ausgewählt.
- Es hat immer das höchste Profil Vorrang  (Unlock -> 3. Limit -> 2. Limit -> 1. Limit - Standart)
- Die Liste mit dem **roten Titel** ist die **Unlock**-Liste – sie hebt alle Taktbeschränkungen auf.

#### Option „Anhand GPU- und VID-Auslastung steuern“ (optional)
Diese Option erlaubt es, dass die Profile anhand der GPU- bzw. VID-Auslastung (Video Engine für Videos schauen) gesteuert werden.

**Priorität/Hierarchie:**
1. Unlock-Liste (roter Titel)
2. GPU-Auslastung
3. Profil 3 (orange)
4. VID-Auslastung
5. Profil 2 (gelb)
6. Profil 1 (grün – Standard)

**So funktioniert das Heruntertakten:**  
Sinkt die Last, fällt man **niemals direkt** in das Standard-Profil (grün), sondern immer stufenweise:  
Unlock → Profil 3 → Profil 2 → Profil 1.

**Schwellwerte konfigurieren:**
- **Aktivieren**: Wann das Profil aktiviert wird (Schwelle überschritten).
- **Deaktivieren**: Wann das Profil deaktiviert wird und automatisch ins nächstkleinere Profil gewechselt wird.

**Tipp:** Wählt man bei allen Listen denselben Aktivierungswert (bzw. bei Unlock den niedrigsten), geht es bei Last zuerst ins Unlock-Profil und taktet dann stufenweise zurück (3 → 2 → 1), sobald die Auslastung unter die Schwelle sinkt.

#### Detaillierte Einstellungen pro Liste
1. **Roter Titel (Unlock-Liste)**  
   Definiert, ab welcher GPU-Auslastung die Limits komplett aufgehoben werden.  
   Ist eine Anwendung in dieser Liste, ist die Auslastung egal – Limits werden trotzdem aufgehoben.  
   VID-Auslastung ist hier immer irrelevant.

2. **Orange Liste (Profil 3)**  
   Aktiviert, wenn **entweder** GPU- **oder** VID-Auslastung die Schwelle überschreitet.  
   Deaktiviert erst, wenn **beide** unter die Schwelle sinken.

3. **Gelbe Liste (Profil 2)**  
   Gleiches Prinzip wie bei orange. Profil 3 hat natürlich Vorrang vor Profil 2.

4. **Zeit (ms) – Hysterese**  
   Der Grenzwert muss so lange durchgehend erfüllt sein, bevor ein Profilwechsel erfolgt (verhindert Flackern).

#### Andere Optionen
Sind größtenteils selbsterklärend (Übersetzung im Tool nutzen). --> "Warnung bei Teufelskreilsauf (Diagnose)" ist ein Feature, das prüft, ob ständig zwischen Profilen hin- und her gewechelst wird. Das kann passieren, wenn man die "aktivieren" und "deaktivieren"-Grenzwerte so gesetzt hat, dass ständig hin und her gesprungen wird. Aktiviert man das Feature, wird einem eine Meldung ausgegeben. Die nächste Meldung kommt (frühestens) nach 60s wieder, wenn man auf "ok" gedrückt hat im Pop-Up.  
--> Ich empfehle bis auf die Teufeskreislauf-Option alle zu aktivieren und beim testen von Grenzwerten auch dei Teufelskreislaufoption zu aktivieren (oder eben manuell nachzuschauen). 

**Wichtig:** Die `.exe`-Datei nach Aktivierung des Autostarts nicht verschieben oder umbenennen.

#### Tray-Symbol
Die Farbe entspricht dem aktiven Profil:  
- Grün, Gelb, Orange, Rot → entsprechendes Profil aktiv  
- **Blau** → gar kein Profil aktiv (volle Taktraten erlaubt)

---

## Englisch with Translator:

This tool reduces the power consumption of NVIDIA graphics cards in low-load or idle scenarios, especially for cards from the Blackwell generation onwards.  
(For older cards, the Multi-Display Power Saver in NVIDIA Inspector also works.)

It is compatible (tested by me) with MSI Afterburner undervolting and overclocking  
(as of 18 December 2025 – MSI Afterburner version 4.6.6 Beta 7).

## Important Note

**I do not provide any support for this tool.**  
You are welcome to report bugs or suggest improvements, but there is no guarantee that I will implement them.  
I am simply making this available in case others find it useful.

## Usage Instructions

### 1. Query Allowed Clock Rates
Under the section **"Allowed Clock Rates"**, query the permitted clock combinations.  
The tool will list the allowed GPU clock rate for each VRAM clock rate. Only these combinations may be used.

### 2. Create Clock Profiles
Using the clock rates from step 1, create up to three clock profiles:
- Profile 1 (green – lowest clocks / default limit)
- Profile 2 (yellow)
- Profile 3 (orange – highest restricted clocks)
- Unlock-profile (red = no clock restrictions)

### 3. Application-Based Control
There are three lists at the bottom of the window:
- Applications (selected from running processes or .exe files) can be added to each list.
- If an application from a list is running, the corresponding clock profile is applied.
- The highest profile always takes priority (so: Unlock -> 3. Limit -> 2. Limit -> 1. Limit (Standard))
- The list with the **red title** is the **Unlock** list – it removes all clock restrictions.

### Control Based on GPU and VID Utilisation (Optional)

This option allows profiles to be switched automatically based on GPU utilisation and VID utilisation (Video Engine – e.g., for video playback).

**Priority hierarchy:**
1. Unlock list (red title)
2. GPU utilisation thresholds
3. Profile 3 (orange)
4. VID utilisation thresholds
5. Profile 2 (yellow)
6. Profile 1 (green – default)

#### How Downclocking Works
When load decreases, the tool **never jumps directly** to the default profile (green). Instead, it steps down gradually:  
Unlock → Profile 3 → Profile 2 → Profile 1.

#### Threshold Configuration
- **Activate**: Defines when the profile becomes active (threshold exceeded).
- **Deactivate**: Defines when the profile is deactivated and the tool switches to the next lower profile.

**Tip:** Set the same activation threshold for all profiles (or the lowest for Unlock) to achieve smooth stepping: full unlock under load, then gradual downclocking as utilisation drops.

#### Detailed Settings per List

1. **Red title (Unlock list)**  
   Defines the GPU utilisation threshold above which all limits are removed.  
   If an application is in this list, utilisation thresholds are ignored – limits are removed regardless.  
   VID utilisation is always ignored here.

2. **Orange list (Profile 3)**  
   The profile activates when **either** GPU **or** VID utilisation exceeds the threshold.  
   It deactivates only when **both** fall below the threshold.

3. **Yellow list (Profile 2)**  
   Same logic as the orange list. Profile 3 always takes priority over Profile 2.

4. **Hysteresis time (ms)**  
   The threshold must be continuously met for this duration before a profile switch occurs (prevents rapid flickering).

### Other Options
Mostly self-explanatory (use the translation tool). --> “Warn on rapid cycling (diagnosis)” is a feature that checks whether you are constantly switching back and forth between profiles. This can happen if you have set the "activate" and "deactivate" thresholds in such a way that you are constantly jumping back and forth. If you activate the feature, a message will be displayed. The next message will appear (at the earliest) after 60 seconds if you have clicked "OK" in the pop-up.  
--> I recommend activating all options except for the "warn on rapid cycling" option. On the other hand I recommend activating the "Warn on rapid cycling" option when testing thresholds (or checking manually). 

**Important:** Do not move or rename the `.exe` file after enabling autostart.

### Tray Icon
The icon colour matches the active profile:  
- Green, Yellow, Orange, Red → corresponding profile active  
- **Blue** → no profile active (full clocks allowed)
