// The decoration behind every screen (DESIGN.md, signature components): pixel clouds on Day,
// and on Night a starry sky seen from a cave mouth, where constellations shaped like system
// diagrams come and go and the odd shooting star crosses. CSS shows the layer that matches
// <html data-theme>; it never takes pointer events and is hidden from assistive technology.
import styles from "./Sky.module.css";

type Constellation = { name: string; path: string; stars: [number, number][]; warm: number; className: string };

const CONSTELLATIONS: Constellation[] = [
  {
    name: "The Load Balancer",
    path: "M20 22H160L128 84H52ZM90 22V84",
    stars: [[20, 22], [160, 22], [128, 84], [52, 84]],
    warm: 2,
    className: styles.conA,
  },
  {
    name: "The Ticket",
    path: "M20 20H150V44Q138 50 150 56V80H20V56Q32 50 20 44Z",
    stars: [[20, 20], [150, 20], [150, 80], [20, 80]],
    warm: 1,
    className: styles.conB,
  },
  {
    name: "The Queue",
    path: "M14 50H144",
    stars: [[14, 50], [44, 50], [64, 50], [94, 50], [114, 50], [144, 50]],
    warm: 5,
    className: styles.conC,
  },
];

const CLOUD = "M8 8h24v8H8zM16 0h12v8H16zM0 16h48v8H0z";

export function Sky() {
  return (
    <div className={styles.sky} aria-hidden="true">
      <div className={styles.day}>
        {[styles.cloudA, styles.cloudB, styles.cloudC].map((cls) => (
          <svg key={cls} className={`${styles.pix} ${styles.cloud} ${cls}`} width="96" height="48" viewBox="0 0 48 24">
            <path fill="#1E5E99" d="M0 22h48v2H0z" />
            <path fill="#FFFFFF" d={CLOUD} />
          </svg>
        ))}
      </div>
      <div className={styles.night}>
        <svg className={styles.pix} width="100%" height="100%">
          <defs>
            <pattern id="sky-stars-a" width="173" height="131" patternUnits="userSpaceOnUse">
              <rect x="12" y="18" width="2" height="2" fill="#EAF2FF" />
              <rect x="97" y="7" width="2" height="2" fill="#C9D6F0" />
              <rect x="141" y="64" width="2" height="2" fill="#EAF2FF" />
              <rect x="58" y="92" width="2" height="2" fill="#AFC0E6" />
            </pattern>
            <pattern id="sky-stars-b" width="211" height="157" patternUnits="userSpaceOnUse">
              <rect x="33" y="51" width="2" height="2" fill="#FFF4C9" />
              <rect x="172" y="22" width="3" height="3" fill="#EAF2FF" />
              <rect x="88" y="139" width="2" height="2" fill="#C9D6F0" />
            </pattern>
          </defs>
          <rect className={styles.twinkleA} width="100%" height="100%" fill="url(#sky-stars-a)" />
          <rect className={styles.twinkleB} width="100%" height="100%" fill="url(#sky-stars-b)" />
        </svg>
        {CONSTELLATIONS.map((c) => (
          <svg key={c.name} className={`${styles.pix} ${styles.constellation} ${c.className}`} width="190" height="120" viewBox="0 0 190 120">
            <path d={c.path} fill="none" stroke="#8DA2D6" strokeDasharray="2 3" />
            {c.stars.map(([x, y], i) => (
              <rect key={`${x}-${y}`} x={x - 2} y={y - 2} width="4" height="4" fill={i === c.warm ? "#FFF4C9" : "#EAF2FF"} />
            ))}
            <text x="20" y="108" fill="#8193B5" fontFamily="var(--font-silk)" fontSize="9">
              {c.name}
            </text>
          </svg>
        ))}
        {[styles.shootA, styles.shootB].map((cls) => (
          <svg key={cls} className={`${styles.pix} ${styles.shoot} ${cls}`} width="64" height="34" viewBox="0 0 64 34">
            <rect width="4" height="4" fill="#FFFFFF" />
            <rect x="6" y="3" width="6" height="2" fill="#EAF2FF" opacity=".8" />
            <rect x="14" y="7" width="10" height="2" fill="#C9D6F0" opacity=".55" />
            <rect x="26" y="13" width="14" height="2" fill="#8DA2D6" opacity=".35" />
            <rect x="42" y="21" width="18" height="2" fill="#8DA2D6" opacity=".18" />
          </svg>
        ))}
        <svg className={`${styles.pix} ${styles.rockTop}`} width="100%" height="44">
          <defs>
            <pattern id="cave-top" width="120" height="44" patternUnits="userSpaceOnUse">
              <path fill="#04050B" d="M0 0h120v18H0zM6 18h14v10H6zM10 28h6v8h-6zM34 18h22v6H34zM74 18h10v14H74zM76 32h6v8h-6zM96 18h18v8H96z" />
              <path fill="#1B2448" d="M0 16h6v2H0zM20 16h14v2H20zM56 16h18v2H56zM84 16h12v2H84zM114 16h6v2h-6z" />
            </pattern>
          </defs>
          <rect width="100%" height="44" fill="url(#cave-top)" />
        </svg>
        <svg className={`${styles.pix} ${styles.rockFloor}`} width="100%" height="34">
          <defs>
            <pattern id="cave-floor" width="140" height="34" patternUnits="userSpaceOnUse">
              <path fill="#04050B" d="M0 16h140v18H0zM10 8h26v8H10zM18 2h12v6H18zM58 12h30v4H58zM96 6h14v10H96zM120 12h20v4h-20z" />
              <path fill="#1B2448" d="M0 14h10v2H0zM10 6h8v2h-8zM18 0h12v2H18zM36 14h22v2H36zM58 10h30v2H58zM110 14h10v2h-10zM120 10h20v2h-20z" />
            </pattern>
          </defs>
          <rect width="100%" height="34" fill="url(#cave-floor)" />
        </svg>
        <div className={`${styles.wall} ${styles.wallLeft}`} />
        <div className={`${styles.wall} ${styles.wallRight}`} />
      </div>
    </div>
  );
}
