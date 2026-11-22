const API="http://127.0.0.1:8766";
async function report(data){try{await fetch(API+"/api/collector-status",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});}catch(e){}}
async function getState(){return await chrome.storage.local.get("olxBatch");}
async function setState(s){await chrome.storage.local.set({olxBatch:s});await report({active:!!s.active,done:s.index||0,total:(s.queue||[]).length,message:s.message||""});}
chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{
 if(msg.action==="start"){(async()=>{try{const data=await(await fetch(API+"/api/queue")).json();if(!data.queue?.length)throw Error("Najpierw zaimportuj JSON ze scraperem.");const state={active:true,index:0,queue:data.queue,tabId:null,busy:false,message:"Rozpoczynam zbieranie…"};await setState(state);const tab=await chrome.tabs.create({url:state.queue[0].url,active:false});state.tabId=tab.id;await setState(state);sendResponse({ok:true,message:"Rozpoczęto: "+data.queue.length+" wyszukiwań."});}catch(e){sendResponse({ok:false,message:e.message});}})();return true;}
 if(msg.action==="stop"){(async()=>{const {olxBatch:s}=await getState();if(s){s.active=false;s.message="Zatrzymano przez użytkownika.";await setState(s);if(s.tabId)try{await chrome.tabs.remove(s.tabId);}catch(e){}}sendResponse({ok:true,message:"Zatrzymano kolejkę."});})();return true;}
});
chrome.tabs.onUpdated.addListener((tabId,change,tab)=>{
 if(change.status!=="complete")return;
 (async()=>{const {olxBatch:s}=await getState();if(!s?.active||s.tabId!==tabId||s.busy)return;if(!tab.url?.startsWith("https://www.olx.pl/"))return;
 s.busy=true;await chrome.storage.local.set({olxBatch:s});
 try{
  const item=s.queue[s.index];
  const [{result:offers}]=await chrome.scripting.executeScript({target:{tabId},func:(category)=>{const cards=[...document.querySelectorAll('[data-cy="l-card"]')];return cards.map(card=>{const a=card.querySelector('a[href*="/d/oferta/"]');const title=card.querySelector("h6")?.innerText||card.querySelector('[data-cy="ad-card-title"]')?.innerText||a?.innerText||"";const priceText=card.querySelector('[data-testid="ad-price"]')?.innerText||card.innerText.match(/[\d\s]+\s*zł/i)?.[0]||"";const price=Number(priceText.replace(/[^\d]/g,""));return{title:title.trim(),price,url:a?.href?.split("?")[0],category,status:"active",collected_at:new Date().toISOString(),source:"olx-batch-visible-result"};}).filter(x=>x.url&&x.price>0);},args:[item.category]});
  if(offers?.length)await fetch(API+"/api/collect",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({offers})});
  s.index++;s.busy=false;s.message="Zebrano "+(offers?.length||0)+" ofert dla "+item.model+".";
  if(s.index>=s.queue.length){s.active=false;s.message="Zakończono: "+s.index+" wyszukiwań. Zebrane oferty zapisano.";await setState(s);return;}
  await setState(s);setTimeout(async()=>{const {olxBatch:latest}=await getState();if(latest?.active&&latest.tabId===tabId)chrome.tabs.update(tabId,{url:latest.queue[latest.index].url});},2200);
 }catch(e){s.active=false;s.busy=false;s.message="Przerwano przy "+(s.index+1)+". wyszukiwaniu: "+e.message;await setState(s);}
 })();
});
