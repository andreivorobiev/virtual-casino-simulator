import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TiltSeven — Атмосфера казино без ставок",
  description:
    "TiltSeven — частный симулятор казино с игровыми токенами: без денежных вкладов, покупок, выводов и призов.",
};

const games = [
  "Рулетка",
  "Блэкджек",
  "Баккара",
  "Слоты",
  "Кено",
  "Бинго",
  "Sic Bo",
  "Видеопокер",
];

const promises = [
  "Без депозитов",
  "Без покупок",
  "Без выводов",
  "Без обмена",
  "Без призов",
  "Без переносимой ценности",
];

export default function RussianHome() {
  return (
    <main className="site-shell">
      <header className="topbar" aria-label="TiltSeven">
        <a className="brand-lockup" href="/ru" aria-label="Главная TiltSeven">
          <img src="/tiltseven-mark.svg" alt="" width="56" height="56" />
          <span>
            <strong>TiltSeven</strong>
            <small>Только игровые токены · без денежной ценности</small>
          </span>
        </a>
        <nav className="nav-links" aria-label="Основная навигация">
          <a href="#floor">Зал</a>
          <a href="#safety">Безопасность</a>
          <a href="#preview">Превью</a>
          <a href="/" hrefLang="en">
            English
          </a>
          <a className="pill-link" href="https://casino.tiltseven.com/">
            Войти в казино
          </a>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Частный симулятор казино</p>
          <h1>Атмосфера казино без ставок.</h1>
          <p className="lede">
            TiltSeven превращает зал казино в аккуратный симулятор: столы,
            барабаны, колёса, карты, боты и журнал игровых токенов, которые
            никогда не становятся деньгами или призами.
          </p>
          <div className="hero-actions" aria-label="Основные действия">
            <a className="button primary" href="https://casino.tiltseven.com/">
              Войти в казино
            </a>
            <a className="button secondary" href="#safety">
              Прочитать обещание безопасности
            </a>
          </div>
          <p className="fine-print">{promises.join(". ")}.</p>
        </div>
        <div className="hero-stage" aria-label="Стилизованное превью казино">
          <div className="orb one" />
          <div className="orb two" />
          <div className="seven-chip">7</div>
          <div className="felt-board">
            {games.slice(0, 4).map((game) => (
              <span key={game}>{game}</span>
            ))}
          </div>
          <div className="reels" aria-hidden="true">
            <span>BAR</span>
            <span>7</span>
            <span>WLD</span>
          </div>
        </div>
      </section>

      <section id="floor" className="section">
        <div className="section-heading">
          <p className="eyebrow">Зал казино как программный продукт</p>
          <h2>Для изучения игр, а не для траты денег.</h2>
        </div>
        <div className="feature-grid">
          <article>
            <h3>Энергия столов</h3>
            <p>
              Рулетка, блэкджек, баккара, Dragon Tiger, Sic Bo и другие игры
              ощущаются как карта зала, а не как таблица.
            </p>
          </article>
          <article>
            <h3>Повторяемые исходы</h3>
            <p>
              Раунды связаны с журналом, понятны для проверки и безопасны для
              повторного просмотра, потому что все токены условные.
            </p>
          </article>
          <article>
            <h3>Ясность администрирования</h3>
            <p>
              Операции, отчёты, профили и восстановление отделены от
              маркетингового сайта и от любых намёков на реальные деньги.
            </p>
          </article>
        </div>
      </section>

      <section id="safety" className="safety-panel">
        <div>
          <p className="eyebrow">Обещание безопасности</p>
          <h2>Ощущение казино. Границы симулятора.</h2>
        </div>
        <ul>
          {promises.map((promise) => (
            <li key={promise}>{promise}</li>
          ))}
        </ul>
      </section>

      <section id="preview" className="section preview-grid">
        <div className="section-heading">
          <p className="eyebrow">Первый взгляд</p>
          <h2>Сейчас бренд-страница, дальше — полноценный публичный сайт.</h2>
          <p>
            Эта первая версия представляет TiltSeven, ведёт посетителей в живой
            виртуальный зал и не включает публикацию DNS, биллинг, провайдеры
            или иные эксплуатационные изменения.
          </p>
        </div>
        <div className="stat-card">
          <strong>30</strong>
          <span>симулируемых игр</span>
        </div>
        <div className="stat-card">
          <strong>0</strong>
          <span>механик с денежной ценностью</span>
        </div>
        <div className="stat-card">
          <strong>2</strong>
          <span>базовых языка</span>
        </div>
      </section>
    </main>
  );
}
