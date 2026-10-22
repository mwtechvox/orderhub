import { Link } from "react-router";

export default function LandingPage() {
  return (
    <main className="home-page">
      <section className="home-hero" id="top">
        <nav className="home-nav" aria-label="Үндсэн цэс">
          <a className="home-brand" href="#top" aria-label="OrderHub нүүр">
            <span className="home-brand-mark" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            <strong>OrderHub</strong>
          </a>
          <div className="home-nav-links">
            <a href="#how">Хэрхэн ажиллах вэ?</a>
            <a href="#features">Онцлогууд</a>
          </div>
          <div className="home-nav-actions">
            <Link className="home-login" to="/login">Нэвтрэх</Link>
            <Link className="home-cta home-cta-small" to="/login">Эхлэх <span aria-hidden="true">→</span></Link>
          </div>
        </nav>

        <div className="home-hero-copy">
          <p className="home-eyebrow"><span aria-hidden="true" /> Facebook-д зориулсан нэгдсэн ажлын орчин</p>
          <h1>Харилцаа бүрийг<br /><em>ойртуулна.</em></h1>
          <p className="home-lede">
            Facebook нийтлэл, сэтгэгдэл, Messenger мессежээ нэг цонхноос удирдаарай.
            Танай баг хурдан хариулж, харилцагч бүрийг анзаарах боломжтой болно.
          </p>
          <div className="home-actions">
            <Link className="home-cta" to="/login">OrderHub руу нэвтрэх <span aria-hidden="true">→</span></Link>
            <a className="home-secondary" href="#how">Танилцах <span aria-hidden="true">↓</span></a>
          </div>
        </div>

        <div className="home-botgo-stage" aria-label="Ботго, OrderHub-ийн туслах дүр">
          <div className="home-botgo-halo" aria-hidden="true" />
          <div className="home-bubble home-bubble-left" aria-hidden="true"><i /><span /><span /></div>
          <div className="home-bubble home-bubble-right" aria-hidden="true"><i /><span /></div>
          <img className="home-botgo" src="/botgo-orderhub.png" alt="Малгайтай ботго, OrderHub-ийн туслах дүр" />
          <p className="home-botgo-status"><i aria-hidden="true" /> Ботго онлайн</p>
        </div>
      </section>

      <section className="home-section home-how" id="how">
        <div className="home-section-heading">
          <p>НЭГ ДОР, ИЛҮҮ ОЙР</p>
          <h2>Харилцагчийнхаа яриаг бүү алдаарай.</h2>
          <span>OrderHub нь Facebook хуудасны өдөр тутмын харилцааг багийн тань ойлгомжтой ажлын урсгал болгоно.</span>
        </div>
        <div className="home-steps">
          <article><b>01</b><h3>Хуудсаа холбоно</h3><p>Facebook Page-ээ холбоод ажлын орчноо бэлдэнэ.</p></article>
          <article><b>02</b><h3>Яриагаа нэгтгэнэ</h3><p>Нийтлэл, сэтгэгдэл, Messenger мессежээ нэг дороос харна.</p></article>
          <article><b>03</b><h3>Багаараа хариулна</h3><p>Харилцагч бүрд цаг алдалгүй, түүхтэй нь хамт хариулна.</p></article>
        </div>
      </section>

      <section className="home-section home-features" id="features">
        <div className="home-section-heading">
          <p>ӨДӨР ТУТМЫН АЖЛАА ЦЭГЦЭЛ</p>
          <h2>Хариулахад хэрэгтэй бүх зүйл ойрхон.</h2>
        </div>
        <div className="home-feature-grid">
          <article><i>✦</i><h3>Нэгдсэн inbox</h3><p>Messenger яриагаа нэг ажлын орчинд төвлөрүүлнэ.</p></article>
          <article><i>◌</i><h3>Сэтгэгдлийн хяналт</h3><p>Нийтлэлийн сэтгэгдэл болон хариуг ойлгомжтой удирдана.</p></article>
          <article><i>↗</i><h3>Харилцагчийн түүх</h3><p>Өмнөх яриагаа хараад илүү уялдаатай хариулна.</p></article>
        </div>
      </section>

      <section className="home-final">
        <div><p>ORDERHUB-ТЭЙ ХАМТ</p><h2>Харилцагч бүртэйгээ илүү ойр байя.</h2></div>
        <Link className="home-cta" to="/login">Нэвтрэх <span aria-hidden="true">→</span></Link>
      </section>
    </main>
  );
}
