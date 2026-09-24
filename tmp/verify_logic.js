// Simulate the fixed image-resolution logic
const VEHICLE_IMAGES = {
  toyota: { camry: { path: '/image/vehicles/toyota/camry.webp' }, landcruiser: { path: '/image/vehicles/toyota/land-cruiser.webp' } },
  ford: { f150: { path: '/image/vehicles/ford/f-150.webp' } },
  tesla: {},
};
const state = { vehicle: { brand: '', model: '', year: '', market: '' } };
function catalogueKey(v) { return (v || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
function getModelLocalPhoto(brand, model) { return VEHICLE_IMAGES[catalogueKey(brand)]?.[catalogueKey(model)]?.path || null; }
function getVehicleImageUrl(brand, model, year) {
  const local = getModelLocalPhoto(brand, model);
  if (!brand) return local || '';
  if (!year && !state.vehicle.market) return local || '';
  let u = '/api/vehicles/image?make=' + encodeURIComponent(brand) + '&model=' + encodeURIComponent(model || '');
  if (year) u += '&year=' + encodeURIComponent(year);
  return u;
}

const cases = [
  ['no year, no market   : Toyota Camry        ', 'Toyota', 'Camry', '', ''],
  ['year 2021, no market : Toyota Camry        ', 'Toyota', 'Camry', '2021', ''],
  ['market GCC, no year  : Ford F-150          ', 'Ford', 'F-150', '', 'GCC'],
  ['year+market          : Toyota Land Cruiser ', 'Toyota', 'Land Cruiser', '2020', 'GCC'],
  ['no local photo       : Tesla Model 3       ', 'Tesla', 'Model 3', '', ''],
  ['year, no local       : Tesla Model 3       ', 'Tesla', 'Model 3', '2022', ''],
];
for (const [label, b, m, y, mk] of cases) {
  const local = getModelLocalPhoto(b, m);
  const primary = getVehicleImageUrl(b, m, y);
  console.log(label, '\n   local  =', local || '(none)', '\n   primary=', primary, '\n   data-local fallback ->', local ? 'shows CAR photo' : 'icon');
  console.log();
}