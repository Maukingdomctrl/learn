// Pen-and-pencil sketch library. Every picture is drawn by code: black lines, white fill, same output every time.
// A picture is chosen by words in the fact. If nothing fits, the card gets a "draw it yourself" box instead:
// no picture is better than a wrong one.

const P = '#fbfaf7'; // paper
export const VIEWBOX = '0 0 170 110';

const waves = (y, x0 = 10, x1 = 160, h = 5) => {
  let d = `M${x0} ${y}`;
  for (let x = x0; x < x1; x += 16) d += ` q4 ${-h} 8 0 q4 ${h} 8 0`;
  return `<path d="${d}" stroke-width="1.8"/>`;
};

const crenels = (x0, x1, y, w = 6, h = 6) => {
  let d = `M${x0} ${y + h}`;
  for (let x = x0; x < x1; x += w * 2) d += ` V${y} H${Math.min(x + w, x1)} V${y + h} H${Math.min(x + 2 * w, x1)}`;
  return `<path d="${d} V${y + h}" />`;
};

const columns = (xs, y0, y1) => xs.map((x) => `<path d="M${x} ${y0} V${y1} M${x + 6} ${y0} V${y1}" stroke-width="1.8"/>`).join('');

const polar = (cx, cy, r, deg) => {
  const a = (deg * Math.PI) / 180;
  return [(cx + r * Math.cos(a)).toFixed(1), (cy + r * Math.sin(a)).toFixed(1)];
};

const sword = `<path d="M85 8 L90 18 V68 H80 V18 Z" fill="${P}"/><path d="M68 68 H102" stroke-width="3.4"/>
  <path d="M85 68 V86" stroke-width="3.4"/><circle cx="85" cy="90" r="4" fill="${P}"/>`;

export const ART = {
  sword() {
    return `<g transform="rotate(38 85 55)">${sword}</g><g transform="rotate(-38 85 55)">${sword}</g>`;
  },
  scroll() {
    return `<path d="M54 28 H118 V84 H54 Z" fill="${P}"/>
      <rect x="46" y="20" width="80" height="11" rx="5.5" fill="${P}"/><rect x="46" y="81" width="80" height="11" rx="5.5" fill="${P}"/>
      <path d="M64 44 H110 M64 52 H110 M64 60 H102 M64 68 H92" stroke-width="1.4"/>
      <circle cx="106" cy="71" r="6" fill="currentColor"/>`;
  },
  rifle() {
    let rounds = '';
    [60, 78, 96].forEach((x) => (rounds += `<path d="M${x} 98 V88 Q${x + 4} 80 ${x + 8} 88 V98 Z" fill="${P}" stroke-width="1.6"/>`));
    return `<path d="M56 50 H156" stroke-width="4"/><path d="M150 46 V50" stroke-width="2"/>
      <path d="M26 56 H122 V64 H66 L50 78 H28 L36 64 H26 Z" fill="${P}"/><path d="M74 64 Q76 72 84 72" stroke-width="1.8"/>
      ${rounds}`;
  },
  scales() {
    return `<path d="M85 20 V92 M62 96 H108" /><circle cx="85" cy="18" r="3.5" fill="currentColor"/>
      <path d="M44 32 H126" /><path d="M44 32 L30 62 M44 32 L58 62 M126 32 L112 62 M126 32 L140 62" stroke-width="1.5"/>
      <path d="M26 62 H62 Q44 80 26 62 Z" fill="${P}"/><path d="M108 62 H144 Q126 80 108 62 Z" fill="${P}"/>`;
  },
  person() {
    return `<circle cx="85" cy="36" r="16" fill="${P}"/>
      <path d="M50 98 Q50 60 85 60 Q120 60 120 98 Z" fill="${P}"/><path d="M85 60 L78 74 L85 98 L92 74 Z" stroke-width="1.4"/>`;
  },
  ship() {
    let f = '';
    [56, 76, 96, 116].forEach((x, i) => {
      f += `<path d="M${x} 57 L${x + 2} 36 H${x + 13} L${x + 13} 57" fill="${P}"/><path d="M${x + 1.7} 42 H${x + 13}"/>`;
      if (i < 3) f += `<path d="M${x + 8} 33 q-5 -6 1 -10 q6 -4 1 -10" stroke-width="1.5"/>`;
    });
    let ports = '';
    for (let x = 36; x <= 134; x += 10) ports += `<circle cx="${x}" cy="72" r="1.6" fill="currentColor" stroke="none"/>`;
    return `<path d="M30 66 L28 26 M142 66 L145 28" stroke-width="1.5"/><path d="M28 26 L145 28" stroke-width="1"/>
      ${f}<path d="M38 66 V57 H134 V66" fill="${P}"/>
      <path d="M16 66 H154 L142 85 H30 Z" fill="${P}"/>${ports}${waves(94)}`;
  },
  river() {
    return `<path d="M6 34 Q46 22 82 38 T164 30" /><path d="M6 80 Q46 68 82 84 T164 76" />
      <path d="M20 50 q5 -4 10 0 q5 4 10 0 M64 60 q5 -4 10 0 q5 4 10 0 M108 52 q5 -4 10 0 q5 4 10 0 M40 66 q5 -4 10 0 q5 4 10 0 M128 66 q5 -4 10 0 q5 4 10 0" stroke-width="1.6"/>
      <path d="M14 30 l-4 -10 M24 27 l-2 -12 M146 26 l2 -12 M156 28 l5 -10 M30 86 l-3 10 M140 82 l3 10" stroke-width="1.3"/>`;
  },
  crown() {
    return `<path d="M45 78 L38 34 L63 56 L85 24 L107 56 L132 34 L125 78 Z" fill="${P}"/>
      <path d="M45 78 H125 V92 H45 Z" fill="${P}"/>
      <circle cx="38" cy="32" r="4.5" fill="${P}"/><circle cx="85" cy="21" r="4.5" fill="${P}"/><circle cx="132" cy="32" r="4.5" fill="${P}"/>
      <circle cx="65" cy="85" r="3"/><circle cx="85" cy="85" r="3.6" fill="currentColor"/><circle cx="105" cy="85" r="3"/>`;
  },
  factory() {
    let win = '';
    [28, 52, 76].forEach((x) => (win += `<rect x="${x}" y="74" width="9" height="9"/>`));
    const teeth = [0, 45, 90, 135, 180, 225, 270, 315]
      .map((a) => {
        const [x1, y1] = polar(145, 72, 11, a);
        const [x2, y2] = polar(145, 72, 15, a);
        return `<path d="M${x1} ${y1} L${x2} ${y2}" stroke-width="3"/>`;
      })
      .join('');
    return `<path d="M10 92 H160"/><path d="M18 92 V58 L42 68 V58 L66 68 V58 L90 68 V92 Z" fill="${P}"/>${win}
      <path d="M100 92 V32 H113 V92 Z M122 92 V44 H133 V92 Z" fill="${P}"/>
      <circle cx="110" cy="22" r="6"/><circle cx="121" cy="14" r="8"/><circle cx="136" cy="10" r="6"/><circle cx="130" cy="34" r="5"/><circle cx="142" cy="28" r="6"/>
      <circle cx="145" cy="72" r="11" fill="${P}"/><circle cx="145" cy="72" r="4"/>${teeth}`;
  },
  steam() {
    return `<path d="M10 94 H160" /><path d="M14 98 H156" stroke-width="1.2"/>
      <path d="M40 80 V50 H104 V80 Z" fill="${P}"/><path d="M104 80 V34 H138 V80 Z" fill="${P}"/><rect x="112" y="42" width="18" height="14"/>
      <path d="M52 50 V28 H64 V50" fill="${P}"/><path d="M50 28 H66" stroke-width="3"/>
      <path d="M30 80 H146" /><path d="M40 72 L28 88" />
      <circle cx="58" cy="86" r="8" fill="${P}"/><circle cx="84" cy="86" r="8" fill="${P}"/><circle cx="122" cy="84" r="10" fill="${P}"/>
      <path d="M58 86 L122 84" stroke-width="1.6"/>
      <circle cx="62" cy="18" r="6"/><circle cx="76" cy="12" r="7"/><circle cx="92" cy="10" r="5"/>`;
  },
  plane() {
    return `<path d="M66 50 L82 24 H92 L86 50 M66 62 L82 88 H92 L86 62" fill="${P}"/>
      <path d="M24 56 Q26 49 42 49 H110 Q126 51 128 56 Q126 61 110 63 H42 Q26 63 24 56 Z" fill="${P}"/>
      <path d="M40 49 L32 34 H40 L52 49" fill="${P}"/>
      ${[56, 66, 76, 96, 104].map((x) => `<circle cx="${x}" cy="55" r="1.6" fill="currentColor" stroke="none"/>`).join('')}
      <path d="M12 48 h8 M8 56 h10 M12 64 h8" stroke-width="1.4"/>
      <path d="M140 94 V52 Q146 36 152 52 V94 Z" fill="${P}"/><path d="M140 84 L132 98 L140 94 M152 84 L160 98 L152 94" fill="${P}"/>
      <circle cx="146" cy="64" r="3.4"/><path d="M142 98 q4 10 4 10 q0 0 4 -10" stroke-width="1.6"/>`;
  },
  museum() {
    return `<path d="M28 44 L85 16 L142 44 Z" fill="${P}"/><path d="M28 44 H142 V52 H28 Z" fill="${P}"/>
      <path d="M78 34 h14 M85 27 v14" stroke-width="1.4"/>
      ${columns([38, 54, 110, 126], 52, 86)}<path d="M72 86 V66 Q85 54 98 66 V86"/><path d="M22 86 H148 M16 94 H154"/>`;
  },
  bank() {
    return `<path d="M28 42 L85 14 L142 42 Z" fill="${P}"/><path d="M28 42 H142 V50 H28 Z" fill="${P}"/>
      <circle cx="85" cy="32" r="7"/><text x="85" y="36" text-anchor="middle" font-size="11" font-family="Georgia, serif" fill="currentColor" stroke="none">£</text>
      ${columns([36, 58, 80, 102, 124], 50, 86)}<path d="M22 86 H148 M16 94 H154"/>`;
  },
  gear() {
    let d = '';
    const n = 10;
    for (let i = 0; i < n * 2; i++) {
      const rad = i % 2 ? 23 : 30;
      const [x0, y0] = polar(85, 54, rad, (i / (n * 2)) * 360);
      const [x1, y1] = polar(85, 54, rad, ((i + 1) / (n * 2)) * 360);
      d += `${i ? 'L' : 'M'}${x0} ${y0} L${x1} ${y1} `;
    }
    return `<path d="${d}Z" fill="${P}"/><circle cx="85" cy="54" r="9"/><circle cx="85" cy="54" r="3" fill="currentColor"/>
      <path d="M22 40 h22 M16 54 h24 M22 68 h22 M126 40 h22 M130 54 h24 M126 68 h22" stroke-width="1.6"/>
      <path d="M50 98 H120" stroke-width="1.5"/>`;
  },
  people() {
    let g = '';
    const person = (x, y, s) =>
      `<circle cx="${x}" cy="${y}" r="${5 * s}" fill="${P}"/><path d="M${x - 9 * s} ${y + 17 * s} q0 -10 ${9 * s} -10 q${9 * s} 0 ${9 * s} 10" fill="${P}"/>`;
    [[30, 26], [56, 22], [82, 26], [108, 22], [134, 26]].forEach(([x, y]) => (g += person(x, y, 0.8)));
    [[18, 50], [44, 46], [70, 50], [96, 46], [122, 50], [148, 46]].forEach(([x, y]) => (g += person(x, y, 1)));
    [[32, 74], [60, 72], [88, 74], [116, 72], [142, 74]].forEach(([x, y]) => (g += person(x, y, 1.15)));
    return g;
  },
  jobs() {
    return `<path d="M50 78 V20" /><path d="M53 24 L53 72 L84 72 Z" fill="${P}"/>
      <path d="M59 34 V72 M65 44 V72 M71 52 V72 M77 62 V72 M53 46 H66 M53 58 H75" stroke-width="1.1"/>
      <path d="M18 78 H86 L77 90 H27 Z" fill="${P}"/>
      <circle cx="122" cy="40" r="17" fill="${P}"/><circle cx="122" cy="40" r="11.5"/><circle cx="122" cy="40" r="6"/><path d="M139 40 q10 4 10 16" />
      <path d="M108 80 h14 v7 q0 7 -7 7 q-7 0 -7 -7 Z" fill="${P}"/><path d="M122 83 L150 76" stroke-width="2.6"/>
      <path d="M113 76 q-5 -6 1 -10 q6 -4 1 -10" stroke-width="1.4"/>${waves(98, 10, 96, 3)}`;
  },
  theatre() {
    return `<path d="M44 26 H96 V58 Q96 84 70 88 Q44 84 44 58 Z" fill="${P}"/>
      <path d="M54 46 q5 -5 10 0 M76 46 q5 -5 10 0" /><path d="M56 64 Q70 76 84 64" />
      <path d="M80 36 H128 V66 Q128 92 104 96 Q80 92 80 66 Z" fill="${P}"/>
      <path d="M88 56 q5 5 10 0 M110 56 q5 5 10 0" /><path d="M92 82 Q104 72 116 82" />
      <path d="M44 32 Q30 34 22 46 M128 42 Q142 46 150 58" stroke-width="1.5"/>`;
  },
  castle() {
    return `<path d="M10 94 H160"/>
      <path d="M28 94 V40 H56 V94 Z M114 94 V40 H142 V94 Z" fill="${P}"/>
      <path d="M56 94 V58 H114 V94 Z" fill="${P}"/>
      ${crenels(28, 56, 34)}${crenels(114, 142, 34)}${crenels(56, 114, 52, 5, 6)}
      <path d="M74 94 V76 Q85 64 96 76 V94" fill="${P}"/>
      <path d="M38 54 v8 M46 54 v8 M124 54 v8 M132 54 v8" stroke-width="1.6"/>
      <path d="M128 34 V16 L142 21 L128 26" fill="${P}" stroke-width="1.6"/>`;
  },
  parliament() {
    return `<path d="M85 20 V12" stroke-width="1.6"/><circle cx="85" cy="10" r="2.4" fill="currentColor"/><path d="M79 30 V20 H91 V30" fill="${P}"/>
      <path d="M57 56 Q57 30 85 30 Q113 30 113 56 Z" fill="${P}"/><path d="M70 56 Q72 38 85 34 M100 56 Q98 38 85 34" stroke-width="1.2"/>
      <path d="M26 56 H144 V64 H26 Z" fill="${P}"/>
      ${columns([34, 52, 70, 94, 112, 130], 64, 88)}<path d="M20 88 H150 M14 96 H156"/>`;
  },
  coal() {
    return `<path d="M8 98 H162" /><path d="M8 102 H162" stroke-width="1.2"/>
      <path d="M40 54 H130 L122 86 H48 Z" fill="${P}"/>
      <path d="M48 54 L56 40 L68 46 L78 34 L92 42 L104 36 L114 46 L124 54 Z" fill="currentColor"/>
      <circle cx="62" cy="91" r="7" fill="${P}"/><circle cx="108" cy="91" r="7" fill="${P}"/>
      <path d="M52 64 H118 M54 74 H116" stroke-width="1.2"/>`;
  },
  bulb() {
    const rays = [200, 235, 270, 305, 340]
      .map((a) => {
        const [x1, y1] = polar(85, 44, 30, a);
        const [x2, y2] = polar(85, 44, 40, a);
        return `<path d="M${x1} ${y1} L${x2} ${y2}" stroke-width="1.8"/>`;
      })
      .join('');
    return `${rays}<path d="M74 66 Q60 56 63 40 Q67 22 85 22 Q103 22 107 40 Q110 56 96 66 Z" fill="${P}"/>
      <path d="M78 66 L80 50 L85 56 L90 50 L92 66" stroke-width="1.5"/>
      <path d="M74 66 H96 V82 H74 Z" fill="${P}"/><path d="M74 72 H96 M74 77 H96" stroke-width="1.4"/><path d="M80 82 Q85 90 90 82" />`;
  },
  calendar() {
    let dots = '';
    for (let r = 0; r < 3; r++) for (let c = 0; c < 5; c++) dots += `<circle cx="${60 + c * 12.5}" cy="${54 + r * 12}" r="1.8" fill="currentColor" stroke="none"/>`;
    return `<path d="M48 24 H122 V94 H48 Z" fill="${P}"/><path d="M48 38 H122" /><path d="M66 18 V30 M104 18 V30" stroke-width="3"/>
      ${dots}<circle cx="97.5" cy="78" r="7"/>`;
  },
  globe() {
    return `<circle cx="85" cy="52" r="34" fill="${P}"/><ellipse cx="85" cy="52" rx="14" ry="34" /><ellipse cx="85" cy="52" rx="27" ry="34" stroke-width="1.3"/>
      <path d="M51 52 H119" /><path d="M56 36 Q85 42 114 36 M56 68 Q85 62 114 68" stroke-width="1.3"/>
      <path d="M85 86 V96 M66 98 H104" />`;
  },
  camera() {
    return `<path d="M40 40 H66 L72 30 H98 L104 40 H130 V88 H40 Z" fill="${P}"/>
      <circle cx="85" cy="63" r="17" fill="${P}"/><circle cx="85" cy="63" r="9"/><path d="M80 58 q3 -3 6 -2" stroke-width="1.4"/>
      <rect x="114" y="47" width="10" height="6"/><path d="M48 34 H60" stroke-width="3"/>`;
  },
  book() {
    return `<path d="M85 34 Q62 24 32 30 V86 Q62 80 85 90 Z" fill="${P}"/><path d="M85 34 Q108 24 138 30 V86 Q108 80 85 90 Z" fill="${P}"/>
      <path d="M42 42 Q60 38 76 44 M42 54 Q60 50 76 56 M42 66 Q60 62 76 68 M94 44 Q110 38 128 42 M94 56 Q110 50 128 54 M94 68 Q110 62 128 66" stroke-width="1.2"/>
      <path d="M85 34 V90" />`;
  },
  pin() {
    return `<path d="M20 88 L56 76 L96 88 L150 74" stroke-width="1.4"/><path d="M20 98 L56 86 L96 98 L150 84" stroke-width="1.2"/>
      <path d="M85 86 C74 70 64 58 64 44 A21 21 0 1 1 106 44 C106 58 96 70 85 86 Z" fill="${P}"/><circle cx="85" cy="44" r="8"/>`;
  },
  market() {
    let scallops = 'M36 40';
    for (let x = 36; x < 134; x += 14) scallops += ` q7 10 14 0`;
    return `<path d="M36 40 L44 22 H126 L134 40 Z" fill="${P}"/><path d="${scallops}" fill="${P}"/>
      <path d="M58 22 L54 40 M72 22 L71 40 M86 22 L86 40 M100 22 L101 40 M114 22 L118 40" stroke-width="1.3"/>
      <path d="M44 48 V92 M126 48 V92" /><path d="M36 70 H134 V78 H36 Z" fill="${P}"/>
      <circle cx="58" cy="64" r="6"/><circle cx="72" cy="64" r="6"/><circle cx="65" cy="56" r="6"/><path d="M96 70 V58 H118 V70" /><path d="M14 92 H156"/>`;
  },
  sport() {
    const [cx, cy, r] = [92, 54, 32];
    let pent = '';
    for (let i = 0; i < 5; i++) {
      const [x, y] = polar(cx, cy, 11, i * 72 - 90);
      pent += `${i ? 'L' : 'M'}${x} ${y} `;
    }
    const spokes = [0, 1, 2, 3, 4]
      .map((i) => {
        const [x1, y1] = polar(cx, cy, 11, i * 72 - 90);
        const [x2, y2] = polar(cx, cy, r, i * 72 - 90);
        return `<path d="M${x1} ${y1} L${x2} ${y2}" stroke-width="1.6"/>`;
      })
      .join('');
    return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${P}"/><path d="${pent}Z" fill="currentColor"/>${spokes}
      <path d="M24 40 h26 M18 54 h28 M24 68 h26" stroke-width="1.6"/><path d="M60 96 H124" stroke-width="1.4"/>`;
  },
  star() {
    let d = '';
    for (let i = 0; i < 10; i++) {
      const [x, y] = polar(85, 56, i % 2 ? 15 : 36, i * 36 - 90);
      d += `${i ? 'L' : 'M'}${x} ${y} `;
    }
    return `<path d="${d}Z" fill="${P}"/><path d="M134 22 v14 M127 29 h14 M36 76 v10 M31 81 h10" stroke-width="1.6"/>`;
  },
};

// Words that point to each picture. Earlier pictures win ties; the generic ones at the end count for less.
const KEYWORDS = [
  ['rifle', ['rifle', 'rifles', 'cartridge', 'cartridges', 'gun', 'guns', 'musket']],
  ['scroll', ['act', 'proclamation', 'treaty', 'constitution', 'doctrine', 'policy', 'annexed', 'promised']],
  ['sword', ['revolt', 'uprising', 'rebellion', 'rebels', 'mutiny', 'war', 'battle', 'fight', 'fought', 'attacked', 'sepoys', 'soldiers', 'army']],
  ['person', ['leader', 'leaders', 'led', 'rani', 'begum', 'saheb', 'viceroy', 'governor-general', 'reformer']],
  ['scales', ['caste', 'equality', 'equal', 'discrimination', 'rights', 'justice', 'untouchability', 'injustice']],
  ['coal', ['coal', 'mine', 'mines', 'mining', 'minerals']],
  ['ship', ['ship', 'ships', 'shipbuilding', 'shipyard', 'titanic', 'port', 'harbour', 'harbor', 'boat', 'navy', 'vessel']],
  ['steam', ['steam', 'locomotive', 'railway', 'railways', 'train']],
  ['plane', ['aerospace', 'aircraft', 'aeroplane', 'plane', 'planes', 'missile', 'missiles', 'aviation']],
  ['jobs', ['linen', 'rope', 'rope-making', 'tobacco', 'textile', 'textiles', 'cotton', 'weaving']],
  ['river', ['river', 'thames', 'lagan', 'rea', 'canal', 'lake', 'tidal', 'stream']],
  ['parliament', ['parliament', 'assembly', 'senedd', 'political', 'government', 'law', 'politics', 'council']],
  ['bank', ['bank', 'banking', 'financial', 'finance', 'money', 'commercial', 'retail', 'business', '£', 'revenue', 'tax', 'taxes', 'debt']],
  ['crown', ['capital', 'king', 'queen', 'monarchy', 'royal', 'crown', 'throne', 'emperor', 'empire']],
  ['factory', ['industry', 'industries', 'industrial', 'factory', 'factories', 'manufacturing', 'mill', 'mills']],
  ['theatre', ['theatre', 'theater', 'arts', 'cultural', 'culture', 'creative', 'media', 'entertainment', 'music', 'film']],
  ['museum', ['museum', 'museums', 'heritage', 'gallery', 'monument']],
  ['castle', ['castle', 'fort', 'medieval', 'architecture', 'georgian', 'tenements', 'palace', 'old town']],
  ['bulb', ['innovation', 'invention', 'inventions', 'invented', 'science', 'scientific', 'ideas', 'discovery', 'advances']],
  ['camera', ['tourism', 'tourist', 'tourists', 'visitors', 'travel']],
  ['book', ['education', 'university', 'school', 'schools', 'college', 'learning', 'educationist', 'newspaper', 'newspapers', 'journal', 'wrote', 'writings']],
  ['sport', ['sport', 'sports', 'sporting', 'football', 'cricket']],
  ['market', ['market', 'markets', 'shop', 'shops', 'trade', 'trading']],
  ['gear', ['engine', 'economic', 'economy', 'machine', 'machines', 'technology']],
  ['people', ['population', 'populous', 'people', 'census', 'inhabitants', 'residents', 'jobs', 'peasants']],
  ['calendar', ['century', 'founded', 'period', 'year', 'years', 'since', 'until'], 0.5],
  ['globe', ['world', 'worldwide', 'international', 'global', 'europe', 'continent'], 0.5],
  ['pin', ['situated', 'region', 'located', 'southeastern', 'midlands', 'area', 'metropolitan', 'island', 'lying'], 0.5],
  ['star', ['famous', 'preeminent', 'important', 'busiest', 'largest', 'biggest'], 0.4],
];

function words(text) {
  const out = [];
  for (const w of text.toLowerCase().match(/£|[a-z][a-z'’-]*/g) || []) {
    const base = w.replace(/['’]s$/, '');
    out.push(base);
    if (base.includes('-')) out.push(...base.split('-').filter(Boolean));
  }
  return out;
}

const DATE = /^(?:1[0-9]{3}|20[0-9]{2})$|\bcentury\b/i;

/** Picks the best-fitting picture for a fact, giving extra weight to the hidden answer. Null if nothing fits. */
export function pickSymbol(text, key = '') {
  const textWords = words(text);
  const keyWords = words(key);
  const lower = ` ${text.toLowerCase()} `;
  let best = null;
  let bestScore = 0;
  for (const [name, list, weight = 1] of KEYWORDS) {
    let score = 0;
    for (const kw of list) {
      if (kw.includes(' ')) {
        if (lower.includes(` ${kw}`)) score += 1;
        continue;
      }
      score += textWords.filter((w) => w === kw).length;
      score += 2 * keyWords.filter((w) => w === kw).length;
    }
    score *= weight;
    if (name === 'calendar' && DATE.test(key.trim())) score += 3;
    if (score > bestScore) {
      best = name;
      bestScore = score;
    }
  }
  return best;
}

/** SVG markup for one picture, or the "draw it yourself" box. */
export function svg(name, attrs = '') {
  const open = `<svg viewBox="${VIEWBOX}" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${attrs}>`;
  if (!name || !ART[name]) {
    return `${open}<rect x="30" y="16" width="110" height="78" rx="6" stroke-dasharray="5 5" stroke-width="1.6"/>
      <path d="M118 30 L130 42 L96 76 L84 78 L86 66 Z" fill="${P}" stroke-width="1.8"/><path d="M112 36 L124 48" stroke-width="1.4"/>
      <text x="62" y="62" text-anchor="middle" font-size="12" font-family="'Patrick Hand', cursive" fill="currentColor" stroke="none">draw it!</text></svg>`;
  }
  return `${open}${ART[name]()}</svg>`;
}

/** Up to four pictures together: the final "portrait" card. */
export function portraitSvg(names) {
  const list = names.filter((n) => ART[n]).slice(0, 4);
  const slots =
    list.length <= 1
      ? [[10, 6, 0.88]]
      : list.length === 2
        ? [[2, 22, 0.5], [86, 22, 0.5]]
        : [[4, 2, 0.48], [86, 2, 0.48], [4, 56, 0.48], [86, 56, 0.48]];
  const parts = list
    .map((n, i) => {
      const [x, y, s] = slots[i];
      return `<g transform="translate(${x} ${y}) scale(${s})" stroke-width="${(2.3 / s).toFixed(1)}">${ART[n]()}</g>`;
    })
    .join('');
  return `<svg viewBox="${VIEWBOX}" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${parts}</svg>`;
}
