# Repository файлын мод

Generated/cache/local secrets-ийг хассан.

```text
OrderHub/
├── backend/
│   ├── apps/
│   │   ├── accounts/
│   │   │   ├── management/
│   │   │   │   ├── commands/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── create_owner.py
│   │   │   │   │   └── seed_demo.py
│   │   │   │   └── __init__.py
│   │   │   ├── migrations/
│   │   │   │   └── __init__.py
│   │   │   ├── __init__.py
│   │   │   └── views.py
│   │   ├── common/
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── errors.py
│   │   │   ├── middleware.py
│   │   │   ├── models.py
│   │   │   ├── provider.py
│   │   │   ├── queue.py
│   │   │   └── throttles.py
│   │   ├── companies/
│   │   │   ├── migrations/
│   │   │   │   ├── 0001_initial.py
│   │   │   │   └── __init__.py
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── models.py
│   │   │   ├── permissions.py
│   │   │   └── views.py
│   │   ├── inbox/
│   │   │   ├── migrations/
│   │   │   │   ├── 0001_initial.py
│   │   │   │   └── __init__.py
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── services.py
│   │   │   ├── tasks.py
│   │   │   └── views.py
│   │   ├── meta/
│   │   │   ├── management/
│   │   │   │   ├── commands/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── sync_meta_account.py
│   │   │   │   └── __init__.py
│   │   │   ├── migrations/
│   │   │   │   ├── 0001_initial.py
│   │   │   │   ├── 0002_rawwebhookevent.py
│   │   │   │   ├── 0003_socialaccount_next_sync_at_and_more.py
│   │   │   │   └── __init__.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── encryption.py
│   │   │   │   ├── facebook.py
│   │   │   │   ├── oauth.py
│   │   │   │   ├── tokens.py
│   │   │   │   └── webhooks.py
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── exceptions.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── tasks.py
│   │   │   ├── views.py
│   │   │   └── webhook_views.py
│   │   ├── social/
│   │   │   ├── migrations/
│   │   │   │   ├── 0001_initial.py
│   │   │   │   ├── 0002_comment_last_event_at.py
│   │   │   │   └── __init__.py
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── services.py
│   │   │   ├── tasks.py
│   │   │   └── views.py
│   │   └── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── celery.py
│   │   ├── settings.py
│   │   ├── test_settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── docs/
│   │   ├── API.md
│   │   ├── APP_REVIEW.md
│   │   ├── DEVIATIONS.md
│   │   ├── LOCAL_DEVELOPMENT.md
│   │   ├── META_SETUP.md
│   │   ├── SECURITY.md
│   │   └── VALIDATION.md
│   ├── scripts/
│   │   └── init_env.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_concurrency.py
│   │   ├── test_inbox.py
│   │   ├── test_integrations.py
│   │   ├── test_meta_client.py
│   │   ├── test_oauth_flow.py
│   │   ├── test_queue.py
│   │   ├── test_social.py
│   │   ├── test_tokens_oauth.py
│   │   └── test_webhooks.py
│   ├── .dockerignore
│   ├── .env.example
│   ├── Dockerfile
│   ├── README.md
│   ├── docker-compose.yml
│   ├── manage.py
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── uv.lock
├── frontend/
│   ├── app/
│   │   ├── inbox/
│   │   │   └── page.tsx
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── posts/
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx
│   │   │   └── page.tsx
│   │   ├── settings/
│   │   │   └── integrations/
│   │   │       └── page.tsx
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── inbox.tsx
│   │   ├── integrations.tsx
│   │   ├── posts.tsx
│   │   ├── providers.tsx
│   │   ├── shell.tsx
│   │   └── ui.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── format.ts
│   │   └── types.ts
│   ├── scripts/
│   │   └── start.mjs
│   ├── tests/
│   │   ├── e2e/
│   │   │   ├── app.spec.ts
│   │   │   └── live-auth.spec.ts
│   │   ├── api.test.ts
│   │   ├── composer.test.tsx
│   │   ├── inbox.test.tsx
│   │   ├── posts.test.tsx
│   │   └── setup.ts
│   ├── .dockerignore
│   ├── .env.example
│   ├── Dockerfile
│   ├── README.md
│   ├── eslint.config.mjs
│   ├── next-env.d.ts
│   ├── next.config.ts
│   ├── package-lock.json
│   ├── package.json
│   ├── playwright.config.ts
│   ├── postcss.config.mjs
│   ├── tsconfig.json
│   └── vitest.config.ts
├── .gitignore
├── AGENTS.md
├── PLANS.md
├── README.md
├── TREE.md
└── deep-research-report.md
```
