# Structure du frontend — SecureScan

Organisation des dossiers et rôles pour faciliter la lecture et l’évolution du code.

```
src/
├── main.tsx              # Point d’entrée : RouterProvider, styles globaux
├── index.css             # Variables CSS (fonts, couleurs, reset)
├── App.css               # Styles layout, pages auth, boutons
├── routes.tsx            # Définition des routes (createBrowserRouter)
│
├── api/                  # Appels HTTP vers le backend
│   ├── index.ts          # Barrel : export client + auth
│   ├── client.ts         # Base URL, fetch avec credentials
│   └── auth.ts           # register, login, logout, getMe
│
├── types/                # Types TypeScript partagés (alignés API)
│   └── index.ts          # User, etc.
│
├── layouts/              # Mises en page communes (header, footer, Outlet)
│   ├── index.ts
│   └── RootLayout.tsx
│
├── views/                # Une vue = une page (écran) par route
│   ├── index.ts
│   ├── HomePage.tsx
│   ├── LoginPage.tsx
│   └── RegisterPage.tsx
│
├── components/           # Composants UI réutilisables
│   ├── index.ts
│   └── Button.tsx
│
├── hooks/                # Hooks React réutilisables (useAuth, useApi…)
│   └── index.ts
│
└── assets/               # Images, icônes
```

## Règles simples

- **Importer via les barils** : `from "./views"`, `from "../api"`, `from "../components"` pour alléger les imports dans `routes` et entre dossiers.
- **types/** : types partagés (ex. `User`) utilisés par l’API et les composants ; évite de dupliquer les définitions.
- **api/** : tout ce qui touche au réseau ; un fichier par domaine (auth, scans…) si le projet grandit.
- **views/** : une vue = une URL ; pas de logique métier lourde, déléguer aux hooks ou à l’API.
- **hooks/** : logique réutilisable (état, effets, appels API) à sortir des vues quand ça se répète.
