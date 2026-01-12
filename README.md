# CEI PDF Signer

Aplicatie pentru semnarea documentelor PDF folosind Cartea de Identitate Electronica (CEI) din Romania.

## Despre

CEI PDF Signer este o aplicatie gratuita si open-source care permite semnarea digitala a documentelor PDF folosind certificatul calificat de pe Cartea de Identitate Electronica romaneasca. Aplicatia functioneaza pe macOS si foloseste biblioteca PKCS#11 de la IDEMIA.

### Caracteristici

- Interfata web moderna si intuitiva
- Semnare multipla documente PDF
- Selectare vizuala a pozitiei semnaturii pe document
- Suport pentru certificatele ECDSA de pe CEI
- Detectare automata a cititorului de carduri
- Export direct in folderul Downloads
- Configurare cale biblioteca PKCS#11 (pentru versiuni diferite de IDPlugManager)

## Cerinte

### Hardware
- Cititor de carduri smart card (USB)
- Cartea de Identitate Electronica (CEI) din Romania

### Software
- macOS 10.13 sau mai nou
- [IDPlugManager](https://www.inteligent.ro/idplugmanager/) - software-ul oficial pentru CEI (instaleaza biblioteca PKCS#11)

## Instalare

### Varianta 1: Aplicatie compilata (recomandat)

1. Descarcati ultima versiune din [Releases](../../releases)
2. Dezarhivati si mutati `CEI PDF Signer.app` in `/Applications`
3. La prima rulare, click dreapta -> Open (pentru a permite rularea)

### Varianta 2: Din sursa

```bash
# Clonati repository-ul
git clone https://github.com/USERNAME/cei-web-signer.git
cd cei-web-signer

# Rulati aplicatia (creeaza venv si instaleaza dependentele automat)
./run.sh
```

Apoi deschideti browserul la `http://localhost:5001`

### Compilare aplicatie nativa

```bash
# Compileaza aplicatia macOS
./build.sh
```

Aplicatia compilata va fi in `dist/CEI PDF Signer.app`

### Creare release pentru GitHub

```bash
# Compileaza si creeaza ZIP pentru distribuire
./build-release.sh
```

Fisierele pentru release vor fi in folderul `release/`

## Utilizare

1. **Conectati cititorul de carduri** si introduceti CEI-ul
2. **Lansati aplicatia** - va detecta automat cardul
3. **Incarcati PDF-urile** - drag & drop sau click pentru selectare
4. **Desenati zona semnaturii** - click si drag pe fiecare document
5. **Click "Sign Files"** - introduceti PIN-ul (6 cifre) si asteptati
6. **Descarcati** - fisierele semnate vor fi salvate in Downloads

### PIN-uri CEI

- **PIN Semnatura (6 cifre)**: pentru semnarea documentelor (Slot 2)
- **PIN Autentificare (4 cifre)**: pentru autentificare online (Slot 0)

### Configurare PKCS#11

Aplicatia foloseste implicit biblioteca PKCS#11 de la IDEMIA:
```
/Library/Application Support/com.idemia.idplug/lib/libidplug-pkcs11.2.7.0.dylib
```

Daca aveti o versiune diferita de IDPlugManager sau biblioteca se afla in alta locatie:
1. Click pe iconita **Settings** (rotita) din header
2. Introduceti calea catre biblioteca PKCS#11
3. Click **Save**

Setarea este salvata local si persista intre sesiuni.

## Rezolvarea problemelor

### "No smart card detected"
- Verificati ca cititorul este conectat
- Verificati ca CEI-ul este introdus corect in cititor
- Reinstalati IDPlugManager

### "PKCS11 library not found"
- Verificati ca IDPlugManager este instalat
- Deschideti Settings si verificati/actualizati calea catre biblioteca PKCS#11
- Calea implicita este pentru versiunea 2.7.0 - daca aveti alta versiune, actualizati calea

### macOS blocheaza cititorul / Aplicatia se blocheaza (hanging)

Daca macOS preia controlul asupra cititorului (apare notificare "Smart card detected") sau aplicatia se blocheaza la pornire cu ecran alb:

**Cauza:** macOS CryptoTokenKit incearca sa foloseasca cititorul simultan cu aplicatia noastra, cauzand o bucla de connect/disconnect.

**Solutie:**

```bash
# Dezactiveaza complet smart card-ul in macOS
sudo defaults write /Library/Preferences/com.apple.security.smartcard allowSmartCard -bool false
sudo defaults write /Library/Preferences/com.apple.security.smartcard UserPairing -bool false
sudo defaults write /Library/Preferences/com.apple.security.smartcard useIFDCCID -bool false

# IMPORTANT: Restartati Mac-ul pentru ca setarile sa aiba efect
```

**Dupa restart:**
- Nu ar trebui sa mai apara notificarea "Smart card detected"
- Aplicatia ar trebui sa functioneze normal

**Daca aplicatia e blocata si trebuie oprita:**
```bash
pkill -9 "CEI PDF Signer"
```

### Aplicatia nu porneste
La prima rulare pe macOS, click dreapta pe aplicatie -> Open, apoi confirmati.

## Structura proiectului

```
cei-web-signer/
├── app.py              # Server Flask + logica semnare
├── main.py             # Wrapper desktop (PyWebView)
├── templates/
│   └── index.html      # Interfata web
├── requirements.txt    # Dependente Python
├── CEIPDFSigner.spec   # Config PyInstaller
├── icon.icns           # Iconita aplicatie
├── run.sh              # Script pentru rulare locala
├── build.sh            # Script pentru compilare aplicatie
└── build-release.sh    # Script pentru creare release GitHub
```

## Tehnologii folosite

- **Python 3** - limbaj principal
- **Flask** - server web
- **PyKCS11** - acces PKCS#11
- **pyHanko** - semnare PDF
- **PyWebView** - wrapper desktop nativ
- **PDF.js** - vizualizare PDF in browser

## Securitate

- PIN-ul nu este stocat niciodata
- Comunicatia este doar locala (localhost)
- Cheia privata nu paraseste niciodata cardul smart
- Codul este open-source pentru audit

## Licenta

MIT License - vezi [LICENSE](LICENSE)

## Contributii

Contributiile sunt binevenite! Deschideti un Issue sau Pull Request.

## Disclaimer

Aceasta aplicatie este oferita "as is", fara garantii. Autorul nu este afiliat cu statul roman sau IDEMIA. Folositi pe propria raspundere.

---

Facut cu drag pentru comunitatea romaneasca.
