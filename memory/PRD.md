# PRD — Valandala Landing Page

## Problema originală
Crearea unei pagini de tip "Under Construction" pentru aplicația mobilă **Valandala** (valandala.ro), inițial numită "Vindetz". Pagina este un fișier HTML static care urmează să fie hostat pe domeniul propriu al utilizatorului.

## Cerințe principale
- Pagină responsivă HTML/CSS pur (fără framework-uri complexe)
- Culori bazate pe logo-ul aplicației (galben → portocaliu → roz/magenta)
- Mesaj "Site în Construcție" / "Lansare în Curând"
- Indicatori pentru App Store și Google Play (fără linkuri active deocamdată)
- Fără formular de contact
- Fără animații la scroll
- Fără footer links
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
- Creat `vindetz-landing.html` (dark theme, GSAP animations) — legacyvindetz
- Pivotare la `valandala-landing.html` (pagină simplă under construction)
- Configurat `App.js` să redirecționeze imediat la pagina statică HTML
- Eliminat animații scroll
- Păstrat pills iOS/Android (App Store / Google Play)
- Eliminat linkuri footer și buton portocaliu
- Redesign complet: temă luminoasă bazată pe logo (galben/portocaliu/roz/magenta)

### Sesiunea 2 (Feb 2026)
- Eliminat logo-ul mic din bara de navigare (nav)
- Înlocuit titlul text mare "Valandala." cu logo-ul imaginii, mărit (`clamp(180px, 30vw, 360px)`)
- Adăugat animație de intrare `fadeUp` pe logo (wrap `div.hero-logo-wrap`)
- Adăugat animație continuă `float` pe logo (plutire sus-jos cu ușoară rotație)
- Rezolvat conflict CSS transform prin separarea animațiilor pe 2 elemente (wrap + img)

## Backlog / Viitor
- Adăugare secțiune cu linkuri reale App Store / Google Play când aplicația este publicată
- Email de notificare "Anunță-mă la lansare" (dacă utilizatorul dorește)
- Versiune multi-limbă (RO/EN)
