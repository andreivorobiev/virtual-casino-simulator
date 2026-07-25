import type { Metadata } from "next";

// Page metadata describes the private preview without implying public launch.
export const metadata: Metadata = {
  title: "TiltSeven — Private play-token casino simulator",
  description:
    "TiltSeven is a private play-token casino simulator with casino-floor energy, ledger-backed rounds, no cash value, no deposits, and no withdrawals.",
};

// List the first visible game labels used in the decorative floor preview.
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

// Keep the no-cash-value safety promise reusable across the page.
const promises = [
  "No deposits",
  "No purchases",
  "No withdrawals",
  "No redemption",
  "No prizes",
  "No transferable value",
];

// Define the above-the-fold proof points without connecting to live casino state.
const proofPoints = [
  ["25+", "casino-style games in the simulator roadmap"],
  ["0", "deposits, withdrawals, prizes, or cash-out flows"],
  ["24/7", "private software-lab feel for bots, rounds, and reviews"],
];

// Render the polished English landing page for the private TiltSeven preview.
export default function Home() {
  return (
    <main className="site-shell" data-testid="tiltseven-preview">
      {/* Header preserves the marketing/app separation and locale switch. */}
      <header className="topbar" aria-label="TiltSeven">
        <a className="brand-lockup" href="/" aria-label="TiltSeven home">
          <img src="/tiltseven-mark.svg" alt="" width="56" height="56" />
          <span>
            <strong>TiltSeven</strong>
            <small>Private preview · play tokens only</small>
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

      {/* Hero introduces the premium simulator feeling before any casino link. */}
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">First-look private preview</p>
          <h1>The casino floor, sharpened into a simulator.</h1>
          <p className="lede">
            TiltSeven gives the floor a premium software spine: tables, reels,
            wheels, cards, bots, and ledger-backed rounds — all powered by play
            tokens with no cash value.
          </p>
          <div className="hero-actions" aria-label="Primary actions">
            <a className="button primary" href="https://casino.tiltseven.com/">
              Enter casino
            </a>
            <a className="button secondary" href="#safety">
              Read the safety promise
            </a>
          </div>
          <dl className="hero-proof" aria-label="TiltSeven preview highlights">
            {proofPoints.map(([value, label]) => (
              <div key={value}>
                <dt>{value}</dt>
                <dd>{label}</dd>
              </div>
            ))}
          </dl>
          <p className="fine-print">{promises.join(". ")}.</p>
        </div>
        <div className="hero-stage" aria-label="Stylized casino preview">
          <div className="card-topline">
            <span>Live floor preview</span>
            <span>Play tokens only</span>
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
            <span>Rounds</span>
            <strong>Ledger-backed</strong>
            <span>Bot-ready</span>
          </div>
        </div>
      </section>

      {/* Product cards explain the governed simulator without adding app dependencies. */}
      <section id="floor" className="section">
        <div className="section-heading">
          <p className="eyebrow">A casino floor as software</p>
          <h2>A polished front door for a governed simulator.</h2>
        </div>
        <div className="feature-grid">
          <article>
            <span className="card-number">01</span>
            <h3>Table games</h3>
            <p>
              Roulette, Blackjack, Baccarat, Casino War, Dragon Tiger, Sic Bo,
              and more are staged like a real floor map, not a spreadsheet.
            </p>
          </article>
          <article>
            <span className="card-number">02</span>
            <h3>Reels and draws</h3>
            <p>
              Slots, Keno, Bingo, Scratch Cards, and wheel games get clear round
              states, replayable outcomes, and simulator-first language.
            </p>
          </article>
          <article>
            <span className="card-number">03</span>
            <h3>Ledger-backed play</h3>
            <p>
              Every token movement belongs to a fake-money ledger so testing,
              bots, and admin review can see what happened without implying cash
              value.
            </p>
          </article>
        </div>
      </section>

      {/* Experience strip captures the intended first-version mood. */}
      <section className="section experience" aria-label="TiltSeven experience pillars">
        <div className="experience-copy">
          <p className="eyebrow">What the first version should feel like</p>
          <h2>Premium, calm, and unmistakably fake-money.</h2>
        </div>
        <div className="experience-rail">
          <article>
            <strong>Private club mood</strong>
            <p>
              Midnight felt, warm light, and confident spacing give the page a
              grown-up casino atmosphere.
            </p>
          </article>
          <article>
            <strong>Simulator clarity</strong>
            <p>
              Every major section repeats the play-token boundary before
              visitors reach the Casino link.
            </p>
          </article>
          <article>
            <strong>Separate app lane</strong>
            <p>
              The marketing surface stays separate from the governed casino
              application runtime.
            </p>
          </article>
        </div>
      </section>

      {/* Safety panel keeps the no-cash-value boundary unmissable. */}
      <section id="safety" className="safety-panel">
        <div>
          <p className="eyebrow">The bright line</p>
          <h2>Casino feel, simulator boundary.</h2>
        </div>
        <ul>
          {promises.map((promise) => (
            <li key={promise}>{promise}</li>
          ))}
        </ul>
      </section>

      {/* Preview section gives the brand direction in compact, reviewable terms. */}
      <section id="preview" className="section preview-grid">
        <div className="section-heading">
          <p className="eyebrow">Brand direction</p>
          <h2>Midnight green, warm gold, sharp red, and a tilted seven.</h2>
          <p>
            This first version introduces the TiltSeven public brand, routes
            visitors to the separate virtual casino, and keeps DNS, billing,
            provider, and casino deployment changes out of this preview lane.
          </p>
        </div>
        <div className="stat-card">
          <strong>01</strong>
          <span>private preview lane</span>
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
