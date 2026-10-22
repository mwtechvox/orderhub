import Image from "next/image";
import Link from "next/link";

export default function Home() {
  return (
    <main className="marketing-page">
      <section className="marketing-hero" id="top">
        <nav className="marketing-nav" aria-label="Үндсэн цэс">
          <Link className="marketing-brand" href="#top" aria-label="OrderHub нүүр">
            <span className="marketing-brand-mark" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            <strong>OrderHub</strong>
          </Link>
          <div className="marketing-nav-links">
            <a href="#how">Хэрхэн ажиллах вэ?</a>
            <a href="#features">Онцлогууд</a>
            <a href="#workspace">Ажлын орчин</a>
          </div>
          <div className="marketing-nav-actions">
            <Link className="marketing-login" href="/login">
              Нэвтрэх
            </Link>
            <Link className="marketing-cta marketing-cta-small" href="/login">
              Эхлэх <span aria-hidden="true">→</span>
            </Link>
          </div>
        </nav>

        <div className="marketing-hero-copy">
          <p className="marketing-eyebrow">
            <span className="marketing-live-dot" aria-hidden="true" />
            Facebook-д зориулсан нэгдсэн ажлын орчин
          </p>
          <h1>
            Харилцаа бүрийг
            <br />
            <span>ойртуулна.</span>
          </h1>
          <p className="marketing-lede">
            Facebook нийтлэл, сэтгэгдэл, Messenger мессежээ нэг цонхноос удирдаарай.
            Танай баг хурдан хариулж, харилцагч бүрийг анзаарах боломжтой болно.
          </p>
          <div className="marketing-hero-actions">
            <Link className="marketing-cta" href="/login">
              OrderHub руу нэвтрэх <span aria-hidden="true">→</span>
            </Link>
            <a className="marketing-secondary" href="#how">
              Танилцах <span aria-hidden="true">↓</span>
            </a>
          </div>
        </div>

        <div className="botgo-stage" aria-label="Ботго, OrderHub-ийн туслах дүр">
          <div className="botgo-halo" aria-hidden="true" />
          <div className="botgo-speech botgo-speech-left" aria-hidden="true">
            <span className="botgo-speech-dot" />
            <span className="botgo-speech-line" />
            <span className="botgo-speech-line botgo-speech-line-short" />
          </div>
          <div className="botgo-speech botgo-speech-right" aria-hidden="true">
            <span className="botgo-speech-dot" />
            <span className="botgo-speech-line" />
          </div>
          <Image
            className="botgo-image"
            src="/botgo-orderhub.png"
            alt="Малгайтай ботго, OrderHub-ийн туслах дүр"
            width={1229}
            height={1280}
            priority
          />
          <div className="botgo-status">
            <span className="botgo-status-dot" aria-hidden="true" />
            Ботго онлайн
          </div>
        </div>
      </section>

      <section className="marketing-section marketing-how" id="how">
        <div className="marketing-section-heading">
          <p className="marketing-kicker">НЭГ ДОР, ИЛҮҮ ОЙР</p>
          <h2>Харилцагчийнхаа яриаг бүү алдаарай.</h2>
          <p>
            OrderHub нь Facebook хуудасны өдөр тутмын харилцааг багийн тань ойлгомжтой
            ажлын урсгал болгоно.
          </p>
        </div>
        <div className="marketing-steps">
          <article>
            <span>01</span>
            <h3>Хуудсаа холбоно</h3>
            <p>Facebook Page-ээ холбоод ажлын орчноо бэлдэнэ.</p>
          </article>
          <article>
            <span>02</span>
            <h3>Яриагаа нэгтгэнэ</h3>
            <p>Нийтлэл, сэтгэгдэл, Messenger мессежээ нэг дороос харна.</p>
          </article>
          <article>
            <span>03</span>
            <h3>Багаараа хариулна</h3>
            <p>Харилцагч бүрд цаг алдалгүй, түүхтэй нь хамт хариулна.</p>
          </article>
        </div>
      </section>

      <section className="marketing-section marketing-workspace" id="workspace">
        <div className="workspace-copy">
          <p className="marketing-kicker">НЭГ ЦОНХНЫ УДИРДЛАГА</p>
          <h2>Танай багийн харилцааны төв.</h2>
          <p>
            Мессеж болон сэтгэгдэл нь тус тусдаа цонх биш. Тухайн харилцагчийн түүхийг
            нэг дороос хараад, дараагийн хариултаа илүү итгэлтэй илгээнэ.
          </p>
          <Link className="marketing-text-link" href="/login">
            Ажлын орчин руу орох <span aria-hidden="true">→</span>
          </Link>
        </div>
        <div className="workspace-demo" aria-label="OrderHub inbox-ийн жишээ">
          <div className="workspace-demo-bar">
            <span className="workspace-brand-dot" />
            <span>OrderHub Inbox</span>
            <span className="workspace-online">Онлайн</span>
          </div>
          <div className="workspace-demo-grid">
            <div className="workspace-list">
              <p>Харилцагчид</p>
              <div className="workspace-person selected">
                <span className="workspace-avatar">Н</span>
                <span>
                  <strong>Номин</strong>
                  <small>Үнэ асуусан</small>
                </span>
                <i>2</i>
              </div>
              <div className="workspace-person">
                <span className="workspace-avatar pink">С</span>
                <span>
                  <strong>Саруул</strong>
                  <small>Сэтгэгдэл бичсэн</small>
                </span>
              </div>
              <div className="workspace-person">
                <span className="workspace-avatar gold">Т</span>
                <span>
                  <strong>Тэмүүлэн</strong>
                  <small>Messenger</small>
                </span>
              </div>
            </div>
            <div className="workspace-chat">
              <div className="workspace-chat-head">
                <span className="workspace-avatar">Н</span>
                <div>
                  <strong>Номин</strong>
                  <small>Messenger</small>
                </div>
              </div>
              <div className="workspace-messages">
                <p className="workspace-bubble incoming">Сайн байна уу? Үнэ нь хэд вэ?</p>
                <p className="workspace-bubble outgoing">Сайн байна уу, Номин оо. Танд дэлгэрэнгүй мэдээлэл явуулъя.</p>
                <small>Дөнгөж сая</small>
              </div>
              <div className="workspace-composer">
                Хариулт бичих...
                <span>↑</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="marketing-section marketing-features" id="features">
        <div className="marketing-section-heading">
          <p className="marketing-kicker">ӨДӨР ТУТМЫН АЖЛАА ЦЭГЦЭЛ</p>
          <h2>Хариулахад хэрэгтэй бүх зүйл ойрхон.</h2>
        </div>
        <div className="marketing-feature-grid">
          <article>
            <span className="feature-icon">✦</span>
            <h3>Нэгдсэн inbox</h3>
            <p>Messenger яриагаа нэг ажлын орчинд төвлөрүүлнэ.</p>
          </article>
          <article>
            <span className="feature-icon">◌</span>
            <h3>Сэтгэгдлийн хяналт</h3>
            <p>Нийтлэлийн сэтгэгдэл болон хариуг ойлгомжтой удирдана.</p>
          </article>
          <article>
            <span className="feature-icon">↗</span>
            <h3>Харилцагчийн түүх</h3>
            <p>Өмнөх яриагаа хараад илүү уялдаатай хариулна.</p>
          </article>
        </div>
      </section>

      <section className="marketing-final">
        <div>
          <p className="marketing-kicker">ORDERHUB-ТЭЙ ХАМТ</p>
          <h2>Харилцагч бүртэйгээ илүү ойр байя.</h2>
        </div>
        <Link className="marketing-cta" href="/login">
          Нэвтрэх <span aria-hidden="true">→</span>
        </Link>
      </section>
    </main>
  );
}
