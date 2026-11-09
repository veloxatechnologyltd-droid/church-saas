// A church's logo, or its initials on the brand colour when it has no logo.
export default function ChurchMark({ church, size = 'h-10 w-10', className = '' }) {
  const name = church?.name || '?';
  const initials = name
    .split(/\s+/)
    .filter((word) => word && !/^(of|the|and|&)$/i.test(word))
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase();
  if (church?.logo_url) {
    return <img src={church.logo_url} alt={`${name} logo`} className={`${size} flex-shrink-0 rounded-xl bg-white object-cover ${className}`} />;
  }
  return (
    <div className={`${size} flex flex-shrink-0 items-center justify-center rounded-xl bg-brand-700 text-sm font-extrabold text-white ${className}`} aria-hidden="true">
      {initials || '?'}
    </div>
  );
}
