export function comparisonSelection(search, ids) {
  const params = new URLSearchParams(search);
  const left = ids.includes(params.get('left')) ? params.get('left') : ids.includes('5f6a') ? '5f6a' : ids[0];
  const requested = params.get('right');
  const right = ids.includes(requested) && requested !== left ? requested
    : ids.includes('jtm45') && left !== 'jtm45' ? 'jtm45' : ids.find((id) => id !== left);
  return { left, right, differences: params.get('differences') === '1' };
}
export function comparisonUrl({ left, right, differences }) {
  const params = new URLSearchParams({ left, right });
  if (differences) params.set('differences', '1');
  return `/compare/?${params}`;
}
export function difference(left, right) {
  if (left === null || left === undefined || right === null || right === undefined) return 'Not recorded';
  return left === right ? 'Same' : 'Different';
}
export function fieldDifference(left, right, key) {
  return difference(left.unknown?.includes(key) ? null : left.values[key], right.unknown?.includes(key) ? null : right.values[key]);
}
