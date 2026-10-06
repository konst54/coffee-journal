// Pure presentation helpers; records follow the shared schema v1.
export function validateDataset(data) {
  if (data?.schema_version !== 1 || !['coffees','batches','equipment','recipes','brews'].every(k => Array.isArray(data[k]))) throw new Error('Unsupported dataset schema');
  return data;
}
const time = b => Number.isFinite(Date.parse(b.brewed_at)) ? Date.parse(b.brewed_at) : -Infinity;
export function selectBrews(data, {coffeeId, deviceId = '', sort = 'recent'} = {}) {
  const batches = new Set(data.batches.filter(b => !coffeeId || b.coffee_id === coffeeId).map(b => b.id));
  return data.brews.filter(b => batches.has(b.batch_id) && (!deviceId || b.brewer_id === deviceId)).sort((a,b) => {
    if (sort === 'rating') {
      const ar = Number.isFinite(a.rating) ? a.rating : -Infinity;
      const br = Number.isFinite(b.rating) ? b.rating : -Infinity;
      if (ar !== br) return ar > br ? -1 : 1;
    }
    if (time(a) !== time(b)) return time(a) > time(b) ? -1 : 1;
    return a.id.localeCompare(b.id);
  });
}
export const value = (v, suffix = '') => v === null || v === undefined || v === '' ? '—' : `${v}${suffix}`;
export function ratio(brew) {
  return Number.isFinite(brew.coffee_g) && brew.coffee_g > 0 && Number.isFinite(brew.water_g)
    ? `1:${Number((brew.water_g / brew.coffee_g).toFixed(2))}` : '—';
}
export function duration(seconds) {
  return Number.isFinite(seconds) && seconds >= 0 ? `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}` : '—';
}
export function brewLine(brew, device) {
  return [value(device), value(brew.temperature_c, ' °C'), value(brew.grind_setting), value(brew.coffee_g, ' г'), value(brew.water_g, ' г'), ratio(brew), duration(brew.duration_s), value(brew.rating)].join(' / ');
}
