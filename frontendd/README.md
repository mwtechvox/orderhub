# OrderHub frontend

Next.js App Router, React, TypeScript, Tailwind CSS, TanStack Query. Монгол UI, desktop болон mobile layout. Meta token browser-д ирэхгүй.

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

`http://localhost:3000/login` нээнэ. Backend-ийн `create_owner` командаар үүсгэсэн нэр/нууц үгээр нэвтэрнэ.

- `/inbox`: яриа, unread тоо, түүх, pending/sending/sent/failed төлөв; 3–4 секундийн polling.
- `/posts`: pagination, хайлт, синк, aggregate count.
- `/posts/[id]`: нийтлэл, медиа, comments/replies, reply form.
- `/settings/integrations`: OAuth, Page сонголт, sync/reconnect/disconnect.

## Орчны хувьсагч

```dotenv
NEXT_PUBLIC_API_BASE_URL=
BACKEND_INTERNAL_URL=http://localhost:8000
```

Хоосон public API URL нь browser-оос өөрийн origin дахь `/api/` руу хандаж, Next.js rewrite-ээр Django руу дамжуулна. Энэ нь session cookie болон CSRF-ийг энгийн байлгана. `BACKEND_INTERNAL_URL` нь server-only routing утга; нууц түлхүүр биш. Next build хийх үед rewrite болон public URL шингэнэ. Өөрчилбөл дахин build хийнэ.

Шууд API ашиглах бол `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` гэж тохируулж болно. HTTPS production-д frontend/backend нэг site эсвэл same-origin reverse proxy ашиглана. Meta secret/token-ийг frontend env-д оруулахгүй. Auth localStorage ашиглахгүй.

## Шалгалт ба production build

```bash
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
npm run start
```

E2E нь суулгасан Google Chrome (`channel: chrome`) ашиглана. Chrome байхгүй CI-д `npx playwright install chromium` ажиллуулаад config-ийн channel-ийг хасна. E2E backend response-ийг mock хийдэг; бодит Meta delivery-г батлахгүй. `npm start` standalone output руу static assets хуулж 3000 порт дээр ажиллуулна.

```bash
docker build -t orderhub-web --build-arg BACKEND_INTERNAL_URL=http://backend:8000 .
```

Runtime-ийг backend-тэй нэг Docker network-д холбож, same-origin HTTPS reverse proxy байрлуулна. `npm run dev` нь локал хөгжүүлэлтийн хамгийн энгийн хувилбар.
