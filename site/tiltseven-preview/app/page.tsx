import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TiltSeven — Play the casino floor, without the stakes",
  description:
    "TiltSeven is a private play-token casino simulator: casino-floor atmosphere, no cash value, no deposits, and no withdrawals.",
};

const games = [
  "Roulette",
  "Blackjack",
  "Baccarat",
  "Slots",
  "Keno",
  "Bingo",
  "Sic Bo",
  "Video poker",
];

const promises = [
  "No deposits",
  "No purchases",
  "No withdrawals",
  "No redemption",
  "No prizes",
  "No transferable value",
];

export default function Home() {
  return (
    <main className="site-shell">
      <header className="topbar" aria-label="TiltSeven">
        <a className="brand-lockup" href="/" aria-label="TiltSeven home">
          <img src="/tiltseven-mark.svg" alt="" width="56" height="56" />
          <span>
            <strong>TiltSeven</strong>
            <small>Play tokens only · no cash value</small>
          </span>
        </a>
        <nav className="nav-links" aria-label="Primary navigation">
          <a href="#floor">The floor</a>
          <a href="#safety">Safety</a>
          <a href="#preview">Preview</a>
          <a href="/ru" lang="ru" hrefLang="ru">
            Русский
          </a>
          <a className="pill-link" href="https://casino.tiltseven.com/">
            Enter casino
          </a>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Private play-token casino simulator</p>
          <h1>Play the casino floor, without the stakes.</h1>
          <p className="lede">
            TiltSeven turns casino atmosphere into a polished simulator: tables,
            reels, wheels, cards, bots, and ledger-backed fake tokens that never
            become money or prizes.
          </p>
          <div className="hero-actions" aria-label="Primary actions">
            <a className="button primary" href="https://casino.tiltseven.com/">
              Enter casino
            </a>
            <a className="button secondary" href="#safety">
              Read the safety promise
            </a>
          </div>
          <p className="fine-print">{promises.join(". ")}.</p>
        </div>
        <div className="hero-stage" aria-label="Stylized casino preview">
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
          <p className="eyebrow">A casino floor as software</p>
          <h2>Built for exploring games, not spending money.</h2>
        </div>
        <div className="feature-grid">
          <article>
            <h3>Table energy</h3>
            <p>
              Roulette, Blackjack, Baccarat, Dragon Tiger, Sic Bo, and more feel
              like a floor map instead of a spreadsheet.
            </p>
          </article>
          <article>
            <h3>Replayable outcomes</h3>
            <p>
              Rounds are ledger-backed, inspectable, and safe to replay because
              every token is fake and every state is bounded.
            </p>
          </article>
          <article>
            <h3>Admin clarity</h3>
            <p>
              Operations, reports, profiles, and recovery tools stay separated
              from the marketing site and from any real-money implication.
            </p>
          </article>
        </div>
      </section>

      <section id="safety" className="safety-panel">
        <div>
          <p className="eyebrow">Safety promise</p>
          <h2>Casino feeling. Simulator boundaries.</h2>
        </div>
        <ul>
          {promises.map((promise) => (
            <li key={promise}>{promise}</li>
          ))}
        </ul>
      </section>

      <section id="preview" className="section preview-grid">
        <div className="section-heading">
          <p className="eyebrow">First look</p>
          <h2>A brand page now, a deeper public site next.</h2>
          <p>
            This first version introduces the TiltSeven brand, routes visitors
            to the live virtual casino, and keeps publishing, DNS, billing, and
            provider changes out of scope until separately approved.
          </p>
        </div>
        <div className="stat-card">
          <strong>30</strong>
          <span>simulated games</span>
        </div>
        <div className="stat-card">
          <strong>0</strong>
          <span>cash-value mechanics</span>
        </div>
        <div className="stat-card">
          <strong>2</strong>
          <span>baseline languages</span>
        </div>
      </section>
    </main>
  );
}
