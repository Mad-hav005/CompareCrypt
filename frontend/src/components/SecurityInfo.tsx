import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

export const SecurityInfo: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border-t border-slate-800/60 pt-4">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="flex items-center space-x-1.5 text-xs text-slate-600 hover:text-slate-400 transition-colors group"
      >
        {isOpen ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
        <span>Security &amp; protocol details</span>
      </button>

      {isOpen && (
        <div className="mt-4 space-y-4">
          {/* Definition list */}
          <div className="space-y-2.5">
            {[
              ['Cryptographic construction', '2Hash-DH OPRF · RFC 3526 2048-bit MODP Group 14'],
              ['Similarity representation', 'Unique boundary-padded character bigrams (2-grams)'],
              ['Similarity metric', 'Sørensen-Dice coefficient: 2|S(x)∩S(y)| / (|S(x)|+|S(y)|) ≥ τ'],
              ['Security model', 'Semi-honest two-party setting'],
              ['Privacy guarantee', 'Computational (DDH assumption in QR_p)'],
              ['Leakage', 'Controlled: record/shingle cardinalities and overlap counts'],
            ].map(([key, val]) => (
              <div key={key} className="flex items-start gap-6">
                <span className="text-xs text-slate-500 w-52 shrink-0 leading-relaxed">{key}</span>
                <span className="text-xs text-slate-300 font-mono leading-relaxed">{val}</span>
              </div>
            ))}
          </div>

          {/* Security note */}
          <div className="pl-4 border-l border-slate-800/80 space-y-1">
            <p className="text-[11px] text-slate-500 leading-relaxed">
              FuzzyCrypt is a research prototype. It guarantees computational unlinkability under DDH
              in QR_p against semi-honest participants.
            </p>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              It does not claim malicious security, information-theoretic security, or formal zero-leakage.
              Non-matching records are excluded from the protocol output.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
