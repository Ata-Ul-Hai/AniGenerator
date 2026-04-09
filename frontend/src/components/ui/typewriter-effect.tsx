import React, { useEffect, useState } from "react";
import { cn } from "../../lib/utils";

interface TypewriterEffectProps {
  words: { text: string; className?: string }[];
  className?: string;
  cursorClassName?: string;
}

export const TypewriterEffect: React.FC<TypewriterEffectProps> = ({
  words,
  className,
  cursorClassName,
}) => {
  const [displayedWords, setDisplayedWords] = useState<typeof words>([]);
  const [charIdx, setCharIdx] = useState(0);
  const [wordIdx, setWordIdx] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (done) return;
    if (wordIdx >= words.length) { setDone(true); return; }
    const word = words[wordIdx];
    if (charIdx <= word.text.length) {
      const t = setTimeout(() => setCharIdx(charIdx + 1), 80);
      return () => clearTimeout(t);
    } else {
      setDisplayedWords((prev) => [...prev, word]);
      setWordIdx(wordIdx + 1);
      setCharIdx(0);
    }
  }, [charIdx, wordIdx, words, done]);

  const currentWord = wordIdx < words.length ? words[wordIdx] : null;

  return (
    <span className={cn("inline", className)}>
      {displayedWords.map((w, i) => (
        <span key={i} className={cn("mr-2", w.className)}>{w.text}</span>
      ))}
      {currentWord && (
        <span className={currentWord.className}>
          {currentWord.text.slice(0, charIdx)}
        </span>
      )}
      {!done && (
        <span className={cn("inline-block w-[2px] h-[1em] bg-zinc-200 ml-0.5 animate-pulse align-middle", cursorClassName)} />
      )}
    </span>
  );
};
