import type { Metadata } from "next";

// Метаданные страницы описывают приватное превью без обещания публичного запуска.
export const metadata: Metadata = {
  title: "TiltSeven — Приватный симулятор казино с игровыми жетонами",
  description:
    "TiltSeven — приватный симулятор казино с атмосферой игрового зала, журналом раундов, игровыми жетонами без денежной ценности, без пополнений и без вывода средств.",
};

// Список первых видимых игр используется только для декоративного превью зала.
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

// Общий список обещаний сохраняет одинаковую безопасную границу по странице.
const promises = [
  "Без пополнений",
  "Без покупок",
  "Без вывода",
  "Без обмена",
  "Без призов",
  "Без передачи ценности",
];

// Цифры первого экрана не подключаются к живому состоянию приложения казино.
const proofPoints = [
  ["25+", "игр в стиле казино в плане симулятора"],
  ["0", "пополнений, вывода, призов и денежных сценариев"],
  ["24/7", "ощущение приватной лаборатории для ботов, раундов и проверок"],
];

// Отрисовать русскую версию приватного маркетингового превью TiltSeven.
export default function RussianHome() {
  return (
    <main className="site-shell" data-testid="tiltseven-preview">
      {/* Шапка сохраняет разделение витрины, приложения и языкового переключения. */}
      <header className="topbar" aria-label="TiltSeven">
        <a className="brand-lockup" href="/ru" aria-label="Главная TiltSeven">
          <img src="/tiltseven-mark.svg" alt="" width="56" height="56" />
          <span>
            <strong>TiltSeven</strong>
            <small>Приватный просмотр · только игровые жетоны</small>
          </span>
        </a>
        <nav className="nav-links" aria-label="Основная навигация">
          <a href="#floor">Игры</a>
          <a href="#safety">Безопасность</a>
          <a href="#preview">Стиль</a>
          <a href="/" hrefLang="en">
            English
          </a>
          <a className="pill-link" href="https://casino.tiltseven.com/">
            Открыть казино
          </a>
        </nav>
      </header>

      {/* Первый экран задаёт премиальный тон и повторяет границу симулятора. */}
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Первый приватный просмотр</p>
          <h1>Казино как стильный программный симулятор.</h1>
          <p className="lede">
            TiltSeven добавляет к атмосфере игрового зала премиальную
            программную основу: столы, барабаны, колёса, карты, боты и журнал
            раундов — только с игровыми жетонами без денежной ценности.
          </p>
          <div className="hero-actions" aria-label="Основные действия">
            <a className="button primary" href="https://casino.tiltseven.com/">
              Открыть казино
            </a>
            <a className="button secondary" href="#safety">
              Прочитать правила безопасности
            </a>
          </div>
          <dl className="hero-proof" aria-label="Особенности приватного просмотра TiltSeven">
            {proofPoints.map(([value, label]) => (
              <div key={value}>
                <dt>{value}</dt>
                <dd>{label}</dd>
              </div>
            ))}
          </dl>
          <p className="fine-print">{promises.join(". ")}.</p>
        </div>
        <div className="hero-stage" aria-label="Стилизованное превью казино">
          <div className="card-topline">
            <span>Превью зала</span>
            <span>Только игровые жетоны</span>
          </div>
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
          <div className="live-strip" aria-hidden="true">
            <span>Раунды</span>
            <strong>Журнал учёта</strong>
            <span>Боты готовы</span>
          </div>
        </div>
      </section>

      {/* Карточки продукта описывают симулятор без подключения к приложению. */}
      <section id="floor" className="section">
        <div className="section-heading">
          <p className="eyebrow">Казино как программный симулятор</p>
          <h2>Стильная витрина для управляемого симулятора.</h2>
        </div>
        <div className="feature-grid">
          <article>
            <span className="card-number">01</span>
            <h3>Настольные игры</h3>
            <p>
              Рулетка, Блэкджек, Баккара, Casino War, Dragon Tiger, Сик Бо и
              другие игры представлены как единый зал, а не таблица данных.
            </p>
          </article>
          <article>
            <span className="card-number">02</span>
            <h3>Барабаны и розыгрыши</h3>
            <p>
              Слоты, Кено, Бинго, скретч-карты и колёса с понятными этапами
              раунда, воспроизводимыми результатами и языком симулятора.
            </p>
          </article>
          <article>
            <span className="card-number">03</span>
            <h3>Учёт игровых жетонов</h3>
            <p>
              Каждое движение жетонов записывается в журнал симулятора, чтобы
              тесты, боты и администраторы видели историю без намёка на
              денежную ценность.
            </p>
          </article>
        </div>
      </section>

      {/* Блок опыта фиксирует настроение первого просмотра. */}
      <section className="section experience" aria-label="Основные ощущения TiltSeven">
        <div className="experience-copy">
          <p className="eyebrow">Каким должен быть первый просмотр</p>
          <h2>Премиально, спокойно и явно без реальных денег.</h2>
        </div>
        <div className="experience-rail">
          <article>
            <strong>Атмосфера приватного клуба</strong>
            <p>
              Полуночное сукно, тёплый свет и уверенные интервалы создают
              взрослое настроение казино.
            </p>
          </article>
          <article>
            <strong>Ясность симулятора</strong>
            <p>
              Каждый крупный раздел повторяет границу игровых жетонов до
              перехода в Casino.
            </p>
          </article>
          <article>
            <strong>Отдельная линия приложения</strong>
            <p>
              Маркетинговая витрина остаётся отделённой от управляемого
              рантайма казино.
            </p>
          </article>
        </div>
      </section>

      {/* Панель безопасности делает границу игровых жетонов заметной. */}
      <section id="safety" className="safety-panel">
        <div>
          <p className="eyebrow">Чёткая граница</p>
          <h2>Атмосфера казино, правила симулятора.</h2>
        </div>
        <ul>
          {promises.map((promise) => (
            <li key={promise}>{promise}</li>
          ))}
        </ul>
      </section>

      {/* Финальный блок переводит визуальный стиль в короткие ревью-точки. */}
      <section id="preview" className="section preview-grid">
        <div className="section-heading">
          <p className="eyebrow">Визуальное направление</p>
          <h2>Полуночный зелёный, тёплое золото, яркий красный и наклонённая семёрка.</h2>
          <p>
            Эта первая версия представляет публичный бренд TiltSeven, ведёт
            посетителей в отдельное виртуальное казино и не меняет DNS,
            биллинг, провайдеров или деплой самого Casino.
          </p>
        </div>
        <div className="stat-card">
          <strong>01</strong>
          <span>приватная линия превью</span>
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
