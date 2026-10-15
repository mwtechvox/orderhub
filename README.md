# OrderHub — Facebook MVP

Django REST API, PostgreSQL, Redis/Celery, React/Vite ашигласан компанийн тусгаарлалттай Facebook ажлын орчин. UI болон хөгжүүлэгчийн үндсэн заавар Монгол хэлээр. `deep-research-report.md`-ийг өөрчлөөгүй.

Бэлэн урсгал: login → Facebook OAuth → Page сонгох → шифрлэсэн token → feed/comments/reactions → comment reply → Messenger conversation/history → асинхрон message reply → баталгаажуулсан webhook.

- [Backend эхлүүлэх](backend/README.md)
- [Frontend эхлүүлэх](frontend/README.md)
- [Meta Dashboard тохируулах](backend/docs/META_SETUP.md)
- [Локал хөгжүүлэлт ба HTTPS tunnel](backend/docs/LOCAL_DEVELOPMENT.md)
- [Аюулгүй байдал](backend/docs/SECURITY.md)
- [API](backend/docs/API.md)
- [Судалгаанаас ялгаа, хязгаарлалт](backend/docs/DEVIATIONS.md)
- [Баталгаажуулалтын үр дүн](backend/docs/VALIDATION.md)
- [Файлын мод](TREE.md)

Instagram, mobile, products/orders, QPay, eBarimt, delivery, AI, accounting хэрэгжүүлээгүй. Бодит Meta app credentials болон App Review байхгүй тул бодит Facebook delivery-г localhost тесттэй адилтгаж болохгүй.
# orderhub
