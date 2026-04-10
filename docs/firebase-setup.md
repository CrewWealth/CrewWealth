# Firebase / Firestore Setup Guide

This document explains how to configure Firebase for CrewWealth, upload the
Firestore security rules, and ensure user documents are provisioned correctly.

---

## 1. Create a Firebase Project

1. Go to [https://console.firebase.google.com/](https://console.firebase.google.com/).
2. Click **Add project** and follow the wizard (enable or skip Google Analytics).
3. Note your **Project ID** (e.g. `crewwealth-cbe02`).

---

## 2. Enable Authentication

1. In the Firebase console, go to **Build → Authentication**.
2. Click **Get started** and enable the **Email/Password** sign-in provider.

---

## 3. Enable Firestore

1. Go to **Build → Firestore Database**.
2. Click **Create database**.
3. Start in **production mode** (the rules below lock it down properly).
4. Choose a Cloud region close to your users.

---

## 4. Upload the Security Rules

The security rules live in [`firestore.rules`](../firestore.rules) in the repo root.
They allow each authenticated user to read and write **only their own**
`/users/{uid}` subtree.

### Option A — Firebase CLI (recommended)

```bash
npm install -g firebase-tools
firebase login
firebase use <your-project-id>
firebase deploy --only firestore:rules
```

### Option B — Firebase Console

1. Open **Firestore Database → Rules**.
2. Paste the contents of `firestore.rules` into the editor.
3. Click **Publish**.

Current rules (see `firestore.rules`):

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    function signedIn() { return request.auth != null; }
    function isOwner(userId) { return signedIn() && request.auth.uid == userId; }

    match /users/{userId} {
      allow read, write: if isOwner(userId);
      match /{document=**} {
        allow read, write: if isOwner(userId);
      }
    }

    match /{document=**} { allow read, write: if false; }
  }
}
```

---

## 5. User Document Provisioning

Each user needs a document at `users/{uid}` in Firestore.  
CrewWealth creates this document automatically in two places:

| Where | When |
|-------|------|
| `app/templates/register.html` | When a new account is created via the registration form |
| `app/templates/settings.html` (`ensureUserDoc`) | On every login, before loading settings — creates the doc with defaults if it is missing |

### Default document structure

```json
{
  "email": "user@example.com",
  "fullName": "Full Name",
  "baseCurrency": "EUR",
  "settings": {
    "currency": "EUR",
    "language": "en",
    "theme": "light"
  },
  "createdAt": "<server timestamp>",
  "updatedAt": "<server timestamp>"
}
```

### Manual provisioning (admin / migration)

If you have existing Auth users without a Firestore document, you can create
them from the Firebase console:

1. Open **Firestore Database → Data**.
2. Click **Start collection**, enter `users`.
3. Set the **Document ID** to the user's UID (find it under **Authentication → Users**).
4. Add the fields listed above.

Or run the following snippet in the Firebase console's **Cloud Shell** (or
locally with the Admin SDK):

```js
const admin = require('firebase-admin');
admin.initializeApp();
const db = admin.firestore();

const uid = 'REPLACE_WITH_UID';
await db.collection('users').doc(uid).set({
  baseCurrency: 'EUR',
  settings: { currency: 'EUR', language: 'en', theme: 'light' },
  createdAt: admin.firestore.FieldValue.serverTimestamp(),
  updatedAt: admin.firestore.FieldValue.serverTimestamp()
}, { merge: true });
```

---

## 6. Environment Variables / Firebase Config

The client-side Firebase config is embedded directly in the HTML templates
(`firebaseConfig` object). Make sure the `projectId` in every template matches
your Firebase project.

For local development you can add a `.env` file based on `.env.example`:

```
FIREBASE_PROJECT_ID=crewwealth-cbe02
FIREBASE_API_KEY=...
FIREBASE_AUTH_DOMAIN=...
FIREBASE_STORAGE_BUCKET=...
FIREBASE_MESSAGING_SENDER_ID=...
FIREBASE_APP_ID=...
```

---

## 7. Troubleshooting

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `No document to update` | `updateDoc` called before doc exists | Use `set({...}, {merge:true})` (already fixed in `settings.html`) |
| `Missing or insufficient permissions` | Rules not uploaded, or user not authenticated | Deploy rules; ensure user is signed in |
| `unauthenticated` | Session expired | Re-login; check `onAuthStateChanged` |
| Nothing saves, no error | Wrong `projectId` in config | Verify `firebaseConfig.projectId` matches your Firebase project |
