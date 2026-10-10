# PRD — Valandala Landing Page

## Problema originală
Crearea unei pagini de tip "Under Construction" / "Coming Soon" pentru aplicația mobilă **Valandala** (valandala.ro), marketplace C2C la nivel național în România. Pagina este un fișier HTML static care urmează să fie hostat pe domeniul propriu al utilizatorului.

## Cerințe principale
- Pagină responsivă HTML/CSS pur (fără framework-uri complexe)
- Temă dark/light cu toggle
- Secțiune hero cu poze de fundal și CTA
- Formular de înscriere pe lista de așteptare (waitlist)
- Indicatori App Store și Google Play
- Limbă: Română

## Arhitectura curentă
```
/app/
├── frontend/
│   ├── src/
│   │   └── App.js  ← redirect instant la /valandala-landing.html
│   └── public/
│       ├── valandala-landing.html  ← pagina activă (copie)
│       └── vindetz-landing.html   ← legacy
├── valandala-landing.html  ← sursa de adevăr (de copiat în public/)
└── vindetz-landing.html    ← legacy
```

**Notă importantă pentru agenți viitori:** Orice modificare la `/app/valandala-landing.html` trebuie copiată și în `/app/frontend/public/` cu:
```bash
cp /app/valandala-landing.html /app/frontend/public/valandala-landing.html
```

## Ce s-a implementat

### Sesiunea 1
- Creat `vindetz-landing.html` (dark theme, GSAP animations) — legacy
- Pivotare la `valandala-landing.html` (pagină simplă under construction)
- Configurat `App.js` să redirecționeze imediat la pagina statică HTML

### Sesiunea 2 (Feb 2026)
- Redesign complet: temă luminoasă bazată pe logo (galben/portocaliu/roz/magenta)
- Eliminat logo din nav, înlocuit titlu text cu logo imagine (animat float)

### Sesiunea 3 (Oct 2026)
- Înlocuire completă cu noul HTML uploadat de utilizator
- Pagină completă cu: header sticky, marquee, hero cu tiles foto, secțiuni multiple
- Toggle dark/light mode cu persistență în localStorage
- Formular waitlist (`data-poppy-form`)
- Secțiuni: "Sună cunoscut?", "Cum funcționează" (4 pași), "De ce Valandala" (6 features), testimoniale (3 quote-uri), footer cu social links
- Font Poppins adăugat (lipsea din original)

## Backlog / Viitor
- Conectare formular waitlist la un serviciu real (ex: Mailchimp, ConvertKit, Poppy)
- Adăugare linkuri reale App Store / Google Play când aplicația este publicată
- Adăugare linkuri reale Instagram, TikTok, Facebook
