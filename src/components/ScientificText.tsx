import React from 'react';

const SUB_TO_ASCII: Record<string, string> = {
  '₀': '0',
  '₁': '1',
  '₂': '2',
  '₃': '3',
  '₄': '4',
  '₅': '5',
  '₆': '6',
  '₇': '7',
  '₈': '8',
  '₉': '9',
  '₊': '+',
  '₋': '-',
  '₌': '=',
  '₍': '(',
  '₎': ')',
};

const SUP_TO_ASCII: Record<string, string> = {
  '⁰': '0',
  '¹': '1',
  '²': '2',
  '³': '3',
  '⁴': '4',
  '⁵': '5',
  '⁶': '6',
  '⁷': '7',
  '⁸': '8',
  '⁹': '9',
  '⁺': '+',
  '⁻': '-',
  '⁼': '=',
  '⁽': '(',
  '⁾': ')',
  'ⁿ': 'n',
  'ⁱ': 'i',
};

/**
 * Renders scientific, chemical, and mathematical strings using semantic HTML `<sub>` and `<sup>`
 * elements for Unicode subscripts/superscripts and clean reversible arrow glyphs (`⇄`),
 * guaranteeing crisp rendering across all operating systems and headless browsers.
 */
export const ScientificText: React.FC<{ text: string; className?: string }> = ({
  text,
  className,
}) => {
  if (!text) return null;

  const tokens = text.split(/([₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎]+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ]+|⇌)/g);

  return (
    <span className={className}>
      {tokens.map((tok, i) => {
        if (!tok) return null;
        if (tok === '⇌') {
          return (
            <span key={i} className="inline-block px-0.5 font-sans" title="Reversible reaction">
              &lt;=&gt;
            </span>
          );
        }
        const first = tok[0];
        if (first in SUB_TO_ASCII) {
          const ascii = tok
            .split('')
            .map((c) => SUB_TO_ASCII[c] ?? c)
            .join('');
          return (
            <sub key={i} className="text-[0.76em] leading-none align-baseline relative -bottom-[0.18em]">
              {ascii}
            </sub>
          );
        }
        if (first in SUP_TO_ASCII) {
          const ascii = tok
            .split('')
            .map((c) => SUP_TO_ASCII[c] ?? c)
            .join('');
          return (
            <sup key={i} className="text-[0.76em] leading-none align-baseline relative -top-[0.38em]">
              {ascii}
            </sup>
          );
        }
        return <React.Fragment key={i}>{tok}</React.Fragment>;
      })}
    </span>
  );
};
