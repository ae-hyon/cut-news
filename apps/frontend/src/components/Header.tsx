'use client';

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
    <header className="sticky top-0 z-[800] bg-bg/80 backdrop-blur-xl border-b border-border-default px-6 h-14 flex items-center justify-between">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-lg font-bold tracking-tight">
          Annoying Cap
        </h1>
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
