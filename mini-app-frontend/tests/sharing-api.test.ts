import { afterEach, expect, it, vi } from 'vitest';
import { sharesApi } from '../src/sharing';
vi.mock('../src/telegram',()=>({tg:{initData:'private-auth'}}));
afterEach(()=>vi.unstubAllGlobals());
it('public access sends the token in the body and never attaches private auth',async()=>{
  const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({title:'Mix'})}); vi.stubGlobal('fetch',fetch);
  await sharesApi.open('x'.repeat(43),new AbortController().signal);
  const [url,options]=fetch.mock.calls[0];
  expect(url).toBe('/api/shares/open');
  expect(options.headers).toEqual({'Content-Type':'application/json'});
  expect(options.credentials).toBe('omit');
  expect(options.body).toBe(JSON.stringify({token:'x'.repeat(43)}));
  await expect(sharesApi.open('bad',new AbortController().signal)).rejects.toThrow();
  expect(fetch).toHaveBeenCalledOnce();
});
