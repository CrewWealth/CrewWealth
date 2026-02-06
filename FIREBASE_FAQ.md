# Firebase Account Management - FAQ

## Veelgestelde Vragen (Dutch/Nederlands)

### V: Nu dat de app live is op render.com, moet ik een nieuw account aanmaken om te testen?

**A: Ja, absoluut!** Dit is de aanbevolen aanpak:

1. **Maak een test account aan** op je live render.com URL
2. Gebruik een test email zoals: `jouwmail+rendertest@gmail.com`
3. Test de volledige registratie flow
4. Controleer of alle features werken
5. Test inloggen en uitloggen

Dit bevestigt dat:
- Firebase Authentication correct werkt in productie
- De render.com deployment goed geconfigureerd is
- Gebruikers zich kunnen registreren op je live site
- Data correct wordt opgeslagen in Firestore

### V: Moet ik daarna de oude accounts verwijderen in Firebase?

**A: Dat hangt af van je situatie:**

#### Verwijder oude accounts ALS:
- Het test accounts zijn die je niet meer nodig hebt
- Je wilt een schone start voor productie
- De accounts test data bevatten die niet meer relevant is
- Je Firebase project wilt opschonen voor echte gebruikers

#### Behoud oude accounts ALS:
- Je ze nodig hebt voor toekomstige tests
- Ze verschillende test scenario's vertegenwoordigen
- Je wilt vergelijken tussen development en productie
- De Firebase free tier geen problemen geeft (wat waarschijnlijk het geval is)

### V: Hoe verwijder ik accounts in Firebase?

**Methode 1: Via Firebase Console**
1. Ga naar https://console.firebase.google.com
2. Selecteer je project: `crewwealth-cbe02`
3. Klik op "Authentication" in het menu
4. Ga naar de "Users" tab
5. Zoek het account dat je wilt verwijderen
6. Klik op de drie puntjes (⋮) naast het account
7. Selecteer "Delete account"
8. Bevestig de verwijdering

**Methode 2: Voor meerdere accounts (Firebase Admin)**
Als je meerdere accounts tegelijk wilt verwijderen, kan je Firebase Admin SDK gebruiken (zie TESTING_GUIDE.md voor code voorbeelden).

### V: Is het veilig om mijn Firebase API key in de code te hebben?

**A: Ja, dit is normaal en veilig!**
- Firebase API keys zijn bedoeld om publiek te zijn
- Ze worden in client-side code gebruikt
- Beveiliging wordt geregeld door Firebase Security Rules, niet door de API key
- Zolg ervoor dat je Firestore Security Rules goed ingesteld zijn

### V: Hoeveel test accounts kan ik aanmaken?

**A: Op de gratis Firebase tier:**
- Email/password authenticatie heeft vrijwel geen limiet
- Je kunt zoveel accounts aanmaken als nodig voor testing
- Phone authentication heeft wel limieten (10,000/maand)

**Aanbeveling**: Houd het schoon en overzichtelijk:
- 1-2 test accounts voor jou zelf
- Verwijder oude/ongebruikte test accounts
- Gebruik meaningful namen zoals "Test Account - Production" voor duidelijkheid

### V: Wat moet ik testen na deployment?

**Complete test checklist:**
- [ ] Account registratie op live site
- [ ] Email validatie
- [ ] Wachtwoord sterkte controle
- [ ] Inloggen met nieuwe account
- [ ] Dashboard toegang
- [ ] Alle pagina's (Budget, Goals, Reports, Settings)
- [ ] Data opslaan (test met income data)
- [ ] Uitloggen
- [ ] Weer inloggen
- [ ] "Remember Me" functionaliteit

## Frequently Asked Questions (English)

### Q: Now that it's live on render.com, do I need to create a new account to test?

**A: Yes, absolutely!** This is the recommended approach - see the detailed guide in TESTING_GUIDE.md.

### Q: Should I delete old Firebase accounts afterwards?

**A: It depends** - see the detailed decision matrix in TESTING_GUIDE.md.

## Best Practices

### Voor Testing (For Testing):
1. Gebruik `email+test1@gmail.com` notatie voor test accounts
2. Houd 1-2 permanente test accounts
3. Verwijder tijdelijke test accounts na gebruik
4. Documenteer je test resultaten

### Voor Productie (For Production):
1. Monitor je Firebase usage in de console
2. Check regelmatig je Security Rules
3. Review accounts periodiek voor opschoning
4. Backup belangrijke data

### Voor Beveiliging (For Security):
1. Gebruik sterke wachtwoorden voor test accounts
2. Stel correcte Firestore Security Rules in
3. Monitor ongebruikelijke activiteit
4. Houd Firebase SDK up-to-date

## Nuttige Links (Useful Links)

- Firebase Console: https://console.firebase.google.com
- Je project: https://console.firebase.google.com/project/crewwealth-cbe02
- Firebase Documentation: https://firebase.google.com/docs
- Firestore Security Rules: https://firebase.google.com/docs/firestore/security/get-started

## Hulp Nodig? (Need Help?)

Check de volgende bestanden:
- `TESTING_GUIDE.md` - Uitgebreide testing instructies
- `README.md` - Project overview
- `SETUP.md` - Development setup

Of open een issue in GitHub voor specifieke vragen.
