# OrderHub frontend

Шинэ OrderHub UI нь React 19, Vite, TypeScript, Tailwind CSS v4, TanStack Query болон React Router ашиглана. Browser зөвхөн OrderHub Django API-тай ярьж, Meta access token эсвэл app secret авдаггүй.

## Бүтэц

```text
src/
├── components/        # дахин ашиглах UI ба social controls
├── features/          # auth, company, inbox, posts, integrations
├── layouts/           # AppShell, sidebar, header, mobile navigation
├── lib/               # typed API client, formatter
├── tests/             # Vitest regression
├── types/             # backend API contract
├── App.tsx            # route composition
└── main.tsx           # providers ба React entry
```

Энэ нь `mak_portal/frontend`-ийн feature-oriented зохион байгуулалтыг дагана. OrderHub-ийн харагдац болон backend contract тусдаа хэвээр.

## Local ажиллуулах

Backend `http://localhost:8000` дээр ажиллаж байх үед:

```bash
cd frontend
cp .env.example .env
pnpm install
pnpm dev
```

UI: `http://localhost:3000`. Vite `/api/*` болон `/health/*` хүсэлтийг `VITE_BACKEND_PROXY_TARGET` руу same-origin proxy хийнэ. Ингэснээр Django session cookie, CSRF болон OAuth callback нэг browser origin дээр ажиллана.

Шалгалт:

```bash
pnpm run typecheck
pnpm run test
pnpm run build
pnpm run format:check
```

`VITE_*` хувьсагчид browser bundle-д харагддаг. Meta app secret, access token, webhook verify token, encryption key-г frontend env-д хэзээ ч бүү хий.
