# App Review бэлтгэл

[Meta тохиргоо, permission matrix](META_SETUP.md)-ийг дагана. Нэг reviewer account-ийг OrderHub-д үүсгэж, туршилтын Company болон Page-тай холбоно. Бодит хэрэглэгчийн нууц мэдээлэл агуулсан бичлэг бүү ашигла.

Видео: нэвтрэх → Facebook OAuth зөвшөөрөл → Page list → сонгох → sync → post count/comment → reply → Facebook дээр батлах → customer Messenger message → webhook-оор inbox шинэчлэгдэх → хариу → Messenger дээр хүлээн авах.

`pages_manage_metadata`: callback verification болон Page subscribed_apps ажилласныг, webhook шинэ өгөгдөл оруулж буйг тайлбарлана. Permission бүрийн бодит product хэрэгцээг тусад нь бичнэ. Meta App ID, webhook/redirect URL, privacy policy, data deletion instructions, business verification, reviewer login/test asset instructions бэлэн болгоно.

App Review зөвшөөрөл автомат биш. Эзэмшигч баталгаажуулж, шаардлагатай Advanced Access авсны дараа Live болгоно.
