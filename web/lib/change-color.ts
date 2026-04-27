export function getChangeColorClasses(isUp: boolean) {
  return isUp
    ? {
        text: 'text-rose-400',
        bg: 'bg-rose-500/10',
        solid: 'bg-rose-500',
      }
    : {
        text: 'text-emerald-400',
        bg: 'bg-emerald-500/10',
        solid: 'bg-emerald-500',
      };
}
