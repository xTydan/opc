const API="http://127.0.0.1:8766";
async function report(data){try{await fetch(API+"/api/collector-status",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});}catch(e){}}
async function getState(){return await chrome.storage.local.get("olxBatch");}
async function setState(s){await chrome.storage.local.set({olxBatch:s});await report({active:!!s.active,done:s.index||0,total:(s.queue||[]).length,message:s.message||"",collected:s.collected||0,last_error:s.last_error||null});}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{
 if(msg.action==="start"){(async()=>{try{const data=await(await fetch(API+"/api/queue")).json();if(!data.queue?.length)throw Error("Najpierw zaimportuj JSON ze scraperem.");const state={active:true,index:0,queue:data.queue,tabId:null,busy:false,collected:0,message:"Rozpoczynam zbieranie…"};await setState(state);const tab=await chrome.tabs.create({url:state.queue[0].url,active:false});state.tabId=tab.id;await setState(state);sendResponse({ok:true,message:"Rozpoczęto: "+data.queue.length+" wyszukiwań."});}catch(e){sendResponse({ok:false,message:e.message});}})();return true;}
 if(msg.action==="stop"){(async()=>{const {olxBatch:s}=await getState();if(s){s.active=false;s.message="Zatrzymano przez użytkownika.";await setState(s);if(s.tabId)try{await chrome.tabs.remove(s.tabId);}catch(e){}}sendResponse({ok:true,message:"Zatrzymano kolejkę."});})();return true;}
});
chrome.tabs.onUpdated.addListener((tabId,change,tab)=>{
 if(change.status!=="complete")return;
 (async()=>{const {olxBatch:s}=await getState();if(!s?.active||s.tabId!==tabId||s.busy)return;if(!tab.url?.startsWith("https://www.olx.pl/"))return;
 s.busy=true;await chrome.storage.local.set({olxBatch:s});
 try{
  await sleep(1800);
  const item=s.queue[s.index];
  const results=await chrome.scripting.executeScript({target:{tabId},func:(category)=> {
   const uniq=new Set();
   let cards=[...document.querySelectorAll('[data-cy="l-card"],[data-testid="l-card"],article')];
   const links=[...document.querySelectorAll('a[href*="/d/oferta/"]')];
   for(const a of links){let p=a;for(let i=0;i<6&&p;i++,p=p.parentElement){if(p.matches?.('[data-cy="l-card"],[data-testid="l-card"],article')){cards.push(p);break;}}}
   cards=[...new Set(cards)];
   const parsePrice=text=>{const matches=[...text.matchAll(/(\d[\d\s\u00a0]*)(?:[,.](\d{2}))?\s*(?:zł|PLN)/gi)];for(const m of matches){const n=Number(m[1].replace(/[\s\u00a0]/g,"")+(m[2]?"."+m[2]:""));if(n>0&&n<1000000)return n;}return null;};
   return cards.map(card=>{
    const a=card.querySelector('a[href*="/d/oferta/"]');if(!a)return null;
    const text=(card.innerText||card.textContent||"").trim();
    const title=(card.querySelector("h6")?.innerText||card.querySelector("h4")?.innerText||card.querySelector('[data-cy="ad-card-title"]')?.innerText||a.innerText||"").trim();
    const price=parsePrice(card.querySelector('[data-testid="ad-price"]')?.innerText||text);
    const href=a.href;
    if(!price||!href)return null;
    const url=new URL(href);url.search="";
    return {title:title||text.slice(0,180),price,url:url.href,category,status:"active",collected_at:new Date().toISOString(),source:"olx-batch-visible-result"};
   }).filter(x=>x&&!uniq.has(x.url)&&uniq.add(x.url));
  },args:[item.category]});
  const offers=results?.[0]?.result||[];
  let stored=0,serverError=null;
  if(offers.length){const response=await fetch(API+"/api/collect",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({offers})});if(!response.ok)throw Error("Serwer odrzucił zapis ofert (HTTP "+response.status+").");const saved=await response.json();stored=saved.received||0;}
  s.collected=(s.collected||0)+stored;s.index++;s.busy=false;s.message="Wyszukiwanie "+s.index+"/"+s.queue.length+": "+item.model+" — znaleziono "+offers.length+", przekazano "+stored+" ofert.";
  if(!offers.length)s.message+=" Nie wykryto kart z cenami na tej stronie.";
  if(s.index>=s.queue.length){s.active=false;s.message="Zakończono: "+s.index+" wyszukiwań. Łącznie zebrano "+s.collected+" ofert.";await setState(s);return;}
  await setState(s);setTimeout(async()=>{const {olxBatch:latest}=await getState();if(latest?.active&&latest.tabId===tabId)chrome.tabs.update(tabId,{url:latest.queue[latest.index].url});},2500);
 }catch(e){s.active=false;s.busy=false;s.last_error=e.message;s.message="Błąd przy wyszukiwaniu "+(s.index+1)+": "+e.message;await setState(s);}
 })();
});
