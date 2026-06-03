'use client';

import Image from 'next/image';

const today = new Date().toLocaleDateString('ko-KR', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
});

interface HeaderProps {
  userName?: string;
}

export default function Header({ userName }: HeaderProps) {
  return (
    <header className="sticky top-0 z-[800] backdrop-blur-xl px-4 py-2 flex items-center justify-between">
      <div>
        <Image
          src="/logo.png"
          alt="Annoying Cap"
          width={102}
          height={46}
          className="object-contain h-auto"
          priority
        />
      </div>
      <div className="flex items-center gap-3">
        <span className="text-text-secondary text-xs">{today}</span>
        {userName && (
          <span className="text-accent text-xs font-medium">{userName}</span>
        )}
      </div>
    </header>
  );
}
