import { expect, it } from 'vitest';
import { matchLabel } from '../src/labelMatcher';

it('matches existing names only with the matching brand and whole words', () => {
  const catalog = [{ name: 'Mango', brand: 'Darkside' }, { name: 'Mint', brand: 'Other' }];
  expect(matchLabel('DARKSIDE\nMANGO\nMint\n100 g', catalog).draft).toEqual({ name: 'Mango', brand: 'Darkside' });
  expect(matchLabel('DARKSIDE\nMANGOES', catalog).matched).toBe(false);
});
it('does not turn warnings or weights into flavor names', () => {
  const result = matchLabel('DARKSIDE\nTOBACCO\nКУРЕНИЕ УБИВАЕТ\n100 g\nMANGO');
  expect(result.draft).toEqual({ name: 'MANGO', brand: 'Darkside' });
  expect(result.candidates).toEqual(['MANGO']);
});
it('ambiguous labels and blank images require manual selection', () => {
  expect(matchLabel('DARKSIDE\nMANGO\nMINT').draft.name).toBe('');
  expect(matchLabel('').draft).toEqual({ name: '', brand: '' });
  expect(matchLabel('DARKSIDE\nDUFT\nMANGO').draft.name).toBe('');
});
it('supports Cyrillic and bounds suggestions from untrusted OCR output', () => {
  expect(matchLabel('Бренд\nЛед', [{ name: 'Лёд', brand: 'Бренд' }]).draft.name).toBe('Лёд');
  expect(matchLabel('x'.repeat(20000)).candidates).toEqual([]);
});
