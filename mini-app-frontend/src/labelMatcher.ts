export type Label = { name: string; brand: string };
export type CatalogEntry = { name: string; brand: string | null };

const BRANDS = ['Darkside', 'Musthave', 'Blackburn', 'Burn', 'Duft', 'Element', 'Sebero', 'Spectrum', 'Satyr', 'Tangiers', 'Al Fakher', 'Adalya', 'Serbetli', 'Fumari', 'Nakhla'];
const normalize = (value: string) => value.normalize('NFKC').toLocaleLowerCase().replace(/ё/g, 'е').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
const contains = (text: string, label: string) => Boolean(label) && ` ${text} `.includes(` ${label} `);
const warning = /курени|здоров|смерт|никотин|несовершеннолет|предупреж|состав|изготов|производ|срок|годен|хранить|масса|нетто|табак|tobacco|nicotine|warning|smoking|health|ingredients|manufactur|net weight|expiry|made in|keep out|\b\d+\s*(g|gr|г|гр|kg|кг)\b|https?:|www\./iu;

/** Conservative single-package draft. Unknown lines remain suggestions, not inventory writes. */
export function matchLabel(text: string, catalog: CatalogEntry[] = []) {
  const bounded = text.slice(0, 10000);
  const normalized = normalize(bounded);
  const brands = [...new Set([...catalog.map(t => t.brand).filter((b): b is string => !!b), ...BRANDS])];
  const matches = brands.filter(b => contains(normalized, normalize(b)));
  const uniqueBrands = [...new Map(matches.map(b => [normalize(b), b])).values()];
  const brand = uniqueBrands.length === 1 ? uniqueBrands[0] : '';
  const known = catalog.filter(t => contains(normalized, normalize(t.name)) && (!t.brand || (brand && normalize(t.brand) === normalize(brand))));
  const unique = [...new Map(known.map(t => [normalize(t.name) + '|' + normalize(t.brand || ''), t])).values()];
  const candidates = [...new Set(bounded.split(/\r?\n/).map(line => line.trim()).filter(line => {
    const value = normalize(line);
    return line.length >= 2 && line.length <= 100 && /\p{L}/u.test(line) && !warning.test(line) && !brands.some(b => value === normalize(b));
  }))].slice(0, 20);
  const exact = unique.length === 1 && uniqueBrands.length <= 1 ? unique[0] : null;
  return {
    draft: { name: exact?.name || (candidates.length === 1 && uniqueBrands.length <= 1 ? candidates[0] : ''), brand: exact?.brand || brand },
    candidates,
    matched: Boolean(exact),
  };
}
